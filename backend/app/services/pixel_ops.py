"""Chantier 9b — ops 2D locales : pixel-art ("pixel") et raccord de tuile
("tile-preview") pour /api/images/process.

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

__all__ = ["PALETTES", "normalize_pixel_opts", "pixelate", "tile_preview"]


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


# ── op "tile-preview" ────────────────────────────────────────────────────────
def tile_preview(img: Image.Image, grid: int = 2):
    """(composite grid×grid, score de raccord 0-100 ; 0 = tuile parfaite).
    Score = moyenne des diffs absolues entre bords opposés de l'image SOURCE
    (pleine résolution) gauche/droite et haut/bas, normalisée sur 255.
    Le composite d'aperçu plafonne la tuile à 512 px de côté."""
    rgb = img.convert("RGB")
    w, h = rgb.size

    def _mean_abs(a, b):
        d = ImageStat.Stat(ImageChops.difference(a, b)).mean
        return sum(d) / len(d)

    seam_v = _mean_abs(rgb.crop((0, 0, 1, h)), rgb.crop((w - 1, 0, w, h)))
    seam_h = _mean_abs(rgb.crop((0, 0, w, 1)), rgb.crop((0, h - 1, w, h)))
    score = round((seam_v + seam_h) / 2 / 255 * 100, 2)

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
