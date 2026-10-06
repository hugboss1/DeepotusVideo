# -*- coding: utf-8 -*-
"""Habiller un maillage d'une matière du Forge — le moteur (T6 « mon modèle »,
puis T14/T15 « une matière par partie »).

BANC-MIROIR : le GLB produit est REPARSÉ (mesh_edit.lire_glb), ses triangles
relus (print3d.lire_glb_triangles), et les octets de chaque texture ressortis
du tampon à l'offset déclaré et comparés à l'octet près. On ne demande jamais
au module ce qu'il croit avoir écrit.

Run (depuis backend/) : python tests/test_mesh_paint.py
"""
import io
import os
import pathlib
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402

from app.services import gltf_builder, mesh_edit, print3d      # noqa: E402
from app.services import mesh_paint as MP                      # noqa: E402

PASS = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


def png(couleur, taille=8):
    buf = io.BytesIO()
    Image.new("RGB", (taille, taille), couleur).save(buf, format="PNG")
    return buf.getvalue()


PAYLOAD = {"basecolor": png((200, 30, 30)), "normal": png((128, 128, 255)),
           "orm": png((240, 180, 20)), "emissive": png((0, 0, 0))}

CUBE = gltf_builder.build_glb({}, None, "cube", "banc")

# ══ 1 · toutes les primitives pointent sur le matériau ajouté ═══════════════
sortie = MP.habiller(CUBE, [{"cible": "tout", "mid": "mat_deadbeef",
                             "nom": "Pierre bleue", "maps": PAYLOAD,
                             "props": {"metallic": 0.4, "roughness": 0.7}}])
doc, binc = mesh_edit.lire_glb(sortie)
avant, _ = mesh_edit.lire_glb(CUBE)
assert len(doc["materials"]) == len(avant.get("materials") or []) + 1
idx = len(doc["materials"]) - 1
assert doc["materials"][idx]["name"] == "Pierre bleue"
vus = [p.get("material") for m in doc["meshes"] for p in m["primitives"]]
assert vus and set(vus) == {idx}, vus
ok(f"habillage : un matériau ajouté (index {idx}), {len(vus)} primitive(s) "
   f"pointent dessus")

# ══ 2 · les octets des textures sont DANS le tampon, intacts ════════════════
mat = doc["materials"][idx]
pbr = mat["pbrMetallicRoughness"]
assert pbr["metallicFactor"] == 1.0 and pbr["roughnessFactor"] == 1.0, pbr
assert pbr["metallicRoughnessTexture"]["index"] == mat["occlusionTexture"]["index"]
trouve = {}
for cle, ref in (("basecolor", pbr["baseColorTexture"]),
                 ("orm", pbr["metallicRoughnessTexture"]),
                 ("normal", mat["normalTexture"]),
                 ("emissive", mat["emissiveTexture"])):
    src = doc["images"][doc["textures"][ref["index"]]["source"]]
    bv = doc["bufferViews"][src["bufferView"]]
    o = bv.get("byteOffset", 0)
    trouve[cle] = binc[o:o + bv["byteLength"]]
    assert src["mimeType"] == "image/png", (cle, src)
assert trouve == PAYLOAD, [k for k in PAYLOAD if trouve[k] != PAYLOAD[k]]
# La spec glTF : le chunk BIN est complété à un multiple de 4, et le tampon
# déclare sa longueur UTILE — au plus 3 octets de bourrage entre les deux (le
# plan exigeait l'égalité : mesuré 1533 déclarés pour 1536 relus, conforme).
assert 0 <= len(binc) - doc["buffers"][0]["byteLength"] <= 3, \
    (doc["buffers"][0]["byteLength"], len(binc))
ok("les quatre textures sortent du tampon à l'octet près, le tampon déclare "
   "sa vraie longueur, les facteurs restent à 1.0 (les niveaux sont cuits)")

# ══ 3 · le GLB reste lisible par le reste du dépôt ══════════════════════════
tris_av = print3d.lire_glb_triangles(CUBE)
tris_ap = print3d.lire_glb_triangles(sortie)
assert len(tris_ap) == len(tris_av) and tris_ap[0] == tris_av[0]
assert print3d.bbox(tris_ap) == print3d.bbox(tris_av)
ok(f"géométrie intacte : {len(tris_ap)} triangles, même boîte englobante — "
   f"l'habillage ne touche qu'aux matériaux")

# ══ 4 · les trois granularités du panneau Parties ═══════════════════════════
d0, _ = mesh_edit.lire_glb(CUBE)
assert MP.cibles(d0, "tout", None) == MP.cibles(d0, "maillage", 0)
noeud = next(i for i, n in enumerate(d0.get("nodes") or [])
             if isinstance(n.get("mesh"), int))
assert MP.cibles(d0, "noeud", noeud) == MP.cibles(d0, "maillage", 0)
ok("cibles : nœud, maillage et « tout » se ramènent aux mêmes primitives sur "
   "un modèle à un seul maillage")

# ══ 4b · trois promesses du module que le plan ne vérifiait pas ═════════════
# (a) l'alignement : chaque bufferView ajouté commence sur un multiple de 4 —
#     la spec l'exige, et le contenu relu à l'offset déclaré ne le voit pas.
for i, bv in enumerate(doc["bufferViews"]):
    assert bv.get("byteOffset", 0) % 4 == 0, (i, bv)
# (b) la descendance : un nœud PARENT sans maillage vise les maillages de ses
#     enfants (cocher un parent dans Parties ne doit pas laisser les enfants nus).
dp, bp = mesh_edit.lire_glb(CUBE)
dp["nodes"].append({"name": "parent", "children": [noeud]})
parent = len(dp["nodes"]) - 1
for sc in dp.get("scenes") or []:
    sc["nodes"] = [parent if n == noeud else n for n in sc.get("nodes", [])]
assert MP.cibles(dp, "noeud", parent) == MP.cibles(dp, "maillage", 0) != set()
# (c) deux lots de la MÊME matière partagent UN matériau glTF : sinon quarante
#     pièces embarqueraient quarante copies des mêmes textures.
deux = MP.habiller(CUBE, [{"cible": "maillage", "index": 0, "mid": "mat_a", "maps": PAYLOAD},
                          {"cible": "tout", "mid": "mat_a", "maps": PAYLOAD}])
dd, _ = mesh_edit.lire_glb(deux)
assert len(dd["materials"]) == len(avant.get("materials") or []) + 1, dd["materials"]
assert len(dd["images"]) == len(doc["images"]), (len(dd["images"]), len(doc["images"]))
ok("vues alignées sur 4 octets ; un nœud parent vise ses enfants ; deux lots "
   "d'une même matière font UN matériau et un seul jeu d'images")

# ══ 5 · les refus se disent ════════════════════════════════════════════════
sans_uv, binc0 = mesh_edit.lire_glb(CUBE)
for m in sans_uv["meshes"]:
    for p in m["primitives"]:
        p["attributes"].pop("TEXCOORD_0", None)
essais = [
    (mesh_edit.ecrire_glb(sans_uv, binc0),
     [{"cible": "tout", "mid": "x", "maps": PAYLOAD}], "uv"),
    (CUBE, [], "aucune"),
    (CUBE, [{"cible": "noeud", "index": 999, "mid": "x", "maps": PAYLOAD}],
     "999"),
    (CUBE, [{"cible": "chose", "index": 0, "mid": "x", "maps": PAYLOAD}],
     "chose"),
    (CUBE, [{"cible": "maillage", "index": None, "mid": "x",
             "maps": PAYLOAD}], "index"),
]
mots = []
for data, lots, mot in essais:
    try:
        MP.habiller(data, lots)
        raise AssertionError(f"{mot} : aurait dû lever")
    except ValueError as e:
        assert mot in str(e).lower(), (mot, str(e))
        mots.append(str(e)[:52])
ok("refus nommés : " + " | ".join(mots))

# ══ 6 · la ROUTE d'aperçu habille un modèle de l'Établi (absent du plan) ═══
# Le plan ne testait que le moteur : la porte réseau (nom de job, version,
# empreinte du cache) n'était exercée par rien.
import asyncio                                                 # noqa: E402
import types                                                   # noqa: E402

_stub = types.ModuleType("fal_client")


async def _sub(model, arguments=None, **kw):
    return {"images": [], "seed": 0}


_stub.subscribe_async = _sub
sys.modules.setdefault("fal_client", _stub)

from httpx import ASGITransport, AsyncClient                   # noqa: E402

from app.main import app                                       # noqa: E402
from app.services import material_store as MS                  # noqa: E402
from app.services import mesh_report                           # noqa: E402


def _matiere():
    mat = MS.create_material(name="Brique rouge", prompt="red brick",
                             full_prompt=MS.build_full_prompt("red brick"),
                             source={"kind": "prompt", "model": "flux",
                                     "filename": None},
                             res=64, seamless=True, seam={"before": 1.0, "after": 0.0})
    MS.save_maps(mat["id"], {"basecolor": Image.new("RGB", (64, 64), (180, 40, 30)),
                             "normal": Image.new("RGB", (64, 64), (128, 128, 255)),
                             "orm": Image.new("RGB", (64, 64), (255, 200, 0))})
    return MS.read_material(mat["id"])


def _job(nom, data):
    d = mesh_report.job_dir(nom)
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(data)
    return d


async def _route():
    mat = _matiere()
    _job("cube_banc", CUBE)
    _job("plan_banc", gltf_builder.build_glb({}, None, "plane", "banc"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t",
                           timeout=120) as c:
        base = f"/api/materials/{mat['id']}/preview.glb?res=256"
        r = await c.get(base + "&model=cube_banc&mversion=1")
        assert r.status_code == 200, r.text
        d, _b = mesh_edit.lire_glb(r.content)
        assert d["materials"][-1]["name"] == "Brique rouge", d["materials"]
        assert print3d.bbox(print3d.lire_glb_triangles(r.content)) == \
            print3d.bbox(print3d.lire_glb_triangles(CUBE))
        r2 = await c.get(base + "&model=plan_banc&mversion=1")
        assert r2.status_code == 200 and r2.content != r.content, \
            "deux modèles, un même GLB : l'empreinte du cache ignore le modèle"
        assert r2.headers["etag"] != r.headers["etag"]
        sphere = await c.get(base)
        assert sphere.status_code == 200 and sphere.content not in (r.content, r2.content)
        for q, code in (("&model=..&mversion=1", 400), ("&model=cube_banc&mversion=9", 404),
                        ("&model=inconnu_banc&mversion=1", 404), ("&model=cube_banc&mversion=0", 400)):
            rr = await c.get(base + q)
            assert rr.status_code == code, (q, rr.status_code, rr.text)
    return r.headers["etag"], r2.headers["etag"]


e1, e2 = asyncio.run(_route())
ok(f"route : le cube de l'Établi ressort habillé de la matière, géométrie intacte ; "
   f"un autre modèle a sa propre empreinte ({e1[3:11]} ≠ {e2[3:11]}) ; "
   f"job « .. » 400, version absente 404, version 0 400")

print(f"\nOK — {PASS} assertions groupées vertes (mesh_paint, habillage)")
