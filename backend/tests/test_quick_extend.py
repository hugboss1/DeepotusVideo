# -*- coding: utf-8 -*-
"""Plan Quick T2 (tache #51 du suivi, 01/10/2026) — « Prolonger le clip » (Veo 3.1 sur fal).

Les gardes portent sur de VRAIS fichiers (mp4 ecrits par ffmpeg, mesures par ffprobe) et le refus CITE la mesure.
Les prix sont ceux releves sur fal.ai le 01/10 (Fast 0,15/0,10 $/s, standard 0,40/0,20 $/s, +7 s). AUCUN appel fal :
upload, subscribe et telechargement sont des espions. La route payante passe la garde des plafonds AVANT tout appel
(402 sans upload), puis, confirmee, le pipeline cree le job fils (lignee parent_job_id), telecharge, ecrit la recette.
Temoin positif : la base (5e25417) n'a ni fal_video_tools ni /generate/extend.
Run (depuis backend/) : & $PY tests/test_quick_extend.py"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzqext_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from app.services import fal_video_tools as FV, pricing             # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _mp4(nom, secs, w, h):
    p = _tmp / nom
    exe = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    subprocess.run([exe, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=24:duration={secs}",
                    "-pix_fmt", "yuv420p", str(p)], check=True, timeout=180)
    return p


def _refus(model, src):
    try:
        FV.guard_extend(model, src); return ""
    except ValueError as e:
        return str(e)


r0 = subprocess.run(["git", "show", "5e25417:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas de /generate/extend", r0.returncode == 0 and b"/generate/extend" not in r0.stdout)

print("\n[A] gardes mesurees par ffprobe")
F = FV.DEFAULT_EXTEND
long_ = FV.probe(_mp4("long.mp4", 25, 720, 1280))
check("A1 ffprobe mesure 25 s en 9:16", 24.5 < long_["duration_s"] < 25.5 and long_["ratio"] == "9:16", str(long_))
m = _refus(F, long_)
check("A2 25 s refuse : la mesure (25.0 s) et la sortie de secours (Montage) sont dans le refus", "25.0 s" in m and "Montage" in m, m)
court = FV.probe(_mp4("court.mp4", 5, 720, 1280))
check("A3 5 s en 720x1280 : accepte", _refus(F, court) == "")
check("A4 5 s en 1920x1080 : accepte", _refus(F, FV.probe(_mp4("large.mp4", 5, 1920, 1080))) == "")
m = _refus(F, FV.probe(_mp4("carre.mp4", 5, 512, 512)))
check("A5 carre refuse en citant les pixels et le format", "512x512" in m and "1:1" in m, m)
m = _refus(F, FV.probe(_mp4("petit.mp4", 5, 640, 360)))
check("A6 16:9 en 360p refuse (720p ou 1080p seulement)", "720p" in m and "640x360" in m, m)
check("A7 un modele inconnu est refuse en nommant les disponibles", "veo-3.1-fast-extend" in _refus("pirate", court))
check("A8 duree illisible : refus", "illisible" in _refus(F, {"duration_s": 0, "width": 720, "height": 1280, "ratio": "9:16"}))
try:
    FV.probe(_tmp / "absent.mp4"); m = ""
except ValueError as e:
    m = str(e)
check("A9 fichier absent : refus lisible", "introuvable" in m, m)

print("\n[B] prix mesures et arguments fal")
check("B1 Fast : 1,05 $ avec son, 0,70 $ sans ; standard : 2,80 $ / 1,40 $", (FV.prix(F, True), FV.prix(F, False),
      FV.prix("veo-3.1-extend", True), FV.prix("veo-3.1-extend", False)) == (1.05, 0.7, 2.8, 1.4))
est = lambda **o: pricing.estimate(dict({"kind": "extend", "duration_s": 7}, **o))["total_usd"]
check("B2 pricing.estimate rend les memes montants", (est(model=F, son=True), est(model=F, son=False),
      est(model="veo-3.1-extend", son=True)) == (1.05, 0.7, 2.8), str((est(model=F, son=True), est(model=F, son=False))))
ep, args = FV.build_extend_args(F, video_url="https://x/y.mp4", prompt="  plus loin  ", son=False)
check("B3 endpoint Fast, champs du contrat (video_url, prompt nettoye, generate_audio)",
      ep == "fal-ai/veo3.1/fast/extend-video" and args == {"video_url": "https://x/y.mp4", "prompt": "plus loin", "generate_audio": False}, str(args))
try:
    FV.build_extend_args(F, video_url="u", prompt="   "); m = ""
except ValueError as e:
    m = str(e)
check("B4 prompt vide refuse (fal l'exige)", "prompt" in m, m)

print("\n[C] routes : mesure gratuite, tir garde par les plafonds, pipeline sans reseau")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.api.routes import pipeline                                 # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import plafonds as P, quick_recipe as QR          # noqa: E402
from app.services.fal_service import FalSeedanceClient              # noqa: E402
from app.services.storage import JobRecord, async_session_factory, init_db  # noqa: E402
import app.services.pipeline as PL                                 # noqa: E402

appels = []
async def _upload(path):
    appels.append(("upload", path)); return "https://fal.test/source.mp4"
async def _subscribe(endpoint, arguments=None, with_logs=False):
    appels.append(("subscribe", endpoint, arguments)); return {"video": {"url": "https://fal.test/out.mp4"}}
async def _download(url, dest):
    appels.append(("download", url)); pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(court_p, dest); return pathlib.Path(dest)
PL.fal_client.upload_file_async = _upload
PL.fal_client.subscribe_async = _subscribe
FalSeedanceClient.download_video = staticmethod(_download)
court_p = _tmp / "court.mp4"


async def _jobs():
    await init_db()
    from datetime import datetime
    async with async_session_factory() as s:
        for jid, f in (("parent-ok", court_p), ("parent-long", _tmp / "long.mp4")):
            s.add(JobRecord(id=jid, status="done", image_filename="a.png", provider="seedance", final_video_path=str(f),
                            video_model="veo-3.1-fast-fal", title="Parent", created_at=datetime.utcnow()))
        await s.commit()
asyncio.run(_jobs())


def _job(jid):
    async def f():
        async with async_session_factory() as s:
            return await s.get(JobRecord, jid)
    return asyncio.run(f())


def _fils():
    from sqlalchemy import select
    async def f():
        async with async_session_factory() as s:
            return (await s.execute(select(JobRecord).where(JobRecord.parent_job_id == "parent-ok"))).scalars().all()
    return asyncio.run(f())


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    j = c.get("/api/generate/extend/check?job_id=parent-ok").json()
    check("C1 check : verdict ok, mesure, les deux prix, source Veo reconnue", j.get("ok") is True and j["usd_son"] == 1.05
          and j["usd_muet"] == 0.7 and j["source"]["ratio"] == "9:16" and j["veo_source"] is True and j["added_s"] == 7, str(j)[:300])
    j = c.get("/api/generate/extend/check?job_id=parent-long").json()
    check("C2 check : 25 s, verdict refuse AVEC la raison", j.get("ok") is False and "25.0 s" in j.get("reason", ""), str(j)[:200])
    check("C3 check : rendu inconnu 404, modele inconnu 400", c.get("/api/generate/extend/check?job_id=nope").status_code == 404
          and c.get("/api/generate/extend/check?job_id=parent-ok&model=x").status_code == 400)
    check("C4 la mesure n'appelle pas fal", appels == [])
    r = c.post("/api/generate/extend", json={"parent_job_id": "parent-long", "prompt": "plus loin"})
    check("C5 tir sur une source refusee : 400 avec la raison, aucun appel", r.status_code == 400 and "25.0 s" in r.text and appels == [], r.text[:200])
    check("C6 prompt vide : 422", c.post("/api/generate/extend", json={"parent_job_id": "parent-ok", "prompt": ""}).status_code == 422)
    P.enregistrer({"global_usd": 0.01, "par_moteur": {}, "alerte_pct": 80})
    r = c.post("/api/generate/extend", json={"parent_job_id": "parent-ok", "prompt": "plus loin", "son": True})
    d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else {}
    dp = (d or {}).get("dz_plafond") or {} if isinstance(d, dict) else {}
    check("C7 au-dessus du plafond : 402, devis = 1,05 $ (son), AUCUN appel fal", r.status_code == 402 and abs(dp.get("devis_usd", 0) - 1.05) < 1e-9
          and appels == [], f"{r.status_code} {dp}")
    r = c.post("/api/generate/extend", json={"parent_job_id": "parent-ok", "prompt": "plus loin", "son": False})
    d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else {}
    dp = (d or {}).get("dz_plafond") or {} if isinstance(d, dict) else {}
    check("C7b sans son : le devis de la garde est 0,70 $", r.status_code == 402 and abs(dp.get("devis_usd", 0) - 0.70) < 1e-9
          and appels == [], f"{r.status_code} {dp}")
    r = c.post("/api/generate/extend", json={"parent_job_id": "parent-ok", "prompt": "plus loin", "son": False,
                                             "quick_recipe": {"v": 1, "tab": "seedance"}}, headers={"X-DZ-Plafond": "confirme"})
    fils = _fils()
    f0 = fils[0] if fils else None
    check("C8 confirme (sans son) : 200, upload puis subscribe Fast avec generate_audio=false, puis telechargement",
          r.status_code == 200 and [a[0] for a in appels] == ["upload", "subscribe", "download"]
          and appels[1][1] == "fal-ai/veo3.1/fast/extend-video" and appels[1][2] == {"video_url": "https://fal.test/source.mp4",
          "prompt": "plus loin", "generate_audio": False}, f"{r.status_code} {appels}")
    check("C9 le job fils : lignee, fournisseur extend, termine, fichier present, duree source + 7 s",
          f0 is not None and f0.provider == "extend" and f0.status == "done" and f0.parent_job_id == "parent-ok"
          and pathlib.Path(f0.final_video_path or "").is_file() and f0.duration_s == 12, str(f0 and (f0.provider, f0.status, f0.duration_s)))
    check("C10 la recette du fils est ecrite", f0 is not None and QR.load(f0.id) == {"v": 1, "tab": "seedance"})
    P.enregistrer({"global_usd": 0, "par_moteur": {}})
    sauve = settings.FAL_KEY
    settings.FAL_KEY = ""
    check("C11 sans cle fal : 503 (regle maison P1 #11)", c.post("/api/generate/extend", json={"parent_job_id": "parent-ok", "prompt": "x"}).status_code == 503)
    settings.FAL_KEY = sauve

print("\n[D] le pipeline rejoue les gardes (appel direct)")
from app.models.schemas import ExtendRequest                        # noqa: E402
n0 = len(appels)
try:
    asyncio.run(pipeline.run_extend(ExtendRequest(parent_job_id="parent-long", prompt="x"))); m = ""
except ValueError as e:
    m = str(e)
check("D1 run_extend sur une source trop longue : refus, aucun appel", "25.0 s" in m and len(appels) == n0, m)

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
