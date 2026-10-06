# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T9, D2a) — le matte vidéo par BiRefNet v2 : registre relu le 06/10/2026 sur l'openapi
« queue » de fal (`fal-ai/birefnet/v2/video` : `video_output_type` « PRORES4444 (.mov) », six modèles, sortie
`video`), arguments FIGÉS, travail suivi en mémoire, fichier .mov AVEC alpha écrit sous outputs/mattes, noms
confinés, prix « à mesurer » (fal n'affiche que « $0 per compute second ») qui suit le travail jusqu'à l'écran. Les
routes : POST /matte passe par la garde des plafonds AVANT tout appel fal (402 sans dépense), GET /matte/{id}, GET
/matte/file/{name} (déclarée avant), refus nommés. Seams fal stubbés : aucun tir réel.
Run: python tests/test_matte_service.py (depuis backend/)"""
import asyncio, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzmatte_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = "test-key"
os.environ["ELEVENLABS_API_KEY"] = ""
os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable"); sys.exit(0)
from loguru import logger
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
from app.config import settings
from app.services import matte_service as MT, pricing as P
w = pathlib.Path(_tmp)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
                "-pix_fmt", "yuv420p", str(w / "clip.mp4")], check=True)
fake_mov = w / "fake.mov"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red@0.5:size=64x64:rate=10:duration=1",
                "-vf", "format=yuva444p10le", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                str(fake_mov)], check=True)
CALLS, UPS = [], []
async def _up(p): UPS.append(pathlib.Path(p).name); return "http://fal.test/clip.mp4"
async def _sub(endpoint, arguments): CALLS.append((endpoint, arguments)); return {"video": {"url": "http://fal.test/m.mov"}}
async def _dl(url, dest): shutil.copy2(fake_mov, dest)
MT._upload, MT._fal_subscribe, MT._download = _up, _sub, _dl

print("\n[1] registre")
check("trois modèles, libellés fal EXACTS (enum de l'openapi)",
      {k: v["fal"] for k, v in MT.MATTE_MODELS.items()} == {"general": "General Use (Light)", "matting": "Matting",
                                                              "portrait": "Portrait"}, str(MT.MATTE_MODELS))
check("arguments figés : ProRes 4444, refine, 1024, qualité haute",
      MT.ARGS_FIXED == {"video_output_type": "PRORES4444 (.mov)", "refine_foreground": True,
                        "operating_resolution": "1024x1024", "video_quality": "high"}, str(MT.ARGS_FIXED))
e = P.estimate({"kind": "matte", "duration_s": 12})
check("devis : 0 $ connu, et la ligne DIT que le prix est à mesurer",
      e["total_usd"] == 0.0 and any("mesurer" in l["label"] for l in e["breakdown"]), str(e))

print("\n[2] un détourage")
loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
async def lance_et_attend(*a, **k):
    mid = MT.detourer(*a, **k)
    for _ in range(100):
        st = MT.status(mid)
        if st["status"] in ("done", "failed"):
            return mid, st
        await asyncio.sleep(0.02)
    return mid, MT.status(mid)
mid, st = loop.run_until_complete(lance_et_attend(w / "clip.mp4", "matting", label="mon clip!"))
check("travail terminé", st["status"] == "done", str(st))
check("fal reçoit l'endpoint et les arguments figés + le modèle choisi + l'URL téléversée",
      CALLS == [("fal-ai/birefnet/v2/video", dict(MT.ARGS_FIXED, video_url="http://fal.test/clip.mp4", model="Matting"))]
      and UPS == ["clip.mp4"], str(CALLS))
p = MT.matte_path(st["file"])
check("fichier .mov sous outputs/mattes, nom assaini", p.is_file() and p.parent == MT.mattes_dir().resolve()
      and st["file"].startswith("mon_clip_") and st["file"].endswith(".mov"), st["file"])
pix = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=pix_fmt", "-of",
                      "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip()
check("alpha présent (yuva444p…, la profondeur dépend de l'encodeur)", pix.startswith("yuva444p"), pix)
check("statut : note de prix « à mesurer », url de fichier", "mesurer" in st["usd_note"] and st["url"] == f"/api/matte/file/{st['file']}")

async def _sub_vide(endpoint, arguments): return {"autre": 1}
MT._fal_subscribe = _sub_vide
_, st2 = loop.run_until_complete(lance_et_attend(w / "clip.mp4", "general"))
check("réponse fal sans vidéo : échec NOMMÉ, pas d'exception qui fuit", st2["status"] == "failed" and "aucune vidéo" in st2["error"], str(st2))
MT._fal_subscribe = _sub

print("\n[3] refus")
for bad in ("../x.mov", "C:/Windows/win.ini", "x.mp4", "a b.mov", ""):
    try: MT.matte_path(bad); check(f"nom refusé : {bad!r}", False)
    except ValueError: check(f"nom refusé : {bad!r}", True)
check("travail inconnu : statut unknown", MT.status("zzz")["status"] == "unknown")
for label, args, mot in (("modèle inconnu", (w / "clip.mp4", "heavy"), "inconnu"),
                         ("source absente", (w / "nope.mp4", "general"), "introuvable")):
    try: MT.detourer(*args); check(label + " refusé", False)
    except ValueError as e: check(f"{label} : ValueError nommée", mot in str(e), str(e))
settings.FAL_KEY = ""
try: MT.detourer(w / "clip.mp4", "general"); check("sans clé : refus", False)
except ValueError as e: check("sans clé : refus nommant fal", "fal" in str(e), str(e))
settings.FAL_KEY = "test-key"

print("\n[4] routes")
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api import routes as R
from app.services.storage import init_db, async_session_factory, JobRecord
loop.run_until_complete(init_db())
OPS = []
async def main():
    async with async_session_factory() as s:
        s.add(JobRecord(id="job-m1", status="done", progress=100, image_filename="x", final_video_path=str(w / "clip.mp4")))
        await s.commit()
    vrai = R._plafond
    async def _plaf_refus(op, cat, ref=None):
        OPS.append(op); raise HTTPException(402, "plafond")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        R._plafond = _plaf_refus
        CALLS.clear()
        r = await c.post("/api/matte", json={"job_id": "job-m1", "model": "matting"})
        check("402 du plafond : AUCUN appel fal, op matte avec la durée de la source",
              r.status_code == 402 and CALLS == [] and OPS and OPS[-1]["kind"] == "matte"
              and abs(OPS[-1]["duration_s"] - 1.0) < 0.2, str(OPS))
        R._plafond = vrai
        r = await c.post("/api/matte", json={"job_id": "job-m1", "model": "matting"})
        d = r.json()
        check("POST /matte : matte_id + note de prix", r.status_code == 200 and d["matte_id"] and "mesurer" in d["usd_note"], r.text[:200])
        for _ in range(100):
            st = (await c.get(f"/api/matte/{d['matte_id']}")).json()
            if st.get("status") in ("done", "failed"): break
            await asyncio.sleep(0.02)
        check("GET /matte/{id} : terminé", st["status"] == "done", str(st))
        rf = await c.get(st["url"])
        check("GET /matte/file/{name} : le .mov servi", rf.status_code == 200 and rf.headers["content-type"].startswith("video/quicktime"),
              str(rf.status_code))
        check("matte inconnu : 404", (await c.get("/api/matte/zzz")).status_code == 404)
        mm = (await c.get("/api/matte-models")).json()
        check("GET /matte-models : le registre servi (ids + libellés), défaut general, note de prix",
              [m["id"] for m in mm["models"]] == list(MT.MATTE_MODELS) and mm["default"] == "general"
              and all(m["label"] == MT.MATTE_MODELS[m["id"]]["label"] for m in mm["models"]) and "mesurer" in mm["usd_note"], str(mm))
        check("nom hors règle (pas un .mov simple) : 404", (await c.get("/api/matte/file/t.db")).status_code == 404)
        (pathlib.Path(settings.outputs_path) / "secret.mov").write_bytes(b"pas un matte")
        rb = await c.get("/api/matte/file/..%5Csecret.mov")   # %5C ATTEINT la route (Windows : « ..\ » remonte)
        check("traversée par antislash : 404, le fichier voisin n'est pas servi",
              rb.status_code == 404 and rb.content != b"pas un matte", str(rb.status_code))
        rh = await c.get("/api/matte/file/..%2Ft.db")   # %2F : décodé AVANT le routage -> catch-all de la SPA
        check("traversée : jamais un fichier servi comme matte", not rh.headers.get("content-type", "").startswith("video/"),
              rh.headers.get("content-type"))
        check("job inconnu : 404", (await c.post("/api/matte", json={"job_id": "nope"})).status_code == 404)
        check("modèle inconnu : 400", (await c.post("/api/matte", json={"job_id": "job-m1", "model": "x"})).status_code == 400)
loop.run_until_complete(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
