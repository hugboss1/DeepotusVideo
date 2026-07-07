"""Atelier DA — direction artistique: builders providers, proposition de
styles par l'agent, planches via provider alternatif, référence de style.
Run: <embedded python> backend/tests/test_style_da.py"""
import asyncio, io, json, os, sys, tempfile, pathlib, types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-oa")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}],
            "seed": (arguments or {}).get("seed", 111)}


async def _fake_upload(path):
    return "http://fal.test/up.png"

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub

from httpx import AsyncClient, ASGITransport            # noqa: E402
import httpx as _httpx                                    # noqa: E402
from PIL import Image as _PILImage                        # noqa: E402
from app.main import app                                  # noqa: E402
from app.services.storage import init_db                  # noqa: E402
from app.services import image_providers as IP            # noqa: E402
from app.services import summarizer as SUMZ                # noqa: E402

_buf = io.BytesIO()
_PILImage.new("RGB", (8, 8), (40, 40, 80)).save(_buf, "PNG")
PNG = _buf.getvalue()
_orig_get = _httpx.AsyncClient.get


async def _fake_get(self, url, *a, **kw):
    if str(url).startswith("http://fal.test/"):
        return _httpx.Response(200, content=PNG,
                               request=_httpx.Request("GET", str(url)))
    return await _orig_get(self, url, *a, **kw)

_httpx.AsyncClient.get = _fake_get


def test_builders():
    # OpenAI: generations vs edits
    url, p = IP.build_openai_request("gpt-image-2", "un chat", "portrait_16_9",
                                     1, has_image=False)
    assert url.endswith("/images/generations") and p["size"] == "1024x1536"
    url, p = IP.build_openai_request("gpt-image-2", "un chat", "landscape_16_9",
                                     1, has_image=True)
    assert url.endswith("/images/edits") and p["size"] == "1536x1024"
    # Nano Banana: t2i (aspect) vs edit (image_urls)
    m, a = IP.build_banana_request("un chat", "portrait_16_9", 1, None)
    assert m == "fal-ai/nano-banana" and a["aspect_ratio"] == "9:16"
    m, a = IP.build_banana_request("un chat", "square", 1, "http://x/y.png")
    assert m == "fal-ai/nano-banana/edit" and a["image_urls"] == ["http://x/y.png"]
    # registre selon les clés (FAL + OPENAI posées)
    ids = {p["id"] for p in IP.available()}
    assert {"flux", "gpt-image-2", "nano-banana"} <= ids
    assert next(p for p in IP.available() if p["id"] == "flux")["seeds"] is True
    assert next(p for p in IP.available() if p["id"] == "nano-banana")["seeds"] is False


PROPOSALS = json.dumps([
    {"label": "Anticipation froide", "style_prompt": "cold retro-futuristic "
     "cinematic style, desaturated steel palette, volumetric fog",
     "rationale": "La pluie d'acier et la ville-machine du chapitre 1."},
    {"label": "Encre abyssale", "style_prompt": "inked noir illustration, "
     "deep blacks", "rationale": "Le ton noir du récit."},
    {"label": "BD moderne", "style_prompt": "modern euro comic art",
     "rationale": "Le rythme séquentiel."},
    {"label": "Photo-réalisme", "style_prompt": "photorealistic film still",
     "rationale": "Les détails concrets du texte."},
])


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # ── proposition de DA par l'agent (persistée) ──
        await c.post("/api/chapters", json={
            "title": "C1", "script_text": "Sous la pluie d'acier, la ville-machine "
            "respire. " * 20})
        SUMZ.available = lambda: True
        SUMZ._chat_dispatch = lambda p, s, m: (PROPOSALS, "stub")
        r = await c.post("/api/atelier/style/propose", json={})
        assert r.status_code == 200, r.text
        assert len(r.json()["proposals"]) == 4
        assert r.json()["proposals"][0]["label"] == "Anticipation froide"
        st = (await c.get("/api/atelier/settings")).json()["settings"]
        assert "Anticipation froide" in st["style_proposals"]

        # ── providers endpoint ──
        r = await c.get("/api/atelier/providers")
        assert any(p["id"] == "nano-banana" for p in r.json()["providers"])

        # ── planches via Nano Banana (t2i maître + edit chaînés, sans seed) ──
        await c.put("/api/atelier/settings",
                    json={"image_provider": "nano-banana", "global_style": ""})
        ent = (await c.post("/api/bible/entities", json={
            "kind": "place", "name": "La Caverne",
            "description": "caverne abyssale"})).json()
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{ent['id']}/generate", json={})
        assert r.status_code == 200, r.text
        assert len(CALLS) == 3
        assert CALLS[0]["model"] == "fal-ai/nano-banana"
        assert CALLS[0]["arguments"]["aspect_ratio"] == "16:9"
        for call in CALLS[1:]:
            assert call["model"] == "fal-ai/nano-banana/edit"
            assert call["arguments"]["image_urls"] == ["http://fal.test/up.png"]
        assert r.json()["ref_image"].startswith("board_")
        # la recette fige le provider → 🔁 rejoue en nano-banana
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{ent['id']}/generate",
                         json={"use_recipe": True})
        assert r.status_code == 200
        assert CALLS[0]["model"] == "fal-ai/nano-banana"

        # ── référence de STYLE (flux, entité sans identité propre) ──
        (pathlib.Path(_tmp, "images") / "style-bd.png").write_bytes(PNG)
        await c.put("/api/atelier/settings",
                    json={"image_provider": "flux",
                          "style_ref_image": "style-bd.png"})
        ent2 = (await c.post("/api/bible/entities", json={
            "kind": "decor", "name": "Mobilier", "description": "mobilier froid"})).json()
        CALLS.clear()
        r = await c.post(f"/api/bible/entities/{ent2['id']}/generate", json={})
        assert r.status_code == 200, r.text
        assert CALLS[0]["model"] == "fal-ai/flux-kontext/dev"   # conditionné
        assert "ART STYLE of the reference image" in CALLS[0]["arguments"]["prompt"]
    print("STYLE DA TEST: PASS")


test_builders()
asyncio.run(main())
