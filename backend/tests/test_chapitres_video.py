# -*- coding: utf-8 -*-
"""t189 (G7, plan « Génération IA enrichie ») — la VIDÉO d'un plan du storyboard, et l'animatique qui la préfère.

  [V] POST /shots/{id}/video : image de début = keyframe_image (Plateau), sinon l'image de production, sinon le croquis ;
      fin = keyframe_end ; prompt = motion_prompt du plan, sinon son action ; modèle par défaut AVEC une fin = Veo 3.1
      Fast first-last (veo-3.1-fast-fal), sans fin = le défaut vidéo de l'app (inchangé) ; les gardes de /generate
      dans le même ordre (503 clé AVANT tout, 400 fin sur un modèle sans FL AVANT la dépense, garde de coût, plafond
      « chapitres ») ; durée bornée par le modèle ; 9:16, sans voix off ; `shot.video` = le job, écrit AVANT la fin du
      rendu, sérialisé par la liste des plans. La couture la plus basse (FalSeedanceClient._soumettre) reçoit l'image
      de fin sous son vrai nom pour Veo FL (`last_frame_url`) ;
  [A] l'animatique : `plan()` (PUR) prend la vidéo résolue d'un plan ; `rendre()` en fait le clip pXXX.mp4 (muet,
      540×960, 30 i/s, coupé OU prolongé à la durée du plan) au lieu de l'image fixe — vérifié au ffprobe sur une vraie
      vidéo testsrc ; la route ne la prend que pour un job TERMINÉ dont le fichier existe.
AUCUN appel réseau réel : fal_client.* comptent, httpx.AsyncClient.post sortant compte, l'envoi et la soumission fal sont
des espions. ffmpeg RÉEL (petite définition). Run (depuis backend/) : & $PY tests/test_chapitres_video.py"""
import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

_tmp = tempfile.mkdtemp(prefix="dzvid189_")
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
from PIL import Image, ImageStat  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
import app.main as _MAIN  # noqa: E402
from app.services import pricing as P, plafonds as PL, catalogue_ia as CI, animatique_service as AN  # noqa: E402
from app.services import fal_service as F  # noqa: E402
from app.services.storage import init_db  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

W = pathlib.Path(_tmp)
IMG = W / "images"
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())

TELEVERSES, SOUMIS = [], []


async def _upload_image(path):
    TELEVERSES.append(pathlib.Path(path).name)
    return f"https://fal.test/up/{pathlib.Path(path).name}"


class _Handle:
    async def iter_events(self, with_logs=True):
        if False:
            yield None

    async def get(self):
        return {}          # aucune vidéo : le job échoue PROPREMENT après la soumission (rien à télécharger)


async def _soumettre(endpoint, arguments):
    SOUMIS.append((endpoint, dict(arguments)))
    return _Handle()

F.FalSeedanceClient.upload_image = staticmethod(_upload_image)
F.FalSeedanceClient._soumettre = staticmethod(_soumettre)


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


async def _req(meth, path, body=None, params=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        if meth == "GET":
            return await c.get("/api" + path, params=params)
        return await c.post("/api" + path, json=body)


def call(meth, path, body=None, params=None):
    return loop.run_until_complete(_req(meth, path, body, params))


def js(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


def sonde(f, *a):
    return subprocess.run(["ffprobe", "-v", "error", *a, str(f)], capture_output=True, text=True).stdout.strip()


def flux(f):
    out = {}
    for ligne in sonde(f, "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0").splitlines():
        t, _, dd = ligne.partition(",")
        try:
            out[t] = float(dd)
        except ValueError:
            out[t] = None
    return out


# ── [V] la route ─────────────────────────────────────────────────────────────
print("[V] POST /shots/{id}/video")
fl = [e["id"] for e in CI.lister("video_fl")]
check("V0 le catalogue video_fl contient Veo 3.1 Fast (fal)", "veo-3.1-fast-fal" in fl, fl)

ch = js(call("POST", "/chapters", {"title": "C", "script_text": "Vane entre.\n\nLa table tombe.\n\nLa pluie."}))
CID = ch.get("id")
shots = js(call("POST", f"/chapters/{CID}/storyboard/decoupe", {"method": "paragraph"})).get("shots", [])
s0, s1, s2 = shots[0]["id"], shots[1]["id"], shots[2]["id"]
s3 = js(call("POST", f"/chapters/{CID}/shots", {"action": ""})).get("id")
for nom, coul in (("k0.png", (200, 40, 40)), ("k1.png", (40, 200, 40)), ("prod1.png", (40, 40, 200)),
                  ("prod3.png", (90, 90, 90))):
    Image.new("RGB", (90, 160), coul).save(IMG / nom)
sql("UPDATE shots SET keyframe_image=?, keyframe_end=?, image=?, duration_s=5.0 WHERE id=?", "k0.png", "k1.png",
    "prod1.png", s0)
sql("UPDATE shots SET image=?, duration_s=3.4 WHERE id=?", "prod1.png", s1)
sql("UPDATE shots SET image=?, action='', source_text='' WHERE id=?", "prod3.png", s3)

r = call("POST", "/shots/inconnu/video", {})
check("V1 plan inconnu -> 404", r.status_code == 404, r.text)
settings.FAL_KEY = ""
PL.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
r = call("POST", f"/shots/{s0}/video", {})
check("V2 sans FAL_KEY : 503 qui nomme la clé, AVANT le plafond", r.status_code == 503 and "FAL_KEY" in r.text,
      f"{r.status_code} {r.text}")
check("V3 sans clé : aucune ligne depenses, rien téléversé ni soumis", depenses() == [] and not TELEVERSES and not SOUMIS)
settings.FAL_KEY = "test-key"
r = call("POST", f"/shots/{s0}/video", {"video_model": "kling-v3-turbo-pro"})
check("V4 une fin sur un modèle SANS first-last : 400 AVANT la dépense", r.status_code == 400 and depenses() == [],
      f"{r.status_code} {r.text}")
r = call("POST", f"/shots/{s2}/video", {})
check("V5 sans aucune image (ni Plateau, ni production, ni croquis) : 400", r.status_code == 400 and "image" in r.text.lower(),
      r.text)
r = call("POST", f"/shots/{s3}/video", {})
check("V6 sans prompt de mouvement ni action : 400", r.status_code == 400, r.text)
sql("UPDATE shots SET sketch_image='absent.png' WHERE id=?", s2)
r = call("POST", f"/shots/{s2}/video", {})
check("V7 image nommée mais fichier absent : 404", r.status_code == 404, r.text)
r = call("POST", f"/shots/{s0}/video", {"video_model": "inconnu-9"})
check("V7b modèle vidéo inconnu : 400 (avant la dépense)", r.status_code == 400 and depenses() == [], r.text)
r = call("POST", f"/shots/{s0}/video", {})
d = js(r).get("detail") if isinstance(js(r), dict) else None
check("V8 plafond « chapitres » bas : 402 dz_plafond, rien soumis",
      r.status_code == 402 and isinstance(d, dict) and d.get("dz_plafond", {}).get("categorie") == "chapitres"
      and not SOUMIS and depenses() == [], f"{r.status_code} {r.text[:300]}")
check("V8b le plan n'a pas reçu de job sur un refus", sql("SELECT video FROM shots WHERE id=?", s0) == [(None,)],
      sql("SELECT video FROM shots WHERE id=?", s0))
PL.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})

r = call("POST", f"/shots/{s0}/video", {})
j = js(r)
jid = j.get("job_id")
check("V9 le tir : 200, job_id rendu, shot.video == job_id", r.status_code == 200 and jid and j.get("video") == jid
      and sql("SELECT video FROM shots WHERE id=?", s0) == [(jid,)], f"{r.status_code} {r.text[:300]}")
check("V10 téléversés : l'image du PLATEAU au début, sa fin ensuite", TELEVERSES == ["k0.png", "k1.png"], TELEVERSES)
check("V11 la soumission va à Veo 3.1 Fast FIRST-LAST, l'image de fin sous `last_frame_url`",
      len(SOUMIS) == 1 and SOUMIS[0][0] == "fal-ai/veo3.1/fast/first-last-frame-to-video"
      and SOUMIS[0][1].get("first_frame_url") == "https://fal.test/up/k0.png"
      and SOUMIS[0][1].get("last_frame_url") == "https://fal.test/up/k1.png", SOUMIS)
check("V12 le prompt est l'ACTION du plan (pas de motion_prompt)", SOUMIS and "Vane entre." in SOUMIS[0][1].get("prompt", ""),
      SOUMIS and SOUMIS[0][1].get("prompt"))
job = sql("SELECT video_model, image_filename, image_filename_end, aspect_ratio, duration_s FROM jobs WHERE id=?", jid)
gen = P.video_gen_seconds("veo-3.1-fast-fal", 5)
check("V13 le job : Veo Fast FL, k0 -> k1, 9:16, durée bornée par le modèle",
      job == [("veo-3.1-fast-fal", "k0.png", "k1.png", "9:16", gen)], f"{job} gen={gen}")
devis = P.estimate({"kind": "campaign", "ops": [P.video_request_op("veo-3.1-fast-fal", gen, "720p")]})["total_usd"]
dep = depenses()
check("V14 UNE ligne depenses « chapitres » et usd rendu == devis", len(dep) == 1 and dep[0][1] == "chapitres"
      and abs(dep[0][3] - devis) < 1e-9 and abs(float(j.get("usd", -1)) - devis) < 1e-9, f"{dep} {j.get('usd')} {devis}")
lst = js(call("GET", f"/chapters/{CID}/shots")).get("shots") or []
check("V15 la liste des plans sérialise `video`", [x.get("video") for x in lst if x["id"] == s0] == [jid]
      and all("video" in x for x in lst), [(x["id"][:6], x.get("video")) for x in lst])

TELEVERSES.clear(); SOUMIS.clear()
sql("UPDATE shots SET motion_prompt=? WHERE id=?", "slow push-in on the falling table", s1)
r = call("POST", f"/shots/{s1}/video", {"max_usd": 50})
j1 = js(r)
check("V16 sans fin : le défaut vidéo de l'app, pas d'image de fin, l'image de PRODUCTION au début",
      r.status_code == 200 and TELEVERSES == ["prod1.png"] and len(SOUMIS) == 1
      and "first_frame_url" not in SOUMIS[0][1] and "last_frame_url" not in SOUMIS[0][1]
      and sql("SELECT video_model, image_filename_end FROM jobs WHERE id=?", j1.get("job_id"))
      == [(F.DEFAULT_VIDEO_MODEL, None)], f"{r.status_code} {r.text[:200]} {SOUMIS}")
check("V17 le motion_prompt du plan prime sur l'action", SOUMIS and "slow push-in on the falling table" in SOUMIS[0][1].get("prompt", ""),
      SOUMIS and SOUMIS[0][1].get("prompt"))
check("V18 le défaut GLOBAL de l'app n'a pas changé", F.DEFAULT_VIDEO_MODEL == "seedance-2.5", F.DEFAULT_VIDEO_MODEL)
r = call("POST", f"/shots/{s1}/video", {"max_usd": 0.01})
check("V19 max_usd sous le devis : 402 de la garde de coût", r.status_code == 402, r.text[:200])
check("V20 aucun appel réseau dans la partie route", RESEAU["n"] == 0, RESEAU)

# ── [A] l'animatique ─────────────────────────────────────────────────────────
print("\n[A] l'animatique préfère la vidéo du plan")
e = AN.plan([{"id": "a", "idx": 0, "action": "x", "duration_s": 2.0, "image": "i.png", "video_fichier": "C:/v/a.mp4"},
             {"id": "b", "idx": 1, "action": "y", "duration_s": 1.0, "video_fichier": "C:/v/b.mp4"},
             {"id": "c", "idx": 2, "action": "z", "duration_s": 1.0}])
check("A1 plan() PUR : la vidéo résolue passe dans l'entrée ; carton faux quand il y a une vidéo",
      [x.get("video") for x in e] == ["C:/v/a.mp4", "C:/v/b.mp4", None] and [x["carton"] for x in e] == [False, False, True], e)

src = W / "src_1s.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=1", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", str(src)], check=True, capture_output=True)
sortie = W / "anim_direct"
entrees = AN.plan([{"id": "a", "idx": 0, "action": "x", "duration_s": 2.0, "video_fichier": str(src)},
                   {"id": "b", "idx": 1, "action": "y", "duration_s": 0.5, "video_fichier": str(src)},
                   {"id": "c", "idx": 2, "action": "z", "duration_s": 1.0}])
AN.rendre(entrees, images=IMG, sortie=sortie)
p0, p1 = sortie / "p000.mp4", sortie / "p001.mp4"
f0, f1 = flux(p0), flux(p1)
check("A2 clip p000 : muet, prolongé à 2,0 s (vidéo de 1 s)", set(f0) == {"video"} and abs((f0["video"] or 0) - 2.0) < 0.05, f0)
check("A3 clip p001 : muet, coupé à 0,5 s", set(f1) == {"video"} and abs((f1["video"] or 0) - 0.5) < 0.05, f1)
check("A4 aucun carton fabriqué pour les plans vidéo (seul le 3e)",
      sorted(x.name for x in sortie.glob("p*.png")) == ["p002.png"], sorted(x.name for x in sortie.glob("p*.png")))
check("A5 cadre de sortie 540×960 à 30 i/s",
      sonde(p0, "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0")
      == "540,960,30/1", sonde(p0, "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0"))
img0 = sortie / "_f0.png"
subprocess.run(["ffmpeg", "-y", "-ss", "0.2", "-i", str(p0), "-frames:v", "1", str(img0)], check=True, capture_output=True)
with Image.open(img0) as im:
    couleurs = len(im.convert("RGB").resize((54, 96)).getcolors(maxcolors=10000) or [])
    moy = ImageStat.Stat(im.convert("RGB")).mean
check("A6 l'image de p000 vient de la VIDÉO (mire colorée), pas du carton sombre",
      couleurs > 20 and max(abs(m - c) for m, c in zip(moy, AN.FOND_CARTON)) > 30, f"{couleurs} {moy}")
fin = sortie / "_fin.png"
subprocess.run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(p0), "-frames:v", "1", str(fin)], check=True, capture_output=True)
with Image.open(fin) as im:
    couleurs_fin = len(im.convert("RGB").resize((54, 96)).getcolors(maxcolors=10000) or [])
check("A7 la fin prolongée GÈLE la dernière image (tpad clone), pas du noir", couleurs_fin > 20, couleurs_fin)
man = AN.lire_manifeste(sortie) or {}
check("A8 le manifeste dit quels plans viennent d'une vidéo", [p.get("video") for p in man.get("plans") or []]
      == [True, True, False] and [p["clip"] for p in man.get("plans") or []] == ["p000.mp4", "p001.mp4", "p002.mp4"], man)

# la route : seul un job TERMINÉ dont le fichier existe compte
fini = W / "outputs" / "final" / "fini.mp4"
fini.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(src, fini)
sql("INSERT INTO jobs (id, status, progress, image_filename, final_video_path, created_at) VALUES (?,?,?,?,?,?)",
    "job-fini", "done", 100, "k0.png", str(fini), "2026-10-12 10:00:00")
sql("INSERT INTO jobs (id, status, progress, image_filename, final_video_path, created_at) VALUES (?,?,?,?,?,?)",
    "job-encours", "generating_video", 30, "k0.png", str(fini), "2026-10-12 10:00:00")
sql("UPDATE shots SET video='job-fini' WHERE id=?", s0)
sql("UPDATE shots SET video='job-encours' WHERE id=?", s1)
r = call("POST", f"/chapters/{CID}/animatique", {})
ja = js(r)
st = {}
for _ in range(240):
    st = js(call("GET", f"/atelier/manuscript/{ja.get('job_id')}"))
    if st.get("done"):
        break
    time.sleep(0.25)
check("A9 l'animatique du chapitre est montée", r.status_code == 200 and st.get("done") and not st.get("error"),
      f"{r.status_code} {st}")
man = AN.lire_manifeste(W / "outputs" / "animatique" / CID) or {}
check("A10 la route prend la vidéo du job TERMINÉ (plan 1), ignore un job EN COURS (plan 2)",
      [p.get("video") for p in man.get("plans") or []][:2] == [True, False], man.get("plans"))
d0 = flux(W / "outputs" / "animatique" / CID / "p000.mp4")
check("A11 le clip p000 du chapitre dure la durée du plan (5 s), muet", set(d0) == {"video"}
      and abs((d0["video"] or 0) - 5.0) < 0.05, d0)

check("A12 aucun appel réseau dans tout le banc", RESEAU["n"] == 0, RESEAU)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
