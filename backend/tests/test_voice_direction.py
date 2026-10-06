# -*- coding: utf-8 -*-
"""T102 (plan-son-vfx T7, P5) — direction d'interprétation par balises Eleven v3 : registre des balises (relu le
06/10/2026 sur elevenlabs.io/docs/best-practices/prompting/eleven-v3), application d'un style, retrait propre quand
le fournisseur ne les lit pas (Voicebox, modèles non-v3) AVEC une note, route /voice-tags, et texte RÉELLEMENT
envoyé au SDK (stub). Le modèle EFFECTIF compte : modèle omis + ELEVENLABS_MODEL=eleven_v3 garde les balises (le
plan du 03/09 ne regardait que le modèle demandé). La garde des plafonds chiffre le texte balisé (ce qui part).
Écarts mesurés au plan : [sad] et [pause] ne sont PAS dans la page relue (les pauses passent par la ponctuation),
[fart] et [strong X accent] y sont.
Run: python tests/test_voice_direction.py (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile, types
_tmp = tempfile.mkdtemp(prefix="dzdir_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["ELEVENLABS_API_KEY"] = "test-11l"
os.environ["FAL_KEY"] = ""
os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SENT = []
class _TTS:
    def convert(self, **kw): SENT.append(kw); return iter([b"ID3" + b"\0" * 64])
class _Client:
    def __init__(self, api_key=None): self.text_to_speech = _TTS()
_m = types.ModuleType("elevenlabs.client"); _m.ElevenLabs = _Client
_p = types.ModuleType("elevenlabs"); _p.client = _m
sys.modules["elevenlabs"] = _p; sys.modules["elevenlabs.client"] = _m
from loguru import logger
logger.remove()
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.api import routes as R
from app.services import voice_providers as VP
settings.ELEVENLABS_API_KEY = "test-11l"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from app.services import voice_direction as VD
print("\n[1] registre")
check("4 groupes, toutes les balises entre crochets",
      set(VD.V3_TAGS) == {"emotion", "voix", "sons", "special"}
      and all(t.startswith("[") and t.endswith("]") for g in VD.V3_TAGS.values() for t in g))
check("les balises de la page relue sont connues", all(VD.is_known(t) for t in (
    "[laughs]", "[laughs harder]", "[starts laughing]", "[wheezing]", "[whispers]", "[sighs]", "[exhales]",
    "[sarcastic]", "[curious]", "[excited]", "[crying]", "[snorts]", "[mischievously]", "[gunshot]",
    "[applause]", "[clapping]", "[explosion]", "[swallows]", "[gulps]", "[sings]", "[woo]", "[fart]",
    "[strong French accent]")))
check("[sad] et [pause] ne sont PAS dans la page : inconnues", not VD.is_known("[sad]") and not VD.is_known("[pause]"))
check("[sings]/[woo] marquées spéciales (expérimentales)", {"[sings]", "[woo]"} <= VD.EXPERIMENTAL)

print("\n[2] style")
st = VD.clamp_style({"tags": ["[excited]", "[foo]", "[whispers]", "[sighs]", "[curious]", "[crying]"], "stability": 0.7})
check("clampé : inconnue retirée, ≤ 4 balises, stabilité snappée",
      st == {"tags": ["[excited]", "[whispers]", "[sighs]", "[curious]"], "stability": 0.5}, str(st))
check("style illisible : vide", VD.clamp_style("nope") == {"tags": [], "stability": 0.5})
check("apply_style préfixe", VD.apply_style("Bonjour", st) == "[excited] [whispers] [sighs] [curious] Bonjour")
check("texte déjà balisé en tête : pas de double préfixe", VD.apply_style("[sarcastic] Adieu", st) == "[sarcastic] Adieu")
check("unknown_tags", VD.unknown_tags("[sad] et [zzz] puis [laughs]") == ["[sad]", "[zzz]"])
check("strip_tags", VD.strip_tags("[sarcastic] Adieu [whispers] monde") == "Adieu monde")

OPS = []
_vrai_plafond = R._plafond
async def _plaf(op, cat, ref=None):
    OPS.append(op); return await _vrai_plafond(op, cat, ref)
R._plafond = _plaf
VB = []
def _vb_tts(**kw):
    VB.append(kw); pathlib.Path(kw["output_path"]).write_bytes(b"ID3" + b"\0" * 64); return kw["output_path"]

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        print("\n[3] routes")
        d = (await c.get("/api/voice-tags")).json()
        check("/voice-tags : groupes + fournisseur + modèle", d["groups"]["emotion"][0] == "[excited]"
              and d["providers"] == {"elevenlabs": True, "voicebox": False} and d["model"] == "eleven_v3"
              and "[sings]" in d["experimental"], str(d)[:300])
        r = await c.post("/api/audio/voiceover", json={"script": "Salut le fond", "model": "eleven_v3",
                                                       "style": {"tags": ["[whispers]"], "stability": 0}})
        check("v3 : le SDK reçoit le texte balisé", r.status_code == 200 and SENT[-1]["text"] == "[whispers] Salut le fond"
              and SENT[-1]["model_id"] == "eleven_v3", r.text[:200] + str(SENT[-1:]))
        check("v3 + balises : la stabilité du style part (Creative = 0)",
              getattr(SENT[-1].get("voice_settings"), "stability", None) == 0.0
              or (SENT[-1].get("voice_settings") or {}).get("stability") == 0.0, str(SENT[-1].get("voice_settings")))
        check("v3 : la garde chiffre le texte balisé (ce qui part)",
              OPS[-1] and OPS[-1][0]["chars"] == len("[whispers] Salut le fond"), str(OPS[-1:]))
        check("v3 : réponse sans note quand tout est connu", r.json()["notes"] == [], r.text[:200])
        r = await c.post("/api/audio/voiceover", json={"script": "[sad] Salut", "model": "eleven_v3"})
        check("v3 : balise inconnue laissée ET dite", SENT[-1]["text"] == "[sad] Salut"
              and any("[sad]" in n for n in r.json()["notes"]), r.text[:200])
        r = await c.post("/api/audio/voiceover", json={"script": "[sarcastic] Salut", "model": "eleven_multilingual_v2"})
        check("hors v3 : balises retirées ET note", SENT[-1]["text"] == "Salut"
              and any("v3" in n for n in r.json()["notes"]), r.text[:200])
        settings.ELEVENLABS_MODEL = "eleven_v3"
        r = await c.post("/api/audio/voiceover", json={"script": "[sarcastic] Salut"})
        check("modèle omis + défaut app v3 : balises GARDÉES (modèle effectif)",
              SENT[-1]["text"] == "[sarcastic] Salut" and SENT[-1]["model_id"] == "eleven_v3", str(SENT[-1:]))
        settings.ELEVENLABS_MODEL = ""
        r = await c.post("/api/audio/voiceover", json={"script": "Salut", "model": "eleven_nope"})
        check("modèle inconnu : 400 (inchangé)", r.status_code == 400, r.text[:200])
        print("\n[4] Voicebox")
        VP.resolve_provider = lambda requested=None: "voicebox"
        VP.voicebox_tts = _vb_tts
        R_vb = await c.post("/api/audio/voiceover", json={"script": "Salut", "model": "eleven_v3",
                                                          "style": {"tags": ["[whispers]"]}})
        check("Voicebox : balises retirées, note qui le nomme", R_vb.status_code == 200 and VB[-1]["text"] == "Salut"
              and any("Voicebox" in n for n in R_vb.json()["notes"]), R_vb.text[:200] + str(VB[-1:]))
        d = (await c.get("/api/voice-tags")).json()
        check("/voice-tags sous Voicebox : elevenlabs faux, voicebox vrai",
              d["providers"] == {"elevenlabs": False, "voicebox": True}, str(d["providers"]))
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
