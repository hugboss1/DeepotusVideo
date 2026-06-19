"""News / RSS pipeline (v1.7).

Sources (RSS/Atom feeds or single article URLs) are persisted as JSON under
the user-data area (preserved across upgrades). Fetched items are cached with
a timestamp so a once-a-day in-app auto-refresh is cheap and restart-safe.

Network/parse work (feedparser, httpx, trafilatura) is blocking, so the public
async API offloads it via asyncio.to_thread and is fully fail-safe: one bad
source never breaks a whole refresh.
"""
import asyncio
import hashlib
import html as _html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_UA = "Mozilla/5.0 (compatible; DeepotusNewsBot/1.7; +local)"
MAX_ITEMS = 300
PER_FEED = 25
REFRESH_INTERVAL_S = 24 * 3600

# Curated default feed pack — established, stable public RSS endpoints,
# all DIRECT publisher feeds (no Google-News wrappers, so the scraper gets
# full article bodies). Covers crypto, geopolitics, economy/macro and
# politics (EU/China/USA). Auto-seeded on first run; re-addable via
# POST /api/news/sources/defaults.
DEFAULT_SOURCES = [
    # --- Crypto ---
    ("Crypto", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Crypto", "Cointelegraph", "https://cointelegraph.com/rss"),
    ("Crypto", "Decrypt", "https://decrypt.co/feed"),
    # --- Geopolitics / world ---
    ("World", "BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("World", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("World", "The Guardian — World",
     "https://www.theguardian.com/world/rss"),
    ("World", "NPR — World", "https://feeds.npr.org/1004/rss.xml"),
    # --- Economy / macro ---
    ("Economy", "BBC Business",
     "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Economy", "The Guardian — Business",
     "https://www.theguardian.com/business/rss"),
    ("Economy", "NPR — Economy", "https://feeds.npr.org/1017/rss.xml"),
    # --- Politics: USA ---
    ("US politics", "BBC US & Canada",
     "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    ("US politics", "The Hill", "https://thehill.com/news/feed/"),
    ("US politics", "Politico", "https://rss.politico.com/politics-news.xml"),
    # --- Politics: Europe ---
    ("EU politics", "Politico Europe", "https://www.politico.eu/feed/"),
    ("EU politics", "BBC Europe",
     "https://feeds.bbci.co.uk/news/world/europe/rss.xml"),
    ("EU politics", "EURACTIV", "https://www.euractiv.com/feed/"),
    # --- Politics: China ---
    ("China", "BBC China",
     "https://feeds.bbci.co.uk/news/world/asia/china/rss.xml"),
    ("China", "The Guardian — China",
     "https://www.theguardian.com/world/china/rss"),
]


def _clean(text: str | None, limit: int = 600) -> str:
    if not text:
        return ""
    t = _html.unescape(_TAG_RE.sub(" ", text))
    t = _WS_RE.sub(" ", t).strip()
    return t[:limit]


def _hid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8", "ignore")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class NewsService:
    def __init__(self):
        self.dir = settings.outputs_path.parent / "news"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.sources_path = self.dir / "sources.json"
        self.cache_path = self.dir / "cache.json"

    # ----- sources -----

    def _default_records(self) -> list[dict]:
        return [
            {
                "id": _hid(url)[:12],
                "type": "rss",
                "url": url,
                "name": f"[{cat}] {name}",
                "enabled": True,
            }
            for cat, name, url in DEFAULT_SOURCES
        ]

    def list_sources(self) -> list[dict]:
        # First run (no file yet): auto-seed the curated pack. Never
        # re-seeds once the file exists (respects user edits/deletes).
        if not self.sources_path.exists():
            recs = self._default_records()
            self._save_sources(recs)
            logger.info(f"news sources seeded with {len(recs)} curated feeds")
            return recs
        try:
            return json.loads(self.sources_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.error("news sources.json corrupt; starting empty")
            return []

    def seed_defaults(self) -> dict:
        """Reconcile to the curated pack: drop the old auto-seeded Google
        News feeds (now replaced by direct publisher feeds), keep every
        user-added source, then add any missing default. Idempotent."""
        existing = self.list_sources()
        kept = [s for s in existing
                if "news.google.com" not in (s.get("url") or "")]
        removed = len(existing) - len(kept)
        have = {s["id"] for s in kept}
        added = [r for r in self._default_records() if r["id"] not in have]
        if added or removed:
            self._save_sources(kept + added)
        return {"added": len(added), "removed": removed,
                "total": len(kept) + len(added)}

    def _save_sources(self, sources: list[dict]) -> None:
        self.sources_path.write_text(
            json.dumps(sources, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_source(self, url: str, name: str | None = None,
                   kind: str = "rss") -> dict:
        url = (url or "").strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Source URL must start with http:// or https://")
        if kind not in ("rss", "article"):
            raise ValueError("kind must be 'rss' or 'article'")
        sources = self.list_sources()
        sid = _hid(url)[:12]
        if any(s["id"] == sid for s in sources):
            raise ValueError("This source is already configured")
        src = {
            "id": sid,
            "type": kind,
            "url": url,
            "name": (name or "").strip() or url,
            "enabled": True,
        }
        sources.append(src)
        self._save_sources(sources)
        logger.info(f"news source added: {kind} {url}")
        return src

    def remove_source(self, source_id: str) -> bool:
        sources = self.list_sources()
        kept = [s for s in sources if s["id"] != source_id]
        if len(kept) == len(sources):
            return False
        self._save_sources(kept)
        return True

    def set_enabled(self, source_id: str, enabled: bool) -> bool:
        sources = self.list_sources()
        found = False
        for s in sources:
            if s["id"] == source_id:
                s["enabled"] = bool(enabled)
                found = True
        if found:
            self._save_sources(sources)
        return found

    # ----- cache -----

    def _read_cache(self) -> dict:
        if not self.cache_path.exists():
            return {"fetched_at": None, "items": [], "errors": []}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"fetched_at": None, "items": [], "errors": []}

    def get_items(self) -> dict:
        return self._read_cache()

    def last_fetch_iso(self) -> str | None:
        return self._read_cache().get("fetched_at")

    def _stale(self) -> bool:
        c = self._read_cache()
        ts = c.get("fetched_at")
        if not ts:
            return True
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            return True
        age = (datetime.now(timezone.utc) - dt).total_seconds()
        return age >= REFRESH_INTERVAL_S

    # ----- fetching (blocking core; call via async wrappers) -----

    def _fetch_rss(self, src: dict) -> list[dict]:
        import feedparser  # imported lazily so a missing dep degrades clearly
        parsed = feedparser.parse(src["url"], agent=_UA)
        items: list[dict] = []
        for e in parsed.entries[:PER_FEED]:
            link = e.get("link") or e.get("id") or ""
            title = _clean(e.get("title"), 300)
            if not title and not link:
                continue
            pub = ""
            tstruct = e.get("published_parsed") or e.get("updated_parsed")
            if tstruct:
                try:
                    pub = datetime.fromtimestamp(
                        time.mktime(tstruct), timezone.utc
                    ).isoformat(timespec="seconds")
                except (OverflowError, ValueError):
                    pub = ""
            image = None
            if e.get("media_thumbnail"):
                image = e["media_thumbnail"][0].get("url")
            elif e.get("media_content"):
                image = e["media_content"][0].get("url")
            elif e.get("enclosures"):
                for enc in e["enclosures"]:
                    if str(enc.get("type", "")).startswith("image"):
                        image = enc.get("href")
                        break
            items.append({
                "id": _hid(src["id"], link or title),
                "source_id": src["id"],
                "source_name": src["name"],
                "title": title,
                "summary": _clean(e.get("summary") or e.get("description")),
                "link": link,
                "published": pub,
                "image": image,
            })
        return items

    def _fetch_article(self, src: dict) -> list[dict]:
        from app.services.article_scraper import fetch_clean_article
        a = fetch_clean_article(src["url"])
        title = a.get("title") or src["name"]
        return [{
            "id": _hid(src["id"], src["url"]),
            "source_id": src["id"],
            "source_name": src["name"],
            "title": _clean(title, 300),
            "summary": _clean(a.get("text"), 1200),
            "link": src["url"],
            "published": _now_iso(),
            "image": None,
        }]

    # ----- article reading + illustration extraction (v1.7.x) -----

    def _essence(self, text: str, desc: str | None,
                 target_words: int = 150) -> str:
        """Neutral summary of the article, up to ~target_words. Builds from
        the extracted body (sentence-accurate); falls back to the page
        description only when there is no usable body."""
        target_chars = max(240, int(target_words * 6.5))
        body = " ".join((text or "").split())
        if body:
            sents: list[str] = []
            for tok in body.split(". "):
                sents.append(tok)
                if len(" ".join(sents)) >= target_chars:
                    break
            return _clean(". ".join(sents), target_chars + 400)
        if desc and len(desc.strip()) >= 60:
            return _clean(desc, target_chars + 400)
        return ""

    def fetch_article_text(self, url: str,
                           target_words: int = 150) -> dict:
        """Blocking: fetch an article past consent/cookie + UA blocks via the
        hardened scraper. Returns {title, essence, text, image_url, status}.
        Fail-safe (returns {} on error)."""
        from app.services.article_scraper import fetch_clean_article
        a = fetch_clean_article(url)
        if not a.get("text"):
            return {"status": a.get("status", "empty")}
        return {
            "title": _clean(a.get("title"), 300),
            "essence": self._essence(a.get("text"), None, target_words),
            "text": (a.get("text") or "")[:16000],
            "image_url": a.get("image_url"),
            "status": a.get("status"),
        }

    def download_article_image(self, img_url: str) -> str | None:
        """Blocking: download an article's lead image into assets/images so
        it is immediately usable by Seedance / templates. Returns the saved
        filename, or None (fail-safe)."""
        if not img_url or not img_url.startswith(("http://", "https://")):
            return None
        try:
            with httpx.Client(verify=SSL_VERIFY, timeout=20.0, follow_redirects=True,
                              headers={"User-Agent": _UA}) as client:
                r = client.get(img_url)
                r.raise_for_status()
                ctype = r.headers.get("content-type", "").split(";")[0].strip()
                if not ctype.startswith("image/"):
                    return None
                data = r.content
            if len(data) > 8 * 1024 * 1024 or len(data) < 512:
                return None
            ext = {"image/jpeg": ".jpg", "image/jpg": ".jpg",
                   "image/png": ".png", "image/webp": ".webp",
                   "image/gif": ".gif"}.get(ctype, ".jpg")
            fname = f"news_{_hid(img_url)[:10]}{ext}"
            dest = settings.images_path / fname
            dest.write_bytes(data)
            logger.info(f"article image saved: {fname} ({len(data)//1024} KB)")
            return fname
        except Exception as e:  # noqa: BLE001
            logger.warning(f"article image download failed {img_url}: {e}")
            return None

    def _enrich_blocking(self, items: list[dict],
                         summary_words: int = 150) -> list[dict]:
        out = []
        from app.services import summarizer
        for it in items:
            it = dict(it)
            link = it.get("link") or ""
            status = "skipped"
            body = ""
            if link.startswith(("http://", "https://")):
                art = self.fetch_article_text(link, summary_words)
                status = art.get("status", "?")
                body = art.get("text") or ""
                if art.get("essence"):
                    it["essence"] = art["essence"]
                if art.get("title") and not it.get("title"):
                    it["title"] = art["title"]
                img = self.download_article_image(art.get("image_url"))
                if img:
                    it["image"] = img
            # Never let junk through: if no real article essence, fall back
            # to the RSS-provided snippet (the real headline/summary).
            if not it.get("essence"):
                it["essence"] = _clean(it.get("summary"),
                                       max(360, summary_words * 7))
                if status not in ("?", "skipped"):
                    status = f"{status}+rss"
            # Optional faithful LLM summary (Anthropic) over the richest
            # text we have (full body, else title + RSS snippet). The
            # deepotus 'prophet' tone is layered on later by prompt_engine.
            if summarizer.available():
                src = body or (
                    f"{it.get('title','')}. {it.get('summary','')}").strip()
                ai = summarizer.summarize(
                    src, title=it.get("title", ""),
                    target_words=summary_words)
                if ai:
                    it["essence"] = ai
                    status = f"{status}+ai"
            it["scrape_status"] = status
            out.append(it)
        return out

    async def enrich_items(self, items: list[dict], *,
                           summary_words: int = 150) -> list[dict]:
        return await asyncio.to_thread(
            self._enrich_blocking, items, summary_words)

    def _refresh_blocking(self) -> dict:
        sources = [s for s in self.list_sources() if s.get("enabled", True)]
        items: list[dict] = []
        errors: list[dict] = []
        for s in sources:
            try:
                got = (self._fetch_article(s) if s["type"] == "article"
                       else self._fetch_rss(s))
                items.extend(got)
            except Exception as e:  # noqa: BLE001 - one source must not break all
                logger.warning(f"news fetch failed for {s['url']}: {e}")
                errors.append({"source_id": s["id"], "url": s["url"],
                               "error": str(e)[:300]})
        # dedupe by id, keep first occurrence, newest-first by published
        seen: set[str] = set()
        deduped: list[dict] = []
        for it in items:
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            deduped.append(it)
        deduped.sort(key=lambda x: x.get("published") or "", reverse=True)
        deduped = deduped[:MAX_ITEMS]
        cache = {
            "fetched_at": _now_iso(),
            "items": deduped,
            "errors": errors,
            "source_count": len(sources),
        }
        self.cache_path.write_text(
            json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        logger.info(
            f"news refresh: {len(deduped)} items from {len(sources)} sources, "
            f"{len(errors)} errors")
        return {
            "fetched_at": cache["fetched_at"],
            "item_count": len(deduped),
            "source_count": len(sources),
            "errors": errors,
        }

    async def refresh(self) -> dict:
        return await asyncio.to_thread(self._refresh_blocking)

    async def refresh_if_stale(self) -> dict | None:
        if not self._stale():
            return None
        if not self.list_sources():
            return None
        logger.info("news cache stale (>24h) - auto-refreshing")
        return await self.refresh()


news_service = NewsService()


async def news_daily_loop():
    """Background task: opportunistic daily refresh while the app runs.

    Checks hourly; only fetches when the cache is older than 24h. Fail-safe:
    never raises out of the loop (an error just retries next hour).
    """
    while True:
        try:
            await news_service.refresh_if_stale()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"news_daily_loop error (will retry): {e}")
        await asyncio.sleep(3600)
