# -*- coding: utf-8 -*-
"""t335 (A5 du lot Scenario, 28/10/2026) — « Previs → plan » : clip de previs (@Video1) + style frames (@Image1…) →
la vidéo du plan par Seedance 2.5 reference-to-video (fal), ou les style frames seules par Veo 3.1 références.

  [R] video_refs (PUR) : l'entrée Seedance v2v (endpoint relu le 28/10, `video_urls` + `image_urls`, `task`), la durée
      seulement en « reference », la résolution, l'audio coupé, les @Video1/@ImageN non nommés DITS, le plafond de
      style frames DIT ; le prix (entrée + sortie) × tarif × 0,6 ; les bornes du clip ; Kling hors des modèles tirés ;
  [P] pricing.estimate kind « video_refs » == video_refs.cout_estime ;
  [S] GET /shots/{id}/previs/sources : modèles (sans clé : listés, dispo False), clips (la vidéo du plan d'abord),
      images du plan, prompt proposé ;
  [D] POST /shots/{id}/previs/devis : gratuit (zéro ligne depenses, rien envoyé), refus et clé absente DITS ;
  [T] POST /shots/{id}/previs : 404 / 400 modèle / 503 clé AVANT tout / 400 clip hors bornes / 400 sans style frame /
      409 sans confirme_cout (devis joint) / 402 plafond « chapitres » / tir : job « previs » rattaché au plan, envoi
      fal exact, vidéo dans la Bibliothèque (source atelier, relation previs, mère = le clip, recette) ; Veo sans clip ;
  [G] video_refs est appelé par une VRAIE route (il ne l'était par aucune) ; le point d'accroche de t336 existe.
AUCUN appel réseau réel : fal_client.* et httpx sortant comptent ; les trois coutures de previs_plan sont des espions.
ffmpeg RÉEL (petits clips testsrc). Run (depuis backend/) : & $PY tests/test_chapitres_previs_plan.py"""
import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzprevis335_")
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
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable")
    sys.exit(0)

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


def leve(f):
    try:
        f()
    except ValueError as e:
        return str(e)
    return None


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

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
import app.main as _MAIN  # noqa: E402
from app.services import pricing as P, plafonds as PL  # noqa: E402
from app.services import video_refs as VR  # noqa: E402
from app.services.storage import init_db  # noqa: E402
try:
    from app.services import previs_plan as PV  # noqa: E402
except ImportError as e:  # le témoin : avant t335, le module n'existe pas
    PV = None
    check("T0 le module previs_plan existe", False, str(e))
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

W = pathlib.Path(_tmp)
IMG = W / "images"
UP = W / "outputs" / "uploads"
UP.mkdir(parents=True, exist_ok=True)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())


def ffmpeg_clip(dest, secondes, w=360, h=640, fps=24):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc=size={w}x{h}:rate={fps}:duration={secondes}", "-pix_fmt", "yuv420p", str(dest)],
                   check=True)
    return dest


# t336 : le clip de previs fait 5 s (au-dessus du plancher de 4 s de Seedance) : il part TEL QUEL ; le clip hors
# bornes est TROP ÉTROIT (un clip trop court est désormais conformé : test_previs_conform_recalage)
CLIP = ffmpeg_clip(UP / "previs_clay.mp4", 5)
COURT = ffmpeg_clip(UP / "trop_court.mp4", 5, w=200, h=356)
RENDU = ffmpeg_clip(W / "rendu_fal.mp4", 5)

TELEVERSES, SOUMIS, TELECHARGES = [], [], []


async def _upload(path):
    TELEVERSES.append(pathlib.Path(path).name)
    return f"https://fal.test/up/{pathlib.Path(path).name}"


async def _fal_subscribe(endpoint, arguments):
    SOUMIS.append((endpoint, json.loads(json.dumps(arguments))))
    return {"video": {"url": "https://fal.test/out/rendu.mp4"}, "seed": 4242}


async def _download(url, dest):
    TELECHARGES.append(url)
    shutil.copy(RENDU, dest)

PV._upload, PV._fal_subscribe, PV._download = _upload, _fal_subscribe, _download


def sql(q, *a):
    con = sqlite3.connect(str(W / "t.db"))
    try:
        r = con.execute(q, a)
        con.commit()
        return r.fetchall()
    finally:
        con.close()


def depenses():
    try:
        return sql("SELECT moteur, categorie, op, estime_usd FROM depenses")
    except sqlite3.OperationalError:
        return []


async def _req(meth, path, body=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient", timeout=120) as c:
        if meth == "GET":
            return await c.get("/api" + path)
        return await c.post("/api" + path, json=body)


def call(meth, path, body=None):
    return loop.run_until_complete(_req(meth, path, body))


def js(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


# ── [R] le registre PUR ──────────────────────────────────────────────────────
print("[R] video_refs : Seedance 2.5 reference-to-video")
S = VR.REGISTRE_REFS.get("seedance-2.5-v2v") or {}
check("R1 l'endpoint RELU le 28/10 : bytedance/seedance-2.5/reference-to-video (pas de « video-to-video » Seedance)",
      S.get("endpoint") == "bytedance/seedance-2.5/reference-to-video" and S.get("champ_video") == "video_urls"
      and S.get("champ") == "image_urls" and VR.VERIFIE_SEEDANCE_LE == "2026-10-28", S)
fr = [{"nom": f"f{i}", "face": f"u{i}"} for i in range(6)]
ep, a, n = VR.construire("seedance-2.5-v2v", "@Video1 dans le look de @Image1", fr[:1], video_url="clip",
                         resolution="720p")
check("R2 editing par défaut : video_urls = [clip], image_urls, task editing, PAS de durée (elle suit le clip), "
      "720p, audio coupé", ep == S.get("endpoint") and a.get("video_urls") == ["clip"] and a.get("image_urls") == ["u0"]
      and a.get("task") == "editing" and "duration" not in a and a.get("resolution") == "720p"
      and a.get("generate_audio") is False and "seed" not in a and n == [], f"{a} {n}")
_, a, n = VR.construire("seedance-2.5-v2v", "rien", fr, video_url="clip", tache="reference", duree=40,
                        resolution="1080p")
check("R3 reference : durée bornée 4-30 (40 -> 30), 6 frames -> 4, 1080p -> 720p, @Video1/@ImageN absents : tout DIT",
      a.get("task") == "reference" and a.get("duration") == 30 and a.get("image_urls") == ["u0", "u1", "u2", "u3"]
      and a.get("resolution") == "720p" and any("6 style frames -> 4" in x for x in n)
      and any("40s -> 30s" in x for x in n) and any("1080p -> 720p" in x for x in n)
      and any("@Video1, @Image1, @Image2, @Image3, @Image4" in x for x in n), f"{a} {n}")
check("R4 sans clip : refus ; sans style frame : refus ; tâche inconnue : refus",
      "clip" in (leve(lambda: VR.construire("seedance-2.5-v2v", "p", fr[:1])) or "")
      and "au moins 1" in (leve(lambda: VR.construire("seedance-2.5-v2v", "p", [], video_url="c")) or "")
      and "extension" in (leve(lambda: VR.construire("seedance-2.5-v2v", "p", fr[:1], video_url="c",
                                                      tache="extension")) or ""))
check("R5 prix : (5 s entrée + 5 s sortie) × 0,473 × 0,6 = 2,838 $ en 720p ; 480p : × 0,2205",
      VR.cout_estime("seedance-2.5-v2v", 5, entree_s=5, resolution="720p") == round(10 * 0.473 * 0.6, 4)
      and VR.cout_estime("seedance-2.5-v2v", 4, entree_s=2.5, resolution="480p") == round(6.5 * 0.2205 * 0.6, 4))
check("R6 bornes du clip : 1 s, .webm, 200 px, 15 i/s refusés ; 2,5 s 360×640 24 i/s accepté",
      "durée" in (VR.clip_refuse("seedance-2.5-v2v", nom="a.mp4", secondes=1, largeur=360, hauteur=640, fps=24,
                                 octets=1) or "")
      and "MP4" in (VR.clip_refuse("seedance-2.5-v2v", nom="a.webm", secondes=3, largeur=360, hauteur=640, fps=24,
                                   octets=1) or "")
      and "côtés" in (VR.clip_refuse("seedance-2.5-v2v", nom="a.mp4", secondes=3, largeur=200, hauteur=640, fps=24,
                                     octets=1) or "")
      and "cadence" in (VR.clip_refuse("seedance-2.5-v2v", nom="a.mov", secondes=3, largeur=360, hauteur=640, fps=15,
                                       octets=1) or "")
      and VR.clip_refuse("seedance-2.5-v2v", nom="a.mp4", secondes=2.5, largeur=360, hauteur=640, fps=24,
                         octets=1) is None)
check("R7 les modèles tirés : Seedance v2v (défaut) et Veo références ; Kling (prix non publié) n'y est PAS",
      VR.MODELES_PREVIS == ("seedance-2.5-v2v", "veo-3.1-ref") and VR.DEFAUT_PREVIS == "seedance-2.5-v2v")

print("\n[P] pricing")
op = VR.op_devis("seedance-2.5-v2v", 5, secondes_entree=5, resolution="720p")
check("P1 estimate(kind video_refs) == cout_estime, ligne fal", abs(P.estimate(op)["total_usd"] - 2.838) < 1e-9
      and P.estimate(op)["breakdown"][0]["provider"] == "fal", P.estimate(op))
check("P2 Veo références : 8 s × 0,20 $ = 1,60 $",
      P.estimate(VR.op_devis("veo-3.1-ref", 8))["total_usd"] == 1.6)
check("P3 modèle inconnu : ligne à 0 qui le DIT",
      P.estimate({"kind": "video_refs", "modele": "x"})["total_usd"] == 0
      and "inconnu" in P.estimate({"kind": "video_refs", "modele": "x"})["breakdown"][0]["label"])
check("P4 le conform (t336) rend tel quel un clip dans les bornes (5 s, 24 i/s, MP4)",
      PV.conformer_clip(CLIP, {"secondes": 5, "fps": 24, "images": 120}, "seedance-2.5-v2v", 4)[:3:2] == (CLIP, []))
inf = PV.infos_clip(CLIP)
check("P5 la sonde du clip (ffprobe) : 5 s, 360×640, 24 i/s, 120 images",
      abs((inf["secondes"] or 0) - 5) < 0.05 and inf["images"] == 120 and (inf["largeur"], inf["hauteur"]) == (360, 640)
      and abs((inf["fps"] or 0) - 24) < 0.01, inf)

# ── le décor : un chapitre, deux plans, un clip de la Bibliothèque ─────────
ch = js(call("POST", "/chapters", {"title": "C", "script_text": "Vane entre.\n\nLa table tombe."}))
CID = ch.get("id")
shots = js(call("POST", f"/chapters/{CID}/storyboard/decoupe", {"method": "paragraph"})).get("shots", [])
s0, s1 = shots[0]["id"], shots[1]["id"]
for nom, coul in (("prod0.png", (200, 40, 40)), ("look2.png", (40, 200, 40)), ("k0.png", (90, 90, 90))):
    Image.new("RGB", (90, 160), coul).save(IMG / nom)
sql("UPDATE shots SET image=?, keyframe_image=?, duration_s=5.0 WHERE id=?", "prod0.png", "k0.png", s0)
fini = W / "outputs" / "final" / "previs_job.mp4"
fini.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(CLIP, fini)
sql("INSERT INTO jobs (id, status, progress, title, image_filename, final_video_path, duration_s, created_at) "
    "VALUES (?,?,?,?,?,?,?,?)", "job-previs", "done", 100, "previs clay", "k0.png", str(fini), 2,
    "2026-10-28 10:00:00")
sql("UPDATE shots SET video='job-previs' WHERE id=?", s0)

print("\n[S] GET /shots/{id}/previs/sources")
r = call("GET", f"/shots/{s0}/previs/sources")
d = js(r)
check("S1 200 : deux modèles (Seedance v2v défaut, Veo références), dispo avec la clé", r.status_code == 200
      and [m["id"] for m in d.get("modeles", [])] == ["seedance-2.5-v2v", "veo-3.1-ref"]
      and d.get("defaut") == "seedance-2.5-v2v" and all(m["dispo"] for m in d["modeles"]), r.text[:400])
check("S2 les clips : la vidéo du plan d'abord (origine « plan »)", (d.get("clips") or [{}])[0].get("job_id")
      == "job-previs" and d["clips"][0]["origine"] == "plan", d.get("clips"))
check("S3 les images du plan : production puis borne du Plateau", [(i["nom"], i["origine"]) for i in d.get("images", [])]
      == [("prod0.png", "production"), ("k0.png", "plateau_debut")], d.get("images"))
check("S4 le prompt proposé nomme @Video1 et @Image1, et reprend l'action du plan",
      "@Video1" in d["modeles"][0]["prompt_defaut"] and "@Image1" in d["modeles"][0]["prompt_defaut"]
      and "Vane entre." in d["modeles"][0]["prompt_defaut"], d["modeles"][0].get("prompt_defaut"))
check("S5 plan inconnu : 404", call("GET", "/shots/zzz/previs/sources").status_code == 404)

print("\n[D] POST /shots/{id}/previs/devis (gratuit)")
r = call("POST", f"/shots/{s0}/previs/devis", {"clip_id": "job-previs"})
d = js(r)
attendu = VR.cout_estime("seedance-2.5-v2v", d.get("secondes_sortie") or 0, entree_s=d.get("secondes_entree") or 0,
                         resolution="720p")
check("D1 devis : clip du plan, style frame par défaut = l'image de PRODUCTION (pas la capture grise), editing, "
      "usd = (entrée + sortie) × 0,473 × 0,6", r.status_code == 200 and d.get("refus") is None
      and d.get("style_frames") == ["prod0.png"] and d.get("tache") == "editing"
      and abs((d.get("secondes_entree") or 0) - 5) < 0.05 and d.get("conform") is None and d.get("secondes_sortie") == d.get("secondes_entree")
      and d.get("usd") == attendu and attendu > 0, r.text[:500])
check("D2 le devis n'écrit rien et n'envoie rien", depenses() == [] and not TELEVERSES and not SOUMIS)
r = call("POST", f"/shots/{s0}/previs/devis", {"video_filename": "trop_court.mp4"})
check("D3 clip trop étroit (200 px) : refus DIT dans le devis (pas d'exception)", r.status_code == 200
      and "côtés" in (js(r).get("refus") or ""), r.text[:300])
r = call("POST", f"/shots/{s0}/previs/devis", {"modele": "veo-3.1-ref", "style_frames": ["prod0.png", "look2.png"]})
check("D4 Veo références : sans clip, 8 s, 1,60 $", r.status_code == 200 and js(r).get("refus") is None
      and js(r).get("usd") == 1.6 and js(r).get("clip") is None, r.text[:300])
settings.FAL_KEY = ""
r = call("POST", f"/shots/{s0}/previs/devis", {"clip_id": "job-previs"})
check("D5 sans clé : le devis se montre quand même, la clé est NOMMÉE", r.status_code == 200
      and js(r).get("cle_absente") == "FAL_KEY" and (js(r).get("usd") or 0) > 0, r.text[:300])

print("\n[T] POST /shots/{id}/previs (payant)")
r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs", "confirme_cout": True})
check("T1 sans FAL_KEY : 503 qui nomme la clé, AVANT tout (zéro ligne depenses, rien envoyé)",
      r.status_code == 503 and "FAL_KEY" in r.text and depenses() == [] and not TELEVERSES and not SOUMIS,
      f"{r.status_code} {r.text[:300]}")
settings.FAL_KEY = "test-key"
check("T2 plan inconnu : 404", call("POST", "/shots/zzz/previs", {}).status_code == 404)
r = call("POST", f"/shots/{s0}/previs", {"modele": "kling-v3-pro-elements", "confirme_cout": True})
check("T3 Kling éléments (prix non publié) : 400, jamais tiré", r.status_code == 400 and "prix" in r.text, r.text[:300])
r = call("POST", f"/shots/{s0}/previs", {"modele": "inconnu", "confirme_cout": True})
check("T4 modèle inconnu : 400", r.status_code == 400, r.text[:300])
r = call("POST", f"/shots/{s0}/previs", {"confirme_cout": True})
check("T5 Seedance sans clip : 400 qui le dit", r.status_code == 400 and "clip" in r.text.lower(), r.text[:300])
r = call("POST", f"/shots/{s0}/previs", {"video_filename": "trop_court.mp4", "confirme_cout": True})
check("T6 clip hors bornes : 400", r.status_code == 400 and "côtés" in r.text, r.text[:300])
r = call("POST", f"/shots/{s1}/previs", {"clip_id": "job-previs", "confirme_cout": True})
check("T7 plan sans image de production et sans style frame choisie : 400", r.status_code == 400
      and "style frame" in r.text, r.text[:300])
r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs", "style_frames": ["../t.db"], "confirme_cout": True})
check("T8 une style frame hors du dossier des images : 400", r.status_code == 400, r.text[:300])
r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs", "resolution": "4k", "confirme_cout": True})
check("T9 résolution hors registre : 400", r.status_code == 400, r.text[:300])
r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs"})
det = js(r).get("detail") if isinstance(js(r), dict) else None
check("T10 sans confirme_cout : 409, le devis JOINT (usd), rien envoyé ni écrit",
      r.status_code == 409 and isinstance(det, dict) and det.get("usd") == attendu
      and (det.get("devis") or {}).get("style_frames") == ["prod0.png"] and depenses() == [] and not SOUMIS,
      f"{r.status_code} {r.text[:300]}")
PL.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs", "confirme_cout": True})
det = js(r).get("detail") if isinstance(js(r), dict) else None
check("T11 plafond bas : 402 dz_plafond « chapitres », rien envoyé, le plan garde sa vidéo",
      r.status_code == 402 and isinstance(det, dict) and det.get("dz_plafond", {}).get("categorie") == "chapitres"
      and not SOUMIS and sql("SELECT video FROM shots WHERE id=?", s0) == [("job-previs",)],
      f"{r.status_code} {r.text[:300]}")
PL.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})

r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs", "style_frames": ["prod0.png", "look2.png"],
                                         "confirme_cout": True})
j = js(r)
jid = j.get("job_id")
check("T12 le tir : 200, job_id, shot.video == le job, usd == le devis (2 frames : même prix)",
      r.status_code == 200 and jid and j.get("video") == jid and j.get("usd") == attendu
      and sql("SELECT video FROM shots WHERE id=?", s0) == [(jid,)], f"{r.status_code} {r.text[:300]}")
check("T13 téléversés : le CLIP d'abord, puis les style frames dans l'ordre",
      TELEVERSES == ["previs_job.mp4", "prod0.png", "look2.png"], TELEVERSES)
ep, args = SOUMIS[0] if SOUMIS else (None, {})
check("T14 la soumission : Seedance 2.5 reference-to-video, video_urls = [clip], image_urls = frames, task editing, "
      "audio coupé, prompt qui nomme @Video1 et @Image1",
      len(SOUMIS) == 1 and ep == "bytedance/seedance-2.5/reference-to-video"
      and args.get("video_urls") == ["https://fal.test/up/previs_job.mp4"]
      and args.get("image_urls") == ["https://fal.test/up/prod0.png", "https://fal.test/up/look2.png"]
      and args.get("task") == "editing" and args.get("generate_audio") is False
      and "@Video1" in args.get("prompt", "") and "@Image1" in args.get("prompt", ""), SOUMIS)
job = sql("SELECT status, provider, video_model, final_prompt, seed, final_video_path FROM jobs WHERE id=?", jid)
check("T15 le job : fini, provider previs, modèle, prompt EXACT envoyé, graine, fichier présent",
      job and job[0][0] == "done" and job[0][1] == "previs" and job[0][2] == "seedance-2.5-v2v"
      and job[0][3] == args.get("prompt") and job[0][4] == 4242 and pathlib.Path(job[0][5]).is_file()
      and pathlib.Path(job[0][5]).parent == UP, job)
lib = sql("SELECT source, kind, job_id, parent_filename, relation, recette FROM library_assets WHERE filename=?",
          pathlib.Path(job[0][5]).name if job else "")
rec = json.loads(lib[0][5]) if lib and lib[0][5] else {}
check("T16 la Bibliothèque : source atelier, vidéo, mère = le clip de previs, relation previs",
      lib and lib[0][:5] == ("atelier", "video", jid, "previs_job.mp4", "previs"), lib)
check("T17 la recette : modèle, endpoint, prompt, tâche, résolution, clip, style frames, plan, usd, graine",
      rec.get("modele") == "seedance-2.5-v2v" and rec.get("endpoint") == ep and rec.get("prompt") == args.get("prompt")
      and rec.get("tache") == "editing" and rec.get("resolution") == "720p" and rec.get("clip") == "previs_job.mp4"
      and rec.get("style_frames") == ["prod0.png", "look2.png"] and rec.get("plan") == s0
      and rec.get("usd") == attendu and rec.get("seed") == 4242, rec)
dep = depenses()
check("T18 UNE ligne depenses « chapitres » au chiffre du devis", len(dep) == 1 and dep[0][1] == "chapitres"
      and abs(dep[0][3] - attendu) < 1e-9, dep)
rc = call("GET", f"/jobs/{jid}/recette")
check("T19 /jobs/{id}/recette lit le prompt exact et le modèle", rc.status_code == 200
      and args.get("prompt", "?") in rc.text and "seedance-2.5-v2v" in rc.text, rc.text[:300])

SOUMIS.clear(); TELEVERSES.clear()
r = call("POST", f"/shots/{s1}/previs", {"modele": "veo-3.1-ref", "style_frames": ["look2.png"],
                                         "confirme_cout": True})
check("T20 Veo références sans clip : image_urls = la frame, 8s, 9:16, audio coupé",
      r.status_code == 200 and len(SOUMIS) == 1 and SOUMIS[0][0] == "fal-ai/veo3.1/reference-to-video"
      and SOUMIS[0][1].get("image_urls") == ["https://fal.test/up/look2.png"] and SOUMIS[0][1].get("duration") == "8s"
      and SOUMIS[0][1].get("aspect_ratio") == "9:16" and SOUMIS[0][1].get("generate_audio") is False
      and TELEVERSES == ["look2.png"], f"{r.status_code} {r.text[:200]} {SOUMIS}")
lib = sql("SELECT parent_filename, relation FROM library_assets WHERE job_id=?", js(r).get("job_id"))
check("T21 sans clip, la mère est la 1re style frame", lib == [("look2.png", "previs")], lib)


async def _echec(endpoint, arguments):
    SOUMIS.append((endpoint, arguments))
    return {"detail": "rien"}
PV._fal_subscribe = _echec
r = call("POST", f"/shots/{s1}/previs", {"modele": "veo-3.1-ref", "style_frames": ["look2.png"],
                                         "confirme_cout": True})
st = sql("SELECT status, error FROM jobs WHERE id=?", js(r).get("job_id"))
check("T22 une réponse fal sans vidéo : le job passe FAILED avec la raison (jamais de job fantôme)",
      st and st[0][0] == "failed" and "aucune vidéo" in (st[0][1] or ""), st)

print("\n[G] branchement")
hors = [p.relative_to(_ICI.parent).as_posix() for p in (_ICI.parent / "app").rglob("*.py")
        if p.name != "video_refs.py" and "video_refs" in p.read_text(encoding="utf-8", errors="replace")]
check("G1 video_refs est appelé par une VRAIE route (api/routes.py) et par previs_plan / pricing",
      "app/api/routes.py" in hors and "app/services/previs_plan.py" in hors, hors)
paths = app.openapi()["paths"]
check("G2 les trois routes sont publiées", all(x in paths for x in (
    "/api/shots/{shot_id}/previs", "/api/shots/{shot_id}/previs/devis", "/api/shots/{shot_id}/previs/sources")),
    [p for p in paths if "previs" in p])
check("G3 aucun appel réseau dans tout le banc", RESEAU["n"] == 0, RESEAU)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
