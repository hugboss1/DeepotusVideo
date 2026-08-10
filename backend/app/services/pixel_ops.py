"""Chantiers 9b/9e — ops 2D locales pour /api/images/process : pixel-art
("pixel"), raccord de tuile ("tile-preview"), tuile seamless ("seamless",
offset 50/50 fondu ou miroir 2×2) et clé chroma (détourage fond uni du
Sprite Lab).

Pur PIL (le runtime embarqué n'a pas numpy). Zéro réseau, zéro settings :
sprite_service importe `pixelate` directement (par frame, sans HTTP) et la
route l'utilise pour les images de la Library.

Pipeline pixel : downscale LANCZOS (côté long = target_px) -> quantize
(palette preset ou adaptative MEDIANCUT) -> alpha binaire -> upscale NEAREST.
Le dither "ordered" est un Bayer 4x4 appliqué en biais RGB avant remap
(PIL ne propose en natif que none/Floyd-Steinberg).
"""
from __future__ import annotations

from PIL import Image, ImageChops, ImageStat

__all__ = ["PALETTES", "normalize_pixel_opts", "pixelate", "tile_preview",
           "seam_score", "normalize_seamless_opts", "make_seamless",
           "chroma_key"]


def _hex(s: str) -> tuple[int, int, int]:
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _pal(*hexes: str) -> tuple[tuple[int, int, int], ...]:
    return tuple(dict.fromkeys(_hex(h) for h in hexes))


# Presets figés (golden tests) : PICO-8, Game Boy (DMG), NES 2C02 (dédupliquée,
# 55 couleurs), Sweetie 16 (Lospec/GrafxKid), 1-bit.
PALETTES: dict[str, tuple[tuple[int, int, int], ...]] = {
    "pico8": _pal("000000", "1D2B53", "7E2553", "008751", "AB5236", "5F574F",
                  "C2C3C7", "FFF1E8", "FF004D", "FFA300", "FFEC27", "00E436",
                  "29ADFF", "83769C", "FF77A8", "FFCCAA"),
    "gameboy": _pal("0F380F", "306230", "8BAC0F", "9BBC0F"),
    "nes": _pal("7C7C7C", "0000FC", "0000BC", "4428BC", "940084", "A80020",
                "A81000", "881400", "503000", "007800", "006800", "005800",
                "004058", "000000",
                "BCBCBC", "0078F8", "0058F8", "6844FC", "D800CC", "E40058",
                "F83800", "E45C10", "AC7C00", "00B800", "00A800", "00A844",
                "008888",
                "F8F8F8", "3CBCFC", "6888FC", "9878F8", "F878F8", "F85898",
                "F87858", "FCA044", "F8B800", "B8F818", "58D854", "58F898",
                "00E8D8", "787878",
                "FCFCFC", "A4E4FC", "B8B8F8", "D8B8F8", "F8B8F8", "F8A4C0",
                "F0D0B0", "FCE0A8", "F8D878", "D8F878", "B8F8B8", "B8F8D8",
                "00FCFC", "F8D8F8"),
    "sweetie16": _pal("1A1C2C", "5D275D", "B13E53", "EF7D57", "FFCD75",
                      "A7F070", "38B764", "257179", "29366F", "3B5DC9",
                      "41A6F6", "73EFF7", "F4F4F4", "94B0C2", "566C86",
                      "333C57"),
    "onebit": _pal("000000", "FFFFFF"),
}


# ── normalisation ────────────────────────────────────────────────────────────
def normalize_pixel_opts(spec: dict) -> dict:
    """Valide/normalise l'op pixel. ValueError lisible sinon (la route la
    transforme en 400). `colors` (adaptatif) et `palette` (preset) sont
    exclusifs ; sans les deux -> adaptatif 16 couleurs."""
    if not isinstance(spec, dict):
        raise ValueError("pixel must be an object "
                         "{target_px, colors|palette, dither, scale}")

    def _int(name, default, lo, hi):
        raw = spec.get(name)
        if raw is None or raw == "":
            return default
        try:
            v = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer ({lo}-{hi})")
        if not lo <= v <= hi:
            raise ValueError(f"{name} must be between {lo} and {hi}")
        return v

    target = _int("target_px", 64, 8, 512)
    scale = _int("scale", 1, 1, 16)

    palette = spec.get("palette")
    colors = None
    if palette not in (None, ""):
        palette = str(palette).lower()
        if palette not in PALETTES:
            raise ValueError(
                f"palette must be one of: {', '.join(sorted(PALETTES))}")
        if spec.get("colors") not in (None, ""):
            raise ValueError("colors and palette are exclusive — "
                             "give one or the other")
    else:
        palette = None
        colors = _int("colors", 16, 2, 256)

    dither = str(spec.get("dither") or "none").lower()
    if dither not in ("none", "ordered", "floyd"):
        raise ValueError("dither must be one of: none, ordered, floyd")

    return {"target_px": target, "colors": colors, "palette": palette,
            "dither": dither, "scale": scale}


# ── dither ordonné (Bayer 4x4, sans numpy) ───────────────────────────────────
_BAYER4 = (0, 8, 2, 10,
           12, 4, 14, 6,
           3, 11, 1, 9,
           15, 7, 13, 5)


def _bayer_bias(w: int, h: int, spread: int) -> Image.Image:
    """Image L (w,h) = 128 + offset Bayer, offset dans [-spread/2, spread/2).
    Ajoutée à chaque canal via ImageChops.add(offset=-128) avant remap."""
    rows = []
    for by in range(4):
        rows.append(bytes(
            128 + int((( _BAYER4[by * 4 + (x % 4)] + 0.5) / 16.0 - 0.5)
                      * spread)
            for x in range(w)))
    return Image.frombytes("L", (w, h), b"".join(rows[y % 4]
                                                 for y in range(h)))


def _palette_image(pal) -> Image.Image:
    """Image P dont les 256 entrées CYCLENT la palette : le padding à zéro de
    putpalette introduirait un noir parasite pour les presets sans noir."""
    flat = []
    for i in range(256):
        flat.extend(pal[i % len(pal)])
    p = Image.new("P", (1, 1))
    p.putpalette(flat)
    return p


def _quantize_rgb(rgb: Image.Image, opts: dict) -> Image.Image:
    """RGB -> P : palette preset ou adaptative (MEDIANCUT sur l'image NON
    biaisée, puis remap — le biais ordered ne doit pas polluer la palette)."""
    if opts["palette"]:
        pal = PALETTES[opts["palette"]]
        target, n = _palette_image(pal), len(pal)
    else:
        n = opts["colors"]
        target = rgb.quantize(colors=n, method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE)
    if opts["dither"] == "ordered":
        spread = max(24, min(128, 256 // max(2, n)))
        bias = _bayer_bias(rgb.width, rgb.height, spread)
        rgb = Image.merge("RGB", tuple(
            ImageChops.add(ch, bias, offset=-128) for ch in rgb.split()))
    dither = (Image.Dither.FLOYDSTEINBERG if opts["dither"] == "floyd"
              else Image.Dither.NONE)
    return rgb.quantize(palette=target, dither=dither)


# ── op "pixel" ───────────────────────────────────────────────────────────────
def pixelate(img: Image.Image, opts: dict) -> Image.Image:
    """Image (tout mode) -> pixel-art RGBA. `opts` vient de
    normalize_pixel_opts. Alpha binaire (seuil 128) pour des bords nets."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    t = opts["target_px"]
    if w >= h:
        gw, gh = t, max(1, round(h * t / w))
    else:
        gw, gh = max(1, round(w * t / h)), t
    small = rgba.resize((gw, gh), Image.LANCZOS)

    alpha = small.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    out = _quantize_rgb(small.convert("RGB"), opts).convert("RGBA")
    out.putalpha(alpha)

    s = opts["scale"]
    if s > 1:
        out = out.resize((gw * s, gh * s), Image.NEAREST)
    return out


# ── métrique de raccord (9b, publique depuis 9e) ─────────────────────────────
def seam_score(img: Image.Image) -> float:
    """Score de raccord 0-100 (0 = tuile parfaite) : moyenne des diffs
    absolues entre bords opposés (gauche/droite, haut/bas), normalisée 255."""
    rgb = img.convert("RGB")
    w, h = rgb.size

    def _mean_abs(a, b):
        d = ImageStat.Stat(ImageChops.difference(a, b)).mean
        return sum(d) / len(d)

    seam_v = _mean_abs(rgb.crop((0, 0, 1, h)), rgb.crop((w - 1, 0, w, h)))
    seam_h = _mean_abs(rgb.crop((0, 0, w, 1)), rgb.crop((0, h - 1, w, h)))
    return round((seam_v + seam_h) / 2 / 255 * 100, 2)


# ── op "tile-preview" ────────────────────────────────────────────────────────
def tile_preview(img: Image.Image, grid: int = 2):
    """(composite grid×grid, score de raccord 0-100 ; 0 = tuile parfaite).
    Le composite d'aperçu plafonne la tuile à 512 px de côté."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    score = seam_score(rgb)

    tile = rgb
    if max(w, h) > 512:
        k = 512 / max(w, h)
        tile = rgb.resize((max(1, round(w * k)), max(1, round(h * k))),
                          Image.LANCZOS)
    comp = Image.new("RGB", (tile.width * grid, tile.height * grid))
    for gy in range(grid):
        for gx in range(grid):
            comp.paste(tile, (gx * tile.width, gy * tile.height))
    return comp, score


# ── op "seamless" (9e) ───────────────────────────────────────────────────────
def normalize_seamless_opts(spec: dict) -> dict:
    """Valide/normalise l'op seamless. ValueError lisible sinon (400 côté
    route). target_px 0 = garder la taille source."""
    if not isinstance(spec, dict):
        raise ValueError("seamless must be an object "
                         "{method, blend, target_px, square}")
    method = str(spec.get("method") or "offset").lower()
    if method not in ("offset", "mirror"):
        raise ValueError("method must be 'offset' or 'mirror'")

    def _int(name, default, lo, hi):
        raw = spec.get(name)
        if raw is None or raw == "":
            return default
        try:
            v = int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer ({lo}-{hi})")
        return v

    blend = _int("blend", 20, 5, 45)
    if not 5 <= blend <= 45:
        raise ValueError("blend must be between 5 and 45 (%)")
    target = _int("target_px", 0, 64, 1024)
    if target != 0 and not 64 <= target <= 1024:
        raise ValueError("target_px must be 0 (source) or between 64 and 1024")
    sq = spec.get("square")
    square = True if sq is None else bool(sq)
    return {"method": method, "blend": blend, "target_px": target,
            "square": square}


def _cross_mask(w: int, h: int, band: int) -> Image.Image:
    """Masque L : tente à 255 sur les lignes x=w/2 et y=h/2, fondue à 0 à
    `band` px de part et d'autre — le fondu de la croix du décalage 50/50.

    Le masque est en plus ramené à 0 sur les `band/3` px du POURTOUR. Sans
    cela la croix reste à 255 jusqu'aux bords le long de sa bande centrale :
    le composite y reprend l'original et **réinjecte la couture d'origine**
    sur `blend` % de la hauteur (mesuré : rampe 512², avant 50.0, après 9.97
    = 20 % × 50). Avec l'atténuation, tout le pourtour vient du décalé, qui
    lui est continu."""
    def _tent(n, c):
        return bytes(max(0, min(255, round(255 * (1 - abs(i - c) / band))))
                     for i in range(n))

    edge = max(2, band // 3)

    def _edge(n):
        return bytes(max(0, min(255, round(255 * min(i, n - 1 - i) / edge)))
                     for i in range(n))

    v = Image.frombytes("L", (w, 1), _tent(w, w // 2)) \
             .resize((w, h), Image.NEAREST)
    hz = Image.frombytes("L", (1, h), _tent(h, h // 2)) \
             .resize((w, h), Image.NEAREST)
    cross = ImageChops.lighter(v, hz)
    ex = Image.frombytes("L", (w, 1), _edge(w)).resize((w, h), Image.NEAREST)
    ey = Image.frombytes("L", (1, h), _edge(h)).resize((w, h), Image.NEAREST)
    return ImageChops.multiply(cross, ImageChops.darker(ex, ey))


def _close_loop(img: Image.Image) -> Image.Image:
    """Ferme la boucle : la dernière colonne devient EXACTEMENT la première
    (idem dernière ligne / première ligne), par un fondu court vers la copie
    décalée d'un pixel.

    Le décalage 50/50 laisse en bord deux colonnes ADJACENTES de la source
    (x=w/2 et x=w/2-1) : proches mais pas égales, d'où un raccord résiduel de
    2 à 5 (mesuré sur 14 images de la Library). Fondre sur `w/96` px vers
    `offset(img, w-1, 0)` — c'est-à-dire l'image décalée d'un seul pixel —
    rend le raccord exactement nul pour un flou local d'un pixel, invisible.
    """
    w, h = img.size
    if w < 8 or h < 8:
        return img

    def _ramp(n: int, band: int) -> bytes:
        start = n - 1 - band
        return bytes(0 if i <= start
                     else min(255, round(255 * (i - start) / band))
                     for i in range(n))

    bw, bh = max(2, w // 96), max(2, h // 96)
    mx = Image.frombytes("L", (w, 1), _ramp(w, bw)).resize((w, h), Image.NEAREST)
    out = Image.composite(ImageChops.offset(img, w - 1, 0), img, mx)
    my = Image.frombytes("L", (1, h), _ramp(h, bh)).resize((w, h), Image.NEAREST)
    return Image.composite(ImageChops.offset(out, 0, h - 1), out, my)


def make_seamless(img: Image.Image, opts: dict) -> Image.Image:
    """Tuile raccordable. `opts` vient de normalize_seamless_opts.
    - offset : décalage 50/50 (les bords opposés deviennent des colonnes/
      lignes adjacentes de la source) + fondu de la croix avec l'original
      (bande `blend` % du petit côté, masque nul sur le pourtour) puis
      fermeture de boucle : le raccord tombe à 0.00 (mesuré).
    - mirror : mosaïque 2×2 de quadrants en miroir — raccord exactement nul,
      rendu kaléidoscope (résolution des quadrants divisée par deux)."""
    rgba = img.convert("RGBA")
    if opts["square"]:
        s = min(rgba.size)
        w, h = rgba.size
        x0, y0 = (w - s) // 2, (h - s) // 2
        rgba = rgba.crop((x0, y0, x0 + s, y0 + s))
    if opts["target_px"]:
        t = opts["target_px"]
        w, h = rgba.size
        if w >= h:
            nw, nh = t, max(1, round(h * t / w))
        else:
            nw, nh = max(1, round(w * t / h)), t
        rgba = rgba.resize((nw, nh), Image.LANCZOS)
    w, h = rgba.size                     # dimensions paires (miroir, 50/50)
    if w % 2 or h % 2:
        rgba = rgba.crop((0, 0, max(2, w - w % 2), max(2, h - h % 2)))
        w, h = rgba.size

    if opts["method"] == "mirror":
        half = rgba.resize((w // 2, h // 2), Image.LANCZOS)
        out = Image.new("RGBA", (w, h))
        out.paste(half, (0, 0))
        out.paste(half.transpose(Image.FLIP_LEFT_RIGHT), (w // 2, 0))
        out.paste(half.transpose(Image.FLIP_TOP_BOTTOM), (0, h // 2))
        out.paste(half.transpose(Image.ROTATE_180), (w // 2, h // 2))
        return out

    rolled = ImageChops.offset(rgba, w // 2, h // 2)
    band = max(2, round(min(w, h) * opts["blend"] / 100))
    return _close_loop(Image.composite(rgba, rolled, _cross_mask(w, h, band)))


# ── clé chroma (9e — détourage fond uni du Sprite Lab) ───────────────────────
def chroma_key(img: Image.Image, tolerance: int = 28, feather: float = 1.6):
    """(image RGBA, ok). Clé = couleur médiane du POURTOUR ; alpha 0 sous
    `tolerance` (distance L de la diff), rampe linéaire jusqu'à
    tolerance×feather. Garde-fous (ok=False, image d'origine conservée) :
    pourtour pas assez uni (<60 % des échantillons proches de la clé) ou
    couverture opaque hors [5 %, 95 %] — l'appelant marque la frame
    `bg_failed` comme pour les échecs rembg (philosophie 9a)."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    rgb = rgba.convert("RGB")
    px = rgb.load()
    step = max(1, (w + h) // 128)
    samples = []
    for x in range(0, w, step):
        samples.append(px[x, 0])
        samples.append(px[x, h - 1])
    for y in range(0, h, step):
        samples.append(px[0, y])
        samples.append(px[w - 1, y])
    rs = sorted(s[0] for s in samples)
    gs = sorted(s[1] for s in samples)
    bs = sorted(s[2] for s in samples)
    key = (rs[len(rs) // 2], gs[len(gs) // 2], bs[len(bs) // 2])
    near = sum(1 for s in samples
               if abs(s[0] - key[0]) + abs(s[1] - key[1])
               + abs(s[2] - key[2]) <= 3 * tolerance)
    if near / len(samples) < 0.6:
        return rgba, False

    lo = int(tolerance)
    hi = max(lo + 1, int(round(tolerance * feather)))
    diff = ImageChops.difference(rgb, Image.new("RGB", (w, h), key)) \
                     .convert("L")
    lut = [0 if v <= lo else 255 if v >= hi
           else int((v - lo) * 255 / (hi - lo)) for v in range(256)]
    alpha = ImageChops.darker(rgba.getchannel("A"), diff.point(lut))
    hist = alpha.histogram()
    coverage = sum(hist[128:]) / float(w * h)
    if not 0.05 <= coverage <= 0.95:
        return rgba, False
    out = rgba.copy()
    out.putalpha(alpha)
    return out, True
