# -*- coding: utf-8 -*-
"""Material Forge P5 — la carte height DÉCLARE sa hauteur physique, et le relief imprimé du Forge 3D la consomme
(T097, plan 2026-09-03-plan-matieres T9, corrigé sur le terrain).

LE PLAN SE TROMPAIT DE MODÈLE : il lisait `relief.mat`, champ qui n'existe pas. Dans le graphe du Forge 3D, la
matière vit dans un nœud `material` CHAÎNÉ au relief ; la profondeur se résout donc là où les deux se rencontrent
(`forge3d.profondeur_relief`, appelée par `forge3d_apercu.element_local`). Et un relief SANS profondeur saisie reste
« auto » (None) après `clean_graph` — sinon 0,6 était écrit dans le graphe stocké et la matière ne gagnait jamais.

BANC-MIROIR : la dernière section mesure la GÉOMÉTRIE produite (étendue en z du maillage), pas un paramètre.

Run (depuis backend/) : python tests/test_material_height_mm.py
"""
import io
import json
import os
import pathlib
import sys
import tempfile
import zipfile

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

from app.services import material_store as MS                  # noqa: E402
from app.services.cards import forge3d                         # noqa: E402
from app.services.cards import forge3d_scene as FS             # noqa: E402

PASS = 0
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def fabriquer(h_mm=None):
    mat = MS.create_material(name="Vitrail bleu", prompt="stained glass",
                             full_prompt=MS.build_full_prompt("stained glass"),
                             source={"kind": "prompt", "model": "flux", "filename": None},
                             res=64, seamless=True, seam={"before": 8.0, "after": 0.0})
    haut = Image.new("L", (64, 64), 0)
    for y in range(20, 44):
        for x in range(64):
            haut.putpixel((x, y), 255)
    MS.save_maps(mat["id"], {
        "basecolor": Image.new("RGB", (64, 64), (40, 80, 160)), "height": haut,
        "ao": Image.new("L", (64, 64), 220), "roughness": Image.new("L", (64, 64), 160),
        "metallic": Image.new("L", (64, 64), 10), "normal": Image.new("RGB", (64, 64), (128, 128, 255)),
        "emissive": Image.new("RGB", (64, 64), (0, 0, 0)), "orm": Image.new("RGB", (64, 64), (220, 160, 10))})
    m = MS.read_material(mat["id"])
    if h_mm is not None:
        m["height_mm"] = h_mm
        MS.write_material(m)
    return MS.read_material(mat["id"]), haut


# ══ 1 · le champ existe, il est borné, il ne lève jamais ═══════════════════
m, _ = fabriquer()
assert m["height_mm"] == 0.0, m["height_mm"]
for brut, veut in ((2.4, 2.4), ("3.5", 3.5), (-1, 0.0), (999, 20.0), (None, 0.0), ("abc", 0.0),
                   (float("nan"), 0.0)):
    got = MS.normalize_material({"height_mm": brut}, m["id"])["height_mm"]
    assert abs(got - veut) < 1e-9, (brut, got, veut)
ok("height_mm : défaut 0 (non renseigné), borné à [0, 20] mm, jamais d'exception sur une entrée pourrie")

# ══ 2 · la fiche, material.json, le LISEZMOI et le bordereau le portent ════
m, haut = fabriquer(2.4)
maps = MS.load_maps(m["id"])
zip_octets = MS.export_zip(m, MS.bake_levels(maps, m["props"]), "standard")
with zipfile.ZipFile(io.BytesIO(zip_octets)) as z:
    lisez = z.read("LISEZMOI.txt").decode("utf-8")
    mj = json.loads(z.read("material.json").decode("utf-8"))
assert mj["height_mm"] == 2.4, mj.get("height_mm")
assert "2.4 mm" in lisez and "aucun moteur de jeu" in lisez, lisez[:900]
assert MS.export_manifest(m, "zip", "standard")["height_mm"] == 2.4
sans, _ = fabriquer()
with zipfile.ZipFile(io.BytesIO(MS.export_zip(sans, MS.load_maps(sans["id"]), "standard"))) as z:
    assert "non renseignée" in z.read("LISEZMOI.txt").decode("utf-8")
ok("2,4 mm dans meta.json, material.json, le LISEZMOI et le bordereau ; « non renseignée » sinon")

# ══ 2b · le PATCH de la route pose la hauteur, bornée ══════════════════════
import asyncio                                                 # noqa: E402
import types                                                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [], "seed": 0}


_stub.subscribe_async = _sub
sys.modules.setdefault("fal_client", _stub)
from httpx import ASGITransport, AsyncClient                   # noqa: E402

from app.main import app                                       # noqa: E402


cible, _ = fabriquer()          # sa PROPRE matière : `sans` sert plus bas de témoin « non renseignée »


async def _patch():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        vus = []
        for brut in ("4.2", 25, "x", 1.5):
            r = await c.patch(f"/api/materials/{cible['id']}", json={"height_mm": brut})
            assert r.status_code == 200, r.text
            vus.append(r.json()["material"]["height_mm"])
        r = await c.patch(f"/api/materials/{cible['id']}", json={"name": "Autre"})
        vus.append(r.json()["material"]["height_mm"])
        return vus


vus = asyncio.run(_patch())
assert vus == [4.2, 20.0, 0.0, 1.5, 1.5], vus
assert MS.read_material(cible["id"])["height_mm"] == 1.5
ok(f"PATCH /materials/{{mid}} : height_mm posé et borné ({vus}), un PATCH sans elle ne l'efface pas")

# ══ 3 · clean_graph : un relief SANS profondeur reste « auto » ═════════════
def nettoie(**rel):
    g = {"nodes": [{"id": "r1", "kind": "relief", **rel}], "edges": []}
    return forge3d.clean_graph(g)["nodes"][0]


assert nettoie()["depth_mm"] is None, "auto : rien d'écrit dans le graphe stocké"
assert nettoie(depth_mm=None)["depth_mm"] is None
assert abs(nettoie(depth_mm=1.1)["depth_mm"] - 1.1) < 1e-9
assert nettoie(depth_mm=99)["depth_mm"] == forge3d.RELIEF_DEPTH_MM_MAX
assert nettoie(depth_mm="abc")["depth_mm"] == forge3d.RELIEF_DEPTH_MM_DEFAUT
again = forge3d.clean_graph({"nodes": [nettoie()], "edges": []})["nodes"][0]
assert again["depth_mm"] is None, "un second nettoyage ne fige pas l'auto en 0,6"
ok("clean_graph : relief sans profondeur -> None (auto), même après un second passage ; saisie bornée")

# ══ 4 · la profondeur se résout par la MATIÈRE CHAÎNÉE ═════════════════════
def resout(depth, mid):
    proc = {"kind": "relief", "depth_mm": depth}
    mat_n = {"kind": "material", "mat": mid} if mid is not None else None
    return forge3d.profondeur_relief(proc, mat_n)


r = resout(None, m["id"])
assert abs(r["depth_mm"] - 2.4) < 1e-9 and r["source"] == "matiere" and r["clamped"] is False, r
r = resout(1.1, m["id"])
assert abs(r["depth_mm"] - 1.1) < 1e-9 and r["source"] == "graphe", r
r = resout(None, sans["id"])
assert r["depth_mm"] == forge3d.RELIEF_DEPTH_MM_DEFAUT == 0.6 and r["source"] == "defaut", r
r = resout(None, None)
assert r["depth_mm"] == 0.6 and r["source"] == "defaut", r
gros, _ = fabriquer(9.0)
r = resout(None, gros["id"])
assert r["depth_mm"] == forge3d.RELIEF_DEPTH_MM_MAX and r["clamped"] is True and r["source"] == "matiere", r
r = resout(None, "mat_00000000")
assert r["source"] == "defaut", r
ok("résolution : 2,4 mm de la matière chaînée, 1,1 si le graphe le dit, 0,6 sans hauteur ni matière, "
   "9 mm écrêté à 3,0 EN LE DISANT, matière introuvable -> défaut")

# ══ 5 · element_local consomme la résolution, pas proc["depth_mm"] ═══════
apercu = (RACINE / "backend" / "app" / "services" / "cards" / "forge3d_apercu.py").read_text(encoding="utf-8")
el = apercu.split("def element_local(", 1)[1].split("\ndef ", 1)[0]
assert "profondeur_relief(proc, mat_n)" in el and 'relief_mesh(alpha_img, w_mm, h_mm, proc["depth_mm"]' not in el, el
ok("element_local construit le relief à la profondeur RÉSOLUE (le seul lecteur de la profondeur d'un relief)")

# ══ 6 · la GÉOMÉTRIE, pas le paramètre ═════════════════════════════════════
maille = FS.relief_mesh(haut, 60.0, 60.0, resout(None, m["id"])["depth_mm"], 0.3, 48)
z = maille["positions"][2::3]
assert abs(min(z) - 0.0) < 1e-9, min(z)
assert abs(max(z) - (0.3 + 2.4)) < 1e-6, max(z)
mes = FS.mesh_measures(maille)
assert mes["closed"] is True and mes["volume_mm3"] > 0, mes      # `volume_mm3` (le plan disait `volume`)
ok(f"maillage de relief : z va de 0 à {max(z):.3f} mm = base 0,3 + hauteur 2,4 de la matière ; solide fermé")

# ══ 7 · /info publie le défaut ═════════════════════════════════════════════
src = (RACINE / "backend" / "app" / "services" / "cards" / "forge3d.py").read_text(encoding="utf-8")
assert '"relief_depth_mm_default": RELIEF_DEPTH_MM_DEFAUT' in src
js = (RACINE / "frontend" / "cardforge" / "js" / "mod-forge3d.js").read_text(encoding="utf-8")
geo = js.split("function geoHtml(", 1)[1].split("\n  }\n", 1)[0]
assert "lim.relief_depth_mm_default != null" in geo and "0.6" not in geo, geo
assert "relief_depth_mm_default" in js.split("function thumbRelief(", 1)[1].split("\n  }\n", 1)[0]
ok("le défaut de 0,6 mm est PUBLIÉ par /info et lu par l'écran, jamais recopié")

print(f"\nOK — {PASS} assertions groupées vertes (hauteur physique)")
