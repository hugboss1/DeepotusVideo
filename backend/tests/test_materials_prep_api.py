# -*- coding: utf-8 -*-
"""Material Forge P1 — la préparation d'une photo TRAVERSE l'application :
route d'aperçu, job de génération, fiche, material.json, LISEZMOI.

BANC-MIROIR : la base color est relue DEPUIS LE DISQUE de la matière, et le
LISEZMOI depuis l'archive ZIP réellement écrite.

Run (depuis backend/) : python tests/test_materials_prep_api.py
"""
import asyncio
import base64
import io
import json
import math
import os
import pathlib
import sys
import tempfile
import types
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageChops                              # noqa: E402
from httpx import ASGITransport, AsyncClient                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [{"url": "http://fal.test/out.png"}], "seed": 7}


_stub.subscribe_async = _sub
sys.modules["fal_client"] = _stub

from app.config import settings                                # noqa: E402
from app.main import app                                       # noqa: E402
from app.services import material_store as MS                  # noqa: E402
from app.services import photo_prep as PP                      # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


QUAD = [[38, 22], [301, 61], [274, 289], [17, 236]]


def photo_de_biais(nom="mur.png"):
    """Une tuile haute fréquence, éclairée en diagonale, puis vue de biais —
    et déposée dans la Bibliothèque comme le ferait un import."""
    w = h = 256
    plate = Image.new("RGB", (w, h))
    px = plate.load()
    for y in range(h):
        for x in range(w):
            v = 128.0
            for kx, ky, amp in ((5, 4, 40.0), (11, 7, 22.0)):
                v += amp * math.sin(2 * math.pi * kx * x / w) \
                         * math.cos(2 * math.pi * ky * y / h)
            v = max(6.0, min(249.0, v))
            px[x, y] = (int(v), int(v * 0.84 + 14), int(v * 0.62 + 32))
    ramp = Image.new("L", (w, h))
    d = ramp.load()
    for y in range(h):
        for x in range(w):
            d[x, y] = int(round(255.0 * (0.35 + 0.65 *
                                         (x / (w - 1) + y / (h - 1)) / 2.0)))
    lit = Image.merge("RGB", tuple(ImageChops.multiply(c, ramp)
                                   for c in plate.split()))
    biais = lit.transform((320, 320), Image.PERSPECTIVE,
                          PP.perspective_coeffs(
                              [(0.0, 0.0), (255.0, 0.0), (255.0, 255.0),
                               (0.0, 255.0)],
                              [tuple(p) for p in QUAD]), Image.BICUBIC)
    p = settings.images_path / nom
    biais.save(p, format="PNG")
    return nom


async def attendre(c, jid):
    for _ in range(400):
        st = (await c.get(f"/api/materials/jobs/{jid}")).json()
        if st["status"] in ("done", "failed"):
            return st
        await asyncio.sleep(0.05)
    raise AssertionError("job jamais terminé")


async def main():
    global PASS
    lib = photo_de_biais()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t",
                           timeout=120) as c:

        # ══ 1 · l'aperçu ne crée rien et rend les deux chiffres ═════════════
        avant = len(MS.list_materials())
        r = await c.post("/api/materials/prep/preview",
                         json={"filename": lib, "prep": {"quad": QUAD,
                                                         "delight": 1.0}})
        assert r.status_code == 200, r.text
        d = r.json()
        m = d["mesure"]
        # seuils calés sur la mesure du 06/10 (9,36 -> 2,84, -69,6 %), pas sur le
        # -85 % que le plan annonçait : voir test_photo_prep.py, section 2.
        assert m["lowfreq_sd_before"] > 8.0, m
        assert m["lowfreq_sd_after"] < 0.35 * m["lowfreq_sd_before"], m
        assert m["baisse_pct"] > 65.0, m
        assert d["apercu"]["png"].startswith("data:image/png;base64,")
        brut = base64.b64decode(d["apercu"]["png"].split(",", 1)[1])
        with Image.open(io.BytesIO(brut)) as im:
            assert im.size == (d["apercu"]["w"], d["apercu"]["h"])
            assert im.size[0] == im.size[1] <= 512, im.size
        assert len(MS.list_materials()) == avant
        ok(f"aperçu : {m['lowfreq_sd_before']} -> {m['lowfreq_sd_after']} "
           f"({m['baisse_pct']:.0f} % de moins), PNG carré ≤ 512, "
           f"aucune matière créée")

        # ══ 2 · les refus, avant toute dépense ══════════════════════════════
        for prep, mot in (({"quad": [[0, 0], [50, 50], [100, 100], [150, 150]],
                            "delight": 1.0}, "align"),
                          ({"quad": [[9, 9], [9, 9], [200, 5], [200, 200]],
                            "delight": 1.0}, "confondus")):
            r = await c.post("/api/materials/prep/preview",
                             json={"filename": lib, "prep": prep})
            assert r.status_code == 400, (r.status_code, r.text)
            assert mot in r.json()["detail"].lower(), r.text
            r = await c.post("/api/materials/generate",
                             json={"filename": lib, "prep": prep, "res": 512})
            assert r.status_code == 400, (r.status_code, r.text)
        ok("quadrilatère dégénéré : 400 parlant sur l'aperçu ET sur la "
           "génération — refusé AVANT de lancer le job")

        # ══ 3 · le job applique la préparation, la fiche la garde ═══════════
        r = await c.post("/api/materials/generate",
                         json={"filename": lib, "res": 512, "seamless": True,
                               "name": "Mur redressé",
                               "prep": {"quad": QUAD, "delight": 1.0}})
        assert r.status_code == 200, r.text
        st = await attendre(c, r.json()["job_id"])
        assert st["status"] == "done", st
        mat = st["material"]
        prep = mat["source"]["prep"]
        assert prep["quad"] == QUAD, prep
        assert prep["delight"] == 1.0
        assert prep["lowfreq_sd_after"] < 0.35 * prep["lowfreq_sd_before"], prep
        ok(f"job : source.prep gardé dans la fiche "
           f"({prep['lowfreq_sd_before']} -> {prep['lowfreq_sd_after']})")

        # ══ 4 · le PNG SUR LE DISQUE porte la correction ════════════════════
        p = MS.map_path(mat["id"], "basecolor")
        assert p.is_file()
        with Image.open(p) as im:
            base = im.convert("RGB")
            assert base.size == (512, 512), base.size
            sd = PP.lowfreq_sd(base)
        assert sd < 6.0, sd
        ok(f"basecolor relue sur le disque : écart-type basse fréquence "
           f"{sd} (< 6,0) — la correction est DANS le fichier livré")

        # ══ 5 · l'archive le dit ════════════════════════════════════════════
        r = await c.get(f"/api/materials/{mat['id']}/export?format=zip")
        assert r.status_code == 200, r.text
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            lisez = z.read("LISEZMOI.txt").decode("utf-8")
            mj = json.loads(z.read("material.json").decode("utf-8"))
        assert "Photo préparée" in lisez, lisez[:600]
        assert "quatre coins" in lisez and "basse fréquence" in lisez
        assert mj["source"]["prep"]["quad"] == QUAD, mj["source"]
        ok("archive : LISEZMOI et material.json disent ce qui a été fait à "
           "la photo")

        # ══ 6 · sans prep, rien ne change ═══════════════════════════════════
        r = await c.post("/api/materials/generate",
                         json={"filename": lib, "res": 512, "name": "Brut"})
        st2 = await attendre(c, r.json()["job_id"])
        assert st2["status"] == "done", st2
        assert st2["material"]["source"]["prep"] is None
        r = await c.get(f"/api/materials/{st2['material']['id']}/export?format=zip")
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            assert "Photo préparée" not in z.read("LISEZMOI.txt").decode("utf-8")
        ok("sans prep : source.prep vaut None et le LISEZMOI n'invente rien")

        # ══ 7 · une entrée pourrie ne fait jamais tomber la route ═══════════
        for mauvais in ({"quad": "oui"}, {"quad": [[1, 2]]}, {"delight": "x"},
                        {"delight": 12}, {"quad": [[1, "a"], [2, 3], [4, 5],
                                                   [6, 7]]}, [], "prep", 7):
            r = await c.post("/api/materials/prep/preview",
                             json={"filename": lib, "prep": mauvais})
            assert r.status_code == 200, (mauvais, r.status_code, r.text)
        assert MS.clean_prep({"delight": 0}) is None
        assert MS.clean_prep(None) is None
        assert MS.prep_note(None) == "" and MS.prep_note({}) == ""
        ok("entrée pourrie : jamais de 500 — le bloc prep tombe à ce qu'il "
           "sait lire, et un bloc vide vaut None")

    print(f"\nOK — {PASS} assertions groupées vertes (préparation de photo, "
          f"bout en bout)")


asyncio.run(main())
