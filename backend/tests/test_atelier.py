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


async def _fake_upload(path):
    return "http://fal.test/uploaded-ref.png"

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
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

        # v1.20 — la planche personnage: turnaround multi-vues + gros plans,
        # grille stricte, modèle DEV (adhérence layout) car pas d'inspiration
        # existante sur disque
        p = CALLS[-1]["arguments"]["prompt"].lower()
        assert "model sheet" in p and "turnaround" in p
        assert "exactly four full-body views" in p and "back view" in p
        assert "exactly three head-and-" in p
        assert "shared ground line" in p and "no overlapping" in p
        assert CALLS[-1]["arguments"]["image_size"] == "landscape_16_9"
        assert CALLS[-1]["model"] == "fal-ai/flux/dev"

        # re-roll without seed -> a seed still comes back (from fal result)
        r = await c.post(f"/api/bible/entities/{eid}/generate", json={})
        assert r.json()["seed"] == 424242
        # entity persisted the new ref + the exact recipe
        r = await c.get("/api/bible/entities?kind=character")
        got0 = r.json()["entities"][0]
        assert got0["ref_image"], "ref not stored"
        assert got0["has_recipe"] is True

        # v1.20 — 🔁 use_recipe rejoue EXACTEMENT le même prompt + seed + modèle
        last_prompt = CALLS[-1]["arguments"]["prompt"]
        r = await c.post(f"/api/bible/entities/{eid}/generate",
                         json={"use_recipe": True})
        assert r.status_code == 200, r.text
        assert CALLS[-1]["arguments"]["prompt"] == last_prompt
        assert CALLS[-1]["arguments"]["seed"] == 424242
        assert CALLS[-1]["model"] == "fal-ai/flux/dev"
        assert r.json()["seed"] == 424242

        # v1.20 — image d'inspiration PRÉSENTE sur disque → Kontext
        # (génération conditionnée: l'identité de la référence est préservée)
        import pathlib as _pl
        img_dir = _pl.Path(os.environ["IMAGES_FOLDER"])
        (img_dir / "elias-card.png").write_bytes(b"\x89PNG_fake")
        r = await c.put(f"/api/bible/entities/{eid}",
                        json={"inspiration_images": ["elias-card.png"]})
        assert r.status_code == 200
        r = await c.post(f"/api/bible/entities/{eid}/generate", json={"seed": 9})
        assert r.status_code == 200, r.text
        assert CALLS[-1]["model"] == "fal-ai/flux-kontext/dev"
        assert CALLS[-1]["arguments"]["image_url"] == "http://fal.test/uploaded-ref.png"
        assert "image_size" not in CALLS[-1]["arguments"]  # kontext cadre sur la réf
        assert "same subject, face and design" in CALLS[-1]["arguments"]["prompt"].lower().replace("exact ", "")
        # la recette mémorise le modèle + le fichier de référence
        r = await c.post(f"/api/bible/entities/{eid}/generate",
                         json={"use_recipe": True})
        assert CALLS[-1]["model"] == "fal-ai/flux-kontext/dev"
        assert CALLS[-1]["arguments"]["seed"] == 9

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
