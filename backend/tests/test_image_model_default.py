"""Scheduler — défaut global du générateur d'image (image_model_default).

Non-régression du bug « l'agent de planning ignore le dropdown Image
generator » : un appel /images/generate SANS modèle explicite (agents,
scripts) doit utiliser le défaut persisté dans atelier_settings, pas
retomber en dur sur FLUX.
Run: <embedded python> backend/tests/test_image_model_default.py
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
OPENAI_CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    FAL_CALLS.append({"model": model, "arguments": arguments})
    return {"images": [{"url": "http://fal.test/img.png"}], "seed": 42}

_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
sys.modules["fal_client"] = _stub

from PIL import Image as _PILImage                        # noqa: E402
import httpx as _httpx                                    # noqa: E402
from httpx import AsyncClient, ASGITransport              # noqa: E402

_buf = io.BytesIO()
_PILImage.new("RGB", (8, 8), (10, 20, 30)).save(_buf, "PNG")
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
    """Intercepte les appels réseau sortants (OpenAI + téléchargement fal)."""

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None, **kw):
        OPENAI_CALLS.append({"url": url, "json": json})
        return _FakeResp()

    async def get(self, url, **kw):
        return _FakeResp()

_RealAsyncClient = _httpx.AsyncClient
_httpx.AsyncClient = _FakeAsyncClient

from app.main import app                                  # noqa: E402
from app.services.storage import init_db                  # noqa: E402


async def main():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport,
                           base_url="http://t") as client:
        # 1) Sans modèle NI défaut sauvegardé -> fallback FLUX (fal).
        r = await client.post("/api/images/generate", json={"prompt": "octo"})
        assert r.status_code == 200, r.text
        assert len(FAL_CALLS) == 1 and not OPENAI_CALLS, \
            (FAL_CALLS, OPENAI_CALLS)

        # 2) Défaut global persisté = gpt-image-2 (ce que fait le dropdown).
        r = await client.put("/api/atelier/settings",
                             json={"image_model_default": "gpt-image-2"})
        assert r.status_code == 200, r.text

        # 3) /image-models expose le défaut configuré (rechargement UI).
        r = await client.get("/api/image-models")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["configured"] == "gpt-image-2", d
        assert d["default"] == "gpt-image-2", d

        # 4) LE BUG: appel sans modèle (agent de planning) -> doit suivre le
        #    défaut sauvegardé, donc OpenAI gpt-image-2, PAS fal/FLUX.
        r = await client.post("/api/images/generate", json={"prompt": "octo"})
        assert r.status_code == 200, r.text
        assert r.json()["model"] == "gpt-image-2", r.json()
        assert len(OPENAI_CALLS) == 1 and len(FAL_CALLS) == 1, \
            (FAL_CALLS, OPENAI_CALLS)
        assert OPENAI_CALLS[0]["json"]["model"] == "gpt-image-2"
        assert "openai.com" in OPENAI_CALLS[0]["url"]

        # 5) Un modèle explicite dans la requête prime sur le défaut.
        r = await client.post("/api/images/generate",
                              json={"prompt": "octo", "model": "flux"})
        assert r.status_code == 200, r.text
        assert len(FAL_CALLS) == 2 and len(OPENAI_CALLS) == 1, \
            (FAL_CALLS, OPENAI_CALLS)

    print("OK — image_model_default: fallback, persistance, respect, override")

asyncio.run(main())
