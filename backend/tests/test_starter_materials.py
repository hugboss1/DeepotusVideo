# -*- coding: utf-8 -*-
"""Catalogue de démarrage des matières — R10c P4, trente matières CC0.

AUCUN RÉSEAU : le banc fabrique un faux catalogue sur disque, exactement dans
la forme que le script de build produit, puis exerce le module runtime et le
`--check` du script. La liste des trente identifiants est vérifiée ICI, en
littéral — c'est un contrat, pas un détail de mise en œuvre.

Run (depuis backend/) : python tests/test_starter_materials.py
"""
import importlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

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

from PIL import Image                                          # noqa: E402

from app.services import material_store as MS                  # noqa: E402
import app.services.starter_materials as SM                    # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = RACINE / "scripts" / "build_materials_catalog.py"

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


# ══ 1 · trente identifiants, six familles, aucun doublon ═══════════════════
sys.path.insert(0, str(RACINE / "scripts"))
build = importlib.import_module("build_materials_catalog")
slugs = [a["slug"] for a in build.ASSETS]
assert len(slugs) == 30, len(slugs)
assert len(set(slugs)) == 30, "doublon dans la liste"
familles = sorted({a["family"] for a in build.ASSETS})
assert familles == ["beton_terrain", "bois", "metaux", "murs", "sols",   # ordre TRIÉ (le plan inversait les deux premiers)
                    "tissus"], familles
for a in build.ASSETS:
    assert a["name"] and a["family"] and a["slug"].islower(), a
    assert " " not in a["slug"], a
ok(f"trente identifiants Poly Haven distincts, six familles "
   f"({', '.join(familles)})")

# ══ 2 · le faux catalogue, dans la forme exacte du build ═══════════════════
DOSSIER = pathlib.Path(_tmp) / "catalogue"
(DOSSIER / "brick_wall_001").mkdir(parents=True)
for carte, couleur in (("basecolor", (150, 70, 60)), ("normal", (128, 128, 255)),
                       ("roughness", (170, 170, 170))):
    Image.new("RGB", (128, 128), couleur).save(
        DOSSIER / "brick_wall_001" / f"{carte}.jpg", quality=82)
CAT = {"version": 1, "generated_at": "2026-09-03T00:00:00Z",
       "source": {"name": "Poly Haven", "url": "https://polyhaven.com",
                  "license": "CC0-1.0",
                  "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"},
       "families": [{"id": "murs", "name": "Murs & briques", "count": 1}],
       "materials": [{"id": "brick_wall_001", "name": "Brick Wall 001",
                      "family": "murs", "tags": ["red", "rough"],
                      "authors": {"Rob Tuytel": "Processing"},
                      "scale": "1.5x1.5", "dimensions": [3000, 3000],
                      "maps": {"basecolor": "brick_wall_001/basecolor.jpg",
                               "normal": "brick_wall_001/normal.jpg",
                               "roughness": "brick_wall_001/roughness.jpg"},
                      "bytes": 0}]}
CAT["materials"][0]["bytes"] = sum(
    (DOSSIER / v).stat().st_size for v in CAT["materials"][0]["maps"].values())
(DOSSIER / "catalog.json").write_text(json.dumps(CAT, ensure_ascii=False),
                                      encoding="utf-8")
(DOSSIER / "NOTICE.txt").write_text("Poly Haven — CC0 1.0\n", encoding="utf-8")

SM.STARTER_DIR = DOSSIER
SM.CATALOG_FILE = DOSSIER / "catalog.json"
SM.reset_cache()
cat = SM.load()
assert cat["available"] is True and len(cat["materials"]) == 1
assert SM.browse(query="brick") and not SM.browse(query="zzz")
assert SM.browse(family="murs") and not SM.browse(family="metaux")
ok("catalogue lu, recherche par nom et filtre par famille")

# ══ 3 · un import devient une matière ORDINAIRE ════════════════════════════
faits = SM.importer(["brick_wall_001"])
assert len(faits) == 1
mid = faits[0]["id"]
m = MS.read_material(mid)
assert MS.MID_RE.match(mid), mid
assert m["maps"] == list(MS.MAP_KINDS), m["maps"]
assert m["source"]["kind"] == "catalog", m["source"]
assert m["credit"]["license"] == "CC0-1.0", m["credit"]
assert "Poly Haven" in m["credit"]["source"], m["credit"]
assert "Rob Tuytel" in m["credit"]["author"], m["credit"]
d = MS.material_dir(mid)
for k in MS.MAP_KINDS:
    assert (d / f"{k}.png").is_file(), k
assert m["map_stats"], "les statistiques de map n'ont pas été calculées"
# les cartes MESURÉES gagnent sur leurs dérivées : la normale livrée est la
# plaque (128,128,255) du catalogue, la rugosité sa valeur 170 — une dérivée
# depuis la couleur unie aurait donné autre chose (et le plan ne le vérifiait pas)
with Image.open(d / "normal.png") as im:
    nx = im.convert("RGB").getpixel((40, 40))
with Image.open(d / "roughness.png") as im:
    rg = im.convert("L").getpixel((40, 40))
assert all(abs(a - b) <= 3 for a, b in zip(nx, (128, 128, 255))), nx
assert abs(rg - 170) <= 3, rg
ok(f"import : {mid} porte les HUIT cartes sur disque — trois mesurées par "
   f"Poly Haven (normale {nx}, rugosité {rg} relues : ELLES ont gagné), cinq "
   f"dérivées localement — et son crédit CC0")

# ══ 3b · les ROUTES (absentes du plan) ═════════════════════════════════════
import asyncio                                                 # noqa: E402
import types                                                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [], "seed": 0}


_stub.subscribe_async = _sub
sys.modules.setdefault("fal_client", _stub)
from httpx import ASGITransport, AsyncClient                   # noqa: E402

from app.main import app                                       # noqa: E402


async def _routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=120) as c:
        d = (await c.get("/api/materials/catalog")).json()
        assert d["available"] is True and len(d["materials"]) == 1 and d["source"]["license"] == "CC0-1.0", d
        assert len((await c.get("/api/materials/catalog?q=zzz")).json()["materials"]) == 0
        j = await c.get("/api/materials/catalog/brick_wall_001/basecolor.jpg")
        assert j.status_code == 200 and j.content[:3] == b"\xff\xd8\xff"
        assert (await c.get("/api/materials/catalog/brick_wall_001/height.jpg")).status_code == 404
        assert (await c.get("/api/materials/catalog/inconnu/basecolor.jpg")).status_code == 404
        for corps in ({}, {"ids": []}, {"ids": "brick"}, {"ids": ["x"] * 31}):
            r = await c.post("/api/materials/catalog/import", json=corps)
            assert r.status_code == 400, (corps, r.status_code)
        assert (await c.post("/api/materials/catalog/import", json={"ids": ["inconnu"]})).status_code == 404
        r = await c.post("/api/materials/catalog/import", json={"ids": ["brick_wall_001"]})
        assert r.status_code == 200 and r.json()["materials"][0]["source"]["kind"] == "catalog", r.text


asyncio.run(_routes())
# le confinement : un chemin de carte qui sortirait du catalogue est refusé
SM._cache["materials"][0]["maps"]["evade"] = "../../../t.db"
try:
    SM.carte_path("brick_wall_001", "evade")
    raise AssertionError("un chemin hors catalogue est passé")
except SM.StarterError as e:
    assert e.status == 400, e.status
del SM._cache["materials"][0]["maps"]["evade"]
ok("routes : catalogue, recherche, carte JPEG servie (404 pour une carte ou une matière absente), "
   "import refusé sur corps vide/mauvais/> 30 et accepté sinon ; chemin hors catalogue -> 400")

# ══ 4 · un identifiant inconnu se refuse en le nommant ═════════════════════
try:
    SM.importer(["pas_dans_le_catalogue"])
    raise AssertionError("aurait dû lever")
except SM.StarterError as e:
    # la phrase EXACTE : un refus venu plus loin (« carte absente de ») nomme
    # aussi l'identifiant, et laissait vert un catalogue qui inventait l'entrée
    assert e.status == 404 and "« pas_dans_le_catalogue » absente du catalogue" in e.message, e.message
    refus_msg = e.message          # `e` disparaît à la sortie du bloc (Python 3) : le plan le relisait après
ok(f"identifiant inconnu : 404 nommé — « {refus_msg[:60]} »")

# ══ 4b · le crédit voyage dans l'ARCHIVE (le plan l'écrivait sans le vérifier)
import io                                                      # noqa: E402
import zipfile                                                 # noqa: E402
mi = MS.read_material(mid)
with zipfile.ZipFile(io.BytesIO(MS.export_zip(mi, MS.load_maps(mid), "standard"))) as z:
    lz = z.read("LISEZMOI.txt").decode("utf-8")
    mjs = json.loads(z.read("material.json").decode("utf-8"))
assert "Source : Poly Haven — Rob Tuytel — CC0-1.0" in lz, lz[-400:]
assert mjs["credit"]["license"] == "CC0-1.0", mjs.get("credit")
ok("archive : le LISEZMOI et material.json portent le crédit CC0 de la matière importée")

# ══ 5 · --check concorde, et rougit quand un fichier manque ════════════════
r = subprocess.run([sys.executable, str(SCRIPT), "--check", "--out",
                    str(DOSSIER)], capture_output=True, timeout=300)
sortie = r.stdout.decode("utf-8", "replace")
assert r.returncode == 0, sortie + r.stderr.decode("utf-8", "replace")
assert "concordent" in sortie, sortie
# un fichier ORPHELIN (présent, mais déclaré nulle part) rougit aussi : il
# partirait dans l'installeur sans que le catalogue le connaisse
orph = DOSSIER / "brick_wall_001" / "oublie.jpg"
orph.write_bytes(b"x")
r1 = subprocess.run([sys.executable, str(SCRIPT), "--check", "--out", str(DOSSIER)],
                    capture_output=True, timeout=300)
assert r1.returncode == 1 and "ORPHELIN" in r1.stdout.decode("utf-8", "replace"), r1.stdout
orph.unlink()
(DOSSIER / "brick_wall_001" / "normal.jpg").unlink()
r2 = subprocess.run([sys.executable, str(SCRIPT), "--check", "--out",
                     str(DOSSIER)], capture_output=True, timeout=300)
assert r2.returncode == 1, r2.stdout
assert "MANQUANT" in r2.stdout.decode("utf-8", "replace")
ok("--check : vert quand tout est là, rouge et parlant quand une carte "
   "manque — la garde de packaging tient")

print(f"\nOK — {PASS} assertions groupées vertes (catalogue de matières CC0)")
