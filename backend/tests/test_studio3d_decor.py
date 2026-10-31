# -*- coding: utf-8 -*-
"""t402 (31/10/2026) — Décor › Accessoire : poser un élément au sol (pivot en bas, centré) et à sa hauteur réelle,
écrit comme une version de plus ; rôles de décor → préréglage de triangles. Boîte SYNTHÉTIQUE, aucune dépense.
Run : python tests/test_studio3d_decor.py (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3dec_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import print3d, studio3d_decor as SD, studio3d_ouvert as SO   # noqa: E402

J = settings.outputs_path / "assets3d"


def boite(c, d):
    x0, y0, z0 = (c[i] - d[i] / 2 for i in range(3))
    x1, y1, z1 = (c[i] + d[i] / 2 for i in range(3))
    P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5),
         (3, 0, 4), (3, 4, 7)]
    return print3d.glb_de_pieces([("m", [(P[a], P[b], P[e]) for a, b, e in F])])


ROCHER = boite((3.0, 5.0, -2.0), (2.0, 4.0, 1.0))          # flotte à y = 3..7, décentré
(J / "rocher").mkdir(parents=True, exist_ok=True)
(J / "rocher" / "model.glb").write_bytes(ROCHER)


def bornes(data):
    return print3d.bbox(print3d.lire_glb_triangles(data))


def test_poser_met_le_bas_au_sol_et_centre_sans_toucher_l_echelle():
    sortie, m = SD.poser(ROCHER)
    (x0, x1), (y0, y1), (z0, z1) = bornes(sortie)
    assert abs(y0) < 1e-6 and abs(y1 - 4.0) < 1e-6
    assert abs(x0 + x1) < 1e-6 and abs(z0 + z1) < 1e-6
    assert m["echelle"] == 1.0 and m["avant"]["bas"] == 3.0 and m["apres"]["bas"] == 0.0


def test_la_hauteur_reelle_met_a_l_echelle_uniformement():
    sortie, m = SD.poser(ROCHER, hauteur_m=1.0)
    (x0, x1), (y0, y1), (z0, z1) = bornes(sortie)
    assert abs(y1 - y0 - 1.0) < 1e-6 and abs(y0) < 1e-6
    assert abs((x1 - x0) - 0.5) < 1e-6 and abs((z1 - z0) - 0.25) < 1e-6      # proportions gardées
    assert m["echelle"] == 0.25


def test_les_refus():
    for h in (0, -1, 1000, True, "2"):
        try:
            SD.poser(ROCHER, hauteur_m=h)
        except ValueError:
            continue
        raise AssertionError(h)
    try:
        SD.budget("inconnu")
    except ValueError:
        pass
    else:
        raise AssertionError("rôle inconnu accepté")
    assert SD.budget("foule") == {"role": "foule", "preset": "micro", "triangles": 500}


def test_la_route_ecrit_une_version_qui_dit_sa_source():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ko = await c.post("/api/studio3d/decor/poser", json={"job": "../rocher"})
            absent = await c.post("/api/studio3d/decor/poser", json={"job": "inconnu"})
            mauvais = await c.post("/api/studio3d/decor/poser", json={"job": "rocher", "hauteur_m": 9999})
            ok = await c.post("/api/studio3d/decor/poser", json={"job": "rocher", "hauteur_m": 0.8})
            roles = await c.get("/api/studio3d/decor/roles")
            return ko, absent, mauvais, ok, roles
    ko, absent, mauvais, ok, roles = asyncio.run(go())
    assert (ko.status_code, absent.status_code, mauvais.status_code) == (400, 404, 400)
    assert ok.status_code == 200, ok.text
    assert ok.json()["version"] == 2
    f = SO.fiche("rocher")
    assert f["version"] == 2 and [(v["operation"], v["depuis"]) for v in f["versions"]][-1] == ("decor_poser", 1)
    (x0, x1), (y0, y1), _ = bornes((J / "rocher" / "model.v2.glb").read_bytes())
    assert abs(y1 - y0 - 0.8) < 1e-6 and abs(y0) < 1e-6
    assert [r["role"] for r in roles.json()["roles"]] == list(SD.ROLES)


def lancer_tous():
    rouges = []
    for nom, fn in list(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (Décor › Accessoire)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
