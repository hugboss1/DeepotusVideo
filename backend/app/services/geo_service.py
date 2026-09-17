"""Lot H — les cartes réelles : tuiles d'altitude Terrarium (AWS Open Data,
publiques, sans clé) et fond de carte OpenStreetMap (attribution obligatoire,
User-Agent explicite, usage modéré), mises en CACHE sur disque
(`DeepotusVideoGenData/cache/geo`, ou `GEO_CACHE` au banc). Décodage des
hauteurs par Pillow — pas de numpy dans le runtime embarqué — puis
assemblage de la mosaïque, rognage à l'emprise et rééchantillonnage à
`max_cote` : une grille de nombres, pas des pixels. Le réseau passe par le
HOOK module `_get_bytes`, monkeypatché au banc — le banc ne SORT jamais.
Zéro clé, zéro dépendance payante (D7).
"""
from __future__ import annotations

import io
import math
import os
from pathlib import Path

TERRARIUM = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
OSM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT = "DeepotusVideoGen/2.8 (Vectorlab lot H; contact: olistruss639@gmail.com)"
ATTRIBUTION = {
    "osm": "© OpenStreetMap contributors (ODbL) — tile.openstreetmap.org",
    "terrarium": "Terrarium DEM — Mapzen / AWS Open Data (Terrain Tiles), sources SRTM, GMTED, ETOPO1 et al.",
}
TUILE = 256
NODATA_SEUIL = -32000.0        # Terrarium : R=G=B=0 → −32768 = « sans donnée »


def cache_dir() -> Path:
    env = os.environ.get("GEO_CACHE", "").strip()
    if env:
        d = Path(env)
    else:
        from app.config import DATA_ROOT
        d = DATA_ROOT / "cache" / "geo"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _get_bytes(url: str) -> bytes:              # pragma: no cover — mocké au banc
    import httpx
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


# ── géométrie des tuiles (miroir exact de mod-geo.js) ────────────────────────

def tuile_xyz(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    lr = math.radians(lat)
    x = math.floor((lon + 180.0) / 360.0 * n)
    y = math.floor((1.0 - math.log(math.tan(lr) + 1.0 / math.cos(lr)) / math.pi) / 2.0 * n)
    return x, y


def _px_monde(lat: float, lon: float, z: int) -> tuple[float, float]:
    """Position en PIXELS de la mosaïque monde (256 px par tuile)."""
    n = 2 ** z * TUILE
    lr = math.radians(lat)
    return ((lon + 180.0) / 360.0 * n,
            (1.0 - math.log(math.tan(lr) + 1.0 / math.cos(lr)) / math.pi) / 2.0 * n)


def valider_emprise(e) -> dict:
    if not isinstance(e, dict):
        raise ValueError("emprise : objet {minLat, maxLat, minLon, maxLon} requis")
    try:
        out = {k: float(e[k]) for k in ("minLat", "maxLat", "minLon", "maxLon")}
    except (KeyError, TypeError, ValueError):
        raise ValueError("emprise : minLat, maxLat, minLon, maxLon numériques requis")
    if not (out["minLat"] < out["maxLat"] and out["minLon"] < out["maxLon"]):
        raise ValueError("emprise : inversée ou vide")
    if not (-85.05 <= out["minLat"] and out["maxLat"] <= 85.05):
        raise ValueError("emprise : latitudes hors de la projection (±85°)")
    return out


def tuiles_couvrant(emprise: dict, z: int) -> dict:
    e = valider_emprise(emprise)
    xmin, ymin = tuile_xyz(e["maxLat"], e["minLon"], z)
    xmax, ymax = tuile_xyz(e["minLat"], e["maxLon"], z)
    return {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax,
            "n": (xmax - xmin + 1) * (ymax - ymin + 1)}


# ── tuiles en cache ──────────────────────────────────────────────────────────

async def tuile(genre: str, z: int, x: int, y: int) -> bytes:
    gabarit = TERRARIUM if genre == "terrarium" else OSM
    p = cache_dir() / f"{genre}_{z}_{x}_{y}.png"
    if p.is_file():
        return p.read_bytes()
    octets = await _get_bytes(gabarit.format(z=z, x=x, y=y))
    if not octets.startswith(b"\x89PNG"):
        raise ValueError(f"tuile {genre} {z}/{x}/{y} : pas un PNG")
    tmp = p.with_suffix(".tmp")
    tmp.write_bytes(octets)
    os.replace(tmp, p)
    return octets


def decoder_terrarium(png: bytes) -> tuple[int, int, list[float]]:
    """h = R·256 + G + B/256 − 32768, pixel par pixel (Pillow, sans numpy)."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(png)).convert("RGB")
    except Exception:
        raise ValueError("tuile Terrarium illisible (pas un PNG)")
    w, h = im.size
    data = list(im.getdata())
    return w, h, [r * 256.0 + g + b / 256.0 - 32768.0 for (r, g, b) in data]


async def _mosaique(genre: str, emprise: dict, z: int, max_tuiles: int):
    c = tuiles_couvrant(emprise, z)
    if c["n"] > max_tuiles:
        raise ValueError(f"zoom {z} : {c['n']} tuiles pour cette emprise, au plus {max_tuiles} — "
                         "réduire le zoom ou l'emprise")
    tuiles = {}
    for ty in range(c["ymin"], c["ymax"] + 1):
        for tx in range(c["xmin"], c["xmax"] + 1):
            tuiles[(tx, ty)] = await tuile(genre, z, tx, ty)
    return c, tuiles


def _fenetre(emprise: dict, z: int, c: dict) -> tuple[int, int, int, int]:
    """Le rectangle de l'emprise en pixels de la mosaïque locale (0 = coin
    NO de la première tuile)."""
    e = valider_emprise(emprise)
    x0, y0 = _px_monde(e["maxLat"], e["minLon"], z)
    x1, y1 = _px_monde(e["minLat"], e["maxLon"], z)
    ox, oy = c["xmin"] * TUILE, c["ymin"] * TUILE
    return (int(math.floor(x0 - ox)), int(math.floor(y0 - oy)),
            max(2, int(math.ceil(x1 - ox))), max(2, int(math.ceil(y1 - oy))))


async def hauteurs(emprise: dict, zoom: int, max_tuiles: int = 16, max_cote: int = 160) -> dict:
    """La grille des hauteurs (m) de l'emprise : assemblée, rognée,
    rééchantillonnée (plus proche voisin) à `max_cote` par côté."""
    z = int(zoom)
    if not (1 <= z <= 15):
        raise ValueError("zoom : entier 1..15")
    c, tuiles = await _mosaique("terrarium", emprise, z, max_tuiles)
    decodees = {k: decoder_terrarium(v) for k, v in tuiles.items()}
    fx0, fy0, fx1, fy1 = _fenetre(emprise, z, c)
    lw, lh = fx1 - fx0, fy1 - fy0
    k = max(1, math.ceil(max(lw, lh) / max_cote))
    w = max(2, lw // k)
    h_ = max(2, lh // k)
    out = []
    for j in range(h_):
        py = fy0 + min(lh - 1, j * k)
        ty, ly = divmod(py, TUILE)
        for i in range(w):
            px = fx0 + min(lw - 1, i * k)
            tx, lx = divmod(px, TUILE)
            tw, th, hs = decodees[(c["xmin"] + tx, c["ymin"] + ty)]
            out.append(round(hs[ly * tw + lx], 1))
    # « sans donnée » Terrarium (R=G=B=0 → −32768, mesuré sur les Alpes le
    # 17/09) : remplacé par le minimum VALIDE — jamais un plateau à −32 km
    valides = [v for v in out if v > NODATA_SEUIL]
    if not valides:
        raise ValueError("relief : aucune hauteur valide dans l'emprise (tuiles sans donnée)")
    plancher = min(valides)
    sans_donnee = sum(1 for v in out if v <= NODATA_SEUIL)
    out = [v if v > NODATA_SEUIL else plancher for v in out]
    e = valider_emprise(emprise)
    lat0 = (e["minLat"] + e["maxLat"]) / 2
    # mètres au sol par pixel de mosaïque à cette latitude, × k
    pas_m = 2 * math.pi * 6378137 * math.cos(math.radians(lat0)) / (2 ** z * TUILE) * k
    return {"w": w, "h": h_, "min": min(out), "max": max(out), "pasM": round(pas_m, 3),
            "zoom": z, "hauteurs": out, "emprise": e, "sans_donnee": sans_donnee,
            "attribution": ATTRIBUTION["terrarium"]}


async def fond(emprise: dict, zoom: int, max_tuiles: int = 16) -> bytes:
    """Le fond OSM de l'emprise : mosaïque assemblée par Pillow, rognée."""
    from PIL import Image
    z = int(zoom)
    if not (1 <= z <= 19):
        raise ValueError("zoom : entier 1..19")
    c, tuiles = await _mosaique("osm", emprise, z, max_tuiles)
    W = (c["xmax"] - c["xmin"] + 1) * TUILE
    H = (c["ymax"] - c["ymin"] + 1) * TUILE
    mos = Image.new("RGB", (W, H))
    for (tx, ty), octets in tuiles.items():
        try:
            im = Image.open(io.BytesIO(octets)).convert("RGB")
        except Exception:
            raise ValueError(f"tuile OSM {z}/{tx}/{ty} illisible")
        mos.paste(im, ((tx - c["xmin"]) * TUILE, (ty - c["ymin"]) * TUILE))
    fx0, fy0, fx1, fy1 = _fenetre(emprise, z, c)
    rogne = mos.crop((max(0, fx0), max(0, fy0), min(W, fx1), min(H, fy1)))
    buf = io.BytesIO()
    rogne.save(buf, "PNG")
    return buf.getvalue()
