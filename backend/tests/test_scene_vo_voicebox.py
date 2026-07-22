"""Étape 4 (spec voicebox 2026-07-11) — VO par scène de bout en bout sur le
provider voicebox, clé ElevenLabs ABSENTE. Le routage generate_long→generate→
voicebox_tts est réel ; seul l'appel HTTP TTS est stubé (aucun réseau).
Vérifie aussi les portes provider-aware: /health, /episodes/render, /audio/voiceover.
Run: <embedded python -X utf8> backend/tests/test_scene_vo_voicebox.py"""
import asyncio
import os
import pathlib
import shutil
import sys
import tempfile
import types
from datetime import datetime
from uuid import uuid4

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.ELEVENLABS_API_KEY = ""                      # 11L débranché
settings.VOICEBOX_URL = ""

from app.main import app                              # noqa: E402
from app.services.storage import init_db, Scene, async_session_factory  # noqa: E402
from app.services import voice_providers as VP        # noqa: E402
import app.api.routes as RT                           # noqa: E402

# ── stub Voicebox : /health + /profiles + TTS (voicebox_tts intact,
#    seul son client HTTP est faux) ──
PROFILES = [
    {"id": "vb-kokoro", "name": "POC Kokoro FR", "language": "fr",
     "voice_type": "preset", "preset_engine": "kokoro",
     "preset_voice_id": "ff_siwis", "default_engine": "kokoro"},
    {"id": "vb-clone", "name": "POC Clone FR", "language": "fr",
     "voice_type": "cloned", "default_engine": "chatterbox"},
]
TTS = []


class _Resp:
    def __init__(self, status=200, jobj=None, content=b""):
        self.status_code, self._j, self.content = status, jobj, content
        self.text = ""

    def json(self):
        return self._j

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _route(method, path, body=None):
    if path.endswith("/health"):
        return _Resp(200, {"status": "healthy"})
    if path.endswith("/profiles"):
        return _Resp(200, PROFILES)
    for p in PROFILES:
        if path.endswith(f"/profiles/{p['id']}"):
            return _Resp(200, p)
    if path.endswith("/generate"):
        TTS.append(body)
        return _Resp(200, {"id": f"g{len(TTS)}", "status": "completed",
                           "error": None})
    if "/audio/" in path:
        return _Resp(200, None, b"WAVDATA")
    return _Resp(404, {})


class _FakeClient:
    def __init__(self, base_url="", timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, path, **kw):
        return _route("GET", path)

    def post(self, path, json=None, **kw):
        return _route("POST", path, json)


VP.httpx = types.SimpleNamespace(
    get=lambda url, timeout=None: _route("GET", str(url)),
    Client=_FakeClient)
VP._reach_cache["t"] = 0
# wav→mp3 : pas de ffmpeg dans ce test
VP.subprocess = types.SimpleNamespace(run=lambda cmd, **kw: shutil.copy2(
    next(a for a in cmd if a.endswith(".wav")), cmd[-1]))
RT._concat_audio = lambda paths, dest: shutil.copy2(paths[0], dest)
RT._audio_duration = lambda p: 4.2

FOUNTAIN = """La marée monte sur les quais.

LE PROPHETE
Depuis longtemps, veilleur.

Il disparaît dans l'écume."""


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://t") as c:
        # /health annonce la voix dispo SANS clé 11L (porte provider-aware)
        r = await c.get("/api/health")
        assert r.json()["voiceover_enabled"] is True, r.json()

        # bible : Narrateur → profil Kokoro, Prophète → clone Chatterbox
        nar = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Narrateur"})).json()
        await c.put(f"/api/bible/entities/{nar['id']}",
                    json={"voice_id": "vb-kokoro", "voice_name": "POC Kokoro FR"})
        pro = (await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Le Prophète"})).json()
        await c.put(f"/api/bible/entities/{pro['id']}",
                    json={"voice_id": "vb-clone", "voice_name": "POC Clone FR"})

        ch = (await c.post("/api/chapters", json={"title": "C1"})).json()
        sid = str(uuid4())
        async with async_session_factory() as session:
            session.add(Scene(id=sid, chapter_id=ch["id"], idx=0,
                              slugline="EXT. QUAI - NUIT",
                              fountain_text=FOUNTAIN,
                              created_at=datetime.utcnow(),
                              updated_at=datetime.utcnow()))
            await session.commit()

        # ── RECETTE étape 4 (mécanique) : VO de scène 100 % voicebox ──
        r = await c.post(f"/api/scenes/{sid}/voiceover", json={"language": "fr"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["scene"]["vo_audio"].startswith("vo_")
        assert d["duration_s"] == 4.2
        # 3 segments : narration (kokoro), réplique (chatterbox), narration
        assert [t["profile_id"] for t in TTS] == \
            ["vb-kokoro", "vb-clone", "vb-kokoro"], TTS
        assert [t["engine"] for t in TTS] == \
            ["kokoro", "chatterbox", "kokoro"]
        assert all(t["language"] == "fr" for t in TTS)
        audio_dir = pathlib.Path(os.environ["IMAGES_FOLDER"]).parent / "audio"
        assert (audio_dir / d["scene"]["vo_audio"]).is_file()

        # /audio/voiceover (Quick, voix off seule) passe aussi
        r = await c.post("/api/audio/voiceover",
                         json={"script": "La ville dort.", "language": "fr"})
        assert r.status_code == 200 and r.json()["ok"] is True, r.text

        # voicebox coupé + pas de clé -> portes fermées avec le bon message
        VP.httpx = types.SimpleNamespace(
            get=lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down")),
            Client=_FakeClient)
        VP._reach_cache["t"] = 0
        r = await c.post(f"/api/scenes/{sid}/voiceover", json={"language": "fr"})
        assert r.status_code == 400 and "Voicebox" in r.json()["detail"], r.text
        # /episodes/render : porte provider-aware (plus settings.has_voiceover)
        r = await c.post("/api/episodes/render",
                         json={"scenes": [{"text": "La ville dort."}]})
        assert r.status_code == 400 and "Voicebox" in r.json()["detail"], r.text
        r = await c.get("/api/health")
        assert r.json()["voiceover_enabled"] is False
    print("SCENE VO VOICEBOX TEST: PASS")


asyncio.run(main())
