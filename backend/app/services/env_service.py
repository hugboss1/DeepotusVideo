"""Material Forge — les 7 environnements équirectangulaires (SPEC section 6).

Sept ciels 1024x512 générés en PIL PUR (zéro numpy, zéro réseau, zéro HDR à
télécharger), mis en cache sur disque au premier appel :

    unlit · daylight · studio · sunset · overcast · night · dramatic

Ils servent d'`environment-image` (et de `skybox-image`) à <model-viewer> :
sans image d'environnement, un matériau PBR métallique s'affiche noir. Les
générer localement évite d'embarquer des .hdr de plusieurs méga-octets et
garde l'application hors ligne.

Construction, en trois passes bon marché :
  1. dégradé vertical ciel -> horizon -> sol, une ligne PIL par rangée (512
     appels, pas 524288 pixels Python) ;
  2. voile d'horizon, un fondu doux de part et d'autre de la ligne médiane ;
  3. sources lumineuses : un disque radial calculé une seule fois en 96x96
     puis agrandi en BICUBIC et collé en mode additif. Le collage est
     répliqué en x -W et x +W pour que la source qui chevauche le bord
     gauche/droit reste continue une fois la sphère refermée (une couture
     visible dans un équirect se voit immédiatement dans les reflets).

Le canevas étant construit par rangées et par collages repliés, le raccord
horizontal est exact par construction.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

__all__ = ["ENVS", "ENV_W", "ENV_H", "ENV_VERSION", "env_list", "env_names",
           "build_env", "env_bytes", "env_path", "clear_env_cache"]

ENV_W, ENV_H = 1024, 512
ENV_VERSION = 2          # incrémenter = invalide le cache disque

# Chaque préréglage : dégradé (zénith, horizon ciel, horizon sol, nadir),
# couleur du voile d'horizon, et la liste des sources lumineuses.
# Une source = (azimut 0..1, élévation en degrés, rayon px, couleur,
#               intensité, dureté 1..6) : dureté élevée = disque net (soleil
#               dur), dureté basse = tache large et molle (panneau de studio).
ENVS = (
    {
        # Dôme uniforme quasi blanc : l'éclairage image-based devient constant
        # dans toutes les directions, la matière s'affiche donc telle quelle,
        # sans ombre ni reflet directionnel. C'est le "sans éclairage" utile.
        "name": "unlit", "label": "Sans éclairage",
        "sky": ((232, 232, 234), (228, 228, 230)),
        "ground": ((224, 224, 226), (220, 220, 222)),
        "haze": (230, 230, 232), "haze_px": 240,
        "lights": (),
    },
    {
        "name": "daylight", "label": "Plein jour",
        "sky": ((44, 96, 196), (170, 202, 236)),
        "ground": ((122, 116, 92), (46, 44, 38)),
        "haze": (214, 228, 244), "haze_px": 90,
        "lights": (
            (0.26, 46.0, 46, (255, 250, 232), 1.00, 5.0),
            (0.26, 46.0, 300, (255, 244, 210), 0.34, 1.6),
            (0.74, 22.0, 420, (150, 178, 210), 0.12, 1.2),
        ),
    },
    {
        "name": "studio", "label": "Studio",
        "sky": ((238, 238, 242), (206, 206, 212)),
        "ground": ((146, 146, 152), (86, 86, 92)),
        "haze": (226, 226, 232), "haze_px": 150,
        "lights": (
            (0.20, 34.0, 250, (255, 255, 255), 0.62, 1.4),   # clé
            (0.62, 20.0, 300, (240, 244, 255), 0.34, 1.2),   # remplissage
            (0.88, 48.0, 180, (255, 250, 245), 0.30, 1.5),   # contre-jour
        ),
    },
    {
        "name": "sunset", "label": "Couchant",
        "sky": ((26, 32, 84), (248, 146, 62)),
        "ground": ((74, 48, 42), (18, 14, 16)),
        "haze": (255, 176, 96), "haze_px": 120,
        "lights": (
            (0.32, 3.5, 40, (255, 226, 168), 1.00, 4.0),
            (0.32, 3.5, 340, (255, 138, 46), 0.55, 1.5),
            (0.32, 3.5, 620, (226, 92, 40), 0.22, 1.1),
        ),
    },
    {
        "name": "overcast", "label": "Ciel couvert",
        "sky": ((186, 190, 198), (228, 230, 234)),
        "ground": ((118, 120, 122), (64, 66, 68)),
        "haze": (232, 234, 238), "haze_px": 180,
        "lights": (
            (0.40, 58.0, 460, (255, 255, 255), 0.34, 1.1),
            (0.40, 58.0, 150, (255, 255, 255), 0.20, 1.4),
        ),
    },
    {
        # Un equirect LDR ne porte pas de haute dynamique : un petit disque
        # tres brillant ne pese quasiment rien dans l'integrale d'eclairage.
        # Pour qu'une scene nocturne reste lisible il faut une lune ETALEE,
        # pas seulement intense.
        "name": "night", "label": "Nuit",
        "sky": ((6, 9, 26), (26, 38, 74)),
        "ground": ((14, 17, 28), (3, 4, 8)),
        "haze": (44, 60, 104), "haze_px": 80,
        "lights": (
            (0.68, 42.0, 22, (255, 255, 255), 1.00, 6.0),    # disque lunaire
            (0.68, 42.0, 300, (150, 178, 232), 0.62, 1.4),   # halo
            (0.68, 42.0, 620, (60, 84, 150), 0.30, 1.1),     # nappe froide
            (0.18, 12.0, 400, (48, 70, 120), 0.22, 1.1),
        ),
        "stars": 900,
    },
    {
        # Fort contraste : une cle large et blanche d'un cote, un contre-jour
        # froid de l'autre, tout le reste tres sombre.
        "name": "dramatic", "label": "Dramatique",
        "sky": ((6, 6, 10), (24, 22, 28)),
        "ground": ((16, 15, 18), (3, 3, 5)),
        "haze": (36, 32, 40), "haze_px": 60,
        "lights": (
            (0.14, 30.0, 40, (255, 252, 246), 1.00, 5.5),    # clé dure
            (0.14, 30.0, 260, (255, 240, 220), 0.92, 1.7),
            (0.14, 30.0, 520, (170, 140, 110), 0.34, 1.1),
            (0.70, 16.0, 320, (70, 110, 190), 0.55, 1.3),    # contre froid
        ),
    },
)

_BY_NAME = {e["name"]: e for e in ENVS}


# ── outils ──────────────────────────────────────────────────────────────────
def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _radial(radius: int, hardness: float) -> Image.Image:
    """Masque radial L. Calculé en 96x96 (9216 pixels Python) puis agrandi :
    un calcul par pixel à la taille finale coûterait 1000x plus cher pour un
    résultat visuellement identique, le dégradé étant lisse par nature."""
    n = 96
    m = Image.new("L", (n, n), 0)
    px = m.load()
    c = (n - 1) / 2.0
    for y in range(n):
        dy = (y - c) / c
        for x in range(n):
            dx = (x - c) / c
            d = math.sqrt(dx * dx + dy * dy)
            if d >= 1.0:
                continue
            px[x, y] = int(255 * ((1.0 - d) ** hardness))
    size = max(4, int(radius) * 2)
    return m.resize((size, size), Image.BICUBIC)


def _add_light(img: Image.Image, cx: int, cy: int, radius: int,
               color: tuple, intensity: float, hardness: float) -> Image.Image:
    """Ajoute une source lumineuse en mode additif borné, repliée sur les deux
    bords. Tout se fait en opérations PIL pleine toile (niveau C) : une boucle
    Python sur 512x512 pixels par source rendrait la génération inutilisable."""
    mask = _radial(radius, hardness)
    size = mask.size[0]
    layer = Image.new("L", (ENV_W, ENV_H), 0)
    x0, y0 = cx - size // 2, cy - size // 2
    for dx in (-ENV_W, 0, ENV_W):
        if x0 + dx + size < 0 or x0 + dx > ENV_W:
            continue
        patch = Image.new("L", (ENV_W, ENV_H), 0)
        patch.paste(mask, (x0 + dx, y0))
        # `lighter` et non `add` : le recouvrement des trois replis ne doit
        # pas doubler l'intensité sur la couture.
        layer = ImageChops.lighter(layer, patch)
    tint = Image.new("RGB", (ENV_W, ENV_H), tuple(
        int(round(c * min(1.0, intensity))) for c in color))
    glow = ImageChops.multiply(tint, Image.merge("RGB", (layer, layer, layer)))
    return ImageChops.add(img, glow)


def build_env(name: str) -> Image.Image:
    """Génère l'équirectangulaire 1024x512 d'un environnement (RGB)."""
    env = _BY_NAME.get(str(name or "").strip().lower()) or _BY_NAME["studio"]
    img = Image.new("RGB", (ENV_W, ENV_H))
    d = ImageDraw.Draw(img)
    mid = ENV_H // 2
    sky_a, sky_b = env["sky"]
    gr_a, gr_b = env["ground"]
    haze, haze_px = env["haze"], float(env["haze_px"])

    for y in range(ENV_H):
        if y < mid:
            base = _lerp(sky_a, sky_b, (y / mid) ** 1.35)
        else:
            base = _lerp(gr_a, gr_b, ((y - mid) / mid) ** 0.65)
        # voile d'horizon : fondu symétrique autour de la médiane
        k = 1.0 - min(1.0, abs(y - mid) / haze_px)
        if k > 0.0:
            k = k * k * (0.55 if y >= mid else 0.85)
            base = _lerp(base, haze, k)
        d.line((0, y, ENV_W - 1, y), fill=base)

    if env.get("stars"):
        rng = random.Random(1789)          # seedé : rendu reproductible
        px = img.load()
        for _ in range(int(env["stars"])):
            x = rng.randrange(ENV_W)
            y = rng.randrange(0, mid - 8)
            b = rng.randrange(90, 256)
            # plus rare et plus faible près de l'horizon
            if rng.random() > (1.0 - y / mid) * 0.9 + 0.1:
                continue
            r, g, bl = px[x, y]
            px[x, y] = (min(255, r + b), min(255, g + b), min(255, bl + b))

    for az, el, radius, color, intensity, hardness in env["lights"]:
        cx = int(az * ENV_W) % ENV_W
        cy = int(round(mid * (1.0 - el / 90.0)))
        img = _add_light(img, cx, cy, int(radius), color, float(intensity),
                         float(hardness))

    # un flou très léger casse le moirage JPEG des grands dégradés
    return img.filter(ImageFilter.GaussianBlur(0.6))


# ── cache disque ────────────────────────────────────────────────────────────
def _cache_dir() -> Path:
    try:
        from app.config import settings
        root = settings.outputs_path / "materials" / "_env"
    except Exception:                       # hors application (tests, CLI)
        import tempfile
        root = Path(tempfile.gettempdir()) / "dz_material_envs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def env_names() -> list[str]:
    return [e["name"] for e in ENVS]


def env_list() -> list[dict]:
    """Liste pour GET /api/materials/envs."""
    return [{"name": e["name"], "label": e["label"]} for e in ENVS]


def env_path(name: str) -> Path:
    """Chemin du JPEG en cache, généré au premier appel."""
    key = str(name or "").strip().lower()
    if key not in _BY_NAME:                 # liste blanche stricte : le nom
        key = "studio"                      # vient du client
    p = _cache_dir() / ("%s-v%d.jpg" % (key, ENV_VERSION))
    if not p.is_file() or p.stat().st_size < 1024:
        tmp = p.with_suffix(".tmp")
        build_env(key).save(tmp, "JPEG", quality=90, optimize=True,
                            subsampling=1)
        tmp.replace(p)                      # écriture atomique
    return p


def env_bytes(name: str) -> bytes:
    return env_path(name).read_bytes()


def clear_env_cache() -> int:
    """Supprime les JPEG en cache (après un incrément d'ENV_VERSION)."""
    n = 0
    for f in _cache_dir().glob("*.jpg"):
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n
