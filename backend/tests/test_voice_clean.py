# -*- coding: utf-8 -*-
"""T100 (plan-son-vfx T3, P2) — chaîne « améliorer » (locale, gratuite) MESURÉE par ebur128, et isolation
ElevenLabs (seam HTTP stubbé, multipart `audio` relu le 06/10) : fichiers écrits, sidecar, Bibliothèque (mère +
relation), coût en caractères par minute ; la route d'isolation passe par la garde des plafonds AVANT le POST,
la chaîne locale n'y passe pas (0 $).
Run: python tests/test_voice_clean.py (depuis backend/)"""
import asyncio, os, pathlib, re, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzclean_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["FAL_KEY"] = ""
os.environ["ELEVENLABS_API_KEY"] = "test-11l"
os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not shutil.which("ffmpeg"): print("SKIP: ffmpeg introuvable"); sys.exit(0)
from loguru import logger
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def lufs(p):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
from app.config import settings
from app.services import voice_clean as VC, sfx_service as S, pricing, plafonds as PL
from app.services.storage import init_db, LibraryAsset, async_session_factory
asyncio.run(init_db())
settings.ELEVENLABS_API_KEY = "test-11l"
audio = S._audio_dir()
src = audio / "prise_brute.mp3"   # voix (sinus) + souffle, très bas : loin de −16 LUFS
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=200:duration=4",
                "-f", "lavfi", "-i", "anoisesrc=amplitude=0.02:duration=4", "-filter_complex",
                "[0:a][1:a]amix=inputs=2,volume=0.03[o]", "-map", "[o]", "-c:a", "libmp3lame", str(src)], check=True)

print("\n[1] chaîne « améliorer »")
cmd = VC.enhance_command(src, audio / "x.mp3")
af = cmd[cmd.index("-af") + 1]
check("ordre RENDU de _FX_ORDER : equalizer < afftdn < acompressor < loudnorm",
      af.index("equalizer") < af.index("afftdn") < af.index("acompressor") < af.index("loudnorm"), af)
check("cible −16 LUFS dans le graphe", "loudnorm=I=-16" in af, af)
r = VC.enhance("prise_brute.mp3")
out = audio / r["filename"]
check("fichier clean_ écrit, aucun .part", out.is_file() and r["filename"] == "clean_prise_brute.mp3"
      and not list(audio.glob("*.part")), str(r))
li, li0 = lufs(out), lufs(src)
check("MESURÉ : sortie à −16 ± 1,5 LUFS", -17.5 <= li <= -14.5, f"{li} LUFS (entrée {li0})")
check("MESURÉ : l'entrée en était loin (> 10 LU)", li0 < -26, str(li0))
m = S.load_meta()[r["filename"]]
check("sidecar : voix, parent, chaîne nommée", m["kind"] == "voix" and m["parent"] == "prise_brute.mp3" and m["chain"] == "ameliorer", str(m))
check("gratuit, et dit", r["usd"] == 0.0 and r["parent"] == "prise_brute.mp3")
check("relation d'amélioration", r["relation"] == "ameliore", str(r))
r_b = VC.enhance("prise_brute.mp3")
check("homonyme : _2", r_b["filename"] == "clean_prise_brute_2.mp3", str(r_b))
try: VC.enhance("absent.mp3"); check("absent refusé", False)
except S.SfxError as e: check("absent : 404", e.status == 404)

print("\n[2] isolation ElevenLabs")
POSTS = []
def _fake_post(key, name, data):
    POSTS.append((key, name, len(data))); return src.read_bytes()
VC._post_isolation = _fake_post
r2 = VC.isoler_voix("prise_brute.mp3")
check("iso_ écrit, meta voix + parent + chaîne", (audio / r2["filename"]).is_file() and r2["filename"] == "iso_prise_brute.mp3"
      and S.load_meta()[r2["filename"]]["parent"] == "prise_brute.mp3"
      and S.load_meta()[r2["filename"]]["chain"] == "isolation", str(r2))
check("un seul POST, avec la clé et le fichier entier", POSTS == [("test-11l", "prise_brute.mp3", src.stat().st_size)], str(POSTS))
dur = S._probe_duration(src)
check("coût = durée/60 × 1000 car. × tarif ElevenLabs", abs(r2["usd"] - (dur / 60) * 1000 * pricing.elevenlabs_rate(None)) < 1e-4,
      f"{r2['usd']} vs {(dur / 60) * 1000 * pricing.elevenlabs_rate(None)}")
check("coût = devis de pricing (même chiffre que la garde)", abs(r2["usd"] - VC.isolation_usd(dur)) < 1e-9
      and abs(pricing.estimate({"kind": "isolate", "duration_s": dur})["total_usd"] - r2["usd"]) < 1e-3, str(r2["usd"]))
check("relation d'isolation", r2["relation"] == "isole", str(r2))
settings.ELEVENLABS_API_KEY = ""
try: VC.isoler_voix("prise_brute.mp3"); check("sans clé : refus", False)
except S.SfxError as e: check("sans clé : 400 ElevenLabs", e.status == 400 and "ElevenLabs" in e.message, e.message)
check("sans clé : aucun POST", len(POSTS) == 1)
settings.ELEVENLABS_API_KEY = "test-11l"
VC.MAX_ISOLATION_BYTES, _old = 10, VC.MAX_ISOLATION_BYTES
try: VC.isoler_voix("prise_brute.mp3"); check("trop gros refusé", False)
except S.SfxError as e: check("> plafond API : 400, aucun POST", e.status == 400 and len(POSTS) == 1, e.message)
VC.MAX_ISOLATION_BYTES = _old
def _vide(key, name, data): return b""
VC._post_isolation = _vide
try: VC.isoler_voix("prise_brute.mp3"); check("réponse vide refusée", False)
except S.SfxError as e: check("réponse vide : 502, rien d'écrit", e.status == 502 and not (audio / "iso_prise_brute_2.mp3").exists(), e.message)
VC._post_isolation = _fake_post

print("\n[3] routes")
from httpx import AsyncClient, ASGITransport
from app.main import app
async def _row(n):
    async with async_session_factory() as s:
        row = await s.get(LibraryAsset, n)
        return row and (row.source, row.kind, row.parent_filename, row.relation)
async def _routes():
    o = {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        e = await c.post("/api/audio/enhance", json={"filename": "prise_brute.mp3"})
        o["enh"] = (e.status_code, e.json())
        o["enh_row"] = await _row(e.json().get("filename", ""))
        o["enh_vide"] = (await c.post("/api/audio/enhance", json={})).status_code
        POSTS.clear()
        i = await c.post("/api/audio/isolate", json={"filename": "prise_brute.mp3"})
        o["iso"] = (i.status_code, i.json(), list(POSTS))
        o["iso_row"] = await _row(i.json().get("filename", ""))
        PL.enregistrer({"par_moteur": {"elevenlabs": 0.0001}})
        POSTS.clear()
        b = await c.post("/api/audio/isolate", json={"filename": "prise_brute.mp3"})
        o["plaf"] = (b.status_code, b.text[:200], list(POSTS))
        e2 = await c.post("/api/audio/enhance", json={"filename": "prise_brute.mp3"})
        o["enh_plaf"] = e2.status_code
        PL.enregistrer({"par_moteur": {"elevenlabs": 0}})
    return o
o = asyncio.run(_routes())
st, js = o["enh"]
check("POST /audio/enhance : 200, clean_", st == 200 and js["filename"].startswith("clean_prise_brute"), f"{st} {js}")
check("Bibliothèque : sonvfx / audio / mère / ameliore", o["enh_row"] == ("sonvfx", "audio", "prise_brute.mp3", "ameliore"), str(o["enh_row"]))
check("POST /audio/enhance sans filename : 400", o["enh_vide"] == 400, str(o["enh_vide"]))
st, js, posts = o["iso"]
check("POST /audio/isolate : 200, un POST", st == 200 and js["filename"].startswith("iso_prise_brute") and len(posts) == 1, f"{st} {js}")
check("Bibliothèque : sonvfx / audio / mère / isole", o["iso_row"] == ("sonvfx", "audio", "prise_brute.mp3", "isole"), str(o["iso_row"]))
st, txt, posts = o["plaf"]
check("plafond ElevenLabs dépassé : 402 dz_plafond AVANT le POST", st == 402 and "dz_plafond" in txt and posts == [], f"{st} {txt} {posts}")
check("la chaîne locale ne connaît pas le plafond (0 $)", o["enh_plaf"] == 200, str(o["enh_plaf"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
