# -*- coding: utf-8 -*-
"""t333 + t338 (A3 + A8 du lot Scenario, 29/10/2026) — les ROUTES du Plateau 3D pour la previs colorée et nommée et la
couverture d'un plan, et la légende jusque dans les prompts (Previs → plan, image de production).

Data-dir temporaire, fal SIMULÉ (aucun appel payé : subscribe et upload tracés), vraie base sqlite, TestClient.
  [1] instances : rôle « faisceau » (primitive seulement), `matiere` gardée et bornée ;
  [2] /palette : GET (scène enregistrée) et POST (scène affichée), faisceaux et repères hors légende ;
  [3] composition : les faisceaux n'entrent pas dans le GLB ;
  [4] captures : la recette de la Bibliothèque porte la légende ; capture d'une caméra de couverture nommée ;
  [5] /couverture : gratuit, rien d'écrit sans `enregistrer`, règle des 180° tenue ; refus nommés ;
  [6] nouveau-plan : aperçu sans écrire, puis un plan neuf APRÈS le plan lié (les suivants décalés) avec sa scène ;
  [7] la légende dans le prompt proposé de Previs → plan (sources et devis) ;
  [8] l'image de production : la capture colorée en DERNIÈRE référence, la légende dans le prompt ;
  [9] migration de la colonne `couverture` et routes montées.
Run : & $PY tests/test_plateau_previs_couverture.py   (depuis backend/)
"""
import base64
import io
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt333_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
          "ELEVENLABS_API_KEY", "MESHY_API_KEY", "HEYGEN_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
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
        print(f"  FAIL  {label} {detail}")


APPELS, TELEVERSES = [], []
from PIL import Image  # noqa: E402
_buf = io.BytesIO()
Image.new("RGB", (30, 40), (30, 60, 90)).save(_buf, "PNG")
PNG = _buf.getvalue()
B64 = "data:image/png;base64," + base64.b64encode(PNG).decode()


async def _fake_subscribe(model, arguments=None, **kw):
    APPELS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}], "seed": 4242}


async def _fake_upload(path):
    TELEVERSES.append(pathlib.Path(path).name)
    return f"http://fal.test/up/{pathlib.Path(path).name}"
_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub
import httpx as _httpx  # noqa: E402
_orig_get = _httpx.AsyncClient.get


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        return _httpx.Response(200, content=PNG, request=_httpx.Request("GET", str(url)))
    return await _orig_get(self, url, *a, **kw)
_httpx.AsyncClient.get = _fake_get

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
import app.main as _MAIN  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def un(sql, *a):
    try:
        return sqlite3.connect(str(_DB)).execute(sql, a).fetchone()
    except sqlite3.OperationalError:
        return None


def capsule(iid, x, z=0.0, role="decor", nom=None, **k):
    return {"id": iid, "nom": nom or iid, "source": {"kind": "proxy", "forme": "capsule"}, "dims": [0.5, 1.7, 0.4],
            "role": role, "transform": {"pos": [x, 0, z], "rot": [0, 0, 0], "scale": 1}, **k}


def cyl(iid, x, z, role="decor", nom=None, **k):
    return {"id": iid, "nom": nom or iid, "source": {"kind": "proxy", "forme": "cylindre"}, "dims": [0.6, 4, 0.6],
            "role": role, "transform": {"pos": [x, 0, z], "rot": [0, 0, 0], "scale": 1}, **k}


with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    marie = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Marie", "description": "robe rouge"}))
    c.post(f"/api/bible/entities/{marie.get('id')}/generate", json={"seed": 1})
    c.put("/api/atelier/settings", json={"image_provider": "nano-banana-pro"})
    ch = js(c.post("/api/chapters", json={"title": "C", "script_text": "Marie parle à Paul.\n\nLa pluie tombe."}))
    shots = js(c.post(f"/api/chapters/{ch.get('id')}/storyboard/decoupe", json={"method": "paragraph"})).get("shots", [])
    s0, s1 = shots[0], shots[1]
    sc = js(c.post("/api/scenes3d", json={"shot_id": s0["id"]}))
    SID = sc.get("id")
    INST = [capsule("marie", 0, role="sujet", nom="Marie (bible)", entity_id=marie.get("id")),
            capsule("paul", 2, nom="Paul"),
            cyl("c1", -3, -2, matiere="cyprès"), cyl("c2", -4, -2.5, nom="arbre (copie)", matiere="cyprès"),
            cyl("phare", 1, 3, role="faisceau", nom="Faisceau du phare"),
            {"id": "rep", "nom": "marque", "source": {"kind": "proxy", "forme": "boite"}, "dims": [0.2, 0.01, 0.2],
             "role": "repere", "transform": {"pos": [0, 0, 1], "rot": [0, 0, 0], "scale": 1}}]
    CAM = {"orbit": [30, 90, 5], "target": [0, 0.85, 0], "fov": 22.94}
    r = c.put(f"/api/scenes3d/{SID}", json={"instances": INST, "camera": CAM})

    print("[1] instances")
    d = js(r)
    check("1a_faisceau_et_matiere_acceptes", r.status_code == 200 and [i["role"] for i in d["instances"]][4] == "faisceau"
          and d["instances"][2]["matiere"] == "cyprès" and d["instances"][1]["matiere"] is None, r.text[:300])
    mauvais = {"id": "x", "nom": "beam", "source": {"kind": "assets3d", "job": "j1", "file": "model.glb"}, "role": "faisceau"}
    check("1b_un_faisceau_maillage_refuse", c.put(f"/api/scenes3d/{SID}", json={"instances": INST + [mauvais]}).status_code == 400)
    long = js(c.post(f"/api/scenes3d/{SID}/palette", json={"scene": {"instances": [cyl("z", 0, 0, matiere="x" * 90)]}}))
    check("1c_matiere_bornee_a_60", long["table"][0]["libelle"] == "x" * 60)

    print("\n[2] /palette")
    p = js(c.get(f"/api/scenes3d/{SID}/palette"))
    cles = [e["cle"] for e in p.get("table", [])]
    check("2a_entite_puis_matieres_faisceau_et_repere_hors_legende",
          cles == [f"entite:{marie.get('id')}", "matiere:paul", "matiere:cypres"], cles)
    check("2b_couleurs_par_instance_copies_partagees", set(p["couleurs"]) == {"marie", "paul", "c1", "c2"}
          and p["couleurs"]["c1"] == p["couleurs"]["c2"] and len(set(p["couleurs"].values())) == 3)
    check("2c_legende_fr_en_et_prompt", len(p["legende"]["fr"]) == 3 and p["legende"]["fr"][2].startswith("cylindres ")
          and p["legende"]["fr"][2].endswith(" = cyprès") and p["legende"]["fr"][0].startswith("capsule ")
          and p["prompt"].startswith("Colour-coded previs: ") and "not solid" in p["prompt"], p["legende"])
    check("2d_faisceaux_listes_et_table_blender", [f["id"] for f in p["faisceaux"]] == ["phare"]
          and p["blender"]["exclus"] == ["phare"] and len(p["blender"]["materiaux"]) == 3)
    check("2e_teinte_nommee_dans_les_deux_langues", all(set(e["teinte"]) == {"fr", "en"} for e in p["table"]))
    p2 = js(c.post(f"/api/scenes3d/{SID}/palette", json={"scene": {"instances": INST[:2]}}))
    check("2f_post_lit_la_scene_affichee_sans_ecrire", len(p2["table"]) == 2 and p2["couleurs"]["marie"] == p["couleurs"]["marie"]
          and len(js(c.get(f"/api/scenes3d/{SID}/palette"))["table"]) == 3)
    check("2g_scene_inconnue_404", c.get("/api/scenes3d/00000000-0000-0000-0000-000000000000/palette").status_code == 404)

    print("\n[3] composition")
    g = js(c.post(f"/api/scenes3d/{SID}/compose"))
    check("3a_le_faisceau_n_entre_pas_dans_le_glb", g.get("faisceaux_exclus") == ["phare"]
          and len(g.get("rapport", {}).get("instances", [])) == 5, str(g)[:300])

    print("\n[4] captures")
    cap = js(c.post(f"/api/scenes3d/{SID}/capture", json={"quand": "debut", "image_b64": B64,
                                                           "scene": {"instances": INST}}))
    rec = un("SELECT recette FROM library_assets WHERE filename=?", cap.get("filename"))
    rec = json.loads(rec[0]) if rec and rec[0] else {}
    check("4a_la_recette_porte_la_legende_et_les_exclus", rec.get("legende", "").startswith("Colour-coded previs: ")
          and rec.get("faisceaux_exclus") == ["phare"] and len(rec.get("palette", [])) == 3, rec)
    check("4b_la_reponse_rend_la_legende", len(cap.get("legende", {}).get("fr", [])) == 3)
    check("4c_camera_sans_couverture_404", c.post(f"/api/scenes3d/{SID}/capture", json={
        "quand": "camera", "camera_id": "large", "image_b64": B64}).status_code == 404)
    check("4d_camera_id_illisible_400", c.post(f"/api/scenes3d/{SID}/capture", json={
        "quand": "camera", "camera_id": "../x", "image_b64": B64}).status_code == 400)

    print("\n[5] /couverture")
    cv = js(c.post(f"/api/scenes3d/{SID}/couverture", json={}))
    check("5a_trois_cameras_nommees_axe_marie_paul", [x["id"] for x in cv.get("cameras", [])] == ["large", "contrechamp", "gros_plan"]
          and cv["partenaire"] == "paul" and cv["regle_180"]["respectee"] and cv["origine"] == "camera", str(cv)[:300])
    check("5b_rien_d_ecrit_sans_enregistrer", js(c.get(f"/api/scenes3d/{SID}"))["couverture"] is None)
    check("5c_libelles_sans_bible", cv["cameras"][2]["nom"] == "Gros plan — Marie" and cv["cameras"][1]["nom"] == "Contre-champ — Paul")
    check("5d_interlocuteur_inconnu_400", c.post(f"/api/scenes3d/{SID}/couverture", json={"partenaire_id": "zz"}).status_code == 400)
    sans = js(c.post(f"/api/scenes3d/{SID}/couverture", json={"partenaire_id": ""}))
    check("5e_sans_interlocuteur_180_autour_du_sujet", sans["partenaire"] is None
          and abs(sans["cameras"][1]["camera"]["orbit"][0] - 210) < 1e-6)
    cv = js(c.post(f"/api/scenes3d/{SID}/couverture", json={"enregistrer": True}))
    lu = js(c.get(f"/api/scenes3d/{SID}"))["couverture"]
    check("5f_enregistree_avec_sa_date", cv.get("enregistre") is True and lu and len(lu["cameras"]) == 3 and lu.get("date"))
    kf = {"t": 0, "orbit": [60, 85, 6], "target": [0, 0.85, 0], "fov": 22.94, "easing": "ease-in-out"}
    c.put(f"/api/scenes3d/{SID}", json={"keyframes": [kf]})
    check("5g_le_premier_keyframe_est_la_camera_du_plan",
          js(c.post(f"/api/scenes3d/{SID}/couverture", json={}))["origine"] == "premier_keyframe")
    c.put(f"/api/scenes3d/{SID}", json={"keyframes": []})
    capc = js(c.post(f"/api/scenes3d/{SID}/capture", json={"quand": "camera", "camera_id": "contrechamp", "image_b64": B64}))
    check("5h_capture_de_camera_nommee", capc.get("filename", "").startswith(f"plateau_{SID[:8]}_cam-contrechamp_")
          and js(c.get(f"/api/scenes3d/{SID}"))["couverture"]["cameras"][1]["capture"] == capc.get("filename"), capc)

    print("\n[6] nouveau-plan")
    ap = js(c.post(f"/api/scenes3d/{SID}/couverture/contrechamp/nouveau-plan", json={}))
    n_plans = un("SELECT COUNT(*) FROM shots WHERE chapter_id=?", ch.get("id"))[0]
    check("6a_apercu_sans_ecrire", ap.get("applique") is False and ap["plan"]["idx"] == s0["idx"] + 1
          and ap["plan"]["keyframe_image"] == capc.get("filename") and n_plans == 2, ap)
    fait = js(c.post(f"/api/scenes3d/{SID}/couverture/contrechamp/nouveau-plan", json={"confirmer": True}))
    neuf = un("SELECT idx, shot_type, camera_move, keyframe_image, action, motion_prompt FROM shots WHERE id=?", fait.get("shot_id"))
    check("6b_plan_neuf_juste_apres", neuf is not None and neuf[0] == s0["idx"] + 1 and neuf[2] == "static, locked-off"
          and neuf[3] == capc.get("filename") and neuf[4] == s0.get("action") and neuf[5].startswith("reverse shot on Paul"), neuf)
    check("6c_les_suivants_decales", un("SELECT idx FROM shots WHERE id=?", s1["id"])[0] == s1["idx"] + 1)
    sc2 = js(c.get(f"/api/scenes3d/{fait.get('scene_id')}"))
    check("6d_sa_scene_posee_sur_la_camera", sc2.get("shot_id") == fait.get("shot_id")
          and sc2["camera"]["orbit"] == cv["cameras"][1]["camera"]["orbit"] and len(sc2["keyframes"]) == 1
          and len(sc2["instances"]) == len(INST) and sc2.get("plan", {}).get("id") == fait.get("shot_id"), str(sc2)[:300])
    check("6e_camera_inconnue_404", c.post(f"/api/scenes3d/{SID}/couverture/zz/nouveau-plan", json={}).status_code == 404)
    libre = js(c.post("/api/scenes3d", json={}))
    c.post(f"/api/scenes3d/{libre['id']}/couverture", json={"enregistrer": True})
    check("6f_scene_sans_plan_409", c.post(f"/api/scenes3d/{libre['id']}/couverture/large/nouveau-plan",
                                           json={"confirmer": True}).status_code == 409)

    print("\n[7] Previs → plan")
    src = js(c.get(f"/api/shots/{s0['id']}/previs/sources"))
    video = [m for m in src.get("modeles", []) if m.get("clip")]
    check("7a_sources_rendent_la_legende", (src.get("legende") or {}).get("prompt", "").startswith("Colour-coded previs: "))
    check("7b_prompt_propose_nomme_chaque_forme", video and all("In @Video1 — Colour-coded previs: " in m["prompt_defaut"]
                                                               for m in video), [m["prompt_defaut"] for m in video][:1])
    sans_clip = [m for m in src.get("modeles", []) if not m.get("clip")]
    check("7c_sans_clip_pas_de_legende", all("Colour-coded" not in m["prompt_defaut"] for m in sans_clip))
    dv = js(c.post(f"/api/shots/{s1['id']}/previs/devis", json={}))
    check("7d_un_plan_sans_scene_n_a_pas_de_legende", dv.get("legende") is None and "Colour-coded" not in dv.get("prompt_defaut", ""))

    print("\n[8] image de production")
    c.post(f"/api/scenes3d/{SID}/vers-plan", json={"appliquer": {"keyframe_image": cap["filename"]}, "confirmer": True})
    APPELS.clear()
    TELEVERSES.clear()
    r = c.post(f"/api/shots/{s0['id']}/image", json={})
    pr = (APPELS[0]["arguments"].get("prompt", "") if APPELS else "")
    check("8a_la_capture_coloree_en_derniere_reference", r.status_code == 200 and TELEVERSES and TELEVERSES[-1] == cap["filename"],
          (r.status_code, r.text[:200], TELEVERSES))
    check("8b_la_legende_dans_le_prompt", "Layout: the last reference image is a colour-coded 3D previs" in pr
          and "Colour-coded previs: " in pr, pr)
    APPELS.clear()
    TELEVERSES.clear()
    r = c.post(f"/api/shots/{s1['id']}/image", json={})
    check("8c_sans_previs_le_prompt_d_avant", all("Layout:" not in (a["arguments"].get("prompt") or "") for a in APPELS))

print("\n[A] l'outil d'agent plateau_previs (lecture, proposition)")
import asyncio  # noqa: E402
from app.services import agent_outils as ao, agent_boites as B  # noqa: E402
check("A1_boite_plateau_lecture_registre_sain", B.BOITES.get("plateau", {}).get("outils") == ["plateau_previs"]
      and ao.OUTILS["plateau_previs"]["nature"] == "lecture" and B.verifier() == [], B.verifier())
boucle = asyncio.new_event_loop()
avant = un("SELECT couverture FROM scenes3d WHERE id=?", SID)
ra = boucle.run_until_complete(ao.plateau_previs(ao.Ctx(cid="c1"), plan=s0["id"]))
dd = ra.get("donnees") or {}
check("A2_legende_et_couverture_proposee", ra["ok"] and len(dd["legende"]["fr"]) == 3
      and dd["faisceaux_exclus"] == ["Faisceau du phare"]
      and [x["id"] for x in dd["couverture_proposee"]["cameras"]] == ["large", "contrechamp", "gros_plan"]
      and dd["couverture_proposee"]["regle_180"]["respectee"] and len(dd["couverture_rangee"]) == 3, ra)
check("A3_rien_n_est_ecrit", un("SELECT couverture FROM scenes3d WHERE id=?", SID) == avant)
rb = boucle.run_until_complete(ao.plateau_previs(ao.Ctx(cid="c1"), plan=s1["id"]))
check("A4_plan_sans_scene", rb["ok"] and rb["donnees"]["scene"] is None)
try:
    boucle.run_until_complete(ao.plateau_previs(ao.Ctx(cid="c1"), plan="../x"))
    check("A5_identifiant_refuse", False)
except ao._Refus:
    check("A5_identifiant_refuse", True)
rc = boucle.run_until_complete(ao.executer("plateau_previs", {"plan": s0["id"]}, ao.Ctx(cid="c1")))
check("A6_hors_boite_de_l_agent_refuse_par_executer", rc["ok"] is False and "boîte" in rc["resume"], rc)
boucle.close()

print("\n[9] migration et routes")
from app.services.storage import SCENES3D_COLUMNS  # noqa: E402
check("9a_colonne_declaree", ("couverture", "TEXT") in SCENES3D_COLUMNS)
old = _tmp / "old.db"
cx = sqlite3.connect(str(old))
cx.execute("CREATE TABLE scenes3d (id VARCHAR(36) PRIMARY KEY, nom VARCHAR(120), instances TEXT)")
cx.commit()
cx.close()
code = ("import asyncio,os,sys;sys.path.insert(0,r'%s');os.environ['DATABASE_URL']='sqlite+aiosqlite:///%s';"
        "from app.services.storage import init_db;asyncio.run(init_db())") % (str(_ICI.parent), old.as_posix())
rr = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ))
cols = {r[1] for r in sqlite3.connect(str(old)).execute("PRAGMA table_info(scenes3d)")}
check("9b_base_d_avant_migree", rr.returncode == 0 and "couverture" in cols, (rr.stderr[-300:], cols))
chemins = set(app.openapi()["paths"])
check("9c_routes_montees", {"/api/scenes3d/{sid}/palette", "/api/scenes3d/{sid}/couverture",
                            "/api/scenes3d/{sid}/couverture/{cid}/nouveau-plan"} <= chemins)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
