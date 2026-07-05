"""HeyGen v3 engine choice (C): request-body builder + preset engine round-trip.
No live HeyGen call. Run: <embedded python> backend/tests/test_engine_v3.py"""
import asyncio, os, sys, tempfile, pathlib

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport            # noqa: E402
from app.main import app                                 # noqa: E402
from app.services.storage import init_db                 # noqa: E402
from app.services.heygen_service import HeyGenClient     # noqa: E402
from app.models.schemas import GenerateHeyGenRequest     # noqa: E402


def test_v3_body_builder():
    b = HeyGenClient.build_v3_avatar_body(
        "Hello", "av1", "vc1", engine="avatar_v",
        aspect_ratio="9:16", speed=2.0, background_color="#101010",
        motion_prompt="wave hands", expressiveness="high")
    assert b["type"] == "avatar" and b["engine"] == {"type": "avatar_v"}
    assert b["aspect_ratio"] == "9:16" and b["resolution"] == "1080p"
    assert b["voice_settings"]["speed"] == 1.5          # clamped from 2.0
    assert b["background"] == {"type": "color", "value": "#101010"}
    assert b["motion_prompt"] == "wave hands"           # allowed on avatar_v
    assert "expressiveness" not in b                    # IV-only, engine is V

    b4 = HeyGenClient.build_v3_avatar_body(
        "Hi", "av1", "vc1", engine="avatar_iv", expressiveness="low")
    assert b4["expressiveness"] == "low"

    b3 = HeyGenClient.build_v3_avatar_body(
        "Hi", "av1", "vc1", engine="avatar_iii", motion_prompt="nope")
    assert "motion_prompt" not in b3                    # III has no motion

    # schema accepts engine values + rejects junk
    GenerateHeyGenRequest(avatar_id="a", voice_id="v", script="s",
                          engine="avatar_iv", expressiveness="high")
    try:
        GenerateHeyGenRequest(avatar_id="a", voice_id="v", script="s",
                              engine="avatar_ix")
        raise AssertionError("invalid engine accepted")
    except ValueError:
        pass


async def test_preset_engine_roundtrip():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        body = {"name": "V max", "avatar_id": "av1", "voice_id": "vc1",
                "engine": "avatar_v"}
        r = await c.post("/api/heygen/presets", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["engine"] == "avatar_v"
        pid = r.json()["id"]

        r = await c.get("/api/heygen/presets")
        got = r.json()["presets"][0]
        assert got["engine"] == "avatar_v"

        # empty engine stays empty-string in API (legacy pipeline)
        r = await c.post("/api/heygen/presets",
                         json={"name": "legacy", "avatar_id": "a", "voice_id": "v"})
        assert r.json()["engine"] == ""

        await c.delete(f"/api/heygen/presets/{pid}")


test_v3_body_builder()
asyncio.run(test_preset_engine_roundtrip())
print("ENGINE V3 TEST: PASS")
