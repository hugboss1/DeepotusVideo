# Article Scraper "skill" (v1.7.x)

Makes the News pipeline actually reach article **body text** past cookie /
consent modals and naive anti-bot User-Agent blocks — no headless browser.

Module: `backend/app/services/article_scraper.py` → `fetch_clean_article(url)`
returns `{title, text, image_url, status}` and never raises.

## Strategy (cheap → stronger, first good result wins)

1. **Direct GET, browser-shaped.** Realistic Chrome header set
   (`User-Agent`, `Accept`, `Accept-Language`, `Sec-CH-UA`, `Sec-Fetch-*`,
   `Upgrade-Insecure-Requests`, `DNT`) **plus pre-accepted consent cookies**
   for the common CMPs (OneTrust `OptanonConsent`/`OptanonAlertBoxClosed`,
   Quantcast `euconsent-v2`, Sourcepoint `sp_consent`, CookieYes, Didomi,
   generic `CookieConsent`/`gdpr=accepted`). Most consent walls are
   client-side, so a browser-like request with consent cookies returns the
   real HTML directly.
2. **AMP fallback.** If the result looks blocked/thin, follow the page's
   `<link rel="amphtml">`. AMP pages are consent-light and clean.
3. **Reader proxy (default ON).** `ARTICLE_READER_FALLBACK` (default
   `true`). Google-News links are opaque wrappers we can't fully decode, so
   when the direct/AMP path is blocked the **original** Google-News URL is
   handed to the public reader `r.jina.ai`, which resolves the redirect/JS
   and returns the article body. Set `false` in `backend/.env` to never
   contact a third party (those items then use the RSS snippet).

### Optional: faithful LLM summary (Anthropic)

Set `ANTHROPIC_API_KEY` in `backend/.env` to turn the richest available
text (full body, else title + RSS snippet) into a faithful neutral 2-3
sentence summary (Claude Haiku, direct httpx call — no SDK dep) **before**
the deepotus 'prophet' tone is layered on. Fully fail-safe: no key / any
error → deterministic essence. Status gains `+ai` when used.

A `status` is returned for diagnostics: `direct` | `amp` | `reader` |
`blocked(<stage>)` | `error` | `empty`.

## Scope (important)

- ✅ Defeats: cookie/consent/GDPR interstitials, JS-gated consent banners,
  User-Agent / "are you a robot" soft blocks, messy markup.
- ❌ Does **not** bypass hard **paywalls** or logins. Those degrade
  gracefully: short text → the RSS/feed summary is used instead, the run
  never fails. (No subscription-evasion tricks by design.)

## Where it's used

`news_service.fetch_article_text()` (the "Read full articles → prophet
summary + extract images" path) and `_fetch_article()` (article-type
sources) both delegate to it. Blocking work runs in a thread; per-item
fail-safe — one stubborn article never breaks a batch.

## Tuning

- trafilatura runs with `favor_recall=True` to keep more body text.
- Block heuristic: `<350` chars, or `<1400` chars containing consent /
  anti-bot phrases.
- To go fully robust on the hardest sites, a headless-browser engine
  (Playwright) could be added later as an optional heavy path — out of
  scope here to keep the install light (mirrors the Remotion decision).
