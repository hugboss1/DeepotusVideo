# -*- coding: utf-8 -*-
"""T100 (plan-son-vfx T2, P1) — stems Demucs : registre relu sur la page /api de fal le 06/10, seams fal stubbés,
fichiers ÉCRITS (ffprobe), sidecar de lignée, Bibliothèque (source sonvfx + mère + relation), refus sans clé ; la
route POST /audio/stems passe par la garde des plafonds AVANT le moindre appel fal (402 sans dépense).
Run: python tests/test_stems_service.py (depuis backend/)"""
import asyncio, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzstems_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
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
def probe(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout or 0)
from app.config import settings
from app.services import stems_service as ST, sfx_service as S, plafonds as PL
from app.services.storage import init_db, LibraryAsset, async_session_factory
asyncio.run(init_db())
audio = S._audio_dir()
src = audio / "theme_abysses.mp3"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=3",
                "-c:a", "libmp3lame", str(src)], check=True)
fake = pathlib.Path(_tmp, "fake_stem.mp3")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-c:a", "libmp3lame", str(fake)], check=True)
CALLS, UPS = [], []
async def _sub(endpoint, arguments):
    CALLS.append((endpoint, arguments))
    return {s: {"url": f"http://fal.test/{s}.mp3", "content_type": "audio/mpeg"}
            for s in arguments["stems"] if s != "piano"}     # piano manquant : dit, pas fatal
async def _up(path):
    UPS.append(pathlib.Path(path).name); return "http://fal.test/in.mp3"
async def _dl(url, dest): shutil.copy2(fake, dest)
ST._fal_subscribe, ST._upload, ST._download = _sub, _up, _dl

print("\n[1] registre")
check("htdemucs_6s : 6 stems, piano en dernier", ST.STEMS_MODELS["htdemucs_6s"]["stems"] ==
      ("vocals", "drums", "bass", "other", "guitar", "piano"))
check("htdemucs_ft : 4 stems", ST.STEMS_MODELS["htdemucs_ft"]["stems"] == ("vocals", "drums", "bass", "other"))
check("défaut = htdemucs_6s (celui de fal)", ST.DEFAULT_MODEL == "htdemucs_6s")

print("\n[2] refus")
settings.FAL_KEY = ""
try:
    asyncio.run(ST.separer_stems("theme_abysses.mp3")); check("sans clé : refus", False)
except S.SfxError as e: check("sans clé : 400 nommant fal", e.status == 400 and "fal" in e.message, e.message)
settings.FAL_KEY = "test-key"
for label, kw, st in (("stem inconnu", {"stems": ["kazoo"]}, 400), ("modèle inconnu", {"model": "nope"}, 400)):
    try:
        asyncio.run(ST.separer_stems("theme_abysses.mp3", **kw)); check(label + " refusé", False)
    except S.SfxError as e: check(f"{label} refusé ({st})", e.status == st, f"{e.status} {e.message}")
try:
    asyncio.run(ST.separer_stems("absent.mp3")); check("fichier absent refusé", False)
except S.SfxError as e: check("fichier absent : 404", e.status == 404)
try:
    asyncio.run(ST.separer_stems("../t.db")); check("chemin hors dossier refusé", False)
except S.SfxError as e: check("chemin hors dossier : 404 (nom seul)", e.status == 404)
check("aucun refus n'a appelé fal", CALLS == [] and UPS == [], str(CALLS))

print("\n[3] séparation")
r = asyncio.run(ST.separer_stems("theme_abysses.mp3", stems=["vocals", "drums", "piano"]))
check("endpoint et arguments figés", CALLS[0][0] == "fal-ai/demucs" and CALLS[0][1] == {
    "audio_url": "http://fal.test/in.mp3", "model": "htdemucs_6s", "stems": ["vocals", "drums", "piano"],
    "output_format": "mp3"}, str(CALLS))
names = [it["filename"] for it in r["items"]]
check("deux fichiers écrits, nommés par stem", names == ["stem_theme_abysses_vocals.mp3", "stem_theme_abysses_drums.mp3"], str(names))
check("durée sondée ≈ 3 s", all(abs(probe(audio / n) - 3.0) < 0.3 for n in names))
check("aucun .part laissé", not list(audio.glob("*.part")))
meta = S.load_meta()
check("sidecar : kind stem + stem + parent + modèle", meta[names[0]]["kind"] == "stem" and meta[names[0]]["stem"] == "vocals"
      and meta[names[0]]["parent"] == "theme_abysses.mp3" and meta[names[0]]["model"] == "htdemucs_6s", str(meta.get(names[0])))
check("stem manquant DIT", r["missing"] == ["piano"], str(r))
check("coût = durée × 0,0007", abs(r["usd"] - 3.0 * 0.0007) < 1e-4, str(r["usd"]))
async def _row(n):
    async with async_session_factory() as s:
        row = await s.get(LibraryAsset, n)
        return row and (row.source, row.kind, row.parent_filename, row.relation)
check("Bibliothèque : sonvfx / audio / mère / relation stem", asyncio.run(_row(names[0])) ==
      ("sonvfx", "audio", "theme_abysses.mp3", "stem"), str(asyncio.run(_row(names[0]))))
r2 = asyncio.run(ST.separer_stems("theme_abysses.mp3", stems=["vocals"]))
check("homonyme : _2, jamais d'écrasement", r2["items"][0]["filename"] == "stem_theme_abysses_vocals_2.mp3", str(r2))
CALLS.clear()
asyncio.run(ST.separer_stems("theme_abysses.mp3", model="htdemucs_ft"))
check("sans stems : la liste complète du modèle", CALLS[0][1]["stems"] == ["vocals", "drums", "bass", "other"], str(CALLS))
async def _boom(endpoint, arguments): raise RuntimeError("quota")
ST._fal_subscribe = _boom
try:
    asyncio.run(ST.separer_stems("theme_abysses.mp3", stems=["bass"])); check("panne fal : 502", False)
except S.SfxError as e: check("panne fal : 502 nommant fal", e.status == 502 and "fal" in e.message, e.message)
ST._fal_subscribe = _sub

print("\n[4] routes")
from httpx import AsyncClient, ASGITransport
from app.main import app
async def _routes():
    out = {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        g = await c.get("/api/audio/stems-models")
        out["models"] = (g.status_code, g.json())
        out["vide"] = (await c.post("/api/audio/stems", json={})).status_code
        CALLS.clear()
        p = await c.post("/api/audio/stems", json={"filename": "theme_abysses.mp3", "stems": ["vocals"]})
        out["ok"] = (p.status_code, p.json(), list(CALLS))
        PL.enregistrer({"par_moteur": {"fal": 0.0001}})
        CALLS.clear()
        b = await c.post("/api/audio/stems", json={"filename": "theme_abysses.mp3", "stems": ["vocals"]})
        out["plafond"] = (b.status_code, b.text[:200], list(CALLS))
        PL.enregistrer({"par_moteur": {"fal": 0}})
    return out
o = asyncio.run(_routes())
st, js = o["models"]
check("GET stems-models : activé, défaut, deux modèles, tarif", st == 200 and js["enabled"] is True and js["default"] == "htdemucs_6s"
      and [m["id"] for m in js["models"]] == ["htdemucs_6s", "htdemucs_ft"] and abs(js["usd_per_s"] - 0.0007) < 1e-9, str(js))
check("POST sans filename : 400", o["vide"] == 400, str(o["vide"]))
st, js, calls = o["ok"]
check("POST : 200, un stem, un appel fal", st == 200 and len(js["items"]) == 1 and len(calls) == 1, f"{st} {js}")
st, txt, calls = o["plafond"]
check("plafond fal dépassé : 402 dz_plafond AVANT tout appel fal", st == 402 and "dz_plafond" in txt and calls == [], f"{st} {txt} {calls}")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
