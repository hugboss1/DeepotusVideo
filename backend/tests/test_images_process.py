"""Studio — nœuds de post-traitement image: POST /images/process.

Couvre: crop local (PIL), upscale simple (PIL), upscale ai (fal esrgan),
remove-bg api (fal rembg), remove-bg local sans rembg (400 clair),
edit via gpt-image (OpenAI edits), variations via kontext (fal),
pixel local 9b (PIL, palette preset), tile-preview 9b (métrique de raccord),
et les erreurs (fichier manquant, op inconnue, pixel invalide).
Run: <embedded python> backend/tests/test_images_process.py
"""
import asyncio
import base64
import io
import os
import pathlib
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-oa")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FAL_CALLS = []
HTTP_POSTS = []


async def _fake_subscribe(model, arguments=None, **kw):
    FAL_CALLS.append({"model": model, "arguments": arguments})
    return {"image": {"url": "http://fal.test/out.png"},
            "images": [{"url": "http://fal.test/out.png"}], "seed": 7}


async def _fake_upload(path):
    return "http://fal.test/up.png"

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub

from PIL import Image as _PILImage                        # noqa: E402
import httpx as _httpx                                    # noqa: E402
from httpx import AsyncClient, ASGITransport              # noqa: E402

_buf = io.BytesIO()
_PILImage.new("RGB", (400, 400), (10, 20, 30)).save(_buf, "PNG")
_PNG = _buf.getvalue()


class _FakeResp:
    status_code = 200
    content = _PNG
    text = ""

    def json(self):
        return {"data": [{"b64_json": base64.b64encode(_PNG).decode()}]}

    def raise_for_status(self):
        pass


class _FakeAsyncClient:
    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None, data=None,
                   files=None, **kw):
        HTTP_POSTS.append({"url": url, "json": json, "data": data,
                           "files": bool(files)})
        return _FakeResp()

    async def get(self, url, **kw):
        return _FakeResp()

_httpx.AsyncClient = _FakeAsyncClient

from app.main import app                                  # noqa: E402
from app.config import settings as _settings              # noqa: E402
from app.services.storage import init_db                  # noqa: E402
from app.services import fal_service as _fs               # noqa: E402
from app.services import image_providers as _ip           # noqa: E402

_fs.FalSeedanceClient.upload_image = staticmethod(_fake_upload)
_ip.httpx.AsyncClient = _FakeAsyncClient

SRC = "src_test.png"
_PILImage.new("RGB", (400, 400), (60, 10, 90)).save(
    pathlib.Path(_settings.images_path) / SRC, "PNG")


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport,
                           base_url="http://t") as client:
        # crop 9:16 — local PIL, dimensions exactes
        r = await client.post("/api/images/process",
                              json={"op": "crop", "filename": SRC,
                                    "ratio": "9:16"})
        assert r.status_code == 200, r.text
        out = r.json()["images"][0]
        w, h = _PILImage.open(
            pathlib.Path(_settings.images_path) / out).size
        assert abs(w / h - 9 / 16) < 0.01, (w, h)

        # upscale simple — x2 local
        r = await client.post("/api/images/process",
                              json={"op": "upscale", "filename": SRC,
                                    "mode": "simple", "scale": 2})
        assert r.status_code == 200, r.text
        out = r.json()["images"][0]
        assert _PILImage.open(
            pathlib.Path(_settings.images_path) / out).size == (800, 800)

        # upscale ai — fal esrgan appelé
        r = await client.post("/api/images/process",
                              json={"op": "upscale", "filename": SRC,
                                    "mode": "ai", "scale": 2})
        assert r.status_code == 200, r.text
        assert FAL_CALLS[-1]["model"] == "fal-ai/esrgan", FAL_CALLS[-1]

        # remove-bg api — fal rembg appelé
        r = await client.post("/api/images/process",
                              json={"op": "remove-bg", "filename": SRC,
                                    "method": "api"})
        assert r.status_code == 200, r.text
        assert FAL_CALLS[-1]["model"] == "fal-ai/imageutils/rembg"

        # remove-bg local sans rembg installé — 400 explicite
        r = await client.post("/api/images/process",
                              json={"op": "remove-bg", "filename": SRC,
                                    "method": "local"})
        assert r.status_code == 400 and "rembg" in r.text, r.text

        # edit via gpt-image — endpoint /edits OpenAI en multipart
        r = await client.post("/api/images/process",
                              json={"op": "edit", "filename": SRC,
                                    "prompt": "make it golden",
                                    "model": "gpt-image-2"})
        assert r.status_code == 200, r.text
        assert HTTP_POSTS and "images/edits" in HTTP_POSTS[-1]["url"]
        assert HTTP_POSTS[-1]["files"] is True

        # variations sans modèle — FLUX Kontext par défaut, n=3
        r = await client.post("/api/images/process",
                              json={"op": "variations", "filename": SRC})
        assert r.status_code == 200, r.text
        assert FAL_CALLS[-1]["model"] == "fal-ai/flux-kontext/dev"
        assert FAL_CALLS[-1]["arguments"]["num_images"] == 3

        # pixel (9b) — local PIL : 400x400, target 32, scale 2 -> 64x64,
        # palette gameboy respectée
        r = await client.post("/api/images/process",
                              json={"op": "pixel", "filename": SRC,
                                    "target_px": 32, "palette": "gameboy",
                                    "scale": 2})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["pixel"]["palette"] == "gameboy"
        out = j["images"][0]
        with _PILImage.open(pathlib.Path(_settings.images_path) / out) as im:
            assert im.size == (64, 64)
            from app.services.pixel_ops import PALETTES
            got = {(p[0], p[1], p[2]) for p in im.convert("RGBA").getdata()
                   if p[3] >= 128}
            assert got <= set(PALETTES["gameboy"]), sorted(got)[:4]

        # tile-preview (9b) — composite 2x2 + métrique de raccord
        r = await client.post("/api/images/process",
                              json={"op": "tile-preview", "filename": SRC,
                                    "grid": 2})
        assert r.status_code == 200, r.text
        j = r.json()
        assert 0 <= j["seam_score"] <= 100
        out = j["images"][0]
        with _PILImage.open(pathlib.Path(_settings.images_path) / out) as im:
            assert im.size == (800, 800)   # 2x2 de 400x400

        # erreurs: fichier absent / op inconnue / pixel invalide
        r = await client.post("/api/images/process",
                              json={"op": "crop", "filename": "nope.png"})
        assert r.status_code == 400, r.text
        r = await client.post("/api/images/process",
                              json={"op": "blur", "filename": SRC})
        assert r.status_code == 400, r.text
        r = await client.post("/api/images/process",
                              json={"op": "pixel", "filename": SRC,
                                    "palette": "vga"})
        assert r.status_code == 400, r.text

        # /image-models expose nano-banana quand FAL_KEY est là
        r = await client.get("/api/image-models")
        ids = [m["id"] for m in r.json()["models"]]
        assert "nano-banana" in ids, ids

    print("OK — images/process: crop, upscale (simple/ai), remove-bg "
          "(api/local-400), edit gpt, variations kontext, pixel 9b, "
          "tile-preview 9b, erreurs, nano-banana liste")

asyncio.run(main())
