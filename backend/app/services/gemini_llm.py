"""Google Gemini summariser & plan generator (v1.15).

Same fail-safe contract: returns a result or None on ANY error.
Direct httpx calls to the Gemini REST API — no google SDK dependency.
"""
import json
import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

_API = "https://generativelanguage.googleapis.com/v1beta/models"


def available() -> bool:
    return bool(settings.GEMINI_API_KEY.strip())


def _url(action: str = "generateContent") -> str:
    return f"{_API}/{settings.GEMINI_MODEL}:{action}?key={settings.GEMINI_API_KEY}"


def summarize(text: str, *, title: str = "", language: str = "EN",
              target_words: int = 150) -> str | None:
    if not available():
        return None
    src = (text or "").strip()
    if len(src) < 80:
        return None
    src = src[:16000]
    lang = "French" if str(language).upper().startswith("FR") else "English"
    prompt = (
        f"Summarize this news article in about {target_words} words in "
        f"{lang} (it is fine to go longer if the article is dense; use "
        f"short paragraphs if needed). Stay neutral and factual: no "
        f"opinion, no hype, no hashtags, no preamble — return only the "
        f"summary.\n\nTitle: {title}\n\nArticle:\n{src}"
    )
    try:
        r = httpx.post(
            _url(),
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max(400, min(4000,
                                           int(target_words * 2.0) + 200)),
                },
            },
            timeout=90.0,
        )
        if r.status_code != 200:
            logger.warning(f"gemini summarizer HTTP {r.status_code}")
            return None
        candidates = r.json().get("candidates") or []
        parts = (candidates[0].get("content", {}).get("parts", [])
                 if candidates else [])
        out = "".join(p.get("text", "") for p in parts).strip()
        return out or None
    except Exception as e:
        logger.warning(f"gemini summarizer error: {e}")
        return None


def chat(prompt: str, *, system: str = "", max_tokens: int = 600,
         temperature: float = 0.9) -> str | None:
    """Generic single-turn completion. Fail-safe: returns None on any error."""
    if not available():
        return None
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    try:
        r = httpx.post(
            _url(),
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=60.0,
        )
        if r.status_code != 200:
            logger.warning(f"gemini chat HTTP {r.status_code}")
            return None
        candidates = r.json().get("candidates") or []
        parts = (candidates[0].get("content", {}).get("parts", [])
                 if candidates else [])
        out = "".join(p.get("text", "") for p in parts).strip()
        return out or None
    except Exception as e:
        logger.warning(f"gemini chat error: {e}")
        return None


async def generate_plan(prompt: str, days: int, posts_per_day: int,
                        channels: list[str], language: str,
                        persona: dict | None) -> list[dict] | None:
    if not available():
        return None
    # v1.27 — contrat de plan partagé (blocs structurés style Sol).
    # Import local : marketing importe ce module, on évite le cycle.
    from app.services import plan_schema
    sys = plan_schema.system_prompt(days, posts_per_day, language,
                                    plan_schema.persona_desc(persona))
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=90.0) as client:
            r = await client.post(
                _url(),
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": sys}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": plan_schema.MAX_TOKENS,
                        "responseMimeType": "application/json",
                    },
                },
            )
            if r.status_code != 200:
                logger.warning(f"gemini plan HTTP {r.status_code}: "
                               f"{r.text[:200]}")
                return None
            candidates = r.json().get("candidates") or []
            parts = (candidates[0].get("content", {}).get("parts", [])
                     if candidates else [])
            text = "".join(p.get("text", "") for p in parts)
            return plan_schema.parse_llm_posts(text, days)
    except Exception as e:
        logger.warning(f"gemini plan error: {e}")
        return None
