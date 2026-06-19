"""Hardened article scraper (v1.7.x).

Goal: actually reach article BODY text past cookie/consent modals and naive
anti-bot User-Agent blocks, without a headless browser.

Strategy (cheap -> stronger, first good result wins):
  1. Direct GET with a realistic browser header set + pre-accepted consent
     cookies (OneTrust / Quantcast / Sourcepoint / CookieYes / generic).
     Most consent walls are client-side; browser-like + consent cookies
     return the real HTML.
  2. If the result looks blocked/empty -> follow the page's AMP version
     (rel="amphtml"); AMP pages are consent-light and clean.
  3. Optional, opt-in only (settings.ARTICLE_READER_FALLBACK): a public
     reader proxy (r.jina.ai) as last resort.

Scope: defeats consent/cookie banners and UA blocks. Does NOT bypass hard
paywalls — those degrade gracefully (short text; the RSS summary stays).
"""
import base64
import re
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

# Language-switcher / nav boilerplate Google News & many sites leak when the
# real body can't be found. If the "article" is mostly this, it's junk.
_BOILER = ("all languages", "deutsch", "español", "français", "italiano",
           "português", "čeština", "bahasa", "magyar", "polski", "svenska",
           "united states", "sign in", "more from")


def _looks_boilerplate(text: str) -> bool:
    if not text:
        return True
    low = text[:600].lower()
    hits = sum(1 for w in _BOILER if w in low)
    seps = text.count(" - ") + text.count(" · ")
    # many language-name hits, or a wall of short " - " separated nav tokens
    return hits >= 4 or (seps >= 8 and len(text) < 1200)


def _resolve_google_news(url: str, client: "httpx.Client") -> str:
    """Google News RSS links wrap the real article. Resolve to the
    publisher URL (query param -> base64 token -> page scrape)."""
    pu = urlparse(url)
    host = pu.netloc.lower()
    if "google." not in host:
        return url
    # google.com/url?url=... / ...&q=...
    q = parse_qs(pu.query)
    for k in ("url", "q"):
        if q.get(k) and q[k][0].startswith("http"):
            return q[k][0]
    # news.google.com/.../articles/<base64 token> — URL embedded in token
    m = re.search(r"/articles/([A-Za-z0-9_\-]+)", url)
    if m:
        seg = m.group(1)
        try:
            raw = base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))
            txt = raw.decode("latin-1", "ignore")
            um = re.search(r"https?://[^\s\x00-\x1f\"'<>\\]+", txt)
            if um and "google." not in urlparse(um.group(0)).netloc:
                return um.group(0)
        except Exception:  # noqa: BLE001
            pass
    # last resort: load the Google page, grab the outbound link
    try:
        r = client.get(url, headers=BROWSER_HEADERS)
        r.raise_for_status()
        h = r.text
        m2 = (re.search(r'data-n-au="(https?://[^"]+)"', h)
              or re.search(r'rel="canonical"\s+href="(https?://[^"]+)"', h)
              or re.search(
                  r'<a[^>]+href="(https?://(?!news\.google|accounts\.google'
                  r'|policies\.google|support\.google)[^"]+)"', h))
        if m2:
            return m2.group(1)
    except Exception:  # noqa: BLE001
        pass
    return url

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
    "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", '
                 '"Not-A.Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}

# Generic "consent already given" cookies for the common CMPs. Sending these
# makes most GDPR/cookie interstitials hand over the article HTML directly.
_CONSENT = (
    "euconsent-v2=CP%2Daccepted; "
    "OptanonAlertBoxClosed=2024-01-01T00:00:00.000Z; "
    "OptanonConsent=isGpcEnabled=0&datestamp=accepted&consentId=1&"
    "groups=C0001:1,C0002:1,C0003:1,C0004:1; "
    "CookieConsent={stamp:%27accepted%27}; "
    "cookieyes-consent=consent:yes; "
    "cookie_consent_level=accepting_all; "
    "gdpr=accepted; cookies_accepted=1; cookie_notice_accepted=true; "
    "didomi_token=accepted; sp_consent=accepted"
)

_BLOCK_HINTS = (
    "accept cookies", "cookie policy", "we use cookies", "consent",
    "enable javascript", "javascript is disabled", "are you a robot",
    "verify you are human", "access denied", "request blocked",
    "checking your browser", "please enable cookies",
)
_AMP_RE = re.compile(
    r'<link[^>]+rel=["\']amphtml["\'][^>]+href=["\']([^"\']+)["\']', re.I)
_AMP_RE2 = re.compile(
    r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']amphtml["\']', re.I)


def _extract(html: str) -> str:
    import trafilatura
    return trafilatura.extract(
        html, include_comments=False, include_tables=False,
        favor_recall=True, no_fallback=False) or ""


def _looks_blocked(text: str) -> bool:
    if len(text) < 350:
        return True
    low = text[:1500].lower()
    return len(text) < 1400 and any(h in low for h in _BLOCK_HINTS)


def _get(client: httpx.Client, url: str) -> str | None:
    try:
        r = client.get(url, headers=BROWSER_HEADERS,
                        cookies={"_consent": "1"})
        r.raise_for_status()
        return r.text
    except Exception as e:  # noqa: BLE001
        logger.debug(f"scraper GET failed {url}: {e}")
        return None


def _meta(html: str) -> tuple[str, str | None]:
    import trafilatura
    title, image = "", None
    try:
        md = trafilatura.extract_metadata(html)
        if md:
            title = md.title or ""
            image = md.image
    except Exception:  # noqa: BLE001
        pass
    return title, image


def fetch_clean_article(url: str) -> dict:
    """Return {title, text, image_url, status}. Never raises."""
    headers = dict(BROWSER_HEADERS)
    headers["Cookie"] = _CONSENT
    best_text, best_html, status = "", "", "empty"

    orig = url  # keep the original (best target for the reader proxy)
    try:
        with httpx.Client(verify=SSL_VERIFY, timeout=25.0, follow_redirects=True,
                          headers=headers) as client:
            # 0. Resolve Google News wrappers to the real publisher URL
            real = _resolve_google_news(url, client)
            if real != url:
                logger.info(f"google-news resolved -> {real[:90]}")
                url = real
            # If we only reached a Google consent/wrapper, force the reader
            # path (jina resolves Google News redirects/JS far better).
            if "google." in urlparse(url).netloc:
                best_text = ""
            # 1. Direct
            html = _get(client, url)
            if html:
                txt = _extract(html)
                if _looks_boilerplate(txt):
                    txt = ""  # language/nav menu, not an article
                best_text, best_html, status = txt, html, "direct"
                # 2. AMP fallback if blocked/thin
                if _looks_blocked(txt):
                    m = _AMP_RE.search(html) or _AMP_RE2.search(html)
                    if m:
                        amp = m.group(1)
                        if amp.startswith("/"):
                            amp = urljoin(url, amp)
                        ahtml = _get(client, amp)
                        if ahtml:
                            atxt = _extract(ahtml)
                            if _looks_boilerplate(atxt):
                                atxt = ""
                            if len(atxt) > len(best_text):
                                best_text, best_html = atxt, ahtml
                                status = "amp"
            # 3. Reader proxy. For Google wrappers, hand jina the ORIGINAL
            # news.google URL — it resolves the redirect/JS better than us.
            if _looks_blocked(best_text) and settings.ARTICLE_READER_FALLBACK:
                target = (orig if "google." in urlparse(url).netloc else url)
                try:
                    rr = client.get(
                        f"https://r.jina.ai/{target}",
                        headers={"User-Agent": BROWSER_HEADERS["User-Agent"]},
                        timeout=35.0)
                    rtxt = rr.text.strip() if rr.status_code == 200 else ""
                    if _looks_boilerplate(rtxt):
                        rtxt = ""
                    if len(rtxt) > len(best_text):
                        best_text = rtxt
                        status = "reader"
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"reader fallback failed: {e}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"scraper failed {url}: {e}")
        return {"title": "", "text": "", "image_url": None, "status": "error"}

    title, image = _meta(best_html) if best_html else ("", None)
    if _looks_blocked(best_text):
        status = f"blocked({status})"
    logger.info(f"scraper {url} -> {status} ({len(best_text)} chars)")
    return {"title": title, "text": best_text, "image_url": image,
            "status": status}
