# -*- coding: utf-8 -*-
"""Plan Quick T5 (tache #52 du suivi, 01/10/2026) — lip-sync Kling sur la voix off, dans Quick (Seedance).

Contrat et prix MESURES le 01/10 (OpenAPI fal + fal.ai) : video 2–10 s, 720–1920 px ; audio 2–60 s, <= 5 Mo ;
0,014 $/s de VIDEO au palier de 5 s. Les gardes portent sur de VRAIS fichiers (ffmpeg / ffprobe) et citent la
mesure ; la route /generate PRE-VERIFIE avant le rendu paye et chiffre le lip-sync dans la garde des plafonds ; un rendu
Seedance COMPLET tourne avec fal espionne (aucun reseau) : le clip lip-synche remplace le natif et garde sa voix.
Temoin positif : la base (fe6df997) n'a pas de LIPSYNC_MODELS.
Run (depuis backend/) : & $PY tests/test_quick_lipsync.py"""
import asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzqlip_"))
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


def _exe(n):
    return shutil.which(n) or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{n}.exe")


def _v(nom, secs, w=720, h=1280, son=False):
    p = _tmp / nom
    cmd = [_exe("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=24:duration={secs}"]
    if son:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=330:duration={secs}", "-shortest"]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", str(p)], check=True, timeout=180)
    return p


def _a(nom, secs, lourd=False):
    p = _tmp / nom
    extra = ["-ac", "2", "-ar", "48000", "-c:a", "pcm_f32le"] if lourd else []
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=220:duration={secs}"] + extra
                   + [str(p)], check=True, timeout=180)
    return p


def _refus(*a):
    try:
        FV.guard_lipsync(*a); return ""
    except ValueError as e:
        return str(e)


K = FV.DEFAULT_LIPSYNC
r0 = subprocess.run(["git", "show", "fe6df997:backend/app/services/fal_video_tools.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas de LIPSYNC_MODELS", r0.returncode == 0 and b"LIPSYNC_MODELS" not in r0.stdout)

print("\n[A] gardes sur de vrais fichiers")
a5 = FV.probe(_a("a5.mp3", 5))
m = _refus(K, FV.probe(_v("v12.mp4", 12)), a5)
check("A1 clip de 12 s refuse : la mesure et la borne citees", "12.0 s" in m and "2 et 10 s" in m, m)
v6 = FV.probe(_v("v6.mp4", 6))
m = _refus(K, v6, FV.probe(_a("a1.mp3", 1)))
check("A2 voix de 1 s refusee en citant 1.0 s et la borne", "1.0 s" in m and "2 et 60 s" in m, m)
m = _refus(K, v6, FV.probe(_a("a70.mp3", 70)))
check("A3 voix de 70 s refusee", "70.0 s" in m, m)
check("A4 paire valide (6 s en 720x1280, voix de 5 s) acceptee", _refus(K, v6, a5) == "")
m = _refus(K, FV.probe(_v("v540.mp4", 6, 540, 960)), a5)
check("A5 540x960 refuse (720 a 1920 px)", "540x960" in m and "720" in m, m)
lourd = _a("lourd.wav", 15, lourd=True)
m = _refus(K, v6, FV.probe(lourd), lourd.stat().st_size)
check("A6 voix de plus de 5 Mo refusee en citant son poids", "5 Mo" in m and "Mo." in m and lourd.stat().st_size > 5 * 1024 * 1024, m)
check("A7 modele inconnu refuse", "kling-lipsync" in _refus("pirate", v6, a5))
ep, args = FV.build_lipsync_args(K, video_url="https://x/v.mp4", audio_url="https://x/a.mp3")
check("A8 endpoint et champs du contrat mesure", ep == "fal-ai/kling-video/lipsync/audio-to-video"
      and args == {"video_url": "https://x/v.mp4", "audio_url": "https://x/a.mp3"}, str(args))

print("\n[B] prix au palier de 5 s (video d'entree)")
check("B1 3 s -> 0,07 $ ; 5 s -> 0,07 $ ; 6 s -> 0,14 $ ; 10 s -> 0,14 $", [FV.prix_lipsync(K, s) for s in (3, 5, 6, 10)] == [0.07, 0.07, 0.14, 0.14])
est = lambda s: pricing.estimate({"kind": "lipsync", "model": K, "duration_s": s})["total_usd"]
check("B2 pricing.estimate rend les memes montants", [est(s) for s in (3, 5, 6, 10)] == [0.07, 0.07, 0.14, 0.14],
      str([est(s) for s in (3, 5, 6, 10)]))

print("\n[C] la route /generate pre-verifie et chiffre AVANT le rendu")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import plafonds as P                              # noqa: E402
(settings.images_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nstub")
audio_dir = settings.images_path.parent / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(_tmp / "a5.mp3", audio_dir / "voix.mp3")
shutil.copy2(_tmp / "a1.mp3", audio_dir / "courte.mp3")
SEED = {"image_filename": "a.png", "custom_prompt": "abysse", "video_model": "kling-v3-pro", "duration_s": 5}
LIP = {"on": True, "model": K, "file": "voix.mp3"}


def devis(c, corps):
    r = c.post("/api/generate", json=corps)
    d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else None
    return r.status_code, (((d or {}).get("dz_plafond") or {}).get("devis_usd", 0) if isinstance(d, dict) else 0), r.text


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    P.enregistrer({"global_usd": 0.000001, "par_moteur": {}, "alerte_pct": 80})
    s0, d0, _ = devis(c, SEED)
    s1, d1, _ = devis(c, dict(SEED, lipsync=LIP))
    check("C1 le lip-sync demande ajoute son prix au devis (5 s -> +0,07 $)", s0 == s1 == 402 and abs((d1 - d0) - 0.07) < 1e-6, f"{d0} {d1}")
    s, _, t = devis(c, dict(SEED, lipsync=dict(LIP, on=False)))
    check("C2 case decochee : aucun surcout", s == 402 and abs(devis(c, dict(SEED, lipsync=dict(LIP, on=False)))[1] - d0) < 1e-9)
    s, _, t = devis(c, dict(SEED, lipsync=dict(LIP, file="absente.mp3")))
    check("C3 voix off introuvable : 400 AVANT tout rendu", s == 400 and "voix off" in t, t[:200])
    s, _, t = devis(c, dict(SEED, lipsync=dict(LIP, file="courte.mp3")))
    check("C4 voix de 1 s : 400 avec la mesure", s == 400 and "1.0 s" in t, t[:200])
    s, _, t = devis(c, dict(SEED, duration_s=20, lipsync=LIP))
    check("C5 duree demandee au-dela du clip natif : 400 (la boucle repeterait la parole)", s == 400 and "dépasse le clip natif" in t, t[:200])
    P.enregistrer({"global_usd": 0, "par_moteur": {}})

print("\n[D] un rendu Seedance complet, fal espionne")
from app.api.routes import pipeline                                 # noqa: E402
import app.services.pipeline as PL                                  # noqa: E402
from app.services import fal_service                                # noqa: E402
from app.services.storage import JobRecord, async_session_factory   # noqa: E402
natif = _v("natif.mp4", 5)
lipsync_out = _v("lip.mp4", 5, son=True)
appels = []
async def _upimg(*a, **k):
    return "https://fal.test/img.png"
async def _gen(**k):
    appels.append(("generate", k.get("duration"))); return {"video": {"url": "https://fal.test/natif.mp4"}}
async def _dl(url, dest):
    appels.append(("download", url)); pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(lipsync_out if "lip" in url else natif, dest); return pathlib.Path(dest)
async def _upf(path):
    appels.append(("upload", pathlib.Path(path).name)); return "https://fal.test/" + pathlib.Path(path).name
async def _sub(endpoint, arguments=None, with_logs=False):
    appels.append(("subscribe", endpoint, arguments)); return {"video": {"url": "https://fal.test/lip-out.mp4"}}
fal_service.FalSeedanceClient.upload_image = staticmethod(_upimg)
pipeline.fal.generate_video = _gen
fal_service.FalSeedanceClient.download_video = staticmethod(_dl)
PL.fal_client.upload_file_async = _upf
PL.fal_client.subscribe_async = _sub
from app.models.schemas import GenerateRequest                      # noqa: E402
jid = asyncio.run(pipeline.run(GenerateRequest(**dict(SEED, lipsync=LIP))))
async def _job():
    async with async_session_factory() as s:
        return await s.get(JobRecord, jid)
j = asyncio.run(_job())
sub = [a for a in appels if a[0] == "subscribe"]
check("D1 le rendu se termine ; le lip-sync est appele UNE fois, sur le clip natif et la voix choisie",
      j is not None and j.status == "done" and len(sub) == 1 and sub[0][1] == "fal-ai/kling-video/lipsync/audio-to-video"
      and sub[0][2] == {"video_url": f"https://fal.test/{jid}.mp4", "audio_url": "https://fal.test/voix.mp3"},
      f"{j and j.status} {appels}")
ordre = [a[0] for a in appels]
check("D2 ordre : generation, telechargement natif, uploads, lip-sync, telechargement du lip-synche",
      ordre == ["generate", "download", "upload", "upload", "subscribe", "download"], str(ordre))
pr = subprocess.run([_exe("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", j.final_video_path],
                    capture_output=True, timeout=60)
types = [s.get("codec_type") for s in json.loads(pr.stdout or b"{}").get("streams", [])]
check("D3 le rendu final est le clip lip-synche : il porte la piste son (la voix)", "audio" in types and "video" in types, str(types))

def _niveau(fichier, freq):
    """Volume moyen (dB) de la bande autour de `freq` dans la piste son : la voix (330 Hz) contre la musique (880 Hz)."""
    r = subprocess.run([_exe("ffmpeg"), "-v", "info", "-i", str(fichier), "-af",
                        f"bandpass=f={freq}:width_type=h:w=60,volumedetect", "-f", "null", "-"],
                       capture_output=True, timeout=120)
    t = r.stderr.decode("utf-8", "replace")
    i = t.find("mean_volume:")
    return float(t[i + 12:t.find(" dB", i)]) if i >= 0 else -999.0


subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=880:duration=8",
                str(audio_dir / "musique.mp3")], check=True, timeout=120)
appels.clear()
jid2 = asyncio.run(pipeline.run(GenerateRequest(**dict(SEED, lipsync=LIP, music={"file": "musique.mp3", "volume_db": -6}))))
async def _job2():
    async with async_session_factory() as s:
        return await s.get(JobRecord, jid2)
j2 = asyncio.run(_job2())
voix, mus = _niveau(j2.final_video_path, 330), _niveau(j2.final_video_path, 880)
check("D4 avec une musique : la voix lip-synchee (330 Hz) reste DANS le rendu, la musique (880 Hz) s'y ajoute",
      j2.status == "done" and voix > -35 and mus > -45, f"voix {voix} dB, musique {mus} dB")
print(f"      (mesure : voix {voix} dB, musique {mus} dB ; sans la voix, la bande 330 Hz tombe sous -49 dB)")

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
