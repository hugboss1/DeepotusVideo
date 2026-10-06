# -*- coding: utf-8 -*-
"""Générateurs paramétriques — les ROUTES (T098, plan-matieres T12).

BANC-MIROIR : la carte height est RELUE sur le disque de la matière créée.

Run (depuis backend/) : python tests/test_pattern_api.py
"""
import asyncio
import os
import pathlib
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402
from httpx import ASGITransport, AsyncClient                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [], "seed": 0}


_stub.subscribe_async = _sub
sys.modules["fal_client"] = _stub

from app.main import app                                       # noqa: E402
from app.services import material_store as MS                  # noqa: E402
from app.services import pbr_service as PBR                    # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=120) as c:
            d = (await c.get("/api/materials/patterns")).json()
            assert len(d["patterns"]) == 10
            for g in d["patterns"]:
                assert g["params"] and all({"k", "type"} <= set(p) for p in g["params"])
            ok("GET /materials/patterns : dix générateurs, leurs bornes publiées")

            r = await c.post("/api/materials/patterns/briques",
                             json={"res": 512, "params": {"rangs": 6},
                                   "name": "Mur de test"})
            assert r.status_code == 200, r.text
            m = r.json()["material"]
            assert m["maps"] == list(MS.MAP_KINDS), m["maps"]
            assert m["pattern"]["id"] == "briques"
            assert m["pattern"]["params"]["rangs"] == 6
            assert m["source"]["kind"] == "pattern"
            with Image.open(MS.map_path(m["id"], "height")) as im:
                st = PBR.stats(im.convert("L"))
            assert st["span"] > 8, st
            ok(f"POST /materials/patterns/briques : matière {m['id']} complète, "
               f"hauteur RELUE sur le disque d'amplitude {st['span']}")

            # la hauteur du GÉNÉRATEUR l'emporte sur celle dérivée de la couleur
            # (le plan l'écrivait sans le vérifier) : on la refait à l'identique
            from app.services import pattern_service as PS
            refaite = PS.generer("briques", 512, PS.clean_params("briques", {"rangs": 6}), 0)["height"]
            with Image.open(MS.map_path(m["id"], "height")) as im:
                lue = im.convert("L")
            from PIL import ImageChops, ImageStat
            ecart = ImageStat.Stat(ImageChops.difference(lue, refaite)).mean[0]
            assert lue.size == refaite.size and ecart < 1.0, (lue.size, ecart)
            ok(f"la carte height sur le disque EST celle du générateur (écart moyen {ecart:.2f})")

            r = await c.post("/api/materials/patterns/briques",
                             json={"res": 256, "params": {"rangs": 999, "joint": "x"}, "seed": "7"})
            assert r.status_code == 200, r.text
            pm = r.json()["material"]["pattern"]
            assert pm["params"]["rangs"] == 32 and pm["params"]["joint"] == 0.1 and pm["seed"] == 7, pm
            ok("réglages bornés jusque dans la fiche (rangs 999 -> 32, joint pourri -> défaut), graine gardée")

            r = await c.post("/api/materials/patterns/nexistepas", json={})
            assert r.status_code == 400 and "nexistepas" in r.json()["detail"]
            ok("générateur inconnu : 400 nommé")

    print(f"\nOK — {PASS} assertions groupées vertes (générateurs, routes)")


if __name__ == "__main__":
    asyncio.run(main())
