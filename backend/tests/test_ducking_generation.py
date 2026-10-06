# -*- coding: utf-8 -*-
"""T102 (plan-son-vfx T8, D1) — le ducking existe hors du Montage : FFmpegMerger.merge (Quick) et POST /audio/duck
(Son & VFX). Preuve par MESURE (volumedetect sur la bande de la musique seule) : le niveau de la musique PENDANT la
voix est plus bas qu'APRÈS ; sans ducking, égal. Le mix rejoint la Bibliothèque (sidecar kind mix + parents, index
source sonvfx, mère = la voix, relation mix) ; gratuit, aucune garde de plafond.
Run: python tests/test_ducking_generation.py (depuis backend/)"""
import asyncio, os, pathlib, re, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzduck_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["FAL_KEY"] = ""
os.environ["ELEVENLABS_API_KEY"] = ""
os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable"); sys.exit(0)
from loguru import logger
logger.remove()
from app.config import settings
from app.services.ffmpeg_service import FFmpegMerger
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def ff(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
def mean_db(p, ss, t):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(ss), "-t", str(t), "-i", str(p), "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.search(r"mean_volume:\s*(-?[\d.]+) dB", err).group(1))
def bande_musique(src, dst):
    # la musique est à 110 Hz, la voix à 1000 Hz : un passe-bande serré ne garde que la musique
    ff("-i", str(src), "-vn", "-af", "highpass=f=80,lowpass=f=150,highpass=f=80,lowpass=f=150", str(dst))

w = pathlib.Path(_tmp)
ff("-f", "lavfi", "-i", "testsrc=duration=6:size=160x120:rate=15", "-pix_fmt", "yuv420p", str(w / "v.mp4"))
# voix : 0-2 s, a un niveau de VOIX OFF (crete ~ -9 dBFS). Le sine nu de lavfi est a 1/8 de pleine echelle
# (-18 dBFS), a peine au-dessus du seuil 0,05 du compresseur : mesure, il ne baissait la musique que de 3 dB,
# ce qui ne dit rien d une vraie voix (ElevenLabs sort autour de -16 LUFS).
ff("-f", "lavfi", "-i", "sine=frequency=1000:duration=2", "-af", "volume=3", "-c:a", "libmp3lame", str(w / "vo.mp3"))
ff("-f", "lavfi", "-i", "sine=frequency=110:duration=6", "-c:a", "libmp3lame", str(w / "bgm.mp3"))

print("\n[1] la Quick (FFmpegMerger.merge)")
out = FFmpegMerger.merge(w / "v.mp4", w / "vo.mp3", w / "duck.mp4", music_path=w / "bgm.mp3",
                         music_volume_db=-6, ducking=True)
bande_musique(out, w / "bgm_only.wav")
during, after = mean_db(w / "bgm_only.wav", 0.5, 1.0), mean_db(w / "bgm_only.wav", 3.5, 1.0)
check("MESURÉ : musique ≥ 4 dB plus basse SOUS la voix qu'après", after - during >= 4.0,
      f"pendant {during} dB, après {after} dB")
out2 = FFmpegMerger.merge(w / "v.mp4", w / "vo.mp3", w / "flat.mp4", music_path=w / "bgm.mp3",
                          music_volume_db=-6, ducking=False)
bande_musique(out2, w / "flat_only.wav")
d2, a2 = mean_db(w / "flat_only.wav", 0.5, 1.0), mean_db(w / "flat_only.wav", 3.5, 1.0)
check("sans ducking : écart < 1 dB", abs(a2 - d2) < 1.0, f"{d2} / {a2}")
out3 = FFmpegMerger.merge(w / "v.mp4", w / "vo.mp3", w / "def.mp4", music_path=w / "bgm.mp3", music_volume_db=-6)
bande_musique(out3, w / "def_only.wav")
check("le ducking est le DÉFAUT de la Quick", mean_db(w / "def_only.wav", 3.5, 1.0) - mean_db(w / "def_only.wav", 0.5, 1.0) >= 4.0)
vo_seule = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
                           "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
check("la vidéo reste copiée (h264 de testsrc)", vo_seule == "h264", vo_seule)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True).stdout or 0)
check("la sortie dure la vidéo (6 s)", abs(dur - 6.0) < 0.3, str(dur))

print("\n[2] POST /audio/duck")
from app.services import sfx_service as S
from app.services.storage import init_db, LibraryAsset, async_session_factory
asyncio.run(init_db())
audio = S._audio_dir()
shutil.copy2(w / "vo.mp3", audio / "vo.mp3"); shutil.copy2(w / "bgm.mp3", audio / "bgm.mp3")
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api import routes as R
OPS = []
async def _plaf(op, cat, ref=None):
    OPS.append(op); return {}
R._plafond = _plaf
async def main():
    from sqlalchemy import select
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        r = await c.post("/api/audio/duck", json={"voice": "vo.mp3", "music": "bgm.mp3", "music_db": -6,
                                                  "ducking": {"ratio": 8}})
        d = r.json()
        check("/audio/duck écrit mix_<voix>_<musique>.mp3 en Bibliothèque",
              r.status_code == 200 and d["filename"] == "mix_vo_bgm.mp3" and (audio / d["filename"]).is_file()
              and d["usd"] == 0.0, r.text[:200])
        dmix = S._probe_duration(audio / d["filename"])
        check("durée = celle de la voix (2 s), pas de la musique", abs(dmix - 2.0) < 0.3, str(dmix))
        meta = S.load_meta().get(d["filename"]) or {}
        check("sidecar : kind mix + parents + niveau", meta.get("kind") == "mix"
              and meta.get("parents") == ["vo.mp3", "bgm.mp3"] and meta.get("music_db") == -6.0, str(meta))
        async with async_session_factory() as s:
            row = (await s.execute(select(LibraryAsset).where(LibraryAsset.filename == d["filename"]))).scalar_one_or_none()
        check("index : source sonvfx, mère = la voix, relation mix",
              row is not None and row.source == "sonvfx" and row.parent_filename == "vo.mp3" and row.relation == "mix",
              str(row and (row.source, row.parent_filename, row.relation)))
        r2 = await c.post("/api/audio/duck", json={"voice": "vo.mp3", "music": "bgm.mp3"})
        check("deuxième mix : nom suffixé, pas d'écrasement", r2.json().get("filename") == "mix_vo_bgm_2.mp3", r2.text[:200])
        r3 = await c.post("/api/audio/duck", json={"voice": "vo.mp3", "music": "bgm.mp3", "music_db": -6, "ducking": False})
        f3 = audio / r3.json()["filename"]
        ff("-i", str(audio / "mix_vo_bgm.mp3"), "-af", "highpass=f=80,lowpass=f=150,highpass=f=80,lowpass=f=150",
           str(w / "m1.wav"))
        ff("-i", str(f3), "-af", "highpass=f=80,lowpass=f=150,highpass=f=80,lowpass=f=150", str(w / "m3.wav"))
        check("MESURÉ : le mix ducké a la musique ≥ 4 dB sous le mix à plat (sous la voix)",
              mean_db(w / "m3.wav", 0.5, 1.0) - mean_db(w / "m1.wav", 0.5, 1.0) >= 4.0,
              f"{mean_db(w / 'm3.wav', 0.5, 1.0)} / {mean_db(w / 'm1.wav', 0.5, 1.0)}")
        r = await c.post("/api/audio/duck", json={"voice": "nope.mp3", "music": "bgm.mp3"})
        check("voix absente : 404", r.status_code == 404)
        r = await c.post("/api/audio/duck", json={"voice": "../t.db", "music": "bgm.mp3"})
        check("chemin hors dossier : 404 (nom seul)", r.status_code == 404)
        r = await c.post("/api/audio/duck", json={"voice": "vo.mp3", "music": "vo.mp3"})
        check("même fichier pour les deux : 400", r.status_code == 400, r.text[:200])
        check("gratuit : aucune garde de plafond appelée", OPS == [], str(OPS))
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
