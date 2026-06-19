"""OpenAI summariser & plan generator (v1.15).

Same fail-safe contract as the Anthropic modules: returns a result or
None on ANY error, so callers always have a deterministic fallback.
Direct httpx calls — no openai SDK dependency.
"""
import json
import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

_API = "https://api.openai.com/v1/chat/completions"


def available() -> bool:
    return bool(settings.OPENAI_API_KEY.strip())


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
            _API,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENAI_MODEL,
                "max_tokens": max(400, min(4000, int(target_words * 2.0) + 200)),
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=90.0,
        )
        if r.status_code != 200:
            logger.warning(f"openai summarizer HTTP {r.status_code}")
            return None
        choices = r.json().get("choices") or []
        out = (choices[0].get("message", {}).get("content", "")
               if choices else "").strip()
        return out or None
    except Exception as e:
        logger.warning(f"openai summarizer error: {e}")
        return None


def chat(prompt: str, *, system: str = "", max_tokens: int = 600,
         temperature: float = 0.9) -> str | None:
    """Generic single-turn completion. Fail-safe: returns None on any error."""
    if not available():
        return None
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    try:
        r = httpx.post(
            _API,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENAI_MODEL,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": msgs,
            },
            timeout=60.0,
        )
        if r.status_code != 200:
            logger.warning(f"openai chat HTTP {r.status_code}")
            return None
        choices = r.json().get("choices") or []
        out = (choices[0].get("message", {}).get("content", "")
               if choices else "").strip()
        return out or None
    except Exception as e:
        logger.warning(f"openai chat error: {e}")
        return None


async def generate_plan(prompt: str, days: int, posts_per_day: int,
                        channels: list[str], language: str,
                        persona: dict | None) -> list[dict] | None:
    if not available():
        return None
    pdesc = ""
    if persona:
        pdesc = (f"Persona: {persona.get('name', '')}. "
                 f"Tone: {persona.get('tone', '')}. "
                 f"Audience: {persona.get('audience', '')}. ")
    sys = (
        "You are a social media content strategist for short-form video "
        "accounts. Produce a posting plan as STRICT JSON, no prose. "
        f"Schema: {{\"posts\":[{{\"day_offset\":int (0..{days - 1}),"
        "\"time\":\"HH:MM\",\"title\":str,"
        "\"format\":\"image|seedance|heygen|composition|news\","
        "\"hook\":str,\"caption\":str,\"script_idea\":str,"
        "\"image_idea\":str,"
        "\"channels\":[\"x\"|\"telegram\"|\"youtube\"|\"instagram\"]}}]}. "
        f"Exactly {days * posts_per_day} posts ({posts_per_day}/day over "
        f"{days} days). Language: {language}. {pdesc}"
        "Vary formats and times (morning/noon/evening)."
    )
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=60.0) as client:
            r = await client.post(
                _API,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "max_tokens": 4000,
                    "messages": [
                        {"role": "system", "content": sys},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            if r.status_code != 200:
                logger.warning(f"openai plan HTTP {r.status_code}: {r.text[:200]}")
                return None
            text = (r.json().get("choices") or [{}])[0].get(
                "message", {}).get("content", "")
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                return None
            data = json.loads(text[start:end + 1])
            posts = data.get("posts")
            if not isinstance(posts, list) or not posts:
                return None
            clean = []
            for p in posts:
                try:
                    clean.append({
                        "day_offset": max(0, min(days - 1,
                                                 int(p.get("day_offset", 0)))),
                        "time": str(p.get("time", "12:00"))[:5],
                        "title": str(p.get("title", ""))[:200],
                        "format": str(p.get("format", "image")),
                        "hook": str(p.get("hook", "")),
                        "caption": str(p.get("caption", "")),
                        "script_idea": str(p.get("script_idea", "")),
                        "image_idea": str(p.get("image_idea", "")),
                        "channels": [c for c in (p.get("channels") or ["x"])
                                     if c in ("x", "telegram", "youtube",
                                              "instagram")] or ["x"],
                    })
                except (TypeError, ValueError):
                    continue
            return clean or None
    except Exception as e:
        logger.warning(f"openai plan error: {e}")
        return None
