"""Atelier P1: bible entities + chapters CRUD, reference generation with seed,
and the /images/generate FLUX seed passthrough. No live fal call (stubbed).
Run: <embedded python> backend/tests/test_atelier.py"""
import asyncio, json, os, sys, tempfile, pathlib, types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")          # FLUX path must be open
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub fal_client BEFORE the app imports it (routes import it lazily inside
# the handler, so a sys.modules stub is picked up at call time).
CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}],
            "seed": arguments.get("seed", 424242)}

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub

from httpx import AsyncClient, ASGITransport          # noqa: E402
import httpx as _httpx                                 # noqa: E402
from app.main import app                               # noqa: E402
from app.services.storage import init_db               # noqa: E402

# The FLUX path downloads each returned URL via httpx — stub the download.
_orig_get = _httpx.AsyncClient.get
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fea75481840000000049454e44ae426082")


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        req = _httpx.Request("GET", str(url))
        return _httpx.Response(200, content=PNG, request=req)
    return await _orig_get(self, url, *a, **kw)

_httpx.AsyncClient.get = _fake_get


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # ---- bible entities CRUD ----
        r = await c.get("/api/bible/entities")
        assert r.status_code == 200 and r.json()["entities"] == [], r.text

        r = await c.post("/api/bible/entities", json={
            "kind": "character", "name": "Le Prophète",
            "description": "vieil oracle poulpe, yeux dorés",
            "style_notes": "style anime sombre, palette abyssale"})
        assert r.status_code == 200, r.text
        ent = r.json(); eid = ent["id"]
        assert ent["kind"] == "character" and ent["seed"] is None

        r = await c.post("/api/bible/entities", json={
            "kind": "place", "name": "Caverne", "description": "caverne abyssale"})
        pid = r.json()["id"]

        r = await c.get("/api/bible/entities?kind=character")
        got = r.json()["entities"]
        assert len(got) == 1 and got[0]["name"] == "Le Prophète", got

        r = await c.put(f"/api/bible/entities/{eid}", json={
            "description": "vieil oracle poulpe, cicatrice au front",
            "inspiration_images": ["insp1.png"]})
        assert r.status_code == 200 and "cicatrice" in r.json()["description"]
        assert r.json()["inspiration_images"] == ["insp1.png"]

        # v1.17.1 — direct ref_image/seed re-link (recovery + manual pinning)
        r = await c.put(f"/api/bible/entities/{eid}",
                        json={"ref_image": "manual.png", "seed": 99})
        assert r.json()["ref_image"] == "manual.png" and r.json()["seed"] == 99

        # ---- reference generation (stubbed FLUX) with seed passthrough ----
        r = await c.post(f"/api/bible/entities/{eid}/generate", json={"seed": 777})
        assert r.status_code == 200, r.text
        g = r.json()
        assert g["seed"] == 777 and g["ref_image"], g
        assert CALLS and CALLS[-1]["arguments"].get("seed") == 777
        assert "oracle poulpe" in CALLS[-1]["arguments"]["prompt"]
        assert "abyssale" in CALLS[-1]["arguments"]["prompt"]  # style_notes in prompt

        # re-roll without seed -> a seed still comes back (from fal result)
        r = await c.post(f"/api/bible/entities/{eid}/generate", json={})
        assert r.json()["seed"] == 424242
        # entity persisted the new ref
        r = await c.get("/api/bible/entities?kind=character")
        assert r.json()["entities"][0]["ref_image"], "ref not stored"

        # ---- /images/generate seed passthrough (FLUX branch) ----
        r = await c.post("/api/images/generate", json={
            "prompt": "test still", "n": 1, "seed": 1234})
        assert r.status_code == 200, r.text
        assert r.json().get("seed") == 1234, r.json()
        assert CALLS[-1]["arguments"].get("seed") == 1234

        # ---- chapters CRUD + spans round-trip ----
        spans = [{"start": 10, "end": 21, "text": "Le Prophète", "entity_id": eid}]
        r = await c.post("/api/chapters", json={
            "title": "Chapitre 1", "series": "Lost Abyss",
            "script_text": "Au fond,   Le Prophète s'éveille dans la caverne.",
            "spans": spans})
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        r = await c.get(f"/api/chapters/{cid}")
        ch = r.json()
        assert ch["title"] == "Chapitre 1" and ch["spans"] == spans, ch
        r = await c.get("/api/chapters")
        assert any(x["id"] == cid for x in r.json()["chapters"])
        r = await c.put(f"/api/chapters/{cid}", json={"title": "Chapitre 1 — l'éveil"})
        assert "éveil" in r.json()["title"]
        r = await c.delete(f"/api/chapters/{cid}")
        assert r.json()["ok"] is True

        # cleanup entity delete
        r = await c.delete(f"/api/bible/entities/{pid}")
        assert r.json()["ok"] is True
    print("ATELIER P1 TEST: PASS")

asyncio.run(main())
