"""OpenAI summariser & plan generator (v1.15).

Same fail-safe contract as the Anthropic modules: returns a result or
None on ANY error, so callers always have a deterministic fallback.
Direct httpx calls — no openai SDK dependency.
"""
import json
import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY
from app.services.moteurs_texte import _openai_raisonne

_API = "https://api.openai.com/v1/chat/completions"


def _corps(max_tokens: int, messages: list, temperature: float | None = None) -> dict:
    """Le corps de la requête pour settings.OPENAI_MODEL. Un modèle de raisonnement (o1, o3, o4-mini, gpt-5*,
    gpt-6* : moteurs_texte._openai_raisonne) refuse `max_tokens` (référence Chat Completions : déprécié, « non
    compatible avec les modèles o-series ») et, son effort n'étant pas `none`, `temperature` (guide « latest model »,
    relevés le 18/10/2026) : sa sortie part en `max_completion_tokens`, sans température. Les autres : inchangés."""
    model = settings.OPENAI_MODEL
    if _openai_raisonne(model):
        return {"model": model, "max_completion_tokens": max_tokens, "messages": messages}
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if temperature is not None:
        body["temperature"] = temperature
    return body


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
            json=_corps(max(400, min(4000, int(target_words * 2.0) + 200)),
                        [{"role": "user", "content": prompt}]),
            timeout=90.0,
            verify=SSL_VERIFY,
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
            json=_corps(max_tokens, msgs, temperature),
            timeout=60.0,
            verify=SSL_VERIFY,
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
    # v1.27 — contrat de plan partagé (blocs structurés style Sol).
    # Import local : marketing importe ce module, on évite le cycle.
    from app.services import plan_schema
    sys = plan_schema.system_prompt(days, posts_per_day, language,
                                    plan_schema.persona_desc(persona))
    try:
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=60.0) as client:
            r = await client.post(
                _API,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=_corps(plan_schema.MAX_TOKENS, [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": prompt},
                ]),
            )
            if r.status_code != 200:
                logger.warning(f"openai plan HTTP {r.status_code}: {r.text[:200]}")
                return None
            text = (r.json().get("choices") or [{}])[0].get(
                "message", {}).get("content", "")
            return plan_schema.parse_llm_posts(text, days)
    except Exception as e:
        logger.warning(f"openai plan error: {e}")
        return None
