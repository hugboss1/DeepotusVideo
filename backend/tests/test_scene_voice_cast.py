# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T15, D4b) — de bout en bout : chaque réplique d'une scène part avec la voix DU personnage
et SON tempérament ; la narration prend celui du Narrateur ; un personnage sans tempérament part NU, au modèle
par défaut (aucune balise inventée) ; hors Eleven v3 (Voicebox) les balises sont retirées et la note le dit UNE
fois. Banc-miroir : on lit les appels RÉELLEMENT faits au TTS, pas la fonction qui prétend les faire. La garde
des plafonds chiffre ce qui part : le texte BALISÉ, au tarif d'Eleven v3 pour les répliques dirigées (le plan du
03/09 la laissait sur le texte nu et le modèle par défaut). GET /voice-cast montre le casting avant de générer,
et chaque site d'appel de `_voice_cast` déballe ses TROIS valeurs (lu dans le source).
Run: python tests/test_scene_voice_cast.py (depuis backend/)"""
import ast, asyncio, json, os, pathlib, shutil, subprocess, sys, tempfile
from uuid import uuid4
_tmp = tempfile.mkdtemp(prefix="dzcast_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["ELEVENLABS_API_KEY"] = "test-11l"; os.environ["FAL_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable"); sys.exit(0)
from loguru import logger
logger.remove()
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.api import routes as R
from app.services.elevenlabs_service import VoiceoverService
from app.services import voice_providers as VP
from app.services.storage import init_db, BibleEntity, Chapter, Scene, async_session_factory
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
settings.ELEVENLABS_API_KEY = "test-11l"
CALLS = []
def _fake_long(self, text, output_path, language="EN", voice_id=None, model_id=None, **kw):
    CALLS.append({"text": text, "voice_id": voice_id, "model_id": model_id})
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=1",
                    "-c:a", "libmp3lame", str(output_path)], check=True)
    return output_path
VoiceoverService.generate_long = _fake_long
VoiceoverService.is_enabled = staticmethod(lambda: True)
VP.resolve_provider = lambda requested=None: "elevenlabs"
OPS = []
async def _plaf(op, cat, ref=None):
    OPS.append(op); return {}
R._plafond = _plaf
CH, SC = uuid4().hex, uuid4().hex
FOUNTAIN = ("Le fond bouge à peine.\n\n"
            "DEEPOTUS\nJe remonte.\n\n"
            "MARIN\nPas ce soir.\n")
async def main():
    await init_db()
    async with async_session_factory() as s:
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Narrateur", voice_id="v_narr",
                          voice_style=json.dumps({"tags": ["[curious]"], "stability": 0.5})))
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Deepotus", voice_id="v_deep",
                          aliases=json.dumps(["Le Dieu"]),
                          voice_style=json.dumps({"tags": ["[whispers]", "[sighs]", "[zzz]"], "stability": 1.0})))
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Marin", voice_id="v_marin"))
        s.add(BibleEntity(id=uuid4().hex, kind="character", name="Silhouette"))
        s.add(BibleEntity(id=uuid4().hex, kind="place", name="Abysse"))
        s.add(Chapter(id=CH, title="Ch1"))
        s.add(Scene(id=SC, chapter_id=CH, idx=0, slugline="INT. ABYSSE", fountain_text=FOUNTAIN))
        await s.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        print("\n[1] le casting, lisible avant de générer")
        d = (await c.get("/api/voice-cast")).json()
        check("GET /voice-cast : narrateur et son tempérament", d["narrator"] == {"voice_id": "v_narr", "name": "Narrateur",
              "style": {"tags": ["[curious]"], "stability": 0.5}}, str(d.get("narrator")))
        check("rôles castés, tempérament CLAMPÉ ([zzz] retiré), alias servi aussi",
              d["cast"]["deepotus"]["style"]["tags"] == ["[whispers]", "[sighs]"] and d["cast"]["marin"]["style"]["tags"] == []
              and d["cast"]["le dieu"]["voice_id"] == "v_deep", str(d.get("cast"))[:300])
        check("personnage sans voix listé à part, un LIEU n'y est pas", d["uncast"] == ["Silhouette"], str(d.get("uncast")))
        print("\n[2] Eleven v3 : chacun sa voix, son tempérament")
        r = await c.post(f"/api/scenes/{SC}/voiceover", json={"language": "fr"})
        check("VO de scène : 200 et trois segments", r.status_code == 200 and len(r.json()["segments"]) == 3, r.text[:200])
        check("narration : voix du Narrateur, SON tempérament devant, Eleven v3",
              CALLS[0] == {"text": "[curious] Le fond bouge à peine.", "voice_id": "v_narr", "model_id": "eleven_v3"}, str(CALLS[:1]))
        check("Deepotus : sa voix, ses deux balises dans l'ordre de la fiche",
              CALLS[1] == {"text": "[whispers] [sighs] Je remonte.", "voice_id": "v_deep", "model_id": "eleven_v3"}, str(CALLS[1:2]))
        check("Marin sans tempérament : texte NU et modèle par défaut",
              CALLS[2] == {"text": "Pas ce soir.", "voice_id": "v_marin", "model_id": None}, str(CALLS[2:3]))
        seg = r.json()["segments"]
        check("le plan de scène nomme le locuteur ET son tempérament",
              [s["speaker"] for s in seg] == ["Narrateur", "Deepotus", "Marin"] and seg[1]["tags"] == ["[whispers]", "[sighs]"]
              and seg[2]["tags"] == [], str(seg))
        check("aucune note sous Eleven v3", r.json()["notes"] == [], str(r.json().get("notes")))
        op = OPS[-1]
        ops = op if isinstance(op, list) else (op.get("ops") if isinstance(op, dict) and op.get("kind") == "campaign" else [op])
        check("la garde chiffre CE QUI PART : texte balisé, Eleven v3 pour les répliques dirigées",
              ops == [{"kind": "elevenlabs", "chars": len("[curious] Le fond bouge à peine."), "model": "eleven_v3"},
                      {"kind": "elevenlabs", "chars": len("[whispers] [sighs] Je remonte."), "model": "eleven_v3"},
                      {"kind": "elevenlabs", "chars": len("Pas ce soir.")}], str(OPS[-1]))
        print("\n[3] Voicebox : nettoyé, et dit UNE fois")
        VP.resolve_provider = lambda requested=None: "voicebox"
        CALLS.clear(); OPS.clear()
        r = await c.post(f"/api/scenes/{SC}/voiceover", json={"language": "fr"})
        check("Voicebox : aucune balise dans le texte envoyé, modèle par défaut",
              all("[" not in x["text"] and x["model_id"] is None for x in CALLS) and CALLS[1]["text"] == "Je remonte.", str(CALLS))
        check("Voicebox : la réponse le DIT une fois, pas trois",
              len([n for n in r.json()["notes"] if "Voicebox" in n]) == 1 and len(r.json()["notes"]) == 1, str(r.json().get("notes")))
        check("Voicebox : rien à chiffrer (local, gratuit)", all(not o for o in OPS), str(OPS))
asyncio.run(main())

print("\n[4] chaque site de _voice_cast déballe TROIS valeurs")
src = (pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "routes.py").read_text(encoding="utf-8")
sites = []
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.Assign) and isinstance(n.value, ast.Await) and isinstance(n.value.value, ast.Call) \
            and getattr(n.value.value.func, "id", "") == "_voice_cast":
        sites.append(len(n.targets[0].elts) if isinstance(n.targets[0], ast.Tuple) else 1)
check(f"{len(sites)} sites, tous à trois valeurs", len(sites) >= 4 and set(sites) == {3}, str(sites))
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
