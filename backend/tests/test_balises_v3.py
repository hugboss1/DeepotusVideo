"""t487 (F6.9, lot « Fiches modèle ») — balises d'émotion ElevenLabs : seul Eleven v3 les lit.

`[whispers]`, `[laughs]`… sont interprétées par Eleven v3 ; Multilingual v2, Flash v2.5 et Voicebox les LIRAIENT à voix
haute. La route voix off et la narration des Chapitres les retiraient déjà ; `VoiceoverService.generate` devient la
dernière porte pour TOUTES les voies (narration d'épisode, voix témoins de l'animatique, lecture de l'assistant).
Seules les balises CONNUES partent : un autre crochet (« [Scène 2] ») est du texte de l'auteur.

Run: <python embarqué> backend/tests/test_balises_v3.py
"""
import os
import pathlib
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-el")

ENVOIS = []


class _TTS:
    def convert(self, text, voice_id, model_id, output_format, voice_settings):
        ENVOIS.append({"moteur": "elevenlabs", "texte": text, "modele": model_id})
        return [b"ID3fake"]


class _Client:
    def __init__(self, api_key=None):
        self.text_to_speech = _TTS()


_mod = types.ModuleType("elevenlabs.client")
_mod.ElevenLabs = _Client
sys.modules.setdefault("elevenlabs", types.ModuleType("elevenlabs"))
sys.modules["elevenlabs.client"] = _mod

from app.services import elevenlabs_service as ES, voice_direction as VD, voice_providers as VP  # noqa: E402

VP.resolve_provider = lambda p=None: p or "elevenlabs"


def _vb(text, output_path, language="EN", voice_id=None):
    ENVOIS.append({"moteur": "voicebox", "texte": text, "modele": None})
    pathlib.Path(output_path).write_bytes(b"RIFFfake")
    return pathlib.Path(output_path)


VP.voicebox_tts = _vb
TMP = pathlib.Path(tempfile.mkdtemp(prefix="balises_v3_"))
ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


def envoi(texte, modele=None, provider=None):
    ENVOIS.clear()
    ES.VoiceoverService().generate(text=texte, output_path=TMP / "v.mp3", model_id=modele, provider=provider)
    return ENVOIS[-1]


print("\n[1] retirer_balises_v3 (pur)")
t, r = VD.retirer_balises_v3("[whispers] Viens   ici. [laughs] Bon.")
check("1.1 balises connues retirées, espaces resserrés", t == "Viens ici. Bon." and r == ["[whispers]", "[laughs]"], (t, r))
t, r = VD.retirer_balises_v3("[Scène 2] Le port. [strong French accent] Bonjour.")
check("1.2 un crochet de l'auteur reste ; l'accent (gabarit v3) part", t == "[Scène 2] Le port. Bonjour."
      and r == ["[strong French accent]"], (t, r))
t, r = VD.retirer_balises_v3("Rien  à retirer [ici].")
check("1.3 sans balise connue : texte rendu À L'IDENTIQUE (espaces compris)", t == "Rien  à retirer [ici]." and r == [], (t, r))

print("\n[2] dernière porte : VoiceoverService.generate")
e = envoi("[excited] On y va !", "eleven_multilingual_v2")
check("2.1 Multilingual v2 : la balise ne part pas", e["texte"] == "On y va !", e)
e = envoi("[sighs] Encore toi.", "eleven_flash_v2_5")
check("2.2 Flash v2.5 : idem", e["texte"] == "Encore toi.", e)
e = envoi("[whispers] Chut.", "eleven_v3")
check("2.3 Eleven v3 : la balise PART (il l'interprète)", e["texte"] == "[whispers] Chut." and e["modele"] == "eleven_v3", e)
e = envoi("[laughs] Ha.", None, "voicebox")
check("2.4 Voicebox : la balise ne part pas", e["moteur"] == "voicebox" and e["texte"] == "Ha.", e)
_def0 = ES.default_model_id
ES.default_model_id = lambda: "eleven_v3"          # l'app réglée sur v3 : Voicebox ne lit TOUJOURS pas les balises
try:
    e = envoi("[laughs] Ha.", None, "voicebox")
finally:
    ES.default_model_id = _def0
check("2.4b Voicebox même quand le défaut ElevenLabs de l'app est v3 : retirée", e["texte"] == "Ha.", e)
ES_def = ES.default_model_id()
e = envoi("[curious] Et alors ?", None)
check("2.5 modèle par défaut (non v3) : retirée", (e["texte"] == "Et alors ?") == (ES_def != "eleven_v3"), (ES_def, e))
e = envoi("[Chapitre 1] Il était une fois.", "eleven_multilingual_v2")
check("2.6 crochet de l'auteur : envoyé tel quel", e["texte"] == "[Chapitre 1] Il était une fois.", e)
try:
    envoi("[laughs] [sighs]", "eleven_multilingual_v2")
    vide = None
except ValueError as x:
    vide = x
check("2.7 un texte fait de balises seulement : refus (rien de payé, rien de vide envoyé)", vide is not None
      and not ENVOIS, (vide, ENVOIS))
ENVOIS.clear()
ES.VoiceoverService().generate_long(text="[whispers] Une phrase. " * 3, output_path=TMP / "l.mp3",
                                    model_id="eleven_multilingual_v2")
check("2.8 generate_long passe par la même porte", ENVOIS and all("[whispers]" not in x["texte"] for x in ENVOIS), ENVOIS)

print("\n[3] la porte est AVANT le choix du moteur")
import inspect  # noqa: E402
g = inspect.getsource(ES.VoiceoverService.generate)
check("3.1 dans generate : le retrait précède l'appel Voicebox ET l'appel ElevenLabs",
      0 < g.index("retirer_balises_v3") < g.index("voicebox_tts(") < g.index("text_to_speech.convert("))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
