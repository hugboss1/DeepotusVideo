"""FastAPI application entry point."""
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# ── Load the per-user .env (stable data dir) BEFORE anything reads settings.
from app.config import ENV_FILE, DATA_ROOT, PROJECT_ROOT
try:
    from dotenv import load_dotenv as _load_dotenv
    if ENV_FILE.is_file():
        _load_dotenv(str(ENV_FILE))
except Exception:
    pass

# ── TLS: use the OS trust store when available (truststore). On machines with
#    antivirus/corporate HTTPS inspection (Avast, Kaspersky, Zscaler…) the OS
#    store already contains the inspecting root, so this fixes the recurring
#    "CERTIFICATE_VERIFY_FAILED" on ANY buyer's machine — no per-machine cert
#    surgery. Falls back to certifi if truststore isn't installed.
try:
    import truststore as _truststore
    _truststore.inject_into_ssl()
except Exception:
    try:
        import certifi as _certifi
        _cert_path = os.environ.get("SSL_CERT_FILE") or _certifi.where()
        if os.path.isfile(_cert_path):
            os.environ["SSL_CERT_FILE"] = _cert_path
            os.environ["REQUESTS_CA_BUNDLE"] = _cert_path
            os.environ.setdefault("SSL_CERT_DIR", os.path.dirname(_cert_path))
    except Exception:
        pass

# Belt-and-suspenders: relax strict X.509 (intercepted certs from AV/proxies
# often lack "Basic Constraints critical"). Public CAs still validate normally.
try:
    import ssl as _ssl
    _orig_ctx = _ssl.create_default_context
    def _patched_ctx(*args, **kwargs):
        ctx = _orig_ctx(*args, **kwargs)
        try:
            ctx.verify_flags &= ~_ssl.VERIFY_X509_STRICT
        except Exception:
            pass
        return ctx
    _ssl.create_default_context = _patched_ctx
except Exception:
    pass


def _migrate_legacy_data():
    """One-time: if the data dir is empty but an OLDER version stored data
    INSIDE the install dir (pre-1.13), copy it into the stable data dir so
    keys/images/renders/DB survive the upgrade. Never overwrites existing
    data-dir files."""
    import shutil
    try:
        legacy_env = PROJECT_ROOT / "backend" / ".env"
        legacy_db = PROJECT_ROOT / "deepotus.db"
        legacy_assets = PROJECT_ROOT / "assets"
        moved = []
        if not ENV_FILE.exists() and legacy_env.is_file():
            # Carry only credentials, not legacy path overrides (DATABASE_URL /
            # IMAGES_FOLDER / OUTPUTS_FOLDER must come from the data dir).
            kept = [ln for ln in legacy_env.read_text(encoding="utf-8", errors="replace").splitlines()
                    if not ln.strip().startswith(("DATABASE_URL=", "IMAGES_FOLDER=", "OUTPUTS_FOLDER=", "SSL_CERT_FILE="))]
            ENV_FILE.write_text("\n".join(kept) + "\n", encoding="utf-8")
            moved.append(".env")
        dst_db = DATA_ROOT / "deepotus.db"
        if not dst_db.exists() and legacy_db.is_file():
            shutil.copy2(legacy_db, dst_db); moved.append("deepotus.db")
        dst_assets = DATA_ROOT / "assets"
        if not dst_assets.exists() and legacy_assets.is_dir():
            shutil.copytree(legacy_assets, dst_assets, dirs_exist_ok=True); moved.append("assets")
        if moved:
            logger.info(f"Migrated legacy in-install data -> {DATA_ROOT}: {moved}")
    except Exception as e:
        logger.warning(f"legacy data migration skipped: {e}")


_migrate_legacy_data()

from app.api.routes import router
from app.config import settings, APP_VERSION
from app.services.storage import init_db
from app.services.news_service import news_daily_loop
from app.services.marketing import schedule_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"DEEPOTUS VIDEO GEN v{APP_VERSION} — starting")
    logger.info(f"  fal.ai key: {'✓ set' if settings.FAL_KEY else '✗ missing'}")
    logger.info(f"  ElevenLabs: {'✓ set' if settings.has_voiceover else '✗ skipped'}")
    logger.info(f"  Telegram:   {'✓ set' if settings.has_telegram else '✗ skipped'}")
    logger.info(f"  Data dir:   {DATA_ROOT}")
    logger.info(f"  Images:     {settings.images_path}")
    logger.info(f"  Outputs:    {settings.outputs_path}")
    logger.info("=" * 60)
    await init_db()
    news_task = asyncio.create_task(news_daily_loop())
    sched_task = asyncio.create_task(schedule_loop())
    # v1.15.1: HeyGen's /v2/avatars is slow (60s+ for large catalogues). Warm
    # the in-process cache in the background at startup so the first time the
    # user opens the HeyGen tab the avatar list is already there (instant),
    # instead of staring at a 60s "loading" that looks like a hang. Fire and
    # forget — never blocks startup, all failures are non-fatal.
    warm_task = None
    if settings.has_heygen:
        async def _warm_heygen_cache():
            try:
                from app.services.heygen_service import HeyGenClient
                client = HeyGenClient()
                await client.list_avatars()
                await client.list_voices()
                logger.info("HeyGen avatar/voice cache warmed.")
            except Exception as e:
                logger.warning(f"HeyGen cache warm skipped (non-fatal): {e}")
        warm_task = asyncio.create_task(_warm_heygen_cache())
    try:
        yield
    finally:
        news_task.cancel()
        sched_task.cancel()
        if warm_task:
            warm_task.cancel()
        logger.info("Shutting down")


app = FastAPI(
    title="Deepotus Video Generator",
    description="Cinematic UGC video generator using Seedance 2.0 (fal.ai) + ElevenLabs",
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow Vite dev server (5173) and any local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CSRF hardening (v1.15.1): the server binds loopback, but a malicious page in
# the user's browser could still POST to 127.0.0.1:8765 and trigger
# credit-spending actions (CORS does not block the side effect of a non-GET
# request). Reject state-changing requests whose Origin is a foreign site;
# allow same-origin (localhost/127.0.0.1) and Origin-less (curl/native) calls.
import urllib.parse as _urlparse
from starlette.responses import JSONResponse as _JSONResponse

_ALLOWED_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "::1", ""}


@app.middleware("http")
async def _csrf_origin_guard(request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin:
            try:
                host = (_urlparse.urlparse(origin).hostname or "").lower()
            except Exception:
                host = "?"
            if host not in _ALLOWED_ORIGIN_HOSTS:
                return _JSONResponse(
                    {"detail": "Cross-origin request blocked"}, status_code=403)
    return await call_next(request)


app.include_router(router, prefix="/api")

# ── Guide: serve the illustrated getting-started guide (FR/EN HTML + PDF +
# screenshots) at /guide. Linked from the sidebar footer.
_guide = Path(__file__).resolve().parent.parent.parent / "docs" / "guide"
if _guide.is_dir():
    from fastapi.staticfiles import StaticFiles as _SF
    app.mount("/guide", _SF(directory=str(_guide), html=True), name="guide")
    logger.info(f"Serving guide from {_guide}")

# ── Emoji: bundled Twemoji PNGs (CC-BY) for the Studio emoji picker, at /emoji.
_emoji_dir = Path(__file__).resolve().parent / "assets" / "emoji"
if _emoji_dir.is_dir():
    from fastapi.staticfiles import StaticFiles as _SFEmoji
    app.mount("/emoji", _SFEmoji(directory=str(_emoji_dir)), name="emoji")

# ── Custom emojis: user-imported PNGs in the DATA dir (survive reinstall),
# served at /emoji-custom for the picker preview. Render reads them directly.
_emoji_custom_dir = DATA_ROOT / "assets" / "emoji_custom"
_emoji_custom_dir.mkdir(parents=True, exist_ok=True)
from fastapi.staticfiles import StaticFiles as _SFEmojiC
app.mount("/emoji-custom", _SFEmojiC(directory=str(_emoji_custom_dir)), name="emoji-custom")

# ── Packaging: serve the built frontend (frontend/dist) from this process.
# One port, one process, no Node at runtime — the silent launcher just
# starts uvicorn and opens http://127.0.0.1:8765 in the default browser.
# In dev (no dist or Vite running on 5173) this mount simply isn't hit.
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.is_dir() and (_dist / "index.html").is_file():
    from fastapi.staticfiles import StaticFiles

    class _SPAStaticFiles(StaticFiles):
        """Fall back to index.html for client-side routes (SPA).

        Also forces revalidation (no-cache) so a reinstall/update never serves
        a stale frontend from the browser cache. The compiled bundle keeps a
        stable filename across versions, so without this the browser would
        keep showing the OLD version (e.g. the v1.14 UI) until a manual
        hard-reload. With no-cache the browser revalidates and picks up the
        new files automatically after an update."""
        async def get_response(self, path, scope):
            from starlette.exceptions import HTTPException as _SHTTPException
            try:
                resp = await super().get_response(path, scope)
            except _SHTTPException as e:
                if e.status_code == 404:
                    resp = await super().get_response("index.html", scope)
                else:
                    raise
            try:
                resp.headers["Cache-Control"] = "no-cache, must-revalidate"
            except Exception:
                pass
            return resp

    app.mount("/", _SPAStaticFiles(directory=str(_dist), html=True),
              name="frontend")
    logger.info(f"Serving frontend from {_dist}")


@app.get("/")
async def root():
    return {
        "service": "deepotus-video-gen",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
