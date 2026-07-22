"""Chantier W-b — modèles TTS ElevenLabs (plan §2) : catalogue ELEVEN_MODELS,
défaut app (ELEVENLABS_MODEL), clamp/filtre voice_settings par modèle, pricing
multiplicateur (flash 0,5×), endpoint /voice-models, modèle+réglages transmis
au SDK, écriture atomique (échec TTS → zéro résidu — cause racine du bug
0 octet, mémoire audio-library-qa-cleanup-20260722). SDK stubbé, zéro réseau.
Run: <embedded python> backend/tests/test_voice_models.py"""
import asyncio
import os
import pathlib
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
# DATA_ROOT isolé : ni le .env réel ni le pricing.json réel ne sont lus.
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-11l")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings                     # noqa: E402
settings.ELEVENLABS_API_KEY = "test-11l"
settings.ELEVENLABS_MODEL = "eleven_multilingual_v2"

# ── stub du SDK elevenlabs (import lazy dans generate) ──
SDK_CALLS: list = []
BEHAVIOR = {"mode": "ok"}   # ok | fail_early | fail_mid


class _FakeTTS:
    def convert(self, **kw):
        SDK_CALLS.append(kw)
        mode = BEHAVIOR["mode"]

        def stream():
            if mode == "fail_early":
                raise RuntimeError("boom before first byte")
            yield b"ID3" + b"x" * 64
            if mode == "fail_mid":
                raise RuntimeError(
                    "status_code: 402, body: {'detail': {'status': "
                    "'paid_plan_required', 'message': 'upgrade'}}")
            yield b"y" * 64
        return stream()


class _FakeEleven:
    def __init__(self, api_key=None):
        self.text_to_speech = _FakeTTS()


_m = types.ModuleType("elevenlabs")
_mc = types.ModuleType("elevenlabs.client")
_mc.ElevenLabs = _FakeEleven
_m.client = _mc
sys.modules["elevenlabs"] = _m
sys.modules["elevenlabs.client"] = _mc

from app.services import pricing                    # noqa: E402
from app.services.elevenlabs_service import (       # noqa: E402
    DEFAULT_ELEVEN_MODEL, ELEVEN_MODELS, VoiceoverService, _chunk_text,
    clamp_voice_settings, default_model_id, resolve_model)


def test_registry_shape():
    assert set(ELEVEN_MODELS) == {"eleven_multilingual_v2", "eleven_v3",
                                  "eleven_flash_v2_5"}
    assert DEFAULT_ELEVEN_MODEL == "eleven_multilingual_v2"
    for mid, m in ELEVEN_MODELS.items():
        for k in ("label", "max_chars", "settings"):
            assert k in m, f"{mid} missing {k}"
        assert m["max_chars"] >= 5000, mid
        assert pricing.elevenlabs_rate(mid) > 0, mid
    base = pricing.elevenlabs_rate(None)
    assert abs(base - 0.00024) < 1e-12
    assert abs(pricing.elevenlabs_rate("eleven_flash_v2_5") - base * 0.5) < 1e-12
    assert abs(pricing.elevenlabs_rate("eleven_v3") - base) < 1e-12
    assert pricing.elevenlabs_mult("modele-inconnu") == 1.0


def test_default_and_resolve():
    assert default_model_id() == "eleven_multilingual_v2"
    settings.ELEVENLABS_MODEL = "eleven_flash_v2_5"
    assert default_model_id() == "eleven_flash_v2_5"
    assert resolve_model(None) == "eleven_flash_v2_5"
    settings.ELEVENLABS_MODEL = "n-importe-quoi"       # inconnu → défaut sûr
    assert default_model_id() == DEFAULT_ELEVEN_MODEL
    settings.ELEVENLABS_MODEL = "eleven_multilingual_v2"
    assert resolve_model(" eleven_v3 ") == "eleven_v3"
    try:
        resolve_model("nope")
        raise AssertionError("unknown id must raise")
    except ValueError as e:
        assert "Unknown TTS model" in str(e) and "eleven_v3" in str(e)


def test_clamp_settings():
    # v2 : clamp aux bornes, speed 0.7–1.2, use_speaker_boost conservé
    out = clamp_voice_settings(
        "eleven_multilingual_v2",
        {"stability": 0.55, "similarity_boost": 0.75, "use_speaker_boost": 1},
        {"style": 2.0, "speed": 5, "stability": -1})
    assert out["style"] == 1.0 and out["speed"] == 1.2
    assert out["stability"] == 0.0 and out["similarity_boost"] == 0.75
    assert out["use_speaker_boost"] is True
    assert clamp_voice_settings("eleven_multilingual_v2", {}, {"speed": 0.1})["speed"] == 0.7
    # v3 : stabilité seule, snappée 0/0.5/1 ; le reste filtré
    out = clamp_voice_settings(
        "eleven_v3",
        {"stability": 0.55, "similarity_boost": 0.75, "use_speaker_boost": True},
        {"style": 0.4, "speed": 1.1, "stability": 0.8})
    assert out == {"stability": 1.0}, out
    assert clamp_voice_settings("eleven_v3", {}, {"stability": 0.3}) == {"stability": 0.5}
    # valeurs pourries / None ignorées
    out = clamp_voice_settings("eleven_flash_v2_5", {"stability": 0.5},
                               {"similarity_boost": "xx", "style": None})
    assert out == {"stability": 0.5}, out


def test_chunk_default_follows_model():
    txt = ("Une phrase. " * 700).strip()          # ~8 400 chars
    assert len(_chunk_text(txt, ELEVEN_MODELS["eleven_multilingual_v2"]["max_chars"])) == 1
    assert len(_chunk_text(txt, ELEVEN_MODELS["eleven_v3"]["max_chars"])) == 2


def test_generate_passes_model_and_settings():
    SDK_CALLS.clear()
    BEHAVIOR["mode"] = "ok"
    svc = VoiceoverService()
    dest = pathlib.Path(_tmp, "out", "vo.mp3")
    p = svc.generate("Bonjour", dest, language="FR",
                     model_id="eleven_flash_v2_5",
                     settings_override={"speed": 1.1, "style": 0.2})
    assert p.is_file() and p.stat().st_size > 0
    assert not dest.with_name(dest.name + ".part").exists()
    kw = SDK_CALLS[-1]
    assert kw["model_id"] == "eleven_flash_v2_5"
    assert kw["voice_settings"]["speed"] == 1.1
    assert kw["voice_settings"]["style"] == 0.2
    svc.generate("Encore", dest, language="EN")   # modèle omis → défaut app
    assert SDK_CALLS[-1]["model_id"] == "eleven_multilingual_v2"


def test_generate_long_forwards_model():
    calls = []
    svc = VoiceoverService()
    orig = VoiceoverService.generate

    def spy(self, text, output_path, language="EN", voice_id=None,
            model_id=None, settings_override=None):
        calls.append({"model": model_id, "chars": len(text),
                      "set": settings_override})
        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(output_path).write_bytes(b"MP3")
        return pathlib.Path(output_path)

    VoiceoverService.generate = spy
    try:
        svc.generate_long("Court texte.", pathlib.Path(_tmp, "gl.mp3"),
                          model_id="eleven_v3",
                          settings_override={"stability": 1})
    finally:
        VoiceoverService.generate = orig
    assert calls == [{"model": "eleven_v3", "chars": len("Court texte."),
                      "set": {"stability": 1}}], calls


def test_atomic_no_residue_on_failure():
    """Non-régression bug 0 octet : un échec TTS (avant OU pendant le stream)
    ne laisse RIEN dans le dossier de destination."""
    svc = VoiceoverService()
    audio = pathlib.Path(_tmp, "audio_unit")
    audio.mkdir(exist_ok=True)
    for mode in ("fail_early", "fail_mid"):
        BEHAVIOR["mode"] = mode
        try:
            svc.generate("Texte voué à l'échec", audio / f"res_{mode}.mp3",
                         language="FR")
            raise AssertionError("must raise")
        except RuntimeError as e:
            assert "ElevenLabs:" in str(e)
        left = [p.name for p in audio.glob("*")]
        assert left == [], f"résidu après {mode}: {left}"
    BEHAVIOR["mode"] = "ok"


async def main():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # ── GET /voice-models : catalogue + tarifs × multiplicateur ──
        r = await c.get("/api/voice-models")
        assert r.status_code == 200, r.text
        d = r.json()
        assert {m["id"] for m in d["models"]} == set(ELEVEN_MODELS)
        assert d["default"] == "eleven_multilingual_v2"
        fl = next(m for m in d["models"] if m["id"] == "eleven_flash_v2_5")
        assert abs(fl["usd_per_char"] - 0.00012) < 1e-12 and fl["mult"] == 0.5
        assert fl["max_chars"] == 40000 and "speed" in fl["settings"]
        v3 = next(m for m in d["models"] if m["id"] == "eleven_v3")
        assert v3["settings"] == ["stability"]
        assert all(m["available"] for m in d["models"])

        audio_dir = pathlib.Path(os.environ["IMAGES_FOLDER"]).parent / "audio"

        # ── échec provider 402 → 502 message actionnable + zéro résidu ──
        BEHAVIOR["mode"] = "fail_mid"
        r = await c.post("/api/audio/voiceover",
                         json={"script": "Bonjour", "language": "fr",
                               "name": "qa_wb"})
        assert r.status_code == 502, r.text
        det = r.json()["detail"]
        assert "premade" in det and "402" in det, det
        residues = [p.name for p in audio_dir.glob("qa_wb*")]
        assert residues == [], residues

        # ── modèle inconnu → 400 propre ──
        BEHAVIOR["mode"] = "ok"
        r = await c.post("/api/audio/voiceover",
                         json={"script": "Bonjour", "model": "gpt-tts"})
        assert r.status_code == 400 and "Unknown TTS model" in r.json()["detail"]

        # ── succès : model + settings jusqu'au SDK, fichier réel, pas de .part ──
        SDK_CALLS.clear()
        r = await c.post("/api/audio/voiceover", json={
            "script": "Bonjour le monde", "language": "fr", "name": "qa_wb",
            "model": "eleven_flash_v2_5",
            "settings": {"stability": 0.2, "speed": 1.15, "style": 3}})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] and d["filename"].startswith("qa_wb-")
        kw = SDK_CALLS[-1]
        assert kw["model_id"] == "eleven_flash_v2_5"
        vs = kw["voice_settings"]
        assert vs["stability"] == 0.2 and vs["speed"] == 1.15 and vs["style"] == 1.0
        assert (audio_dir / d["filename"]).is_file()
        assert not list(audio_dir.glob("*.part"))

        # ── estimate : multiplicateur répercuté + label modèle ──
        est = pricing.estimate({"kind": "elevenlabs", "chars": 1000,
                                "model": "eleven_flash_v2_5"})
        assert abs(est["total_usd"] - 0.12) < 1e-9
        assert "eleven_flash_v2_5" in est["breakdown"][0]["label"]
        est2 = pricing.estimate({"kind": "elevenlabs", "chars": 1000})
        assert abs(est2["total_usd"] - 0.24) < 1e-9
    print("VOICE MODELS TEST: PASS")


test_registry_shape()
test_default_and_resolve()
test_clamp_settings()
test_chunk_default_follows_model()
test_generate_passes_model_and_settings()
test_generate_long_forwards_model()
test_atomic_no_residue_on_failure()
asyncio.run(main())
