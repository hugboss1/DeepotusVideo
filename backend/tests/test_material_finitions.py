# -*- coding: utf-8 -*-
"""Finitions nommées, ESSAYÉES avant d'être posées (T098, plan-matieres T16).

BANC-MIROIR : le GLB d'aperçu est reparsé ; la matière est RELUE sur disque après l'aperçu.

Run (depuis backend/) : python tests/test_material_finitions.py
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
from app.services import mesh_edit                             # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def _fabriquer_matiere():
    mat = MS.create_material(name="Essai", prompt="test", full_prompt=MS.build_full_prompt("test"),
                             source={"kind": "prompt", "model": "flux", "filename": None},
                             res=64, seamless=True, seam={"before": 1.0, "after": 0.0})
    MS.save_maps(mat["id"], {"basecolor": Image.new("RGB", (64, 64), (120, 120, 120)),
                             "normal": Image.new("RGB", (64, 64), (128, 128, 255)),
                             "roughness": Image.new("L", (64, 64), 128),
                             "metallic": Image.new("L", (64, 64), 0),
                             "ao": Image.new("L", (64, 64), 255),
                             "height": Image.new("L", (64, 64), 128),
                             "emissive": Image.new("RGB", (64, 64), (0, 0, 0)),
                             "orm": Image.new("RGB", (64, 64), (255, 128, 0))})
    return MS.read_material(mat["id"])


async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=120) as c:
        # ══ 1 · quatre finitions de plus, nommées ═══════════════════════════
        d = (await c.get("/api/materials/presets")).json()
        ids = [p["id"] for p in d["presets"]]
        for neuf in ("laque", "cuir", "emissif_anime", "metal_brosse_aniso"):
            assert neuf in ids, ids
        for p in d["presets"]:
            assert p["label"] and isinstance(p["props"], dict), p
            assert p.get("famille") in ("metal", "surface", "verre",
                                        "lumiere", "organique"), p
        ok(f"{len(ids)} préréglages, quatre de plus, chacun rangé dans une "
           f"famille")

        # ══ 2 · l'aperçu APPLIQUE la finition sans toucher la matière ═══════
        m = _fabriquer_matiere()
        avant = MS.read_material(m["id"])["props"]["roughness"]
        r = await c.get(f"/api/materials/{m['id']}/preview.glb?finish=laque")
        assert r.status_code == 200 and r.content[:4] == b"glTF", r.status_code
        doc, _ = mesh_edit.lire_glb(r.content)
        pbr = doc["materials"][0]["pbrMetallicRoughness"]
        # les niveaux restent CUITS : les facteurs valent 1.0, c'est la carte
        # qui porte la finition
        assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0
        assert MS.read_material(m["id"])["props"]["roughness"] == avant, \
            "l'aperçu a écrit dans la matière"
        ok("preview.glb?finish=laque : la finition est appliquée à l'aperçu, "
           "la matière n'a pas bougé d'un iota")

        # ══ 3 · deux finitions différentes donnent deux GLB différents ══════
        a = (await c.get(f"/api/materials/{m['id']}/preview.glb?finish=laque")).content
        b = (await c.get(f"/api/materials/{m['id']}/preview.glb?finish=cuir")).content
        assert a != b, "le cache sert le même GLB pour deux finitions"
        c0 = (await c.get(f"/api/materials/{m['id']}/preview.glb")).content
        assert a != c0 and b != c0
        ok("la finition entre dans l'empreinte du cache : trois GLB "
           "différents pour trois finitions")

        # ══ 4 · une finition inconnue se refuse ═════════════════════════════
        r = await c.get(f"/api/materials/{m['id']}/preview.glb?finish=chose")
        assert r.status_code == 400 and "chose" in r.json()["detail"]
        ok("finition inconnue : 400 nommé")

        # ══ 5 · l'émissif animé DIT que l'animation n'est pas dans le fichier ═
        d = (await c.get("/api/materials/presets")).json()
        em = next(p for p in d["presets"] if p["id"] == "emissif_anime")
        assert em["anime"]["hz"] > 0 and "glTF" in em["anime"]["note"], em
        ok("émissif animé : la pulsation est un effet d'aperçu, et la recette le dit")

    print(f"\nOK — {PASS} assertions groupées vertes (finitions)")


if __name__ == "__main__":
    asyncio.run(main())
