"""SQLite-backed job persistence — v1.2 with new fields + auto-migration."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from loguru import logger

from app.config import settings


class Base(DeclarativeBase):
    pass


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    image_filename: Mapped[str] = mapped_column(String(255))
    image_filename_end: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    final_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    final_video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    caption_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caption_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    style: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    template_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    voiceover_language: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    voice_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    composition_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    composition_layout: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    layer_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    batch_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # v1.15.6 — JSON cost inputs for /cost/usage (episodes: images + narration chars)
    cost_meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ScheduledPost(Base):
    """v1.9 — one planned publication. Created by hand in the Scheduler or
    materialized from a marketing plan. The schedule loop fires due posts:
    mode='auto' publishes to capable channels (Telegram); mode='assisted'
    flips the post to 'ready' so the user posts manually with one click."""
    __tablename__ = "scheduled_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channels: Mapped[str] = mapped_column(String(120), default="x")  # csv
    run_at: Mapped[datetime] = mapped_column(DateTime, index=True)   # UTC
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    # draft | scheduled | ready | posted | failed
    mode: Mapped[str] = mapped_column(String(12), default="assisted")  # auto | assisted
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hook: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    script_idea: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_idea: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # v1.10 — analytics loop: the tweet id when posted via the X adapter,
    # and a JSON blob of public metrics (impressions, likes, …) refreshed
    # best-effort by the daily metrics pass. Feeds the plan generator.
    x_post_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # v1.12 — resolved visual source for the post's render (a library image
    # filename used as the Seedance start frame / the post's still). Set in
    # the plan's Sources step; the Produce button uses it instead of
    # generating a fresh frame.
    source_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


_engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


# Columns added in v1.2 — for SQLite auto-migration from v1.1 DBs
# Columns added in v1.3 — added to same list for forward-compat
V1_2_NEW_COLUMNS = [
    ("image_filename_end", "VARCHAR(255)"),
    ("seed", "INTEGER"),
    ("duration_s", "INTEGER"),
    ("aspect_ratio", "VARCHAR(10)"),
    ("style", "VARCHAR(20)"),
    ("template_id", "VARCHAR(60)"),
    ("voiceover_language", "VARCHAR(4)"),
    ("current_step", "VARCHAR(80)"),
    # v1.3 additions
    ("batch_id", "VARCHAR(36)"),
    ("batch_index", "INTEGER"),
    ("batch_size", "INTEGER"),
    # v1.3.1 additions
    ("voice_mode", "VARCHAR(20)"),
    # v1.4 additions
    ("provider", "VARCHAR(20)"),
    ("composition_id", "VARCHAR(36)"),
    ("composition_layout", "VARCHAR(30)"),
    ("layer_index", "INTEGER"),
    # v1.7.2 additions
    ("title", "VARCHAR(200)"),
    # v1.15.6 — episode/voiceover cost inputs (JSON: images + narration chars)
    ("cost_meta", "TEXT"),
]


# v1.9 — full expected shape of scheduled_posts, for auto-ALTER when an
# older/stub table already exists (create_all never alters existing tables).
SCHEDULED_POSTS_COLUMNS = [
    ("title", "VARCHAR(200)"),
    ("caption", "TEXT"),
    ("channels", "VARCHAR(120)"),
    ("run_at", "DATETIME"),
    ("status", "VARCHAR(20)"),
    ("mode", "VARCHAR(12)"),
    ("job_id", "VARCHAR(36)"),
    ("format", "VARCHAR(20)"),
    ("hook", "TEXT"),
    ("script_idea", "TEXT"),
    ("image_idea", "TEXT"),
    ("plan_id", "VARCHAR(36)"),
    ("error", "TEXT"),
    ("created_at", "DATETIME"),
    ("posted_at", "DATETIME"),
    # v1.10 additions
    ("x_post_id", "VARCHAR(40)"),
    ("metrics", "TEXT"),
    # v1.12 additions
    ("source_image", "VARCHAR(255)"),
]


async def _auto_migrate():
    """Add new columns to existing tables without losing data."""
    async with _engine.begin() as conn:
        # v1.9 — the Reef design pack shipped a scheduled_posts stub with an
        # incompatible NOT NULL `scheduled_at` column. Rebuild: rename the
        # old table (kept as backup), recreate the real shape, copy rows.
        result = await conn.execute(text("PRAGMA table_info(scheduled_posts)"))
        sp_cols = {row[1] for row in result.fetchall()}
        if "scheduled_at" in sp_cols:
            logger.info("Auto-migrating: rebuilding legacy scheduled_posts "
                        "(design-pack stub shape)")
            await conn.execute(text(
                "ALTER TABLE scheduled_posts RENAME TO scheduled_posts_legacy"))
            # SQLite index names are database-global and survive the rename;
            # drop the legacy ones so the fresh table can recreate them.
            for idx in ("ix_scheduled_posts_status",
                        "ix_scheduled_posts_run_at",
                        "ix_scheduled_posts_plan_id",
                        "ix_scheduled_posts_scheduled_at"):
                await conn.execute(text(f"DROP INDEX IF EXISTS {idx}"))
            await conn.run_sync(
                lambda sc: Base.metadata.tables["scheduled_posts"].create(sc))
            await conn.execute(text("""
                INSERT INTO scheduled_posts
                    (id, title, caption, channels, run_at, status, mode,
                     job_id, format, hook, script_idea, image_idea, plan_id,
                     error, created_at, posted_at)
                SELECT id,
                       COALESCE(title, ''),
                       caption,
                       COALESCE(channels, 'x'),
                       COALESCE(run_at, scheduled_at),
                       COALESCE(status, 'draft'),
                       COALESCE(mode, 'assisted'),
                       COALESCE(job_id, render_job_id),
                       format, hook, script_idea, image_idea, plan_id,
                       error,
                       COALESCE(created_at, scheduled_at),
                       posted_at
                FROM scheduled_posts_legacy
            """))
            logger.info("scheduled_posts rebuilt; old data kept in "
                        "scheduled_posts_legacy")
        else:
            # Recovery path: a previous rebuild attempt renamed the stub but
            # crashed before copying (SQLite auto-commits DDL). If a legacy
            # table still holds rows that never made it over, copy them once.
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='scheduled_posts_legacy'"))
            if result.fetchone() and "run_at" in sp_cols:
                await conn.execute(text("""
                    INSERT INTO scheduled_posts
                        (id, title, caption, channels, run_at, status, mode,
                         job_id, format, hook, script_idea, image_idea,
                         plan_id, error, created_at, posted_at)
                    SELECT id, COALESCE(title, ''), caption,
                           COALESCE(channels, 'x'),
                           COALESCE(run_at, scheduled_at),
                           COALESCE(status, 'draft'),
                           COALESCE(mode, 'assisted'),
                           COALESCE(job_id, render_job_id),
                           format, hook, script_idea, image_idea, plan_id,
                           error, COALESCE(created_at, scheduled_at), posted_at
                    FROM scheduled_posts_legacy
                    WHERE id NOT IN (SELECT id FROM scheduled_posts)
                """))

        for table, columns in (("jobs", V1_2_NEW_COLUMNS),
                               ("scheduled_posts", SCHEDULED_POSTS_COLUMNS)):
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            existing_cols = {row[1] for row in result.fetchall()}
            if not existing_cols:
                continue  # Table doesn't exist yet, create_all handles it
            for col_name, col_type in columns:
                if col_name not in existing_cols:
                    logger.info(f"Auto-migrating: ALTER TABLE {table} "
                                f"ADD COLUMN {col_name} {col_type}")
                    await conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))


async def init_db():
    # Create tables (no-op if already exist)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Then auto-migrate any v1.1 DB that's missing v1.2 columns
    await _auto_migrate()


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
