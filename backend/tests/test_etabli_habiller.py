# -*- coding: utf-8 -*-
"""Une matière PAR PARTIE dans l'Établi — routes /etabli/masques (lecture) et /etabli/habiller (une version de
plus, par la seule plume). T098, plan-matieres T15.

BANC-MIROIR : le dossier du job est listé AVANT et APRÈS la lecture des masques ; la v1 est relue à l'octet après
l'habillage ; la fiche est lue dans report.json.

Run (depuis backend/) : python tests/test_etabli_habiller.py
"""
import asyncio
import json
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

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def _fabriquer_matiere():
    mat = MS.create_material(name="Pierre bleue", prompt="blue stone",
                             full_prompt=MS.build_full_prompt("blue stone"),
                             source={"kind": "prompt", "model": "flux", "filename": None},
                             res=64, seamless=True, seam={"before": 1.0, "after": 0.0})
    MS.save_maps(mat["id"], {"basecolor": Image.new("RGB", (64, 64), (60, 90, 150)),
                             "normal": Image.new("RGB", (64, 64), (128, 128, 255)),
                             "orm": Image.new("RGB", (64, 64), (255, 180, 0)),
                             "roughness": Image.new("L", (64, 64), 180),
                             "metallic": Image.new("L", (64, 64), 0),
                             "ao": Image.new("L", (64, 64), 255)})
    return MS.read_material(mat["id"])


def _derniere_fiche(job):
    from app.services import mesh_report
    reg = json.loads((mesh_report.job_dir(job) / "report.json").read_text(encoding="utf-8"))
    return reg["entries"][-1]


async def main():
    global PASS
    from app.services import gltf_builder, mesh_edit, mesh_report, print3d
    # un job d'Établi minimal : model.glb dans son dossier
    job = "banc_habiller"
    d = mesh_report.job_dir(job)
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(gltf_builder.build_glb({}, None, "cube",
                                                         "banc"))
    mat = _fabriquer_matiere()          # helper local, cf. test_material_naming

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t",
                           timeout=180) as c:
        # ══ 1 · les masques se LISENT, sans rien écrire ══════════════════════
        avant = sorted(p.name for p in d.iterdir())
        r = await c.get(f"/api/etabli/masques?job={job}&version=1")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("model/gltf-binary")
        doc, binc = mesh_edit.lire_glb(r.content)
        assert "COLOR_0" in doc["meshes"][0]["primitives"][0]["attributes"]
        assert sorted(p.name for p in d.iterdir()) == avant, "une écriture !"
        ok("GET /etabli/masques : un GLB à COLOR_0, et RIEN d'écrit sur le "
           "disque du job")

        # ══ 2 · l'habillage écrit une VERSION, par la seule plume ════════════
        r = await c.post("/api/etabli/habiller",
                         json={"job": job, "version": 1,
                               "lots": [{"cible": "tout", "mid": mat["id"]}]})
        assert r.status_code == 200, r.text
        fiche = r.json()
        assert (d / "model.v2.glb").is_file(), sorted(p.name for p in d.iterdir())
        assert (d / "model.glb").read_bytes() == \
            gltf_builder.build_glb({}, None, "cube", "banc"), \
            "la version 1 a été touchée"
        doc2, _ = mesh_edit.lire_glb((d / "model.v2.glb").read_bytes())
        assert doc2["materials"][-1]["name"] == mat["name"]
        assert {p.get("material") for m in doc2["meshes"]
                for p in m["primitives"]} == {len(doc2["materials"]) - 1}
        derniere = _derniere_fiche(job)
        assert "habiller" in json.dumps(derniere, ensure_ascii=False)
        assert mat["id"] in json.dumps(derniere, ensure_ascii=False)
        ok("POST /etabli/habiller : model.v2.glb écrit par mesh_edit, v1 "
           "intacte à l'octet, la fiche nomme l'opération et la matière")

        # ══ 3 · les refus, avec le même vocabulaire que les cinq voisines ════
        for corps, code, mot in (
                ({"job": job, "version": 0,
                  "lots": [{"cible": "tout", "mid": mat["id"]}]}, 400, "version"),
                ({"job": job, "version": 1, "lots": []}, 400, "lots"),
                ({"job": job, "version": 1,
                  "lots": [{"cible": "tout", "mid": "mat_zzzzzzzz"}]}, 404,
                 "mat_zzzzzzzz"),
                # « ../evade » : la porte commune APLATIT le nom (evade) — aucune
                # évasion possible, donc 404 sur un job inexistant, comme les
                # écritures voisines (le plan attendait un 400)
                ({"job": "../evade", "version": 1,
                  "lots": [{"cible": "tout", "mid": mat["id"]}]}, 404, "evade/model.glb"),
                ({"job": job, "version": 9,
                  "lots": [{"cible": "tout", "mid": mat["id"]}]}, 404,
                 "model.v9.glb")):
            r = await c.post("/api/etabli/habiller", json=corps)
            assert r.status_code == code, (corps, r.status_code, r.text)
            assert mot in r.json()["detail"], (mot, r.text)
        ok("cinq refus : version, lots vide, matière inconnue, job évadé, "
           "version absente — même porte que les cinq écritures voisines")

        # ══ 4 · deux lots de cibles différentes, même matière -> un matériau ═
        r = await c.post("/api/etabli/habiller",
                         json={"job": job, "version": 1,
                               "lots": [{"cible": "noeud", "index": 0, "mid": mat["id"]},
                                        {"cible": "materiau", "index": 0, "mid": mat["id"]}]})
        assert r.status_code == 200, r.text
        v = r.json()["version"]
        doc3, _ = mesh_edit.lire_glb((d / f"model.v{v}.glb").read_bytes())
        assert sum(1 for m in doc3["materials"] if m.get("name") == mat["name"]) == 1, doc3["materials"]
        assert print3d.bbox(print3d.lire_glb_triangles((d / f"model.v{v}.glb").read_bytes())) == \
            print3d.bbox(print3d.lire_glb_triangles((d / "model.glb").read_bytes()))
        ok(f"v{v} : nœud ET matériau visés, une seule matière glTF, géométrie intacte")

    print(f"\nOK — {PASS} assertions groupées vertes (habiller par partie)")


if __name__ == "__main__":
    asyncio.run(main())
