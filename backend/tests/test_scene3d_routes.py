# -*- coding: utf-8 -*-
"""t127 T3-T4 (07/10/2026) — les routes du Plateau 3D (/api/scenes3d) et le pont vers le plan.

Data-dir temporaire, clés vidées, AUCUN réseau : les routes sont appelées en direct. Un vrai job `assets3d` est écrit
sur disque (un GLB boîte décalée), une vraie base sqlite reçoit les plans.

  [1] création (scène par défaut, scène liée à un plan) ; [2] validation des écritures (400 nommés) ;
  [3] mesure (scène affichée vs enregistrée, écart avec le plan) ; [4] mouvement (durée du plan) ;
  [5] maillages posables (dims, offset, chemins refusés, allégé / plein) ; [6] composition versionnée ;
  [7] captures → images + Bibliothèque « plateau » ; [8] vers-plan (rien sans confirmer, écart dit) ;
  [9] colonnes du plan (migration légère) et montage du routeur.
Run : & $PY tests/test_scene3d_routes.py   (depuis backend/)
"""
import asyncio
import base64
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzs3d_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
for k in ("FAL_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY"):
    os.environ[k] = ""
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


async def appel(f, *a, **k):
    try:
        return (200, await f(*a, **k))
    except Exception as e:
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)))


try:
    from app.services import scene3d_routes as R, scene3d_glb as G, print3d as P
    from app.services.storage import init_db, async_session_factory, Shot, LibraryAsset, SHOTS_COLUMNS
    from app.config import settings
except Exception as e:
    R = None
    print(f"  (import impossible : {e!r})")
check("x0_import", R is not None)
if R is None:
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

L = asyncio.new_event_loop()
run = L.run_until_complete
run(init_db())


async def _plan(shot_type="close-up", move="static, locked-off", duree=4.0):
    async with async_session_factory() as s:
        sh = Shot(id=f"shot-{os.urandom(4).hex()}", chapter_id="chap-1", idx=2, shot_type=shot_type,
                  camera_move=move, duration_s=duree)
        s.add(sh)
        await s.commit()
        return sh.id

SHOT = run(_plan())

print("\n[1] création")
c, d = run(appel(R.creer, {}))
check("1a_scene_par_defaut_un_sujet_capsule_et_une_camera_35mm",
      c == 200 and len(d["instances"]) == 1 and d["instances"][0]["role"] == "sujet"
      and d["instances"][0]["source"] == {"kind": "proxy", "forme": "capsule"} and d["camera"]["orbit"] == [0, 90, 6]
      and abs(d["camera"]["fov"] - 22.9) < 0.1, d)
SID = d["id"]
c, d2 = run(appel(R.creer, {"shot_id": SHOT}))
check("1b_liee_a_un_plan_herite_du_chapitre_et_du_nom", c == 200 and d2["chapter_id"] == "chap-1" and d2["nom"] == "plan 3", d2)
SID_PLAN = d2["id"]
check("1c_plan_inconnu_404", run(appel(R.creer, {"shot_id": "nope"}))[0] == 404)
c, lp = run(appel(R.lire, SID_PLAN))
check("1f_lire_rend_le_plan_lie_pour_la_timeline", c == 200 and lp["plan"]["idx"] == 2 and lp["plan"]["duration_s"] == 4.0
      and lp["plan"]["shot_type"] == "close-up" and "plan" not in run(appel(R.lire, SID))[1], lp.get("plan"))
c, lst = run(appel(R.lister, shot_id=SHOT))
check("1d_liste_filtree_par_plan", c == 200 and [x["id"] for x in lst["scenes"]] == [SID_PLAN] and lst["scenes"][0]["instances"] == 1, lst)
check("1e_identifiant_illisible_404", run(appel(R.lire, "../x"))[0] == 404)

print("\n[2] validation")
SUJ = {"id": "s", "source": {"kind": "proxy", "forme": "capsule"}, "dims": [0.5, 1.7, 0.4], "role": "sujet"}
for nom, body in (("aspect", {"aspect": "4:3"}), ("deux_sujets", {"instances": [SUJ, dict(SUJ, id="t")]}),
                  ("forme", {"instances": [dict(SUJ, source={"kind": "proxy", "forme": "cone"})]}),
                  ("chemin_job", {"instances": [dict(SUJ, source={"kind": "assets3d", "job": "../etc", "file": "model.glb"}, niveau="plein")]}),
                  ("fichier_job", {"instances": [dict(SUJ, source={"kind": "assets3d", "job": "abc", "file": "x.glb"}, niveau="plein")]}),
                  ("proxy_sans_dims", {"instances": [dict(SUJ, dims=None)]}),
                  ("niveau_incoherent", {"instances": [dict(SUJ, niveau="plein")]}),
                  ("keyframes_recul", {"keyframes": [{"t": 1, "orbit": [0, 90, 5], "target": [0, 1, 0], "fov": 30},
                                                     {"t": 1, "orbit": [0, 90, 4], "target": [0, 1, 0], "fov": 30}]}),
                  ("focale", {"focale_mm": 2}), ("ids_doubles", {"instances": [dict(SUJ), dict(SUJ, role="decor")]})):
    check(f"2_{nom}_refuse_400", run(appel(R.modifier, SID, body))[0] == 400)
c, d = run(appel(R.modifier, SID, {"nom": "Lina au quai", "aspect": "2.39:1", "instances": [SUJ, {
    "id": "mur", "source": {"kind": "proxy", "forme": "boite"}, "dims": [4, 3, 0.2], "role": "decor",
    "transform": {"pos": [0, 0, -3]}}]}))
check("2k_ecriture_valide_persistee_et_normalisee", c == 200 and d["aspect"] == "2.39:1" and d["nom"] == "Lina au quai"
      and d["instances"][1]["transform"] == {"pos": [0.0, 0.0, -3.0], "rot": [0.0, 0.0, 0.0], "scale": 1.0}
      and d["instances"][1]["couleur"] == "#8a8f98", d)

print("\n[3] mesure")
CAM = {"orbit": [0, 90, 6], "target": [0, 0.85, 0], "fov": 22.94}
c, m = run(appel(R.mesurer, SID, {"camera": CAM}))
check("3a_mesure_du_cadre", c == 200 and m["shot_type"] == "medium" and "plan" not in m, m)
c, m2 = run(appel(R.mesurer, SID, {"camera": CAM, "scene": {"instances": [dict(SUJ, transform={"pos": [0, 0, 3]})]}}))
check("3b_la_scene_affichee_l_emporte_sur_le_disque", c == 200 and m2["shot_type"] == "extreme close-up", m2)
c, m3 = run(appel(R.mesurer, SID_PLAN, {"camera": CAM}))
check("3c_ecart_avec_le_plan_lie_dit", c == 200 and m3["plan"] == {"shot_type": "close-up", "ecart": True}, m3)
check("3d_seuils_invalides_400", run(appel(R.mesurer, SID, {"camera": CAM, "seuils": {"zz": 1}}))[0] == 400)

print("\n[4] mouvement")
KF = [{"t": 0, "orbit": [0, 90, 6.2], "target": [0, 0.85, 0], "fov": 22.94},
      {"t": 5, "orbit": [0, 90, 2.4], "target": [0, 0.85, 0], "fov": 22.94}]
c, mv = run(appel(R.mouvement, SID_PLAN, {"keyframes": KF}))
check("4a_push_in_et_prompt", c == 200 and mv["camera_move"] == "slow push-in" and "6.2 m to 2.4 m" in mv["motion_prompt"], mv)
check("4b_ecart_et_duree_du_plan_depassee_dits", mv["plan"]["ecart"] is True and any("dépasse la durée" in a for a in mv["avertissements"]), mv)
check("4c_sans_keyframe_400", run(appel(R.mouvement, SID, {}))[0] == 400)

print("\n[5] maillages posables")
JOB = "abc12345"
jd = settings.outputs_path / "assets3d" / JOB
jd.mkdir(parents=True, exist_ok=True)
boite = P.glb_de_triangles(G.placer(G.triangles_proxy("boite", [4, 2, 1]), {"pos": [10, 5, 10]}), "piece")
(jd / "model.glb").write_bytes(boite)
(jd / "asset.json").write_text(json.dumps({"name": "Caisse", "engine": "test", "stage": "done"}), encoding="utf-8")
c, sd = run(appel(R.source_dims, job=JOB, file="model.glb"))
check("5a_dims_et_offset_du_maillage", c == 200 and [round(x, 6) for x in sd["dims"]] == [4, 2, 1]
      and [round(x, 6) for x in sd["offset"]] == [-10, -5, -10] and sd["tris"] == 12, sd)
check("5b_chemin_refuse_400", run(appel(R.source_dims, job="..", file="model.glb"))[0] == 400
      and run(appel(R.source_dims, job=JOB, file="../model.glb"))[0] == 400)
check("5c_version_absente_404", run(appel(R.source_dims, job=JOB, file="model.v7.glb"))[0] == 404)
c, src = run(appel(R.sources))
check("5d_sources_listent_le_job", c == 200 and any(j["job"] == JOB and any(v["file"] == "model.glb" for v in j["versions"]) for j in src["jobs"]), src)
c, mp = run(appel(R.maillage, job=JOB, file="model.glb", niveau="plein"))
check("5e_plein_sert_le_fichier", c == 200 and str(getattr(mp, "path", "")).endswith("model.glb"))
c, ma = run(appel(R.maillage, job=JOB, file="model.glb", niveau="allege"))
check("5f_allege_d_un_petit_maillage_le_garde_et_le_dit", c == 200 and ma.body == boite and ma.headers.get("x-decime") == "0", (c, getattr(ma, "headers", None)))
check("5g_niveau_inconnu_400", run(appel(R.maillage, job=JOB, file="model.glb", niveau="ultra"))[0] == 400)

print("\n[6] composition")
MESH = {"id": "caisse", "source": {"kind": "assets3d", "job": JOB, "file": "model.glb"}, "niveau": "plein",
        "role": "decor", "transform": {"pos": [2, 0, 0]}}
run(appel(R.modifier, SID, {"instances": [SUJ, MESH]}))
c, cp = run(appel(R.composer, SID))
check("6a_compose_v1_relu_par_le_lecteur", c == 200 and cp["version"] == 1 and (settings.outputs_path / "scenes3d" / SID / "scene.v1.glb").is_file()
      and len(P.lire_glb_triangles((settings.outputs_path / "scenes3d" / SID / "scene.v1.glb").read_bytes())) == cp["rapport"]["tris_total"], cp if c != 200 else cp["rapport"])
check("6b_fiche_mesh_report_jointe", c == 200 and isinstance(cp.get("fiche"), dict) and cp["fiche"], cp.get("fiche") if c == 200 else cp)
c, d = run(appel(R.lire, SID))
check("6c_dims_mesurees_du_maillage_remontees_dans_la_scene", [round(x, 6) for x in d["instances"][1]["dims"]] == [4, 2, 1], d["instances"])
c, cp2 = run(appel(R.composer, SID))
c3, f = run(appel(R.scene_glb, SID))
check("6d_recomposer_versionne_et_sert_la_derniere", cp2["version"] == 2 and str(f.path).endswith("scene.v2.glb"), (cp2.get("version"), getattr(f, "path", f)))
check("6e_glb_non_compose_404", run(appel(R.scene_glb, SID_PLAN))[0] == 404)

print("\n[7] captures")
from PIL import Image
buf = io.BytesIO()
Image.new("RGB", (32, 18), (200, 40, 40)).save(buf, "PNG")
B64 = base64.b64encode(buf.getvalue()).decode()
c, cap1 = run(appel(R.capture, SID_PLAN, {"quand": "debut", "image_b64": "data:image/png;base64," + B64}))
c2, cap2 = run(appel(R.capture, SID_PLAN, {"quand": "debut", "image_b64": B64}))
check("7a_capture_png_numerotee", c == 200 and c2 == 200 and cap1["filename"] == f"plateau_{SID_PLAN[:8]}_debut_1.png"
      and cap2["filename"].endswith("_debut_2.png") and (settings.images_path / cap1["filename"]).is_file(), (cap1, cap2))


async def _prov(nom):
    from sqlalchemy import select
    async with async_session_factory() as s:
        r = (await s.execute(select(LibraryAsset).where(LibraryAsset.filename == nom))).scalars().first()
        return r and (r.source, r.recette)
prov = run(_prov(cap1["filename"]))
check("7b_bibliotheque_provenance_plateau_avec_recette", prov and prov[0] == "plateau" and "plateau" in str(prov[1]), prov)
jpg = io.BytesIO()
Image.new("RGB", (8, 8)).save(jpg, "JPEG")
check("7c_non_png_415", run(appel(R.capture, SID_PLAN, {"quand": "fin", "image_b64": base64.b64encode(jpg.getvalue()).decode()}))[0] == 415)
check("7d_quand_inconnu_400", run(appel(R.capture, SID_PLAN, {"quand": "milieu", "image_b64": B64}))[0] == 400)
check("7e_base64_illisible_400", run(appel(R.capture, SID_PLAN, {"quand": "fin", "image_b64": "%%%"}))[0] == 400)

print("\n[8] vers-plan")
AP = {"shot_type": "medium", "camera_move": "slow push-in", "motion_prompt": mv["motion_prompt"], "keyframe_image": cap1["filename"]}
c, vp = run(appel(R.vers_plan, SID_PLAN, {"appliquer": AP}))


async def _lire_plan():
    async with async_session_factory() as s:
        sh = await s.get(Shot, SHOT)
        return {k: getattr(sh, k) for k in ("shot_type", "camera_move", "motion_prompt", "keyframe_image", "image")}
avant = run(_lire_plan())
check("8a_sans_confirmer_rien_n_est_ecrit_l_ecart_est_dit",
      c == 200 and vp["applique"] is False and vp["avant"]["shot_type"] == "close-up" and "camera_move" in vp["change"]
      and avant["shot_type"] == "close-up" and avant["motion_prompt"] is None, (vp, avant))
c, vp2 = run(appel(R.vers_plan, SID_PLAN, {"appliquer": AP, "confirmer": True}))
apres = run(_lire_plan())
check("8b_confirmer_ecrit_les_quatre_champs_sans_toucher_l_image_de_production",
      c == 200 and vp2["applique"] is True and apres["shot_type"] == "medium" and apres["camera_move"] == "slow push-in"
      and apres["motion_prompt"] == mv["motion_prompt"] and apres["keyframe_image"] == cap1["filename"] and apres["image"] is None, apres)
c, vp3 = run(appel(R.vers_plan, SID_PLAN, {"appliquer": AP, "confirmer": True}))
check("8c_rien_a_changer_rien_d_applique", c == 200 and vp3["change"] == [] and vp3["applique"] is False, vp3)
# une image EXISTANTE qui n'est pas une capture du Plateau : seul le préfixe la refuse (témoin d'existence ci-dessous)
(settings.images_path / "photo.png").write_bytes(buf.getvalue())
check("8d0_temoin_photo_existe", (settings.images_path / "photo.png").is_file())
for nom, ap in (("move_inconnu", {"camera_move": "drone"}), ("image_pas_du_plateau", {"keyframe_end": "photo.png"}),
                ("champ_inconnu", {"image": "x.png"}), ("vide", {})):
    check(f"8_{nom}_400", run(appel(R.vers_plan, SID_PLAN, {"appliquer": ap}))[0] == 400)
check("8h_scene_sans_plan_409", run(appel(R.vers_plan, SID, {"appliquer": {"shot_type": "wide"}}))[0] == 409)
from app.api import routes as RT


async def _dict_plan():
    async with async_session_factory() as s:
        return RT._shot_dict(await s.get(Shot, SHOT))
sdict = run(_dict_plan())
check("8i_le_plan_serialise_porte_le_pont", sdict["motion_prompt"] == mv["motion_prompt"] and sdict["keyframe_image"] == cap1["filename"]
      and "keyframe_end" in sdict, sdict)

print("\n[9] colonnes et routeur")
check("9a_shots_columns_declarees", {"motion_prompt", "keyframe_image", "keyframe_end"} <= {n for n, _t in SHOTS_COLUMNS})
# une base « d'avant » : la table shots sans les trois colonnes → _auto_migrate les ajoute
old = TMP + "/old.db"
cx = sqlite3.connect(old)
cx.execute("CREATE TABLE shots (id VARCHAR(36) PRIMARY KEY, chapter_id VARCHAR(36), idx INTEGER, shot_type VARCHAR(30), "
           "camera_move VARCHAR(40), duration_s FLOAT, created_at DATETIME, updated_at DATETIME)")
cx.commit()
cx.close()
code = ("import asyncio,os,sys;sys.path.insert(0,r'%s');os.environ['DATABASE_URL']='sqlite+aiosqlite:///%s';"
        "from app.services.storage import init_db;asyncio.run(init_db())") % (os.path.join(HERE, ".."), old.replace("\\", "/"))
import subprocess
rr = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ))
cols = {r[1] for r in sqlite3.connect(old).execute("PRAGMA table_info(shots)")}
check("9b_base_d_avant_migree", rr.returncode == 0 and {"motion_prompt", "keyframe_image", "keyframe_end", "image"} <= cols, (rr.stderr[-300:], cols))
from app.main import app
chemins = set(app.openapi()["paths"])   # `app.routes` n'aplatit pas les routeurs inclus (test_cards_core, test_dictation)
check("9c_routeur_monte_sous_api_scenes3d", {"/api/scenes3d", "/api/scenes3d/{sid}/mesure", "/api/scenes3d/{sid}/vers-plan",
                                            "/api/scenes3d/maillage"} <= chemins, sorted(c for c in chemins if "scenes3d" in c))

L.close()
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
