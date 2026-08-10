# -*- coding: utf-8 -*-
"""Aperçus d'effets — une image fixe rendue AVEC l'effet, pour le rack VFX.

Le panneau Effets choisissait jusqu'ici un effet sur son NOM : « Halation »,
« Prisme », « Tramage » ne disent rien tant qu'on ne les a pas appliqués à un
clip et relancé un rendu. Ce module rend la vignette : une seule image, passée
par la MÊME chaîne ffmpeg que le rendu final (``effects_engine.build_chain``),
donc ce que la vignette montre est ce que le rendu produira.

  GET /api/effects/catalog   catalogue + catégories + bornes des paramètres
  GET /api/effects/preview   une image JPEG avec l'effet appliqué

Source de l'aperçu, dans l'ordre de préférence :
  - ``image:<nom>``  une image de la Bibliothèque (basename + confinement)
  - ``job:<id>``     une frame du rendu de ce job, prise à l'instant demandé
  - rien             la MIRE intégrée, dessinée en PIL pur (pas d'asset à
                     livrer) : dégradé de ciel, soleil (bloom/halation),
                     silhouettes (contours), grille au sol (distorsion),
                     mire de couleurs (étalonnage), damier fin (pixel/tramage).

Cache disque : la même combinaison (effet + paramètres + source + instant +
largeur) ne relance jamais ffmpeg. La clé porte aussi la taille et la date de
la source, donc remplacer une image de la Bibliothèque invalide ses vignettes.

Sécurité : le type d'effet doit exister dans ``effects_engine.EFFECTS``, le nom
de fichier est réduit au basename, son extension est en liste blanche et le
chemin résolu doit être DANS le dossier images (même garde-fou que
``_lut_path``). Aucun chemin venant du client n'atteint ffmpeg autrement.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import threading
from pathlib import Path

from app.config import settings

#: Extensions acceptées pour une source « image de la Bibliothèque ».
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

#: Taille de rendu de la vignette (largeur), bornée.
W_MIN, W_MAX, W_DEFAULT = 96, 640, 320

#: Instant du rendu, en secondes : les effets animés (VHS, secousse,
#: ondulation, braises) sont figés à cet instant. 0 les montrerait à leur
#: image de départ, souvent identique à la source.
T_MIN, T_MAX, T_DEFAULT = 0.0, 30.0, 0.6

_MIRE_W, _MIRE_H = 960, 540


def ffmpeg_bin() -> str:
    """ffmpeg du PATH, sinon celui embarqué par l'app."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import os
    cand = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    return cand if os.path.isfile(cand) else "ffmpeg"


def cache_dir() -> Path:
    p = settings.outputs_path / "fxpreview"
    p.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------- la mire ---
def _lerp(a, b, u):
    return tuple(int(round(a[i] + (b[i] - a[i]) * u)) for i in range(3))


def build_mire(dest: Path) -> Path:
    """Dessine la mire intégrée en PIL pur (aucun numpy, aucun asset livré).

    Elle est conçue POUR juger un effet : chaque zone révèle une famille.
    Un aplat uni ne montrerait ni le grain, ni le tramage, ni la distorsion.
    """
    from PIL import Image, ImageDraw, ImageFilter

    w, h = _MIRE_W, _MIRE_H
    im = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(im)

    # Ciel : bleu nuit -> orange d'horizon (dégradés = étalonnage, banding)
    sky_top, sky_mid, horizon = (14, 22, 58), (52, 64, 130), (232, 140, 58)
    hz = int(h * 0.58)
    for y in range(hz):
        u = y / max(1, hz - 1)
        col = _lerp(sky_top, sky_mid, u / 0.65) if u < 0.65 else _lerp(sky_mid, horizon, (u - 0.65) / 0.35)
        d.line([(0, y), (w, y)], fill=col)
    # Sol : brun sombre, dégradé vers le bas
    for y in range(hz, h):
        u = (y - hz) / max(1, h - hz - 1)
        d.line([(0, y), (w, y)], fill=_lerp((78, 44, 30), (16, 12, 14), u))

    # Soleil : disque quasi blanc + halo (révèle bloom, halation, fuite)
    sx, sy, sr = int(w * 0.70), int(h * 0.30), int(h * 0.085)
    halo = Image.new("RGB", (w, h), (0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([sx - sr * 3, sy - sr * 3, sx + sr * 3, sy + sr * 3], fill=(150, 96, 40))
    halo = halo.filter(ImageFilter.GaussianBlur(sr))
    from PIL import ImageChops
    im = ImageChops.add(im, halo)
    d = ImageDraw.Draw(im)
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 250, 232))

    # Grille au sol en perspective (distorsion d'objectif, tourbillon, vague)
    grid = (255, 255, 255)
    for k in range(-8, 9):
        x_far = int(w * 0.5 + k * w * 0.035)
        x_near = int(w * 0.5 + k * w * 0.17)
        d.line([(x_far, hz), (x_near, h)], fill=(120, 96, 86), width=1)
    yy = hz
    step = 4.0
    while yy < h:
        d.line([(0, int(yy)), (w, int(yy))], fill=(120, 96, 86), width=1)
        step *= 1.45
        yy += step

    # Silhouettes (contours nets -> bord lumineux, netteté, flou)
    d.polygon([(0, hz), (int(w * 0.16), int(h * 0.30)), (int(w * 0.30), hz)], fill=(10, 10, 16))
    d.polygon([(int(w * 0.22), hz), (int(w * 0.40), int(h * 0.38)), (int(w * 0.56), hz)], fill=(16, 14, 24))
    # « Poulpe » stylisé : disque + tentacules, des courbes franches
    ox, oy = int(w * 0.30), int(h * 0.72)
    d.ellipse([ox - 46, oy - 58, ox + 46, oy + 30], fill=(232, 74, 132))
    d.ellipse([ox - 24, oy - 30, ox - 8, oy - 14], fill=(255, 255, 255))
    d.ellipse([ox + 8, oy - 30, ox + 24, oy - 14], fill=(255, 255, 255))
    d.ellipse([ox - 20, oy - 26, ox - 12, oy - 18], fill=(20, 10, 20))
    d.ellipse([ox + 12, oy - 26, ox + 20, oy - 18], fill=(20, 10, 20))
    for k in range(5):
        bx = ox - 40 + k * 20
        for s in range(14):
            t = s / 13.0
            px = int(bx + 12 * math.sin(t * 3.1 + k))
            py = int(oy + 24 + t * 52)
            d.ellipse([px - 7 + int(3 * t), py - 6, px + 7 - int(3 * t), py + 6],
                      fill=(200, 56, 112))

    # Mire de couleurs (étalonnage, colorisation, négatif, postérisation)
    swatch = [(220, 32, 32), (240, 150, 24), (240, 226, 40), (52, 200, 90),
              (36, 190, 226), (48, 84, 226), (150, 60, 220), (240, 240, 240)]
    bw, bh = 54, 40
    x0, y0 = 22, h - bh - 22
    for i, c in enumerate(swatch):
        d.rectangle([x0 + i * bw, y0, x0 + (i + 1) * bw - 3, y0 + bh], fill=c)

    # Rampe de gris (banding, postérisation, tramage, contraste)
    rx, ry, rw, rh = 22, h - bh - 62, len(swatch) * bw - 3, 26
    for i in range(rw):
        v = int(255 * i / max(1, rw - 1))
        d.line([(rx + i, ry), (rx + i, ry + rh)], fill=(v, v, v))

    # Damier fin (pixelisation, tramage, netteté, flou)
    cx, cy, cs, cn = w - 22 - 8 * 16, h - 22 - 8 * 16, 8, 16
    for a in range(cn):
        for b in range(cn):
            if (a + b) % 2 == 0:
                d.rectangle([cx + a * cs, cy + b * cs, cx + (a + 1) * cs - 1,
                             cy + (b + 1) * cs - 1], fill=(255, 255, 255))
            else:
                d.rectangle([cx + a * cs, cy + b * cs, cx + (a + 1) * cs - 1,
                             cy + (b + 1) * cs - 1], fill=(24, 24, 28))

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "PNG")
    return dest


def mire_path() -> Path:
    p = cache_dir() / f"mire_{_MIRE_W}x{_MIRE_H}.png"
    if not p.is_file():
        build_mire(p)
    return p


# ------------------------------------------------------ paramètres reçus ---
def coerce_params(effect_type: str, raw: dict) -> dict:
    """Ne garde que les paramètres DÉCLARÉS par le catalogue pour ce type, et
    ramène chacun dans ses bornes.

    Rien d'autre ne franchit cette porte : les valeurs finissent dans un
    ``-filter_complex``, où une chaîne libre injecterait des filtres.
    """
    from app.services import effects_engine as fx

    spec = (fx.catalog().get(effect_type) or {})
    out = {}
    for name in spec.get("params") or []:
        if name not in raw or raw[name] in (None, ""):
            continue
        b = spec["bounds"][name]
        v = raw[name]
        kind = b.get("type")
        if kind == "range":
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if v != v:
                continue
            v = max(float(b["min"]), min(float(b["max"]), v))
            out[name] = int(v) if float(b.get("step", 1)) >= 1 else v
        elif kind == "color":
            s = str(v).strip().lstrip("#").lower()
            if len(s) in (3, 6) and all(c in "0123456789abcdef" for c in s):
                out[name] = "#" + s
        elif kind == "choice":
            if str(v) in [str(c) for c in (b.get("choices") or [])]:
                out[name] = str(v)
        elif kind == "lut":
            # même garde-fou que le rendu : basename, .cube, présent dans le
            # dossier LUT. Un nom refusé est simplement ignoré.
            if fx._lut_path(str(v)) is not None:
                out[name] = Path(str(v)).name
    return out


# ----------------------------------------------------------- les sources ---
def library_image(name: str) -> Path:
    """Chemin d'une image de la Bibliothèque, ou ValueError.

    Réduction au basename + extension en liste blanche + confinement vérifié
    APRÈS résolution (un lien symbolique pointant hors du dossier est refusé) —
    c'est le garde-fou de ``_lut_path`` appliqué aux images.
    """
    raw = str(name or "")
    safe = Path(raw).name
    if not safe or safe != raw:
        raise ValueError("nom d'image invalide")
    if not safe.lower().endswith(IMAGE_EXTS):
        raise ValueError("extension d'image non autorisée")
    root = settings.images_path.resolve()
    p = (root / safe).resolve()
    if p.parent != root or not p.is_file():
        raise ValueError("image introuvable dans la Bibliothèque")
    return p


def _job_slug(job_id: str) -> str:
    s = "".join(c for c in str(job_id or "") if c.isalnum() or c in "-_")
    if not s:
        raise ValueError("identifiant de rendu invalide")
    return s[:64]


#: Un panneau ouvert lance ~20 aperçus EN MÊME TEMPS sur le même plan et le
#: même instant : sans verrou, vingt ffmpeg écrivaient le même fichier
#: temporaire, se marchaient dessus et la moitié des vignettes finissait en
#: 500 (le front bascule alors sur ses images génériques pour toute la
#: session). Un verrou par fichier de destination : le premier extrait,
#: les autres attendent et lisent le cache.
_FRAME_LOCKS: dict[str, threading.Lock] = {}
_FRAME_LOCKS_GUARD = threading.Lock()


def _frame_lock(key: str) -> threading.Lock:
    with _FRAME_LOCKS_GUARD:
        lk = _FRAME_LOCKS.get(key)
        if lk is None:
            lk = _FRAME_LOCKS[key] = threading.Lock()
        return lk


def _extract_frame(video: Path, t: float, dst: Path) -> Path:
    """Une seule extraction ffmpeg, fichier temporaire propre à cet appel."""
    tmp = dst.with_name(f"{dst.stem}.{os.getpid()}-{threading.get_ident()}.tmp.png")
    try:
        r = subprocess.run(
            [ffmpeg_bin(), "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
             "-frames:v", "1", "-update", "1", str(tmp)],
            capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not tmp.is_file() or not tmp.stat().st_size:
            # t au-delà de la fin du clip : on retombe sur la première image
            r = subprocess.run(
                [ffmpeg_bin(), "-y", "-v", "error", "-i", str(video),
                 "-frames:v", "1", "-update", "1", str(tmp)],
                capture_output=True, text=True, timeout=120)
            if r.returncode != 0 or not tmp.is_file() or not tmp.stat().st_size:
                raise RuntimeError("extraction de l'image impossible")
        tmp.replace(dst)
    finally:
        tmp.unlink(missing_ok=True)
    return dst


def video_frame(video: Path, t: float, slug: str) -> Path:
    """Extrait (et met en cache) l'image d'un rendu à l'instant t."""
    dst = cache_dir() / f"frame_{slug}_{t:.2f}.png"
    if dst.is_file() and dst.stat().st_size:
        return dst
    with _frame_lock(dst.name):
        if dst.is_file() and dst.stat().st_size:   # un autre fil l'a extraite
            return dst
        return _extract_frame(Path(video), t, dst)


def source_still(source: str | None, t: float, job_video: Path | None = None):
    """(image fixe de départ, signature de cache) pour la source demandée."""
    s = str(source or "").strip()
    if not s or s == "mire":
        p = mire_path()
        return p, "mire"
    if s.startswith("image:"):
        p = library_image(s[6:])
        st = p.stat()
        return p, f"img:{p.name}:{int(st.st_mtime)}:{st.st_size}"
    if s.startswith("job:"):
        slug = _job_slug(s[4:])
        if job_video is None or not Path(job_video).is_file():
            raise ValueError("rendu introuvable")
        p = video_frame(Path(job_video), t, slug)
        return p, f"job:{slug}:{t:.2f}"
    raise ValueError("source inconnue (attendu : mire, image:<nom>, job:<id>)")


# --------------------------------------------------------------- le rendu ---
def _prune_cache(keep: int = 800):
    try:
        files = sorted((p for p in cache_dir().glob("fx_*.jpg")
                        if ".tmp." not in p.name),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files[keep:]:
            p.unlink(missing_ok=True)
    except OSError:
        pass


def render_preview(effect_type: str, raw_params: dict, *, source=None,
                   t: float = T_DEFAULT, width: int = W_DEFAULT,
                   job_video: Path | None = None) -> Path:
    """Rend (ou retrouve en cache) la vignette d'un effet. Renvoie le JPEG.

    ValueError = requête refusée (type inconnu, source hors dossier).
    RuntimeError = ffmpeg n'a pas produit d'image.
    """
    from app.services import effects_engine as fx
    from PIL import Image as PILImage

    etype = str(effect_type or "").strip()
    if etype not in fx.EFFECTS:
        raise ValueError(f"type d'effet inconnu : {etype[:40]!r}")

    params = coerce_params(etype, raw_params or {})
    try:
        t = float(t)
    except (TypeError, ValueError):
        t = T_DEFAULT
    t = max(T_MIN, min(T_MAX, t))
    try:
        width = int(width)
    except (TypeError, ValueError):
        width = W_DEFAULT
    width = max(W_MIN, min(W_MAX, width)) // 2 * 2

    still, sig = source_still(source, t, job_video)

    key = hashlib.sha1(json.dumps(
        [etype, params, sig, round(t, 3), width, 3],   # 3 = version du rendu
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]
    out = cache_dir() / f"fx_{key}.jpg"
    if out.is_file() and out.stat().st_size:
        return out

    with PILImage.open(still) as im:
        sw, sh = im.size
    w = width
    h = max(2, int(round(width * sh / max(1, sw)))) // 2 * 2

    eff = dict(params, type=etype)
    ctx = {"w": w, "h": h, "dur": t + 0.4, "fps": 25}
    chain = fx.build_chain([eff], "fxin", "fxout", "p0", ctx)
    graph = ";".join(
        [f"[0:v]scale={w}:{h}:flags=bicubic,setsar=1[fxin]"] + chain +
        ["[fxout]format=yuv420p[fxjpg]"])

    # Même combinaison demandée deux fois en parallèle (deux panneaux, un
    # re-rendu) : un seul ffmpeg, l'autre lit le cache. Temporaire unique.
    tmp = out.with_name(f"{out.stem}.{os.getpid()}-{threading.get_ident()}.tmp.jpg")
    cmd = [ffmpeg_bin(), "-y", "-v", "error",
           "-loop", "1", "-framerate", "25", "-t", f"{t + 0.4:.2f}",
           "-i", str(still), "-filter_complex", graph, "-map", "[fxjpg]",
           "-ss", f"{t:.3f}", "-frames:v", "1", "-update", "1",
           "-q:v", "3", str(tmp)]
    with _frame_lock(out.name):
        if out.is_file() and out.stat().st_size:
            return out
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode != 0 or not tmp.is_file() or not tmp.stat().st_size:
                last = (r.stderr or "").strip().splitlines()
                raise RuntimeError(f"rendu de l'aperçu impossible : "
                                   f"{last[-1][:200] if last else 'sortie vide'}")
            tmp.replace(out)
        finally:
            tmp.unlink(missing_ok=True)
    _prune_cache()
    return out


def catalog_payload() -> dict:
    """Charge utile de GET /api/effects/catalog."""
    from app.services import effects_engine as fx
    return {
        "categories": fx.categories(),
        "effects": fx.catalog(),
        "preview": {"width_default": W_DEFAULT, "width_max": W_MAX,
                    "t_default": T_DEFAULT, "t_max": T_MAX,
                    "sources": ["mire", "image:<nom>", "job:<id>"]},
    }


if __name__ == "__main__":  # dessin de la mire seule, pour l'oeil
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("mire.png")
    print(build_mire(out))
