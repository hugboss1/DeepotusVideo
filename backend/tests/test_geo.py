"""Lot H — les cartes réelles : tuiles Terrarium (hauteurs) et OSM (fond) en
cache disque, décodage par Pillow (sans numpy), assemblage rogné à l'emprise
et rééchantillonné, routes /geo. Le réseau passe par le hook module
`_get_bytes`, monkeypatché ici : le banc ne SORT jamais.

Run: pytest tests/test_geo.py -q
"""
import asyncio
import io
import json
import math
import os
import pathlib
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["GEO_CACHE"] = str(pathlib.Path(_tmp, "geo"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402


def _tuile_terrarium(hauteur_fn):
    """Une tuile 256×256 Terrarium : h = R·256 + G + B/256 − 32768."""
    im = Image.new("RGB", (256, 256))
    px = im.load()
    for y in range(256):
        for x in range(256):
            v = hauteur_fn(x, y) + 32768.0
            r = int(v // 256)
            g = int(v % 256)
            b = int(round((v - math.floor(v)) * 256)) % 256
            px[x, y] = (r, g, b)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _tuile_osm(couleur):
    im = Image.new("RGB", (256, 256), couleur)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


APPELS = []


def _brancher(monkeypatch, plat=100.0, carre=300.0):
    from app.services import geo_service as G

    async def faux_get(url):
        APPELS.append(url)
        if "terrarium" in url:
            # un carré haut au centre de chaque tuile
            return _tuile_terrarium(lambda x, y: carre if 96 <= x < 160 and 96 <= y < 160 else plat)
        return _tuile_osm((30, 120, 200))

    monkeypatch.setattr(G, "_get_bytes", faux_get)
    APPELS.clear()
    return G


EMPRISE = {"minLat": 45.0, "maxLat": 45.2, "minLon": 6.0, "maxLon": 6.3}


# ── A. décodage et couverture ────────────────────────────────────────────────

def test_le_decodage_terrarium_est_exact():
    from app.services import geo_service as G
    w, h, hs = G.decoder_terrarium(_tuile_terrarium(lambda x, y: 100.0 if x < 128 else 300.5))
    assert (w, h) == (256, 256) and len(hs) == 256 * 256
    assert hs[0] == pytest.approx(100.0, abs=0.01)
    assert hs[200] == pytest.approx(300.5, abs=0.01)
    with pytest.raises(ValueError):
        G.decoder_terrarium(b"pas un png")


def test_la_couverture_en_tuiles_miroir_du_client():
    from app.services import geo_service as G
    c = G.tuiles_couvrant(EMPRISE, 10)
    assert c["n"] == (c["xmax"] - c["xmin"] + 1) * (c["ymax"] - c["ymin"] + 1) >= 2
    assert G.tuile_xyz(45.0, 6.0, 10) == (529, 368)          # même formule que mod-geo


# ── B. hauteurs : assemblage, rognage, rééchantillonnage, cache ─────────────

def test_les_hauteurs_assemblent_rognent_et_mettent_en_cache(monkeypatch):
    G = _brancher(monkeypatch)
    z = 10
    n_tuiles = G.tuiles_couvrant(EMPRISE, z)["n"]
    r = asyncio.run(G.hauteurs(EMPRISE, z, max_cote=160))
    assert r["w"] <= 160 and r["h"] <= 160 and r["w"] >= 2 and r["h"] >= 2
    assert len(r["hauteurs"]) == r["w"] * r["h"]
    assert r["min"] == pytest.approx(100.0, abs=0.5)
    assert r["max"] == pytest.approx(300.0, abs=0.5)
    assert r["pasM"] > 0 and r["zoom"] == z
    assert len(APPELS) == n_tuiles                            # une requête par tuile
    # le cache disque : le second appel ne SORT pas
    r2 = asyncio.run(G.hauteurs(EMPRISE, z, max_cote=160))
    assert len(APPELS) == n_tuiles and r2["min"] == r["min"]
    assert len(list(pathlib.Path(os.environ["GEO_CACHE"]).glob("terrarium_*.png"))) == n_tuiles
    # trop de tuiles → refus parlant AVANT toute requête
    APPELS.clear()
    with pytest.raises(ValueError):
        asyncio.run(G.hauteurs(EMPRISE, 14, max_tuiles=16))
    assert APPELS == []
    # emprise invalide
    with pytest.raises(ValueError):
        asyncio.run(G.hauteurs({"minLat": 1, "maxLat": 0, "minLon": 0, "maxLon": 1}, 10))


def test_le_fond_osm_rend_un_png_rogne(monkeypatch):
    G = _brancher(monkeypatch)
    png = asyncio.run(G.fond(EMPRISE, 10))
    im = Image.open(io.BytesIO(png))
    assert im.format == "PNG" and im.size[0] <= 2048 and im.size[0] >= 64
    assert im.getpixel((5, 5))[:3] == (30, 120, 200)
    assert G.ATTRIBUTION["osm"].startswith("©")
    assert any("openstreetmap" in u for u in APPELS)


# ── C. les routes ────────────────────────────────────────────────────────────

def test_les_routes_geo(monkeypatch):
    from httpx import AsyncClient, ASGITransport
    G = _brancher(monkeypatch)

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.get("/api/geo/attribution")
            assert r.status_code == 200 and "osm" in r.json() and "terrarium" in r.json()
            r = await c.post("/api/geo/relief", json={"emprise": EMPRISE, "zoom": 10})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["w"] >= 2 and len(d["hauteurs"]) == d["w"] * d["h"] and d["max"] > d["min"]
            r = await c.post("/api/geo/fond", json={"emprise": EMPRISE, "zoom": 10})
            assert r.status_code == 200 and r.headers["content-type"].startswith("image/png")
            r = await c.post("/api/geo/relief", json={"emprise": {"minLat": 1, "maxLat": 0, "minLon": 0, "maxLon": 1}, "zoom": 10})
            assert r.status_code == 400
            r = await c.post("/api/geo/relief", json={"emprise": EMPRISE, "zoom": 15})
            assert r.status_code == 400                                # trop de tuiles

            # réseau muet → 502 parlant
            async def mort(url):
                raise OSError("pas de réseau")
            monkeypatch.setattr(G, "_get_bytes", mort)
            r = await c.post("/api/geo/relief", json={"emprise": {"minLat": 10, "maxLat": 10.1, "minLon": 10, "maxLon": 10.1}, "zoom": 10})
            assert r.status_code == 502

    asyncio.run(scenario())


# ── D. miroir de surface ─────────────────────────────────────────────────────

def test_le_miroir_lot_h_cartes_reelles():
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    vl = racine / "frontend" / "vectorlab"
    for m in ("mod-geo.js", "mod-relief.js", "mod-carte.js"):
        assert (vl / "js" / m).is_file(), m
    for m in ("mod-geo.js", "mod-relief.js"):
        assert "import " not in (vl / "js" / m).read_text("utf-8"), m
    core = (vl / "js" / "core.js").read_text("utf-8")
    assert "initCarte(VL)" in core
    html = (vl / "index.html").read_text("utf-8")
    assert 'id="panneauCarte"' in html
    imp = (vl / "js" / "mod-impression.js").read_text("utf-8")
    assert 'value="relief"' in imp and "mod-relief.js" in imp
    carte = (vl / "js" / "mod-carte.js").read_text("utf-8")
    # le panneau se rend par innerHTML : ses contrôles vivent dans le module
    assert 'id="carteGpxInput"' in carte and 'id="carteFond"' in carte and 'id="carteRelief"' in carte
    assert "/api/geo/relief" in carte and "/api/geo/fond" in carte and "OpenStreetMap" in carte
    doc = (vl / "js" / "mod-doc.js").read_text("utf-8")
    for op in ("op_geo_importer", "op_geo_relief", "op_geo_courbes", "op_geo_tuiles"):
        assert f"export function {op}" in doc, op
    qa = vl / "qa"
    for b in ("geo", "relief", "geo_doc", "carte_ui"):
        assert (qa / f"{b}.test.mjs").is_file(), b
