"""Étape 3 (spec voicebox 2026-07-11) — casting voix sur catalogue Voicebox.
Recette: suggest-voice retourne une voix Voicebox sur un personnage, clé
ElevenLabs absente. Voicebox et LLM stubés (aucun réseau).
Run: <embedded python -X utf8> backend/tests/test_casting_voicebox.py"""
import asyncio
import json
import os
import pathlib
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.config import settings                       # noqa: E402
# le .env du data-dir a priorité sur l'environnement -> forcer sur l'objet
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.ELEVENLABS_API_KEY = ""                      # 11L débranché
settings.VOICEBOX_URL = ""

from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import voice_providers as VP        # noqa: E402
from app.services import summarizer as SUMZ           # noqa: E402

# ── profils Voicebox (schéma live v0.5.0 relevé le 2026-07-12) ──
PROFILES = [
    {"id": "vb-clone", "name": "POC Clone FR (Chatterbox)", "description": None,
     "language": "fr", "voice_type": "cloned", "preset_engine": None,
     "preset_voice_id": None, "default_engine": "chatterbox",
     "personality": None},
    {"id": "vb-kokoro", "name": "POC Kokoro FR", "description": None,
     "language": "fr", "voice_type": "preset", "preset_engine": "kokoro",
     "preset_voice_id": "ff_siwis", "default_engine": "kokoro",
     "personality": None},
]


class _Resp:
    def __init__(self, status=200, jobj=None):
        self.status_code = status
        self._j = jobj

    def json(self):
        return self._j

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _fake_get(url, timeout=None):
    u = str(url)
    if u.endswith("/health"):
        return _Resp(200, {"status": "healthy"})
    if u.endswith("/profiles"):
        return _Resp(200, PROFILES)
    raise ConnectionError(f"stub: {u}")


VP.httpx = types.SimpleNamespace(get=_fake_get)

SEEN = {}


def _fake_chat(prompt, system, max_tokens):
    SEEN["prompt"] = prompt
    return ('{"best": "vb-kokoro", "alternates": ["vb-clone"], '
            '"why": "Voix féminine française, assortie à l\'oracle."}',
            "stub")


SUMZ.available = lambda: True
SUMZ._chat_dispatch = _fake_chat


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # provider résolu = voicebox (pas de clé 11L, /health stub OK)
        r = await c.get("/api/voice/providers")
        assert r.status_code == 200 and r.json()["resolved"] == "voicebox", r.text

        # GET /voices (picker Épisodes/VO) suit le provider
        r = await c.get("/api/voices")
        d = r.json()
        assert d["enabled"] is True and d["provider"] == "voicebox", d
        assert {v["voice_id"] for v in d["voices"]} == {"vb-clone", "vb-kokoro"}
        assert all(v["language"] == "fr" for v in d["voices"]), d["voices"]

        # ── RECETTE étape 3 : suggest-voice retourne une voix Voicebox ──
        r = await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Le Prophète",
            "description": "vieil oracle poulpe des abysses, voix posée"})
        eid = r.json()["id"]
        r = await c.post(f"/api/bible/entities/{eid}/suggest-voice", json={})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["suggested"]["voice_id"] == "vb-kokoro"
        assert d["suggested"]["category"] == "voicebox"
        assert d["suggested"]["labels"]["gender"] == "female"   # via ff_siwis
        assert d["entity"]["voice_id"] == "vb-kokoro"
        assert d["entity"]["voice_name"] == "POC Kokoro FR"
        assert [a["voice_id"] for a in d["alternates"]] == ["vb-clone"]
        # le prompt du casting annonce le provider et les labels pauvres
        assert "provider 'voicebox'" in SEEN["prompt"]
        assert "sparse" in SEEN["prompt"] and "vb-kokoro" in SEEN["prompt"]

        # aucun provider (voicebox coupé) -> 400 explicite, pas un 500
        VP.httpx = types.SimpleNamespace(
            get=lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down")))
        VP._reach_cache["t"] = 0        # invalider le cache de détection
        r = await c.post(f"/api/bible/entities/{eid}/suggest-voice", json={})
        assert r.status_code == 400, r.text
        r = await c.get("/api/voices")
        assert r.json() == {"voices": [], "enabled": False}
    print("CASTING VOICEBOX TEST: PASS")


asyncio.run(main())
