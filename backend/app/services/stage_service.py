"""Material Forge — le SOL du viewport (plateau technique), en PIL pur.

Un aperçu de matière posé dans le vide ne donne aucune échelle : l'oeil n'a
rien pour juger la taille du motif ni la hauteur de l'objet. La barre de
référence pose une grille en perspective sous l'objet, et c'est ce qui rend
son viewport crédible. On fait la même chose, mais en VRAIE géométrie 3D
(un quad texturé ajouté au GLB d'aperçu) plutôt qu'en décor plaqué : la
grille suit donc l'orbite, le pan et le zoom exactement comme le sol qu'elle
prétend être.

La texture est une seule image RGBA 1024x1024, plaquée en projection planaire
sur un quad de 16 x 16 unités (donc une case de grille = 1 unité) :

  * fond très sombre, dans le langage de l'application ;
  * grille fine tous les 64 px (= 1 unité), grille forte tous les 256 px ;
  * les deux axes centraux teintés de l'accent orange ;
  * une flaque de contact sombre au centre — l'ombre portée de l'objet,
    cuite dans la texture : `<model-viewer>` place son ombre dynamique au bas
    de la boîte englobante de la SCENE, or la scène contient désormais le sol,
    ce qui rendrait cette ombre inutilisable (un carré noir plein cadre) ;
  * un alpha en fondu radial : le quad se dissout avant son bord, on ne voit
    donc jamais la limite carrée du sol — il se lit comme un plateau infini.

Tout est calculé en opérations PIL pleine toile (le seul travail par pixel
Python se fait sur des masques 192x192 ensuite agrandis), et le résultat est
mis en cache en mémoire et sur disque.
"""
from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageDraw

__all__ = ["STAGE_PX", "STAGE_SPAN", "STAGE_VERSION", "build_stage",
           "stage_png", "clear_stage_cache"]

STAGE_PX = 1024          # côté de la texture
STAGE_SPAN = 16.0        # côté du quad en unités monde (1 case = 1 unité)
STAGE_VERSION = 3        # incrémenter = invalide le cache disque

_BG = (13, 14, 17)
_MINOR = (42, 46, 55)
_MAJOR = (98, 107, 126)
_AXIS = (132, 88, 36)    # accent doré très rabattu : présent, jamais criard
_CELL = STAGE_PX // 16   # 64 px = 1 unité
_MAJOR_EVERY = 4         # une ligne forte toutes les 4 cases

_mem: dict[str, bytes] = {}


def _radial_mask(size: int, inner: float, outer: float, gamma: float) -> Image.Image:
    """Masque L circulaire calculé en 192x192 puis agrandi : 36 864 pixels
    Python au lieu de 1 048 576, pour un dégradé visuellement identique."""
    n = 192
    m = Image.new("L", (n, n), 0)
    px = m.load()
    c = (n - 1) / 2.0
    span = max(1e-6, outer - inner)
    for y in range(n):
        dy = (y - c) / c
        for x in range(n):
            dx = (x - c) / c
            d = math.sqrt(dx * dx + dy * dy)
            if d <= inner:
                px[x, y] = 255
            elif d < outer:
                t = 1.0 - (d - inner) / span
                t = t * t * (3.0 - 2.0 * t)        # smoothstep
                px[x, y] = int(255 * (t ** gamma))
    return m.resize((size, size), Image.BICUBIC)


def build_stage() -> Image.Image:
    """Génère la texture RGBA du sol."""
    n = STAGE_PX
    img = Image.new("RGB", (n, n), _BG)
    d = ImageDraw.Draw(img)

    half = n // 2
    for i in range(-(n // _CELL) // 2, (n // _CELL) // 2 + 1):
        p = half + i * _CELL
        if p < 0 or p > n - 1:
            continue
        if i == 0:
            col = _AXIS
        elif i % _MAJOR_EVERY == 0:
            col = _MAJOR
        else:
            col = _MINOR
        d.line((p, 0, p, n - 1), fill=col)
        d.line((0, p, n - 1, p), fill=col)

    # flaque de contact : assombrissement radial au centre, sous l'objet.
    pool = _radial_mask(n, 0.030, 0.145, 1.15)
    img = Image.composite(Image.new("RGB", (n, n), (2, 2, 3)), img, pool)

    # halo chaud très faible juste autour de la flaque : la matière posée sur
    # le sol renvoie un peu de lumière, et cela ancre l'objet dans l'accent.
    warm = _radial_mask(n, 0.14, 0.34, 1.5)
    img = Image.composite(
        Image.blend(img, Image.new("RGB", (n, n), (74, 46, 20)), 0.22),
        img, warm)

    # alpha : le plateau se dissout avant son bord (pas de limite carrée).
    alpha = _radial_mask(n, 0.16, 0.98, 1.25)
    img = img.convert("RGBA")
    img.putalpha(alpha)
    return img


def _cache_dir() -> Path:
    try:
        from app.config import settings
        root = settings.outputs_path / "materials" / "_env"
    except Exception:                         # hors application (tests, CLI)
        import tempfile
        root = Path(tempfile.gettempdir()) / "dz_material_envs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def stage_png() -> bytes:
    """PNG RGBA du sol, mémoire puis disque puis génération."""
    key = "stage-v%d" % STAGE_VERSION
    hit = _mem.get(key)
    if hit:
        return hit
    p = _cache_dir() / (key + ".png")
    if p.is_file() and p.stat().st_size > 1024:
        data = p.read_bytes()
    else:
        buf = io.BytesIO()
        build_stage().save(buf, "PNG", optimize=True)
        data = buf.getvalue()
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)                        # écriture atomique
    _mem[key] = data
    return data


def clear_stage_cache() -> int:
    _mem.clear()
    n = 0
    for f in _cache_dir().glob("stage-v*.png"):
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n
