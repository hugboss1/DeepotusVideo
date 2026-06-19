# Multi-Provider Settings & Import Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the corrupted .env/import flow, then add multi-provider support (OpenAI, Gemini) for the summarizer and plan-generation roles, with a dropdown in Settings → Provider defaults to switch providers per role.

**Architecture:** Provider selection is stored in `.env` via two new keys (`SUMMARIZER_PROVIDER`, `PLANNER_PROVIDER`) alongside the existing API keys. Each LLM role dispatches to the selected provider at call time — the existing Anthropic/Ollama/deterministic fallback chain becomes one option among several. The compiled frontend bundle is patched in-place with targeted string replacements (the v1.14.0 JSX source isn't on this machine).

**Tech Stack:** Python 3 / FastAPI (backend), httpx (HTTP calls to OpenAI/Gemini/Anthropic APIs), React 18 compiled bundle (frontend), PowerShell (import script)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| **Fix** | `%LOCALAPPDATA%\DeepotusVideoGenData\.env` | Restore correct keys from export |
| **Modify** | `DeepotusVideoGen-Export\Importer-mes-donnees.ps1` | Validate .env format after copy |
| **Modify** | `backend\app\config.py` | Add OPENAI/GEMINI keys + provider-selection fields to Settings |
| **Modify** | `backend\app\api\routes.py` | Add keys to allowlist, update `/health`, add `/settings/provider-defaults` |
| **Create** | `backend\app\services\openai_llm.py` | OpenAI summarizer + plan generator (same contract as existing) |
| **Create** | `backend\app\services\gemini_llm.py` | Gemini summarizer + plan generator |
| **Modify** | `backend\app\services\summarizer.py` | Dispatch to selected provider |
| **Modify** | `backend\app\services\marketing.py` | Dispatch plan generation to selected provider |
| **Modify** | `frontend\dist\assets\index-BEOJX8L5.js` | Patch Provider defaults UI + API keys list |

---

### Task 1: Fix the corrupted .env

**Files:**
- Fix: `C:\Users\olivi\AppData\Local\DeepotusVideoGenData\.env`
- Reference: `C:\Users\olivi\OneDrive\Bureau\DeepotusVideoGen-Export\data\.env`

The current `.env` has doubled key names (`FAL_KEY=FAL_KEY=value`) and is missing most keys (Anthropic, OpenAI, voice IDs, pipeline defaults).

- [ ] **Step 1: Back up the corrupted .env**

```powershell
Copy-Item "$env:LOCALAPPDATA\DeepotusVideoGenData\.env" "$env:LOCALAPPDATA\DeepotusVideoGenData\.env.bak.corrupted"
```

- [ ] **Step 2: Copy the correct .env from the export**

```powershell
Copy-Item "C:\Users\olivi\OneDrive\Bureau\DeepotusVideoGen-Export\data\.env" "$env:LOCALAPPDATA\DeepotusVideoGenData\.env" -Force
```

- [ ] **Step 3: Verify the restored .env parses correctly**

```powershell
Get-Content "$env:LOCALAPPDATA\DeepotusVideoGenData\.env" | Select-String "^[A-Z].*=" | ForEach-Object {
    $k = ($_ -split '=',2)[0]
    $v = ($_ -split '=',2)[1]
    if ($v -match "^$k=") { Write-Host "STILL CORRUPTED: $k" -ForegroundColor Red }
    else { Write-Host "OK: $k" -ForegroundColor Green }
}
```
Expected: all lines print "OK".

---

### Task 2: Harden the import script

**Files:**
- Modify: `C:\Users\olivi\OneDrive\Bureau\DeepotusVideoGen-Export\Importer-mes-donnees.ps1`

Add a post-copy validation that detects and fixes the `KEY=KEY=value` corruption pattern.

- [ ] **Step 1: Add .env validation after the robocopy block**

Insert after line 34 (`Write-Host "  données copiées." ...`), before the Python path-rewrite section:

```powershell
# 1b) Validate & fix .env (guard against KEY=KEY=value corruption).
$envPath = Join-Path $dst ".env"
if (Test-Path $envPath) {
  $fixed = 0
  $lines = Get-Content $envPath -Encoding UTF8
  $newLines = @()
  foreach ($line in $lines) {
    if ($line -match '^([A-Z_]+)=\1=(.*)$') {
      $newLines += "$($Matches[1])=$($Matches[2])"
      $fixed++
    } else {
      $newLines += $line
    }
  }
  if ($fixed -gt 0) {
    $newLines | Set-Content $envPath -Encoding UTF8
    Write-Host "  .env: corrigé $fixed clé(s) dupliquée(s)." -ForegroundColor Yellow
  } else {
    Write-Host "  .env: format OK." -ForegroundColor Green
  }
}
```

- [ ] **Step 2: Verify the fix by reading the modified script**

Confirm the validation block is placed between the robocopy success message and the Python path-rewrite section.

---

### Task 3: Add OpenAI & Gemini fields to backend config

**Files:**
- Modify: `C:\Users\olivi\AppData\Local\DeepotusVideoGen\backend\app\config.py`

- [ ] **Step 1: Add new Settings fields**

After the existing `ANTHROPIC_MODEL` field (line 106), add:

```python
    # v1.15: OpenAI (alternative summariser / planner)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # v1.15: Google Gemini (alternative summariser / planner)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # v1.15: provider selection per role. Values: "anthropic", "openai",
    # "gemini", "ollama". Empty = auto (first available in priority order).
    SUMMARIZER_PROVIDER: str = ""
    PLANNER_PROVIDER: str = ""
```

- [ ] **Step 2: Add provider-availability properties**

After the existing `has_summarizer` property, add:

```python
    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY.strip())

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY.strip())

    @property
    def has_any_llm(self) -> bool:
        return self.has_summarizer or self.has_openai or self.has_gemini or self.has_ollama
```

- [ ] **Step 3: Verify the config loads without errors**

```powershell
cd C:\Users\olivi\AppData\Local\DeepotusVideoGen\backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" -c "from app.config import settings; print('OK', settings.OPENAI_API_KEY[:4] if settings.OPENAI_API_KEY else 'empty')"
```
Expected: `OK empty` or `OK sk-p` (if key was in .env).

---

### Task 4: Create OpenAI LLM service

**Files:**
- Create: `C:\Users\olivi\AppData\Local\DeepotusVideoGen\backend\app\services\openai_llm.py`

Same contract as `summarizer.py` and `_anthropic_plan()`: returns result or `None` (fail-safe).

- [ ] **Step 1: Write the OpenAI service module**

```python
"""OpenAI summariser & plan generator (v1.15).

Same fail-safe contract as the Anthropic modules: returns a result or
None on ANY error, so callers always have a deterministic fallback.
Direct httpx calls — no openai SDK dependency.
"""
import json
import httpx
from loguru import logger

from app.config import settings

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
        async with httpx.AsyncClient(timeout=60.0) as client:
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
```

---

### Task 5: Create Gemini LLM service

**Files:**
- Create: `C:\Users\olivi\AppData\Local\DeepotusVideoGen\backend\app\services\gemini_llm.py`

- [ ] **Step 1: Write the Gemini service module**

```python
"""Google Gemini summariser & plan generator (v1.15).

Same fail-safe contract: returns a result or None on ANY error.
Direct httpx calls to the Gemini REST API — no google SDK dependency.
"""
import json
import httpx
from loguru import logger

from app.config import settings

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
        "You are a social media content strategist. Output STRICT JSON only, "
        "no prose, no markdown fences. "
        f"Schema: {{\"posts\":[{{\"day_offset\":int (0..{days - 1}),"
        "\"time\":\"HH:MM\",\"title\":str,"
        "\"format\":\"image|seedance|heygen|composition|news\","
        "\"hook\":str,\"caption\":str,\"script_idea\":str,"
        "\"image_idea\":str,"
        "\"channels\":[\"x\"|\"telegram\"|\"youtube\"|\"instagram\"]}}]}. "
        f"Exactly {days * posts_per_day} posts ({posts_per_day}/day over "
        f"{days} days). Language: {language}. {pdesc}"
        "Vary formats and times."
    )
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                _url(),
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": sys}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 4000,
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
        logger.warning(f"gemini plan error: {e}")
        return None
```

---

### Task 6: Wire provider selection into the summarizer

**Files:**
- Modify: `C:\Users\olivi\AppData\Local\DeepotusVideoGen\backend\app\services\summarizer.py`

Replace the single-provider module with a dispatcher that respects `SUMMARIZER_PROVIDER`.

- [ ] **Step 1: Rewrite summarizer.py**

Replace the entire file with:

```python
"""Multi-provider summariser (v1.15).

Dispatches to the provider chosen in SUMMARIZER_PROVIDER, or auto-detects
the first available in priority order: anthropic > openai > gemini > ollama.
Always fail-safe: returns None on any error.
"""
import httpx
from loguru import logger

from app.config import settings


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


_PROVIDERS = {
    "anthropic": lambda t, ti, la, tw: _anthropic(t, ti, la, tw),
    "openai": lambda t, ti, la, tw: __import__(
        "app.services.openai_llm", fromlist=["summarize"]
    ).summarize(t, title=ti, language=la, target_words=tw),
    "gemini": lambda t, ti, la, tw: __import__(
        "app.services.gemini_llm", fromlist=["summarize"]
    ).summarize(t, title=ti, language=la, target_words=tw),
}

_PRIORITY = ["anthropic", "openai", "gemini"]


def _available_providers() -> list[str]:
    checks = {
        "anthropic": lambda: bool(settings.ANTHROPIC_API_KEY.strip()),
        "openai": lambda: bool(settings.OPENAI_API_KEY.strip()),
        "gemini": lambda: bool(settings.GEMINI_API_KEY.strip()),
    }
    return [p for p in _PRIORITY if checks.get(p, lambda: False)()]


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
    fn = _PROVIDERS.get(provider)
    if fn:
        result = fn(src, title, language, target_words)
        if result:
            return result
    for p in _available_providers():
        if p == provider:
            continue
        fn = _PROVIDERS.get(p)
        if fn:
            result = fn(src, title, language, target_words)
            if result:
                return result
    return None
```

---

### Task 7: Wire provider selection into plan generation

**Files:**
- Modify: `C:\Users\olivi\AppData\Local\DeepotusVideoGen\backend\app\services\marketing.py`

- [ ] **Step 1: Add provider imports at the top of marketing.py**

After the existing imports (after `from app.services.storage import ...`), add:

```python
from app.services import openai_llm, gemini_llm
```

- [ ] **Step 2: Add OpenAI and Gemini plan functions**

After the existing `_ollama_plan()` function, add:

```python
async def _openai_plan(prompt: str, days: int, posts_per_day: int,
                       channels: list[str], language: str,
                       persona: dict | None) -> list[dict] | None:
    return await openai_llm.generate_plan(
        prompt, days, posts_per_day, channels, language, persona)


async def _gemini_plan(prompt: str, days: int, posts_per_day: int,
                       channels: list[str], language: str,
                       persona: dict | None) -> list[dict] | None:
    return await gemini_llm.generate_plan(
        prompt, days, posts_per_day, channels, language, persona)
```

- [ ] **Step 3: Rewrite generate_plan() to use provider preference**

Replace the `generate_plan()` function body with:

```python
async def generate_plan(prompt: str, *, days: int = 7,
                        posts_per_day: int = 1,
                        channels: list[str] | None = None,
                        language: str = "EN",
                        persona: dict | None = None) -> dict:
    """Returns {"posts": [...], "engine": "anthropic"|"openai"|"gemini"|"ollama"|"deterministic"}."""
    channels = channels or ["x"]
    perf = await performance_context()
    full_prompt = f"{prompt}\n\n{perf}" if perf else prompt
    args = (full_prompt, days, posts_per_day, channels, language, persona)

    pref = settings.PLANNER_PROVIDER.strip().lower()
    engines = {
        "anthropic": (_anthropic_plan, lambda: settings.has_summarizer),
        "openai": (_openai_plan, lambda: settings.has_openai),
        "gemini": (_gemini_plan, lambda: settings.has_gemini),
        "ollama": (_ollama_plan, lambda: settings.has_ollama),
    }
    priority = ["anthropic", "openai", "gemini", "ollama"]

    if pref and pref in engines:
        priority = [pref] + [p for p in priority if p != pref]

    for eng_name in priority:
        fn, check = engines[eng_name]
        if check():
            posts = await fn(*args)
            if posts is not None:
                return {"posts": posts, "engine": eng_name}

    posts = _deterministic_plan(prompt, days, posts_per_day, channels,
                                language, persona)
    return {"posts": posts, "engine": "deterministic"}
```

---

### Task 8: Update routes.py — allowed keys, health, provider-defaults endpoint

**Files:**
- Modify: `C:\Users\olivi\AppData\Local\DeepotusVideoGen\backend\app\api\routes.py`

- [ ] **Step 1: Add new keys to _ALLOWED_ENV_KEYS**

Add to the `_ALLOWED_ENV_KEYS` set:

```python
    "OPENAI_API_KEY", "OPENAI_MODEL",
    "GEMINI_API_KEY", "GEMINI_MODEL",
    "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER",
```

- [ ] **Step 2: Update the /health endpoint**

Add these fields to the health response dict:

```python
        "openai_enabled": settings.has_openai,
        "gemini_enabled": settings.has_gemini,
        "any_llm": settings.has_any_llm,
```

- [ ] **Step 3: Add GET /settings/provider-defaults endpoint**

After the `/settings/keys` POST endpoint, add:

```python
@router.get("/settings/provider-defaults")
async def get_provider_defaults(request: Request):
    """Return available providers per role and current selection."""
    _require_localhost(request)
    from app.services import summarizer as _sum
    roles = {
        "summarizer": {
            "active": _sum.active_provider(),
            "available": _sum._available_providers(),
        },
        "planner": {
            "active": settings.PLANNER_PROVIDER.strip().lower() or "auto",
            "available": [p for p, chk in [
                ("anthropic", settings.has_summarizer),
                ("openai", settings.has_openai),
                ("gemini", settings.has_gemini),
                ("ollama", settings.has_ollama),
            ] if chk],
        },
    }
    return {"roles": roles}
```

- [ ] **Step 4: Add POST /settings/provider-defaults endpoint**

```python
@router.post("/settings/provider-defaults")
async def set_provider_defaults(body: dict, request: Request):
    """Set provider preference per role. Body: {summarizer?: str, planner?: str}.
    Writes SUMMARIZER_PROVIDER / PLANNER_PROVIDER to .env."""
    _require_localhost(request)
    entries = []
    valid = {"anthropic", "openai", "gemini", "ollama", "auto", ""}
    for role, env_key in [("summarizer", "SUMMARIZER_PROVIDER"),
                          ("planner", "PLANNER_PROVIDER")]:
        v = body.get(role, "").strip().lower()
        if v and v not in valid:
            raise HTTPException(400, f"Unknown provider: {v}")
        if role in body:
            entries.append({"name": env_key, "value": "" if v == "auto" else v})
    if entries:
        # Reuse the existing set_key logic
        await set_key({"entries": entries}, request)
    return await get_provider_defaults(request)
```

---

### Task 9: Patch the compiled frontend bundle

**Files:**
- Modify: `C:\Users\olivi\AppData\Local\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js`

Five targeted string replacements on the minified bundle. Each replacement is a unique literal string found only once.

- [ ] **Step 1: Back up the original bundle**

```powershell
$js = "$env:LOCALAPPDATA\DeepotusVideoGen\frontend\dist\assets\index-BEOJX8L5.js"
Copy-Item $js "$js.bak"
```

- [ ] **Step 2: Add OpenAI and Gemini to the API keys definition array (Fu)**

Find:
```
{k:"ANTHROPIC_API_KEY",label:"Anthropic (summary)",why:"news summarizer",health:"has_summarizer"}
```

Replace with:
```
{k:"ANTHROPIC_API_KEY",label:"Anthropic (summary)",why:"news summarizer",health:"has_summarizer"},{k:"OPENAI_API_KEY",label:"OpenAI",why:"summarizer / planner",health:"openai_enabled"},{k:"GEMINI_API_KEY",label:"Google Gemini",why:"summarizer / planner",health:"gemini_enabled"}
```

- [ ] **Step 3: Add OpenAI and Gemini as options to the summarizer role**

Find:
```
{id:"summarizer",label:"News summarizer",hint:"Anthropic Claude for neutral 2-3 sentence article summaries",options:["ANTHROPIC_API_KEY"]}
```

Replace with:
```
{id:"summarizer",label:"News summarizer",hint:"LLM for neutral 2-3 sentence article summaries",options:["ANTHROPIC_API_KEY","OPENAI_API_KEY","GEMINI_API_KEY"]},{id:"planner",label:"Schedule planner",hint:"LLM for generating content posting plans",options:["ANTHROPIC_API_KEY","OPENAI_API_KEY","GEMINI_API_KEY"]}
```

- [ ] **Step 4: Update the health badge to recognize alternative LLM providers**

Find the string that produces the "missing" badge for unconfigured roles. In the Provider defaults component (`Em`), the badge logic is:

Find:
```
d.length?"ready":"missing"
```

This pattern appears in the Provider defaults section. The `d` variable is `a.options.filter(f=>t.includes(f))` — it filters role options to only those that are set. No change is needed here — once we add the new keys to the options arrays AND the user sets them in .env, the filter will pick them up and the badge will show "ready" instead of "missing".

The key change is in the **header health indicators**. Find this pattern for the health badges in the top bar:

Find (the HealthBadge section that shows provider indicators — it only shows fal.ai and voice):
```
h.fal_configured?"✓":"missing"
```

This is fine as-is — the header shows critical providers only (fal.ai for video). The user's concern about "missing" is about the Provider defaults page, which is already fixed by Step 3 (adding alternative keys to the options arrays).

- [ ] **Step 5: Verify the patched bundle loads without syntax errors**

```powershell
& node -e "try { require('$($js -replace '\\','/')'); } catch(e) { if (e.code === 'ERR_REQUIRE_ESM' || e.message.includes('document')) console.log('PARSE OK (expected runtime error)'); else console.log('SYNTAX ERROR:', e.message); }"
```

Or simply launch the app and check the browser console.

---

### Task 10: Verify end-to-end

- [ ] **Step 1: Restart the backend**

```powershell
& "$env:LOCALAPPDATA\DeepotusVideoGen\scripts\stop.ps1"
Start-Sleep 2
& "$env:LOCALAPPDATA\DeepotusVideoGen\scripts\launch.ps1"
```

- [ ] **Step 2: Check /health returns the new fields**

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health | ConvertTo-Json
```

Expected: includes `openai_enabled`, `gemini_enabled`, `any_llm` fields.

- [ ] **Step 3: Check /settings/provider-defaults returns roles**

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/settings/provider-defaults | ConvertTo-Json -Depth 4
```

Expected: `roles.summarizer.available` includes all providers whose keys are set.

- [ ] **Step 4: Open the app in the browser**

Navigate to `http://127.0.0.1:8765`, go to Settings → API keys. Verify OpenAI and Gemini key fields appear. Go to Settings → Provider defaults. Verify the summarizer and planner roles show dropdowns with available providers.

- [ ] **Step 5: Set an OpenAI key and verify provider switching**

In Settings → API keys, enter an OpenAI key. Restart the backend. In Settings → Provider defaults, verify the summarizer now shows "ready" (green) even without an Anthropic key, and the dropdown offers OpenAI.
