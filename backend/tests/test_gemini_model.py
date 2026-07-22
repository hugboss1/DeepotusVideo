"""Chantier W-c — Gemini à jour (plan §3) : défaut gemini-flash-latest,
clé en header x-goog-api-key (plus jamais en query string), modèle
personnalisable via /settings/keys (allowlist existante), chaînes LLM qui
énumèrent gemini, fail-safe sans clé. Zéro réseau (httpx stubbé).
Run: <embedded python> backend/tests/test_gemini_model.py"""
import asyncio
import os
import pathlib
import sys
import tempfile
import types

_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp     # .env + pricing isolés
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp,'t.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
os.environ.pop("GEMINI_MODEL", None)       # le défaut du code doit s'appliquer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings                     # noqa: E402
import app.services.gemini_llm as GL                # noqa: E402
from app.services import summarizer                 # noqa: E402


class _Resp:
    def __init__(self, status=200, jobj=None):
        self.status_code = status
        self._j = jobj or {}

    def json(self):
        return self._j


HTTP_CALLS: list = []


def _fake_post(url, headers=None, json=None, timeout=None, verify=None):
    HTTP_CALLS.append({"url": url, "headers": headers or {},
                       "json": json, "verify": verify})
    return _Resp(200, {"candidates": [{"content": {"parts": [
        {"text": "ok-gemini"}]}}]})


GL.httpx = types.SimpleNamespace(post=_fake_post)


def test_default_model_is_stable_alias():
    assert settings.GEMINI_MODEL == "gemini-flash-latest"
    assert GL._url().endswith("/models/gemini-flash-latest:generateContent")


def test_key_in_header_never_in_url():
    settings.GEMINI_API_KEY = "k-secret-w-c"
    HTTP_CALLS.clear()
    out = GL.chat("dis bonjour")
    assert out == "ok-gemini"
    call = HTTP_CALLS[-1]
    assert "key=" not in call["url"] and "k-secret-w-c" not in call["url"]
    assert call["headers"].get("x-goog-api-key") == "k-secret-w-c"
    assert call["headers"].get("Content-Type") == "application/json"
    assert call["verify"] is not None      # SSL_VERIFY transmis explicitement


def test_custom_model_honored():
    settings.GEMINI_API_KEY = "k-secret-w-c"
    settings.GEMINI_MODEL = "gemini-2.0-flash"     # pin explicite
    HTTP_CALLS.clear()
    GL.summarize("x" * 120, title="t", language="FR")
    assert HTTP_CALLS[-1]["url"].endswith("/models/gemini-2.0-flash:generateContent")
    settings.GEMINI_MODEL = "gemini-flash-latest"


def test_failsafe_without_key():
    settings.GEMINI_API_KEY = ""
    HTTP_CALLS.clear()
    assert GL.available() is False
    assert GL.chat("x") is None and GL.summarize("x" * 120) is None
    assert HTTP_CALLS == []                # aucun appel réseau sans clé


def test_chains_enumerate_gemini():
    # summarizer : gemini dans la priorité + provider forcé honoré
    assert "gemini" in summarizer._PRIORITY
    settings.ANTHROPIC_API_KEY = ""
    settings.OPENAI_API_KEY = ""
    settings.GEMINI_API_KEY = "k-secret-w-c"
    settings.SUMMARIZER_PROVIDER = "gemini"
    assert summarizer.active_provider() == "gemini"
    out, prov = summarizer._chat_dispatch("dis bonjour", "", 100)
    assert (out, prov) == ("ok-gemini", "gemini")
    settings.SUMMARIZER_PROVIDER = ""
    # planner marketing : gemini dans la priorité
    from app.services import marketing
    assert "gemini" in marketing._PLAN_PRIORITY


async def main():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # ── /settings/keys : GEMINI_MODEL dans l'allowlist, round-trip .env ──
        r = await c.get("/api/settings/keys")
        assert r.status_code == 200, r.text
        keys = {k["key"] for k in r.json()["keys"]}
        assert "GEMINI_MODEL" in keys and "GEMINI_API_KEY" in keys
        r = await c.post("/api/settings/keys",
                         json={"name": "GEMINI_MODEL",
                               "value": "gemini-2.5-flash-test"})
        assert r.status_code == 200 and r.json()["restart_required"] is True
        env_txt = (pathlib.Path(_tmp) / ".env").read_text(encoding="utf-8")
        assert "GEMINI_MODEL=gemini-2.5-flash-test" in env_txt
        r = await c.get("/api/settings/keys")
        row = next(k for k in r.json()["keys"] if k["key"] == "GEMINI_MODEL")
        assert row["set"] is True
        # clé hors allowlist → 400
        r = await c.post("/api/settings/keys",
                         json={"name": "EVIL_KEY", "value": "x"})
        assert r.status_code == 400

        # ── /prompt/refine : fail-safe sans AUCUNE clé LLM ──
        settings.ANTHROPIC_API_KEY = ""
        settings.OPENAI_API_KEY = ""
        settings.GEMINI_API_KEY = ""
        settings.OLLAMA_MODEL = ""
        r = await c.post("/api/prompt/refine", json={"text": "Bonjour."})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ai"] is False and d["text"] == "Bonjour." and d["provider"] == ""

        # ── /prompt/refine : via gemini (stub) quand seule sa clé est là ──
        settings.GEMINI_API_KEY = "k-secret-w-c"
        r = await c.post("/api/prompt/refine", json={"text": "Bonjour."})
        d = r.json()
        assert d["ai"] is True and d["provider"] == "gemini"
        assert d["text"] == "ok-gemini"

        # ── santé : sonde gemini_enabled suit la clé ──
        h = (await c.get("/api/health")).json()
        assert h["gemini_enabled"] is True
        settings.GEMINI_API_KEY = ""
        h = (await c.get("/api/health")).json()
        assert h["gemini_enabled"] is False
    print("GEMINI MODEL TEST: PASS")


test_default_model_is_stable_alias()
test_key_in_header_never_in_url()
test_custom_model_honored()
test_failsafe_without_key()
test_chains_enumerate_gemini()
asyncio.run(main())
