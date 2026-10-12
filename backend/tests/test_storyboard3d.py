# -*- coding: utf-8 -*-
"""t189 (G7, plan « Génération IA enrichie ») — le storyboard 3D : SAM 3 de fal reconstruit les objets de l'image d'un
plan en GLB placés, qui deviennent les instances de la scène du Plateau 3D de ce plan.

Schémas fal relus le 12/10/2026 (`fal-ai/sam-3/3d-objects`, `fal-ai/sam-3/3d-body`) ; prix affiché « $0.02 per unit »
(unité non précisée : chiffré 0,02 $ par requête, « unité fal à confirmer au premier tir »).

Ce que le banc tient :
  [0] PUR : build_request (le cas du plan à la lettre, boîtes, corps humain, modèle inconnu) ; _aplatir (plat,
      imbriqué, None) ; _euler_deg = la décomposition XYZ de three.js, PROUVÉE en recomposant la matrice par
      scene3d._rotation sur plusieurs quaternions non triviaux (le cas du plan : rot[1] ≈ 60) ;
      instances_depuis_sam3 (ids, rôles — un seul sujet, le premier —, pos, échelle moyenne et son plancher,
      métadonnées imbriquées ET nulles) ; la sortie passe scene3d_routes._instances ;
  [1] route POST /shots/{id}/objets3d, seams de matte_service espionnés : ordre des refus (404 plan, 400 modèle,
      503 FAL_KEY AVANT le plafond — zéro ligne depenses, aucun seam appelé —, 400 image absente, prompt vide sans
      boîtes, boîtes illisibles, seuil hors 0,1–1) ; la garde « chapitres » (402) arrête AVANT fal ; le tir : GLB
      écrits sous outputs/assets3d/sam3_*/model.glb (glTF), sources du Plateau, Scene3D liée au plan créée (9:16,
      « plan N ») avec dims mesurées (la mesure ne rend pas 409), usd == devis, UNE ligne depenses ; 2e appel : la
      MÊME scène, anciennes sam3_* retirées, ancien sujet rétrogradé decor ; un objet unique (model_glb) ; le corps
      humain ; une réponse sans glTF -> erreur lisible, scène intacte, aucun dossier laissé ;
  [2] recensement : la route est dans PAYANTES, gardée, et atteint le puits `reconstruire`.
AUCUN appel réseau réel : fal_client.* sont des gardes qui comptent, httpx.AsyncClient.post sortant est compté.
Run (depuis backend/) : & $PY tests/test_storyboard3d.py"""
import asyncio
import json
import math
import os
import pathlib
import sqlite3
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzsb3d189_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
os.environ["FAL_KEY"] = "test-key"
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from loguru import logger  # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


import fal_client  # noqa: E402

RESEAU = {"n": 0, "noms": []}


def _garde(nom):
    async def _refus(*a, **k):
        RESEAU["n"] += 1
        RESEAU["noms"].append(nom)
        raise RuntimeError(f"GARDE RESEAU : {nom} appelé dans un banc")
    return _refus


for _nom in ("submit_async", "subscribe_async", "run_async", "upload_file_async", "upload_async",
             "upload_image_async"):
    setattr(fal_client, _nom, _garde(_nom))

import httpx  # noqa: E402
_post_orig = httpx.AsyncClient.post


async def _post_compte(self, url, *a, **k):
    u = str(url)
    if not (u.startswith("/") or u.startswith("http://testclient")):
        RESEAU["n"] += 1
        RESEAU["noms"].append(f"httpx.post {u[:60]}")
        raise RuntimeError("GARDE RESEAU : httpx.AsyncClient.post sortant")
    return await _post_orig(self, url, *a, **k)
httpx.AsyncClient.post = _post_compte

from httpx import AsyncClient, ASGITransport  # noqa: E402
from PIL import Image  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
import app.main as _MAIN  # noqa: E402
from app.services import scene3d as S, scene3d_routes as SR, print3d, pricing as P, plafonds as PL  # noqa: E402
from app.services import matte_service as MT  # noqa: E402
from app.services.storage import init_db  # noqa: E402
import _recensement_payant as RP  # noqa: E402

try:
    from app.services import storyboard3d as SB
except Exception as _e:  # noqa: BLE001 — le banc ROUGIT, il ne plante pas
    SB = None
    print(f"  (storyboard3d absent : {_e})")


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

W = pathlib.Path(_tmp)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())


def n_depenses():
    con = sqlite3.connect(str(W / "t.db"))
    try:
        return con.execute("SELECT COUNT(*) FROM depenses").fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        con.close()


def depenses():
    con = sqlite3.connect(str(W / "t.db"))
    try:
        return con.execute("SELECT moteur, categorie, op, estime_usd FROM depenses").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def sql(q, *a):
    con = sqlite3.connect(str(W / "t.db"))
    try:
        r = con.execute(q, a)
        con.commit()
        return r.fetchall()
    finally:
        con.close()


async def _req(meth, path, body=None, params=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        if meth == "GET":
            return await c.get("/api" + path, params=params)
        if meth == "PUT":
            return await c.put("/api" + path, json=body)
        return await c.post("/api" + path, json=body)


def call(meth, path, body=None, params=None):
    return loop.run_until_complete(_req(meth, path, body, params))


def js(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


def glb_boite(w, h, d):
    """Un vrai GLB minimal : un triangle dont la boîte englobante mesure w × h × d."""
    return print3d.glb_de_triangles([((0.0, 0.0, 0.0), (w, h, 0.0), (0.0, 0.0, d))])


def mat_quat(q):
    """La matrice de rotation d'un quaternion [x, y, z, w] — calculée ICI, indépendamment du service."""
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def ecart(m1, m2):
    return max(abs(m1[i][j] - m2[i][j]) for i in range(3) for j in range(3))


# ── [0] PUR ──────────────────────────────────────────────────────────────────
print("[0] fonctions pures")
if SB is None:
    check("storyboard3d importable", False)
else:
    check("0.1 build_request : le cas du plan à la lettre",
          SB.build_request("https://x/p.png", "personnage, table", []) ==
          ("fal-ai/sam-3/3d-objects", {"image_url": "https://x/p.png", "prompt": "personnage, table",
                                       "export_textured_glb": True}),
          SB.build_request("https://x/p.png", "personnage, table", []))
    ep, a = SB.build_request("https://x/p.png", "", [{"x_min": 1, "y_min": 2, "x_max": 30, "y_max": 40}])
    check("0.2 avec des boîtes : box_prompts (entiers), pas de prompt, GLB texturé",
          ep == "fal-ai/sam-3/3d-objects" and a.get("box_prompts") == [{"x_min": 1, "y_min": 2, "x_max": 30, "y_max": 40}]
          and "prompt" not in a and a.get("export_textured_glb") is True, a)
    check("0.3 corps humain : ni keypoints, ni .ply, ni MHR",
          SB.build_request("https://x/p.png", "", [], modele="sam-3-3d-body") ==
          ("fal-ai/sam-3/3d-body", {"image_url": "https://x/p.png", "include_3d_keypoints": False,
                                    "export_meshes": False, "include_mhr_params": False}),
          SB.build_request("https://x/p.png", "", [], modele="sam-3-3d-body"))
    ep, a = SB.build_request("https://x/p.png", "  chaise   ", [], detection_threshold=0.4)
    check("0.4 prompt nettoyé et seuil relayé", a.get("prompt") == "chaise" and a.get("detection_threshold") == 0.4, a)
    try:
        SB.build_request("https://x/p.png", "a", [], modele="sam-9")
        check("0.5 modèle inconnu -> ValueError", False)
    except ValueError:
        check("0.5 modèle inconnu -> ValueError", True)
    check("0.6 registre : objets par défaut, deux modèles",
          SB.DEFAUT == "sam-3-3d-objects" and set(SB.ENDPOINTS) == {"sam-3-3d-objects", "sam-3-3d-body"}, SB.ENDPOINTS)

    check("0.7 _aplatir : plat, imbriqué, None", SB._aplatir([1, 2, 3]) == [1.0, 2.0, 3.0]
          and SB._aplatir([[1, 2, 3]]) == [1.0, 2.0, 3.0] and SB._aplatir(None) is None
          and SB._aplatir([[0, 0.5, 0, 0.866]]) == [0.0, 0.5, 0.0, 0.866], SB._aplatir([[1, 2, 3]]))

    e = SB._euler_deg([0, 0.5, 0, 0.866])
    check("0.8 le cas du plan : q=[0,0.5,0,0.866] -> rot[1] ≈ 60", abs(e[1] - 60) < 0.05 and abs(e[0]) < 1e-6
          and abs(e[2]) < 1e-6, e)
    quats = [[0.3, -0.2, 0.5, 0.79], [0.1, 0.7, -0.3, 0.6], [-0.6, 0.2, 0.2, 0.75], [0.4, 0.4, 0.4, 0.7],
             [0.0, 0.0, 0.7071, 0.7071], [0.5, 0.5, -0.5, 0.5]]
    ecarts = [ecart(S._rotation(SB._euler_deg(q)), mat_quat(q)) for q in quats]
    check(f"0.9 Euler XYZ PROUVÉ : scene3d._rotation(euler) recompose la matrice du quaternion ({len(quats)} cas)",
          max(ecarts) < 1e-6, ecarts)
    check("0.10 quaternion identité -> [0,0,0] ; quaternion non normalisé accepté",
          max(abs(v) for v in SB._euler_deg([0, 0, 0, 1])) < 1e-9
          and ecart(S._rotation(SB._euler_deg([0.6, -0.4, 1.0, 1.6])), mat_quat([0.6, -0.4, 1.0, 1.6])) < 1e-6)
    check("0.11 la convention d'axes est documentée et passe par UNE fonction pure (identité aujourd'hui)",
          isinstance(getattr(SB, "AXES_SAM3", None), dict) and SB._vers_plateau([1, 2, 3], [10, 20, 30]) == ([1.0, 2.0, 3.0], [10.0, 20.0, 30.0]),
          getattr(SB, "AXES_SAM3", None))

    meta = [{"object_index": 1, "rotation": None, "translation": None, "scale": None, "camera_pose": None},
            {"object_index": 0, "rotation": [[0, 0.5, 0, 0.866]], "translation": [[1, 0, 2]], "scale": [[1, 2, 3]],
             "camera_pose": None}]
    inst = SB.instances_depuis_sam3(meta, ["sam3_ab_0", "sam3_ab_1"], ["personnage", "table"],
                                    dims=[[0.5, 1.7, 0.4], None])
    check("0.12 deux instances, ids sam3_01/02, source assets3d model.glb, niveau allege",
          [i["id"] for i in inst] == ["sam3_01", "sam3_02"]
          and all(i["source"] == {"kind": "assets3d", "job": j, "file": "model.glb"} and i["niveau"] == "allege"
                  for i, j in zip(inst, ["sam3_ab_0", "sam3_ab_1"])), inst)
    check("0.13 rôles : le PREMIER (object_index 0) est le sujet, les autres décor ; noms du prompt",
          [i["role"] for i in inst] == ["sujet", "decor"] and [i["nom"] for i in inst] == ["personnage", "table"], inst)
    t0 = inst[0]["transform"]
    check("0.14 pos = translation, échelle = moyenne de [sx,sy,sz], rot[1] ≈ 60 (métadonnées imbriquées)",
          t0["pos"] == [1.0, 0.0, 2.0] and abs(t0["scale"] - 2.0) < 1e-9 and abs(t0["rot"][1] - 60) < 0.05, t0)
    t1 = inst[1]["transform"]
    check("0.15 métadonnées NULLES : transformation identité", t1 == {"pos": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0],
                                                                       "scale": 1.0}, t1)
    check("0.16 dims posées quand mesurées, absentes sinon", inst[0].get("dims") == [0.5, 1.7, 0.4]
          and inst[1].get("dims") is None, inst)
    plat = SB.instances_depuis_sam3([{"object_index": 0, "rotation": [0, 0.5, 0, 0.866], "translation": [1, 0, 2],
                                      "scale": [0, 0, 0]}], ["sam3_ab_0"], [])
    check("0.17 métadonnées PLATES acceptées ; échelle nulle -> plancher 1e-3 ; nom par défaut « objet 1 »",
          plat[0]["transform"]["scale"] == 1e-3 and plat[0]["nom"] == "objet 1"
          and abs(plat[0]["transform"]["rot"][1] - 60) < 0.05 and plat[0]["role"] == "sujet", plat)
    try:
        v = SR._instances(inst)
        check("0.18 la sortie passe scene3d_routes._instances (un sujet, ids uniques, job conforme)",
              len(v) == 2 and sum(1 for x in v if x["role"] == "sujet") == 1, v)
    except HTTPException as e:
        check("0.18 la sortie passe scene3d_routes._instances", False, e.detail)
    many = SB.instances_depuis_sam3([], [f"sam3_cd_{k}" for k in range(5)], ["a"])
    check("0.19 sans métadonnées : identité pour tous, un seul sujet",
          sum(1 for i in many if i["role"] == "sujet") == 1 and many[0]["role"] == "sujet"
          and [i["nom"] for i in many] == ["a", "objet 2", "objet 3", "objet 4", "objet 5"], many)
    check("0.20 noms_depuis_prompt : découpe sur les virgules", SB.noms_depuis_prompt(" personnage , table,, lampe ")
          == ["personnage", "table", "lampe"], SB.noms_depuis_prompt(" personnage , table,, lampe "))
    try:
        b = SB.valider_boites([{"x_min": 1.0, "y_min": 2, "x_max": 30, "y_max": 40, "object_id": 3}])
        ok_b = b == [{"x_min": 1, "y_min": 2, "x_max": 30, "y_max": 40, "object_id": 3}]
    except ValueError as e:
        ok_b, b = False, e
    check("0.21 valider_boites : entiers, object_id gardé", ok_b, b)
    for mauvaise in ([{"x_min": 5, "y_min": 2, "x_max": 3, "y_max": 40}], [{"x_min": "a"}], "boite",
                     [{"x_min": -1, "y_min": 0, "x_max": 3, "y_max": 4}]):
        try:
            SB.valider_boites(mauvaise)
            check(f"0.22 boîte refusée : {mauvaise!r:.50}", False)
        except ValueError:
            check(f"0.22 boîte refusée : {mauvaise!r:.50}", True)
    try:
        SB.valider_boites([{"x_min": 0, "y_min": 0, "x_max": 91, "y_max": 40}], taille=(90, 160))
        check("0.24 boîte qui dépasse la LARGEUR réelle -> ValueError", False)
    except ValueError as e:
        check("0.24 boîte qui dépasse la LARGEUR réelle -> ValueError", "hors de l'image" in str(e), e)
    try:
        SB.valider_boites([{"x_min": 0, "y_min": 0, "x_max": 30, "y_max": 161}], taille=(90, 160))
        check("0.25 boîte qui dépasse la HAUTEUR réelle -> ValueError", False)
    except ValueError:
        check("0.25 boîte qui dépasse la HAUTEUR réelle -> ValueError", True)
    try:
        SB.valider_boites([{"x_min": 3.2, "y_min": 0, "x_max": 3.4, "y_max": 40}], taille=(90, 160))
        check("0.26 boîte vide APRÈS arrondi aux entiers -> ValueError", False)
    except ValueError:
        check("0.26 boîte vide APRÈS arrondi aux entiers -> ValueError", True)
    check("0.27 boîte au bord exact de l'image acceptée",
          SB.valider_boites([{"x_min": 0, "y_min": 0, "x_max": 90, "y_max": 160}], taille=(90, 160))
          == [{"x_min": 0, "y_min": 0, "x_max": 90, "y_max": 160}])
    trou = SB.instances_depuis_sam3(
        [{"object_index": 0, "translation": [[1, 0, 0]]}, {"translation": [[9, 9, 9]]},
         {"object_index": 2, "translation": [[-1, 0, 0]], "scale": [[2, 2, 2]]}],
        ["sam3_ef_0", "sam3_ef_1"], ["a", "b", "c"], indices=[0, 2])
    check("0.28 GLB nul au milieu : noms ET transformations par object_index (pas par position), méta sans index "
          "ignorée", [(i["nom"], i["transform"]["pos"], i["transform"]["scale"]) for i in trou]
          == [("a", [1.0, 0.0, 0.0], 1.0), ("c", [-1.0, 0.0, 0.0], 2.0)] and trou[0]["role"] == "sujet", trou)
    sans = SB.instances_depuis_sam3([{"translation": [1, 1, 1]}, {"translation": [2, 2, 2]}, {"translation": [3, 3, 3]}],
                                    ["sam3_ef_0", "sam3_ef_1"], [], indices=[0, 2])
    check("0.29 métadonnées sans object_index : lues à la POSITION de l'objet",
          [(i["nom"], i["transform"]["pos"]) for i in sans] == [("objet 1", [1.0, 1.0, 1.0]), ("objet 3", [3.0, 3.0, 3.0])],
          sans)
    check("0.23 devis : 0,02 $ par requête pour les deux modèles (unité fal à confirmer, dite)",
          abs(P.estimate(SB.op_devis("sam-3-3d-objects"))["total_usd"] - 0.02) < 1e-9
          and abs(P.estimate(SB.op_devis("sam-3-3d-body"))["total_usd"] - 0.02) < 1e-9
          and "confirmer" in P.estimate(SB.op_devis("sam-3-3d-objects"))["breakdown"][0]["label"],
          P.estimate(SB.op_devis("sam-3-3d-objects")))

# ── [1] route ────────────────────────────────────────────────────────────────
print("\n[1] route POST /shots/{id}/objets3d")
SEAMS = {"upload": [], "fal": [], "download": []}
REPONSE = {}
GLBS = {}


async def _upload(path):
    SEAMS["upload"].append(pathlib.Path(path).name)
    return f"https://fal.test/up/{pathlib.Path(path).name}"


async def _fal(endpoint, arguments):
    SEAMS["fal"].append((endpoint, dict(arguments)))
    return json.loads(json.dumps(REPONSE["r"]))


async def _download(url, dest):
    SEAMS["download"].append(url)
    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(GLBS.get(url, b"pas un glb"))


MT._upload, MT._fal_subscribe, MT._download = _upload, _fal, _download

GLBS.update({"https://fal.test/o0.glb": glb_boite(0.6, 1.8, 0.4), "https://fal.test/o2.glb": glb_boite(1.2, 0.8, 0.9),
             "https://fal.test/scene.glb": glb_boite(2, 2, 2), "https://fal.test/corps.glb": glb_boite(0.5, 1.75, 0.3)})
MULTI = {"model_glb": {"url": "https://fal.test/scene.glb"},
         "individual_glbs": [{"url": "https://fal.test/o0.glb"}, None, {"url": "https://fal.test/o2.glb"}],
         "metadata": [{"object_index": 0, "rotation": [[0, 0.5, 0, 0.866]], "translation": [[1, 0, 2]],
                       "scale": [[1, 2, 3]], "camera_pose": None},
                      {"rotation": None, "translation": [[9, 9, 9]], "scale": None, "camera_pose": None},
                      {"object_index": 2, "rotation": None, "translation": [[-1, 0, 0]], "scale": None,
                       "camera_pose": None}],
         "gaussian_splat": None, "artifacts_zip": None}

ch = js(call("POST", "/chapters", {"title": "C", "script_text": "Vane entre.\n\nLa table tombe.\n\nLa pluie."}))
shots = js(call("POST", f"/chapters/{ch.get('id')}/storyboard/decoupe", {"method": "paragraph"})).get("shots", [])
s0, s1, s2 = shots[0]["id"], shots[1]["id"], shots[2]["id"]
Image.new("RGB", (90, 160), (40, 90, 140)).save(W / "images" / "plan0.png")
Image.new("RGB", (90, 160), (90, 40, 140)).save(W / "images" / "croquis2.png")
sql("UPDATE shots SET image=? WHERE id=?", "plan0.png", s0)
sql("UPDATE shots SET sketch_image=? WHERE id=?", "croquis2.png", s2)


def dossiers_a3d():
    d = W / "outputs" / "assets3d"
    return sorted(p.name for p in d.iterdir()) if d.is_dir() else []


def seams_vides():
    return not SEAMS["upload"] and not SEAMS["fal"] and not SEAMS["download"]


def vider():
    for k in SEAMS:
        SEAMS[k].clear()


r = call("POST", "/shots/inconnu/objets3d", {"prompt": "chaise"})
check("1.1 plan inconnu -> 404", r.status_code == 404, r.text)
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "chaise", "modele": "sam-9"})
check("1.2 modèle inconnu -> 400", r.status_code == 400 and "sam-9" in r.text, r.text)
settings.FAL_KEY = ""
PL.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "chaise"})
check("1.3 sans FAL_KEY : 503 qui nomme la clé, AVANT le plafond (pas 402)", r.status_code == 503 and "FAL_KEY" in r.text,
      f"{r.status_code} {r.text}")
r = call("POST", f"/shots/{s1}/objets3d", {"prompt": "chaise"})
check("1.3b sans FAL_KEY : 503 même sur un plan SANS image (la clé passe avant les champs)", r.status_code == 503, r.text)
check("1.4 sans clé : ZÉRO ligne depenses, aucun seam appelé", n_depenses() == 0 and seams_vides(), SEAMS)
settings.FAL_KEY = "test-key"
r = call("POST", f"/shots/{s1}/objets3d", {"prompt": "chaise"})
check("1.5 plan sans image ni croquis -> 400", r.status_code == 400 and "image" in r.text.lower(), r.text)
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "   "})
check("1.6 prompt vide sans boîtes -> 400", r.status_code == 400, r.text)
r = call("POST", f"/shots/{s0}/objets3d", {"boxes": [{"x_min": 9, "y_min": 0, "x_max": 3, "y_max": 4}]})
check("1.7 boîtes illisibles -> 400", r.status_code == 400 and "boîte" in r.text.lower(), r.text)
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "chaise", "detection_threshold": 1.5})
check("1.8 seuil hors 0,1–1 -> 400", r.status_code == 400 and "0,1" in r.text, r.text)
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "chaise", "detection_threshold": "x"})
check("1.8b seuil illisible -> 400", r.status_code == 400, r.text)
check("1.9 refus des champs : aucun seam, aucune dépense", n_depenses() == 0 and seams_vides(), SEAMS)
REPONSE["r"] = MULTI
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "personnage, table"})
d = js(r).get("detail") if isinstance(js(r), dict) else None
check("1.10 plafond « chapitres » bas : 402 dz_plafond, AVANT tout envoi à fal",
      r.status_code == 402 and isinstance(d, dict) and d.get("dz_plafond", {}).get("categorie") == "chapitres"
      and not SEAMS["fal"] and n_depenses() == 0, f"{r.status_code} {r.text[:300]} {SEAMS}")
PL.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
vider()

r = call("POST", f"/shots/{s0}/objets3d", {"boxes": [{"x_min": 0, "y_min": 0, "x_max": 91, "y_max": 40}]})
check("1.10b boîte hors de l'image réelle (90 × 160) : 400 AVANT la garde", r.status_code == 400
      and "hors de l'image" in r.text and seams_vides() and n_depenses() == 0, f"{r.status_code} {r.text}")
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "personnage, chaise, table", "detection_threshold": 0.5})
j = js(r)
check("1.11 le tir : 200", r.status_code == 200, f"{r.status_code} {r.text[:400]}")
check("1.12 l'image de PRODUCTION du plan est téléversée", SEAMS["upload"] == ["plan0.png"], SEAMS["upload"])
check("1.13 arguments EXACTS envoyés à fal",
      SEAMS["fal"] == [("fal-ai/sam-3/3d-objects", {"image_url": "https://fal.test/up/plan0.png",
                                                    "prompt": "personnage, chaise, table", "export_textured_glb": True,
                                                    "detection_threshold": 0.5})], SEAMS["fal"])
check("1.14 les GLB individuels NON nuls sont téléchargés (pas le combiné)",
      SEAMS["download"] == ["https://fal.test/o0.glb", "https://fal.test/o2.glb"], SEAMS["download"])
jobs = sorted(p.parent.name for p in (W / "outputs" / "assets3d").glob("sam3_*/model.glb"))
check("1.15 deux GLB sous outputs/assets3d/sam3_*/model.glb, en-tête glTF",
      len(jobs) == 2 and all((W / "outputs" / "assets3d" / k / "model.glb").read_bytes()[:4] == b"glTF" for k in jobs), jobs)
objets = j.get("objets") or []
check("1.16 réponse : scene_id, n = 2, objets {id, nom, job, role} — noms par object_index (0 et 2)",
      j.get("n") == 2 and [o.get("id") for o in objets] == ["sam3_01", "sam3_02"]
      and [o.get("role") for o in objets] == ["sujet", "decor"] and [o.get("nom") for o in objets] == ["personnage", "table"]
      and sorted(o.get("job") for o in objets) == jobs, j)
devis = P.estimate({"kind": "objets3d", "modele": "sam-3-3d-objects", "n": 1})["total_usd"]
check("1.17 usd rendu == devis (0,02 $)", abs(float(j.get("usd", -1)) - devis) < 1e-9 and abs(devis - 0.02) < 1e-9, j)
dep = depenses()
check("1.18 UNE ligne depenses : fal, chapitres, objets3d, 0,02 $", len(dep) == 1 and dep[0][:3] == ("fal", "chapitres", "objets3d")
      and abs(dep[0][3] - 0.02) < 1e-9, dep)
sid = j.get("scene_id")
sc = js(call("GET", f"/scenes3d/{sid}"))
check("1.19 la Scene3D est liée au plan (chapitre hérité, « plan 1 », 9:16)",
      sc.get("shot_id") == s0 and sc.get("chapter_id") == ch.get("id") and sc.get("nom") == "plan 1"
      and sc.get("aspect") == "9:16", {k: sc.get(k) for k in ("shot_id", "chapter_id", "nom", "aspect")})
ins = sc.get("instances") or []
check("1.20 instances : dims MESURÉES sur les GLB écrits, transformations SAM 3",
      len(ins) == 2 and all(abs(a - b) < 1e-4 for a, b in zip(ins[0].get("dims") or [], [0.6, 1.8, 0.4]))
      and all(abs(a - b) < 1e-4 for a, b in zip(ins[1].get("dims") or [], [1.2, 0.8, 0.9]))
      and ins[0]["transform"]["pos"] == [1.0, 0.0, 2.0] and abs(ins[0]["transform"]["rot"][1] - 60) < 0.05
      and ins[1]["transform"]["pos"] == [-1.0, 0.0, 0.0], ins)
r = call("POST", f"/scenes3d/{sid}/mesure", {})
check("1.21 la mesure du cadre accepte la scène (sujet mesuré : pas de 409)", r.status_code == 200, r.text[:200])
src = js(call("GET", "/scenes3d/sources"))
noms_src = {x["job"]: x["nom"] for x in src.get("jobs") or []}
check("1.22 les GLB apparaissent dans les sources du Plateau, nommés (asset.json)",
      set(jobs) <= set(noms_src) and sorted(noms_src[k] for k in jobs) == ["personnage", "table"], noms_src)

# 2e appel : on pose d'abord un sujet À LA MAIN (proxy) — SAM 3 en pose un aussi, l'ancien devient décor
ins_main = ins + [{"id": "perso", "nom": "Perso", "source": {"kind": "proxy", "forme": "capsule"},
                   "dims": [0.5, 1.7, 0.4], "role": "decor"}]
for x in ins_main:
    x["role"] = "decor"
ins_main[-1]["role"] = "sujet"
r = call("PUT", f"/scenes3d/{sid}", {"instances": ins_main})
check("1.23 (préparation) un sujet posé à la main", r.status_code == 200, r.text[:200])
vider()
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "personnage, table"})
j2 = js(r)
sc2 = js(call("GET", f"/scenes3d/{sid}"))
ins2 = sc2.get("instances") or []
jobs2 = sorted(o.get("job") for o in j2.get("objets") or [])
check("1.24 2e appel : la MÊME scène est mise à jour (pas une nouvelle)", r.status_code == 200 and j2.get("scene_id") == sid
      and len(js(call("GET", "/scenes3d", params={"shot_id": s0})).get("scenes") or []) == 1, f"{r.status_code} {j2}")
check("1.25 les anciennes instances sam3_* sont retirées, les nouvelles pointent les NOUVEAUX jobs",
      sorted(i["source"].get("job") for i in ins2 if i["id"].startswith("sam3_")) == jobs2 and set(jobs2).isdisjoint(jobs),
      [(i["id"], i["source"]) for i in ins2])
perso = next((i for i in ins2 if i["id"] == "perso"), None)
check("1.26 l'instance posée à la main est GARDÉE, rétrogradée décor ; un seul sujet (sam3_01)",
      perso is not None and perso["role"] == "decor"
      and [i["id"] for i in ins2 if i["role"] == "sujet"] == ["sam3_01"], [(i["id"], i["role"]) for i in ins2])
check("1.27 deux lignes depenses au total", n_depenses() == 2, depenses())
plein = js(call("GET", f"/scenes3d/{sid}")).get("instances") or []
remplis = [i for i in plein if not i["id"].startswith("sam3_")] + [
    {"id": f"main_{k:02d}", "nom": f"M{k}", "source": {"kind": "proxy", "forme": "boite"}, "dims": [1, 1, 1],
     "role": "decor"} for k in range(32)]
r = call("PUT", f"/scenes3d/{sid}", {"instances": remplis + [i for i in plein if i["id"].startswith("sam3_")]})
vider()
r2 = call("POST", f"/shots/{s0}/objets3d", {"prompt": "personnage, table"})
check("1.27b scène pleine (33 instances gardées + 32 objets SAM 3 possibles > 64) : 400 lisible AVANT la garde",
      r.status_code == 200 and r2.status_code == 400 and "33" in r2.text and seams_vides() and n_depenses() == 2,
      f"{r.status_code} {r2.status_code} {r2.text}")
r = call("PUT", f"/scenes3d/{sid}", {"instances": plein})
check("1.27c (remise en état) la scène retrouve ses instances", r.status_code == 200, r.text[:200])

# un seul objet : pas d'individual_glbs -> model_glb
vider()
REPONSE["r"] = {"model_glb": {"url": "https://fal.test/scene.glb"}, "individual_glbs": None,
                "metadata": [{"object_index": 0, "rotation": None, "translation": [[0, 0, 1]], "scale": [[2, 2, 2]]}]}
r = call("POST", f"/shots/{s2}/objets3d", {"boxes": [{"x_min": 1, "y_min": 2, "x_max": 30, "y_max": 40}]})
j3 = js(r)
check("1.28 objet unique : model_glb téléchargé, une instance sujet ; le CROQUIS sert à défaut d'image",
      r.status_code == 200 and SEAMS["download"] == ["https://fal.test/scene.glb"] and j3.get("n") == 1
      and SEAMS["upload"] == ["croquis2.png"]
      and SEAMS["fal"][0][1].get("box_prompts") == [{"x_min": 1, "y_min": 2, "x_max": 30, "y_max": 40}]
      and "prompt" not in SEAMS["fal"][0][1], f"{r.status_code} {j3} {SEAMS}")
sc3 = js(call("GET", f"/scenes3d/{j3.get('scene_id')}"))
check("1.29 objet unique : nom « objet 1 », échelle 2, sujet, scène « plan 3 »",
      [(i["nom"], i["role"], i["transform"]["scale"]) for i in sc3.get("instances") or []] == [("objet 1", "sujet", 2.0)]
      and sc3.get("nom") == "plan 3", sc3)

# corps humain
vider()
REPONSE["r"] = {"model_glb": {"url": "https://fal.test/corps.glb"}, "visualization": {"url": "https://fal.test/v.png"},
                "metadata": {"people": [{"keypoints": [[0, 0]]}]}}
sql("DELETE FROM scenes3d WHERE shot_id=?", s2)
r = call("POST", f"/shots/{s2}/objets3d", {"modele": "sam-3-3d-body"})
j4 = js(r)
check("1.30 corps humain : arguments exacts, une instance sujet identité",
      r.status_code == 200 and SEAMS["fal"] == [("fal-ai/sam-3/3d-body", {"image_url": "https://fal.test/up/croquis2.png",
                                                                          "include_3d_keypoints": False, "export_meshes": False,
                                                                          "include_mhr_params": False})]
      and j4.get("n") == 1 and j4["objets"][0]["role"] == "sujet", f"{r.status_code} {j4} {SEAMS['fal']}")
sc4 = js(call("GET", f"/scenes3d/{j4.get('scene_id')}"))
check("1.31 corps : transformation identité, dims mesurées",
      [i["transform"] for i in sc4.get("instances") or []] == [{"pos": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0], "scale": 1.0}]
      and all(abs(a - b) < 1e-4 for a, b in zip((sc4.get("instances") or [{}])[0].get("dims") or [], [0.5, 1.75, 0.3])), sc4)

# réponse fal sans glTF
vider()
avant = js(call("GET", f"/scenes3d/{sid}")).get("instances")
dossiers_avant = dossiers_a3d()
REPONSE["r"] = {"model_glb": {"url": "https://fal.test/html"}, "individual_glbs": [{"url": "https://fal.test/html"}],
                "metadata": []}
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "chaise"})
check("1.32 réponse sans glTF : erreur LISIBLE (502 qui le dit)", r.status_code == 502 and "glTF" in r.text, f"{r.status_code} {r.text}")
check("1.33 la scène n'est pas touchée, aucun dossier laissé",
      js(call("GET", f"/scenes3d/{sid}")).get("instances") == avant
      and dossiers_a3d() == dossiers_avant,
      dossiers_a3d())
vider()
REPONSE["r"] = {"model_glb": None, "individual_glbs": None, "metadata": None}
r = call("POST", f"/shots/{s0}/objets3d", {"prompt": "chaise"})
check("1.34 aucun GLB dans la réponse : 502 qui le dit", r.status_code == 502 and "GLB" in r.text, f"{r.status_code} {r.text}")

settings.FAL_KEY = ""
cat = js(call("GET", "/ia/catalogue", params={"nature": "objets3d"}))
m = {e.get("id"): e for e in cat.get("modeles") or []}
check("1.35 /ia/catalogue?nature=objets3d : les deux modèles, 0,02 $ par requête, unité à confirmer, objets par défaut",
      set(m) == {"sam-3-3d-objects", "sam-3-3d-body"}
      and all(e["voie"] == "fal" and abs(e["usd"] - 0.02) < 1e-9 and e["unite"] == "requete"
              and e["unite_a_confirmer"] is True and e["note"] == "" for e in m.values())
      and m["sam-3-3d-objects"]["defaut"] is True and m["sam-3-3d-body"]["defaut"] is False
      and m["sam-3-3d-body"]["corps"] is True, cat)
check("1.36 sans FAL_KEY : les modèles restent LISTÉS (dispo False, clé nommée)",
      all(e["dispo"] is False and e["cle"] == "FAL_KEY" for e in m.values()), m)
settings.FAL_KEY = "test-key"

# ── [2] recensement ──────────────────────────────────────────────────────────
print("\n[2] recensement des routes payantes")
rec = RP.recenser()
k = ("routes", "POST", "/shots/{shot_id}/objets3d")
check("2.1 la route est recensée : gardée, et atteint le puits `reconstruire`",
      k in rec and rec[k]["garde"] and "reconstruire" in rec[k]["puits"], rec.get(k))
_pg = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
check("2.2 elle est dans PAYANTES de test_plafonds_garde", '("routes", "POST", "/shots/{shot_id}/objets3d")' in _pg)
_src = (RP.RACINE / "api" / "routes.py").read_text(encoding="utf-8")
_f = _src[_src.find('@router.post("/shots/{shot_id}/objets3d"'):]
_f = _f[:_f.find("\n@router")]
check("2.3 la route exige la machine locale (_require_local_depense)", "_require_local_depense" in _f.split("\n")[0], _f[:200])
check("2.4 ordre du source : _refus_cle AVANT _plafond AVANT reconstruire",
      0 < _f.find("_refus_cle(") < _f.find("_plafond(") < _f.find("reconstruire("), "")

check("2.5 aucun appel réseau dans tout le banc (fal_client.*, httpx.post sortant)", RESEAU["n"] == 0, RESEAU)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
