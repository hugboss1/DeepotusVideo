"""HeyGen v3 animate-image + cinematic (D): body builders + API validation.
No live HeyGen call. Run: <embedded python> backend/tests/test_animate_v3.py"""
import asyncio, os, sys, tempfile, pathlib

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport            # noqa: E402
from app.main import app                                 # noqa: E402
from app.services.storage import init_db                 # noqa: E402
from app.services.heygen_service import HeyGenClient     # noqa: E402
from app.config import settings                          # noqa: E402

# a tiny real png (1x1) so base64 read works
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fea75481840000000049454e44ae426082")
_img = pathlib.Path(_tmp) / "still.png"
_img.write_bytes(PNG)


def test_image_body():
    b = HeyGenClient.build_v3_image_body(
        _img, "Hello world", "vc1", engine="avatar_iv",
        aspect_ratio="9:16", speed=1.9, motion_prompt="slow head turn",
        expressiveness="medium")
    assert b["type"] == "image"
    assert b["image"]["type"] == "base64"
    assert b["image"]["media_type"] == "image/png" and b["image"]["data"]
    assert b["engine"] == {"type": "avatar_iv"}
    assert b["voice_settings"]["speed"] == 1.5          # clamped
    assert b["motion_prompt"] == "slow head turn"
    assert b["expressiveness"] == "medium"
    assert "background" not in b                        # image IS the frame

    bv = HeyGenClient.build_v3_image_body(_img, "Hi", "v", engine="avatar_v",
                                          expressiveness="high")
    assert "expressiveness" not in bv                   # IV-only


def test_cinematic_body():
    b = HeyGenClient.build_v3_cinematic_body(
        "An octopus prophet rises from the abyss", ["look1", "look2"],
        reference_paths=[_img], duration_s=30, aspect_ratio="9:16",
        resolution="1080p")
    assert b["type"] == "cinematic_avatar"
    assert b["avatar_id"] == ["look1", "look2"]
    assert b["duration"] == 15                          # clamped 4..15
    assert len(b["references"]) == 1
    assert b["enhance_prompt"] is True

    ba = HeyGenClient.build_v3_cinematic_body("p", ["l1"], auto_duration=True)
    assert ba.get("auto_duration") is True and "duration" not in ba
    b4 = HeyGenClient.build_v3_cinematic_body("p", ["a", "b", "c", "d"])
    assert len(b4["avatar_id"]) == 3                    # capped at 3


async def test_endpoints_validate():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # missing image -> 404 (has_heygen must be true for this env)
        r = await c.post("/api/generate/heygen-image", json={
            "image_filename": "nope.png", "script": "s", "voice_id": "v"})
        assert r.status_code in (400, 404), r.text
        # cinematic: bad look count -> 422
        r = await c.post("/api/generate/heygen-cinematic", json={
            "prompt": "p", "look_ids": []})
        assert r.status_code == 422, r.text
        # cinematic: missing reference -> 404/400
        r = await c.post("/api/generate/heygen-cinematic", json={
            "prompt": "p", "look_ids": ["l1"], "reference_images": ["ghost.png"]})
        assert r.status_code in (400, 404), r.text


test_image_body()
test_cinematic_body()
asyncio.run(test_endpoints_validate())
print("ANIMATE V3 TEST: PASS")
