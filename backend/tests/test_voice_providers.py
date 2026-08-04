"""Voix interchangeables (spec voicebox 2026-07-11, étape 2) — façade
elevenlabs/voicebox : registre/résolution, catalogue, TTS Voicebox (stub HTTP,
aucun réseau), routage VoiceoverService.
Run: <embedded python> backend/tests/test_voice_providers.py"""
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
_db = pathlib.Path(_tmp, "t.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings                      # noqa: E402
# le .env du data-dir a priorité sur l'environnement (voir config.py) :
# on force les valeurs de test directement sur l'objet settings.
settings.DATABASE_URL = f"sqlite+aiosqlite:///{_db.as_posix()}"
settings.ELEVENLABS_API_KEY = ""
settings.VOICEBOX_URL = ""

from app.services import voice_providers as VP       # noqa: E402

con = sqlite3.connect(_db)
con.execute("CREATE TABLE atelier_settings (key TEXT PRIMARY KEY, value TEXT)")
con.commit()
con.close()

# ───────────────────────────── stub httpx ─────────────────────────────
CALLS: list = []
ROUTES: dict = {}   # (method, path) -> _Resp | [suite de _Resp]


class _Resp:
    def __init__(self, status=200, jobj=None, content=b""):
        self.status_code = status
        self._j = jobj
        self.content = content
        self.text = json.dumps(jobj) if jobj is not None else ""

    def json(self):
        return self._j

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _dispatch(method, path):
    CALLS.append((method, path))
    r = ROUTES.get((method, path))
    if isinstance(r, list):
        return r.pop(0) if len(r) > 1 else r[0]
    if r is None:
        raise ConnectionError(f"stub: pas de route {method} {path}")
    return r


class _FakeClient:
    def __init__(self, base_url="", timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, path, **kw):
        return _dispatch("GET", path)

    def post(self, path, json=None, **kw):
        CALLS.append(("BODY", json))
        return _dispatch("POST", path)


def _module_get(url, timeout=None):
    path = "/" + str(url).split("/", 3)[-1]
    return _dispatch("GET", path)


VP.httpx = types.SimpleNamespace(get=_module_get, Client=_FakeClient)

PROFILE = {"id": "prof1", "name": "POC Kokoro FR", "language": "fr",
           "voice_type": "preset", "preset_engine": "kokoro",
           "preset_voice_id": "ff_siwis",
           "default_engine": "kokoro", "description": "voix POC"}
CLONE = {"id": "prof2", "name": "Clone Oracle", "language": "fr",
         "voice_type": "cloned", "default_engine": "chatterbox",
         "personality": "vieil oracle grave"}


def test_builders():
    # catalogue : /profiles -> format casting (_fetch_11l_voices)
    cat = VP.map_voicebox_profiles([PROFILE, CLONE, {"name": "sans id"}])
    assert len(cat) == 2 and cat[0]["voice_id"] == "prof1"
    assert cat[0]["labels"]["language"] == "fr"
    assert cat[0]["labels"]["engine"] == "kokoro"
    assert cat[0]["category"] == "voicebox"
    # étape 3 — genre déduit du preset Kokoro (ff_siwis = french female)
    assert cat[0]["labels"]["gender"] == "female"
    assert cat[0]["labels"]["voice_preset"] == "ff_siwis"
    # clone: pas de preset -> pas de genre (le LLM infère du nom/description),
    # labels vides filtrés, personality conservée
    assert "gender" not in cat[1]["labels"]
    assert "description" not in cat[1]["labels"]
    assert cat[1]["labels"]["personality"] == "vieil oracle grave"
    assert VP._preset_gender("am_adam") == "male"
    assert VP._preset_gender(None) == ""
    # payload /generate : engine du PROFIL (jamais le défaut serveur qwen)
    p = VP.build_generate_payload(PROFILE, "Bonjour", "FR")
    assert p == {"profile_id": "prof1", "text": "Bonjour",
                 "language": "fr", "engine": "kokoro"}
    assert VP.build_generate_payload({"id": "x"}, "t", "")["engine"] == "kokoro"
    assert VP.build_generate_payload(
        {"id": "x", "default_engine": "chatterbox"}, "t", "fr-FR"
    ) == {"profile_id": "x", "text": "t", "language": "fr",
          "engine": "chatterbox"}


def test_resolution():
    ROUTES.clear()
    # voicebox joignable, pas de clé 11L -> défaut voicebox
    ROUTES[("GET", "/health")] = _Resp(200, {"status": "healthy"})
    settings.ELEVENLABS_API_KEY = ""
    assert VP.resolve_provider("") == "voicebox"
    # clé 11L présente -> défaut elevenlabs, mais le réglage voicebox gagne
    settings.ELEVENLABS_API_KEY = "k-test"
    assert VP.resolve_provider("") == "elevenlabs"
    assert VP.resolve_provider("voicebox") == "voicebox"
    # étape 4 — la détection est cachée (TTL): un /health tombé ne se voit
    # qu'après expiration ; on invalide à la main dans les tests.
    ROUTES[("GET", "/health")] = _Resp(500, {})
    assert VP.resolve_provider("voicebox") == "voicebox"      # cache encore chaud
    VP._reach_cache["t"] = 0
    # voicebox demandé mais injoignable -> repli elevenlabs
    assert VP.resolve_provider("voicebox") == "elevenlabs"
    # rien de disponible -> ""
    settings.ELEVENLABS_API_KEY = ""
    VP._reach_cache["t"] = 0
    assert VP.resolve_provider("") == ""
    # réglage atelier lu en sqlite sync (requested=None)
    c = sqlite3.connect(_db)
    c.execute("INSERT INTO atelier_settings VALUES ('voice_provider', 'voicebox')")
    c.commit()
    c.close()
    assert VP.configured_provider() == "voicebox"
    ROUTES[("GET", "/health")] = _Resp(200, {"status": "healthy"})
    VP._reach_cache["t"] = 0
    assert VP.resolve_provider() == "voicebox"
    # registre disponibilité (pour l'UI)
    ids = {p["id"]: p["ready"] for p in VP.available()}
    assert ids == {"elevenlabs": False, "voicebox": True}


def test_voicebox_tts():
    ROUTES.clear()
    CALLS.clear()
    wav = b"RIFF" + b"\x00" * 64
    ROUTES[("GET", "/profiles/prof1")] = _Resp(200, PROFILE)
    ROUTES[("POST", "/generate")] = _Resp(
        200, {"id": "g1", "status": "generating"})
    ROUTES[("GET", "/history/g1")] = [
        _Resp(200, {"id": "g1", "status": "loading_model"}),
        _Resp(200, {"id": "g1", "status": "generating"}),
        _Resp(200, {"id": "g1", "status": "completed", "error": None,
                    "duration": 1.2}),
    ]
    ROUTES[("GET", "/audio/g1")] = _Resp(200, None, wav)
    out = pathlib.Path(_tmp, "vo.wav")
    got = VP.voicebox_tts("Bonjour l'oracle", out, language="FR",
                          voice_id="prof1", poll_s=0)
    assert got == out and out.read_bytes() == wav
    body = next(c[1] for c in CALLS if c[0] == "BODY")
    assert body["engine"] == "kokoro" and body["language"] == "fr"
    assert body["profile_id"] == "prof1"

    # voice_id inconnu (id ElevenLabs hérité) -> repli profil de la langue,
    # en préférant Kokoro (un clone Chatterbox FR listé AVANT ne gagne pas)
    CALLS.clear()
    ROUTES[("GET", "/profiles/eleven-id")] = _Resp(404, {})
    ROUTES[("GET", "/profiles")] = _Resp(
        200, [{"id": "p-en", "name": "EN", "language": "en",
               "default_engine": "kokoro"},
              {"id": "p-clone", "name": "Clone FR", "language": "fr",
               "default_engine": "chatterbox"}, PROFILE])
    out2 = pathlib.Path(_tmp, "vo2.wav")
    ROUTES[("GET", "/history/g1")] = _Resp(
        200, {"id": "g1", "status": "completed", "error": None})
    VP.voicebox_tts("Bonjour", out2, language="FR", voice_id="eleven-id",
                    poll_s=0)
    body = next(c[1] for c in CALLS if c[0] == "BODY")
    assert body["profile_id"] == "prof1"      # FR + kokoro, pas p-en/p-clone

    # erreur moteur -> RuntimeError préfixée Voicebox (notifs provider)
    ROUTES[("POST", "/generate")] = _Resp(
        200, {"id": "g2", "status": "generating"})
    ROUTES[("GET", "/history/g2")] = _Resp(
        200, {"id": "g2", "status": "error", "error": "out of memory"})
    try:
        VP.voicebox_tts("Bonjour", pathlib.Path(_tmp, "vo3.wav"),
                        language="FR", voice_id="prof1", poll_s=0)
        raise AssertionError("une erreur Voicebox devait remonter")
    except RuntimeError as e:
        assert str(e).startswith("Voicebox:") and "out of memory" in str(e)


def test_service_routing():
    from app.services.elevenlabs_service import VoiceoverService
    seen = {}

    def _fake_tts(text, output_path, language="EN", voice_id=None, **kw):
        seen.update(text=text, path=output_path, language=language,
                    voice_id=voice_id)
        output_path.write_bytes(b"RIFF")
        return output_path

    orig_resolve, orig_tts = VP.resolve_provider, VP.voicebox_tts
    try:
        VP.resolve_provider = lambda *a, **k: "voicebox"
        VP.voicebox_tts = _fake_tts
        assert VoiceoverService.is_enabled() is True
        svc = VoiceoverService()
        out = pathlib.Path(_tmp, "routed.mp3")
        got = svc.generate(text="Salut", output_path=out, language="FR",
                           voice_id="prof1")
        assert got == out and seen["voice_id"] == "prof1"
        assert seen["language"] == "FR"
        # aucun provider -> service désactivé
        VP.resolve_provider = lambda *a, **k: ""
        assert VoiceoverService.is_enabled() is False
    finally:
        VP.resolve_provider, VP.voicebox_tts = orig_resolve, orig_tts


test_builders()
test_resolution()
test_voicebox_tts()
test_service_routing()
print("VOICE PROVIDERS TEST: PASS")
