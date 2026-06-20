"""Application configuration.

Data location rule (v1.13):
- User data (.env keys, images, renders, deepotus.db, branding) lives in a
  STABLE per-user data directory OUTSIDE the install folder, so reinstalling
  or updating the app never orphans it. Override with DEEPOTUS_DATA_DIR.
  Default on Windows: %LOCALAPPDATA%\\DeepotusVideoGenData.
- Absolute path settings are used as-is; relative ones resolve under the
  data directory.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root = parent of backend/ (the install dir — CODE only, no user data)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Single source of truth for the app version (health endpoint, FastAPI docs,
# packaging scripts). Bump here only.
APP_VERSION = "1.15.2"


def _data_root() -> Path:
    """Stable per-user data dir, separate from the install dir."""
    env = os.environ.get("DEEPOTUS_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        return Path(local) / "DeepotusVideoGenData"
    return Path.home() / ".deepotus-video-gen"


DATA_ROOT = _data_root()
DATA_ROOT.mkdir(parents=True, exist_ok=True)
ENV_FILE = DATA_ROOT / ".env"

# Load the saved per-user .env into the process environment with OVERRIDE, BEFORE
# Settings() is instantiated below. pydantic reads OS env vars with precedence
# over its env_file, so a launcher/shell/old-installer that exported an empty or
# stale var (e.g. FAL_KEY="", a relative DATABASE_URL, an old IMAGES_FOLDER) would
# otherwise SHADOW the real saved keys — making a relaunch look like "lost
# connection to providers / library". Forcing the data-dir .env to win fixes that
# on any machine.
try:
    from dotenv import load_dotenv as _load_dotenv
    if ENV_FILE.is_file():
        _load_dotenv(str(ENV_FILE), override=True)
except Exception:
    pass


def resolve_path(raw: str) -> Path:
    """Absolute -> as-is. Relative -> resolved under the data directory."""
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (DATA_ROOT / p).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # fal.ai (required)
    FAL_KEY: str = ""

    # ElevenLabs (optional)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID_EN: str = "21m00Tcm4TlvDq8ikWAM"
    ELEVENLABS_VOICE_ID_FR: str = "ThT5KcBeYPX3keUQqHPh"

    # HeyGen (optional, v1.4) - required for avatar/composition features
    HEYGEN_API_KEY: str = ""

    # Paths -- absolute used as-is; relative resolved under the data dir.
    IMAGES_FOLDER: str = "./assets/images"
    OUTPUTS_FOLDER: str = "./assets/outputs"
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(DATA_ROOT / 'deepotus.db').as_posix()}"

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8765

    # Pipeline defaults
    DEFAULT_VIDEO_DURATION: int = 5
    DEFAULT_ASPECT_RATIO: str = "9:16"
    DEFAULT_RESOLUTION: str = "1080p"
    DEFAULT_LANGUAGE: str = "EN"

    # News scraper (v1.7.x): third-party reader proxy fallback (r.jina.ai)
    # for Google-News-wrapped / hard-blocked articles. ON by default — when
    # it triggers, the target URL is sent to that public reader to recover
    # the body. Set to false to never contact a third party.
    ARTICLE_READER_FALLBACK: bool = True

    # Optional Anthropic summariser (v1.7.x): when ANTHROPIC_API_KEY is set,
    # selected articles get a faithful neutral 2-3 sentence summary BEFORE
    # the deepotus 'prophet' tone is applied. Empty -> deterministic path.
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"

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

    # v1.9: publishing channels (all optional, BYO keys).
    # Telegram is the reference auto-publish channel: free, no review process.
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # v1.11: local LLM via Ollama (optional). When OLLAMA_MODEL is set, the
    # marketing plan generator uses your local model — plans never leave the
    # machine and cost nothing. Priority: Anthropic > Ollama > built-in.
    # Recommended models: qwen2.5:14b-instruct or better; 8B is the floor.
    OLLAMA_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = ""

    # v1.10: X (Twitter) auto-publish — OAuth 1.0a user-context keys from
    # developer.x.com (free tier allows writes). All four are required.
    X_API_KEY: str = ""
    X_API_SECRET: str = ""
    X_ACCESS_TOKEN: str = ""
    X_ACCESS_SECRET: str = ""

    @property
    def images_path(self) -> Path:
        p = resolve_path(self.IMAGES_FOLDER)
        p.mkdir(parents=True, exist_ok=True)  # auto-create
        return p

    @property
    def outputs_path(self) -> Path:
        p = resolve_path(self.OUTPUTS_FOLDER)
        p.mkdir(parents=True, exist_ok=True)
        (p / "videos").mkdir(exist_ok=True)
        (p / "audio").mkdir(exist_ok=True)
        (p / "final").mkdir(exist_ok=True)
        (p / "captions").mkdir(exist_ok=True)
        return p

    @property
    def has_voiceover(self) -> bool:
        return bool(self.ELEVENLABS_API_KEY.strip())

    @property
    def has_heygen(self) -> bool:
        return bool(self.HEYGEN_API_KEY.strip())

    @property
    def has_summarizer(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY.strip())

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY.strip())

    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY.strip())

    @property
    def has_any_llm(self) -> bool:
        return self.has_summarizer or self.has_openai or self.has_gemini or self.has_ollama

    @property
    def has_telegram(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN.strip()
                    and self.TELEGRAM_CHAT_ID.strip())

    @property
    def has_ollama(self) -> bool:
        return bool(self.OLLAMA_MODEL.strip())

    @property
    def has_x(self) -> bool:
        return all(v.strip() for v in (
            self.X_API_KEY, self.X_API_SECRET,
            self.X_ACCESS_TOKEN, self.X_ACCESS_SECRET))


settings = Settings()

# v1.15.1 (sellable): TLS verification is ON by default. The OS trust store
# (truststore, injected in main.py) covers AV/corporate HTTPS inspection, so
# real verification works on buyers' machines. Locked-down networks can opt
# OUT with DEEPOTUS_INSECURE_SSL=1 (legacy bypass). Services pass
# verify=SSL_VERIFY to every httpx client.
INSECURE_SSL = os.environ.get("DEEPOTUS_INSECURE_SSL", "").strip() == "1"
SSL_VERIFY = not INSECURE_SSL
