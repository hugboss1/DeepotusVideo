"""Multi-provider summariser (v1.15).

Dispatches to the provider chosen in SUMMARIZER_PROVIDER, or auto-detects
the first available in priority order: anthropic > openai > gemini > ollama.
Always fail-safe: returns None on any error.
"""
import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY


def _anthropic(text: str, title: str, language: str,
               target_words: int) -> str | None:
    lang = "French" if str(language).upper().startswith("FR") else "English"
    prompt = (
        f"Summarize this news article in about {target_words} words in "
        f"{lang} (it is fine to go longer if the article is dense; use "
        f"short paragraphs if needed). Stay neutral and factual: no "
        f"opinion, no hype, no hashtags, no preamble — return only the "
        f"summary.\n\nTitle: {title}\n\nArticle:\n{text}"
    )
    max_tok = max(400, min(4000, int(target_words * 2.0) + 200))
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": max_tok,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=90.0,
            verify=SSL_VERIFY,
        )
        if r.status_code != 200:
            logger.warning(f"summarizer[anthropic] HTTP {r.status_code}")
            return None
        blocks = r.json().get("content") or []
        return "".join(
            b.get("text", "") for b in blocks if b.get("type") == "text"
        ).strip() or None
    except Exception as e:
        logger.warning(f"summarizer[anthropic] error: {e}")
        return None


def _openai(text: str, title: str, language: str,
            target_words: int) -> str | None:
    from app.services.openai_llm import summarize as _s
    return _s(text, title=title, language=language, target_words=target_words)


def _gemini(text: str, title: str, language: str,
            target_words: int) -> str | None:
    from app.services.gemini_llm import summarize as _s
    return _s(text, title=title, language=language, target_words=target_words)


_PROVIDERS = {
    "anthropic": _anthropic,
    "openai": _openai,
    "gemini": _gemini,
}

_PRIORITY = ["anthropic", "openai", "gemini"]


def _available_providers() -> list[str]:
    checks = {
        "anthropic": lambda: bool(settings.ANTHROPIC_API_KEY.strip()),
        "openai": lambda: bool(settings.OPENAI_API_KEY.strip()),
        "gemini": lambda: bool(settings.GEMINI_API_KEY.strip()),
    }
    from app.services import moteurs_texte as _MT     # t222 : puis les fournisseurs libres prêts (clé + modèle)
    return [p for p in _PRIORITY if checks.get(p, lambda: False)()] + [m for m in _MT.libres() if _MT.configure(m)] \
        + [m for m in _MT.locaux() if _MT.configure(m)]  # t223 : puis les serveurs locaux prêts (un modèle)


def _local_chat(moteur: str, prompt: str, system: str, max_tokens: int) -> str | None:
    """t223 : un serveur local `local:<id>`, à son modèle par défaut. None sur tout échec (même contrat qu'ici)."""
    from app.services import serveurs_locaux as _SL
    sid = _SL.de_moteur(moteur)
    if not sid:
        return None
    try:
        return _SL.tirer(sid, "", prompt, system, max_tokens).strip() or None
    except RuntimeError as e:
        logger.warning(f"llm[{moteur}] error: {e}")
        return None


def _libre_chat(moteur: str, prompt: str, system: str, max_tokens: int) -> str | None:
    """t222 : un fournisseur libre `fl:<id>`, à son modèle par défaut. None sur tout échec (même contrat qu'ici)."""
    if moteur.startswith("local:"):         # t223 : même chemin pour un serveur local
        return _local_chat(moteur, prompt, system, max_tokens)
    from app.services import fournisseurs_llm as _FL
    fid = _FL.de_moteur(moteur)
    if not fid:
        return None
    try:
        return _FL.tirer(fid, "", prompt, system, max_tokens, timeout=90.0).strip() or None
    except RuntimeError as e:
        logger.warning(f"llm[{moteur}] error: {e}")
        return None


def _libre_resume(moteur: str):
    def fn(text: str, title: str, language: str, target_words: int) -> str | None:
        lang = "French" if str(language).upper().startswith("FR") else "English"
        prompt = (
            f"Summarize this news article in about {target_words} words in "
            f"{lang} (it is fine to go longer if the article is dense; use "
            f"short paragraphs if needed). Stay neutral and factual: no "
            f"opinion, no hype, no hashtags, no preamble — return only the "
            f"summary.\n\nTitle: {title}\n\nArticle:\n{text}"
        )
        return _libre_chat(moteur, prompt, "", max(400, min(4000, int(target_words * 2.0) + 200)))
    return fn


def available() -> bool:
    return bool(_available_providers()) or settings.has_ollama


def active_provider() -> str:
    pref = settings.SUMMARIZER_PROVIDER.strip().lower()
    avail = _available_providers()
    if pref and pref in avail:
        return pref
    return avail[0] if avail else ""


def summarize(text: str, *, title: str = "", language: str = "EN",
              target_words: int = 150) -> str | None:
    if not available():
        return None
    src = (text or "").strip()
    if len(src) < 80:
        return None
    src = src[:16000]
    provider = active_provider()
    fn = _PROVIDERS.get(provider) or (_libre_resume(provider) if provider.startswith(("fl:", "local:")) else None)
    if fn:
        result = fn(src, title, language, target_words)
        if result:
            return result
    for p in _available_providers():
        if p == provider:
            continue
        fn = _PROVIDERS.get(p) or (_libre_resume(p) if p.startswith(("fl:", "local:")) else None)
        if fn:
            result = fn(src, title, language, target_words)
            if result:
                return result
    return None


# ── v1.15.1: generic completion + brand-voice rewrite ───────────────────
# Lets the (otherwise deterministic) prompt engine produce GENUINELY
# AI-written scripts when an LLM key is configured — honest "AI" without
# losing the deterministic fallback or the brand vocabulary filter.

def _anthropic_chat(prompt: str, system: str, max_tokens: int) -> str | None:
    try:
        body = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
            timeout=60.0,
            verify=SSL_VERIFY,
        )
        if r.status_code != 200:
            logger.warning(f"rewrite[anthropic] HTTP {r.status_code}")
            return None
        blocks = r.json().get("content") or []
        return "".join(
            b.get("text", "") for b in blocks if b.get("type") == "text"
        ).strip() or None
    except Exception as e:
        logger.warning(f"rewrite[anthropic] error: {e}")
        return None


def _chat_dispatch(prompt: str, system: str,
                   max_tokens: int) -> tuple[str | None, str]:
    """Try the active provider, then the rest, until one returns text."""
    provider = active_provider()
    order = [provider] + [p for p in _available_providers() if p != provider]
    for p in order:
        if not p:
            continue
        out = None
        if p == "anthropic":
            out = _anthropic_chat(prompt, system, max_tokens)
        elif p == "openai":
            from app.services.openai_llm import chat as _c
            out = _c(prompt, system=system, max_tokens=max_tokens)
        elif p == "gemini":
            from app.services.gemini_llm import chat as _c
            out = _c(prompt, system=system, max_tokens=max_tokens)
        elif p.startswith(("fl:", "local:")):
            out = _libre_chat(p, prompt, system, max_tokens)
        if out:
            return out, p
    return None, ""


def rewrite_script(draft: str, *, voice_desc: str = "", language: str = "EN",
                   max_words: int = 90) -> tuple[str | None, str]:
    """LLM-polish a deterministic avatar-script draft in the voice of the current brand space.

    Returns (text, provider) on success, or (None, "") so callers keep the
    deterministic draft. Never raises.
    """
    if not available() or not (draft or "").strip():
        return None, ""
    lang = "French" if str(language).upper().startswith("FR") else "English"
    from app.services import textes_espace   # t208-bis : le prompt de l'espace (Deepotus : la graine, à l'octet)
    system = textes_espace.textes()["polir_systeme"]
    prompt = (
        f"Rewrite this short avatar script in {lang}"
        + (f", in this voice: {voice_desc}" if voice_desc else "")
        + f". Keep it under {max_words} words.\n\nDraft:\n{draft}"
    )
    max_tok = max(200, min(1200, int(max_words * 3) + 80))
    return _chat_dispatch(prompt, system, max_tok)
