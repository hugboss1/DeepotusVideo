"""Self-contained async test for the avatar-preset API.
Run: <embedded python> backend/tests/test_presets.py
Uses an isolated temp SQLite DB (DATABASE_URL env override) so it never
touches the real deepotus.db. Exits non-zero on failure."""
import asyncio, os, sys, tempfile, pathlib

# Isolate the DB BEFORE importing the app (engine is built at import time).
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport   # noqa: E402
from app.main import app                        # noqa: E402
from app.services.storage import init_db        # noqa: E402


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # empty
        r = await c.get("/api/heygen/presets")
        assert r.status_code == 200, r.text
        assert r.json()["presets"] == [], r.text

        # create
        body = {"name": "News Reel", "avatar_id": "av123",
                "avatar_type": "avatar", "avatar_img": "http://img/a.png",
                "voice_id": "Z32YLIMiuw7UvRLEbHqF",
                "voice_name": " xdynoMoney - Voice 1", "voice_prev": "http://a/p.mp3",
                "voice_lang": "English", "speed": 1.0}
        r = await c.post("/api/heygen/presets", json=body)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert pid and r.json()["name"] == "News Reel"

        # list has it
        r = await c.get("/api/heygen/presets")
        got = r.json()["presets"]
        assert len(got) == 1 and got[0]["id"] == pid
        assert got[0]["voice_id"] == "Z32YLIMiuw7UvRLEbHqF"

        # validation: missing avatar_id -> 422
        r = await c.post("/api/heygen/presets", json={"name": "x", "voice_id": "v"})
        assert r.status_code == 422, r.text

        # delete
        r = await c.delete(f"/api/heygen/presets/{pid}")
        assert r.status_code == 200 and r.json()["ok"] is True
        r = await c.get("/api/heygen/presets")
        assert r.json()["presets"] == []

        # delete missing -> 404
        r = await c.delete("/api/heygen/presets/nope")
        assert r.status_code == 404
    print("PRESETS TEST: PASS")

asyncio.run(main())
