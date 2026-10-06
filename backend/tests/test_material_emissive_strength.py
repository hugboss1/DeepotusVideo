# -*- coding: utf-8 -*-
"""L'intensité émissive ne change plus la TEINTE (KHR_materials_emissive_strength).

Mesuré le 06/10 sur preview.glb?finish=emissif_anime (#ff8a1f, intensité 3.0) :
linéaire [1, 0.254, 0.014] x 3 puis borné à [0,1] donnait [1, 0.76, 0.041] —
l'orange devenait jaune. La couleur va désormais telle quelle dans
emissiveFactor et l'intensité > 1 dans l'extension.

BANC-MIROIR : le GLB d'aperçu est reparsé depuis la route.

Run (depuis backend/) : python tests/test_material_emissive_strength.py
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

EXT = "KHR_materials_emissive_strength"
PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def _lin(hexa):
    out = []
    for i in (1, 3, 5):
        c = int(hexa[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def _proche(a, b, tol=1e-5):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


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
                             "emissive": Image.new("RGB", (64, 64), (255, 255, 255)),
                             "orm": Image.new("RGB", (64, 64), (255, 128, 0))})
    return MS.read_material(mat["id"])


async def _doc(c, url):
    r = await c.get(url)
    assert r.status_code == 200 and r.content[:4] == b"glTF", r.status_code
    doc, _ = mesh_edit.lire_glb(r.content)
    return doc, doc["materials"][0]


async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=120) as c:
        m = _fabriquer_matiere()
        base = f"/api/materials/{m['id']}/preview.glb"

        # ══ 1 · émissif animé : la couleur reste ORANGE, l'intensité dans l'extension ═
        doc, mat = await _doc(c, base + "?finish=emissif_anime")
        attendu = _lin("#ff8a1f")
        assert _proche(mat["emissiveFactor"], attendu), \
            (mat["emissiveFactor"], attendu)
        # la teinte, mesurée comme rapport G/R : 0.254 et non 0.76
        g_r = mat["emissiveFactor"][1] / mat["emissiveFactor"][0]
        assert abs(g_r - attendu[1] / attendu[0]) < 1e-4, g_r
        ok(f"emissiveFactor = couleur linéaire {[round(x, 3) for x in attendu]} "
           f"(G/R = {g_r:.3f}, plus de virage au jaune)")
        assert mat["extensions"][EXT] == {"emissiveStrength": 3.0}, mat.get("extensions")
        assert EXT in doc["extensionsUsed"], doc.get("extensionsUsed")
        assert EXT not in (doc.get("extensionsRequired") or []), doc.get("extensionsRequired")
        ok("KHR_materials_emissive_strength = 3.0, dans extensionsUsed, PAS requise")

        # ══ 2 · intensité 0.0 (le défaut) : aucune émission, aucune extension ═
        r = await c.patch(f"/api/materials/{m['id']}",
                          json={"props": {"emissive": "#ff8a1f", "emissive_strength": 0.0}})
        assert r.status_code == 200, r.text
        doc, mat = await _doc(c, base)
        assert mat["emissiveFactor"] == [0.0, 0.0, 0.0], mat["emissiveFactor"]
        assert EXT not in (mat.get("extensions") or {}), mat.get("extensions")
        assert EXT not in (doc.get("extensionsUsed") or []), doc.get("extensionsUsed")
        ok("intensité 0.0 : emissiveFactor noir et pas d'extension — un lecteur "
           "sans l'extension n'allume rien non plus")

        # ══ 3 · intensité 1.0 : la couleur seule, l'extension omise ══════════
        await c.patch(f"/api/materials/{m['id']}", json={"props": {"emissive_strength": 1.0}})
        doc, mat = await _doc(c, base)
        assert _proche(mat["emissiveFactor"], attendu), mat["emissiveFactor"]
        assert EXT not in (mat.get("extensions") or {}), mat.get("extensions")
        assert EXT not in (doc.get("extensionsUsed") or []), doc.get("extensionsUsed")
        ok("intensité 1.0 : couleur linéaire, extension omise")

        # ══ 4 · intensité 0.5 : repliée dans le facteur (exact, sans borne) ══
        await c.patch(f"/api/materials/{m['id']}", json={"props": {"emissive_strength": 0.5}})
        doc, mat = await _doc(c, base)
        assert _proche(mat["emissiveFactor"], [x * 0.5 for x in attendu]), mat["emissiveFactor"]
        assert EXT not in (mat.get("extensions") or {}), mat.get("extensions")
        ok("intensité 0.5 : facteur = couleur x 0.5, pas d'extension (rendu "
           "identique partout)")

    print(f"\nOK — {PASS} assertions groupées vertes (intensité émissive)")


if __name__ == "__main__":
    asyncio.run(main())
