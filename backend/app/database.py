"""
Database configuration and session management for SQLite.

This module sets up SQLAlchemy with async support for SQLite database.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, event, text
from sqlalchemy.pool import NullPool
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR}/timelines.db"

# Create async engine with foreign key enforcement
# For aiosqlite, we use connect_args to enable foreign keys
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",  # Log SQL queries in debug mode
    future=True,
    poolclass=NullPool,  # Disable connection pooling for SQLite
    connect_args={
        "check_same_thread": False,  # Allow multi-threaded access
    },
)


# Enable foreign keys and WAL mode for each connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints and WAL mode for each new SQLite connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # Better concurrency
    cursor.close()


logger.info("Database engine configured with foreign key enforcement")

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            # Enable foreign keys for this session
            await session.execute(text("PRAGMA foreign_keys=ON"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database by creating all tables.

    Should be called on application startup.
    """
    async with engine.begin() as conn:
        # Enable foreign keys for this connection
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=WAL"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized with foreign key enforcement enabled")

    # Seed default LLM configuration if not exists
    await _seed_llm_config()

    # Seed default translation configuration if not exists
    await _seed_translation_config()

    # Seed system audio presets if not exists
    await _seed_audio_presets()


async def _seed_llm_config():
    """
    Seed default LLM configuration from environment variables.

    Creates the singleton LLM config row if it doesn't exist.
    Uses environment variables for default values:
    - DEFAULT_LLM_PROVIDER (default: "google")
    - DEFAULT_LLM_MODEL (default: "gemini-2.5-flash")
    - GEMINI_API_KEY (optional, can be None)
    - OPENROUTER_API_KEY (optional, can be None)
    """
    # Import here to avoid circular imports
    from app.db_models import LLMConfigDB
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as session:
        try:
            # Check if config already exists
            result = await session.execute(select(LLMConfigDB).where(LLMConfigDB.id == 1))
            existing_config = result.scalar_one_or_none()

            if existing_config is None:
                # Create default configuration
                default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "google")
                default_model = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
                api_key_google = os.getenv("GEMINI_API_KEY")
                api_key_openrouter = os.getenv("OPENROUTER_API_KEY")

                default_config = LLMConfigDB(
                    id=1,
                    provider=default_provider,
                    model_name=default_model,
                    api_key_google=api_key_google,
                    api_key_openrouter=api_key_openrouter,
                    api_key_anthropic=os.getenv("ANTHROPIC_API_KEY"),
                    api_key_openai=os.getenv("OPENAI_API_KEY"),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                session.add(default_config)
                await session.commit()

                logger.info(
                    f"Seeded default LLM config: provider={default_provider}, "
                    f"model={default_model}"
                )
            else:
                logger.debug("LLM config already exists, skipping seed")

        except Exception as e:
            logger.error(f"Error seeding LLM config: {e}")
            await session.rollback()
            raise


async def _seed_translation_config():
    """
    Seed default translation configuration from environment variables.

    Creates the singleton translation config row if it doesn't exist.
    Uses environment variables for default values:
    - DEEPL_API_KEY (optional, can be empty string if not configured)
    - DEEPL_API_TIER (default: "free")
    - DEEPL_ENABLED (default: "false")
    """
    # Import here to avoid circular imports
    from app.db_models import TranslationConfigDB
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as session:
        try:
            # Check if config already exists
            result = await session.execute(
                select(TranslationConfigDB).where(TranslationConfigDB.id == 1)
            )
            existing_config = result.scalar_one_or_none()

            if existing_config is None:
                # Get configuration from environment
                api_key = os.getenv("DEEPL_API_KEY", "")
                api_tier = os.getenv("DEEPL_API_TIER", "free")
                enabled_str = os.getenv("DEEPL_ENABLED", "false").lower()
                enabled = 1 if enabled_str in ("true", "1", "yes") and api_key else 0

                default_config = TranslationConfigDB(
                    id=1,
                    api_key=api_key if api_key else "not_configured",
                    api_tier=api_tier,
                    enabled=enabled,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                session.add(default_config)
                await session.commit()

                logger.info(
                    f"Seeded default translation config: tier={api_tier}, "
                    f"enabled={bool(enabled)}, "
                    f"api_key_set={bool(api_key)}"
                )
            else:
                logger.debug("Translation config already exists, skipping seed")

        except Exception as e:
            logger.error(f"Error seeding translation config: {e}")
            await session.rollback()
            raise


async def _seed_audio_presets():
    """
    Seed system audio script presets.

    Creates the 4 built-in presets for audio script generation if they don't exist:
    - Documentary Narration (single voice)
    - Two Participant Debate (dual voice podcast)
    - Historical News Bulletin (single voice, fast-paced)
    - Narrative Storytelling (single voice, dramatic)
    """
    # Import here to avoid circular imports
    from app.db_models import ScriptPresetDB
    from datetime import datetime, timezone
    import json

    async with AsyncSessionLocal() as session:
        try:
            # Check if system presets already exist
            result = await session.execute(
                select(ScriptPresetDB).where(ScriptPresetDB.is_system == 1)
            )
            existing_presets = result.scalars().all()

            if len(existing_presets) > 0:
                logger.debug(f"Audio presets already seeded ({len(existing_presets)} system presets found)")
                return

            # Define system presets
            now = datetime.now(timezone.utc)

            system_presets = [
                ScriptPresetDB(
                    id="preset-documentary",
                    name="Documentary Narration",
                    description="Professional single-narrator documentary style with authoritative tone",
                    script_type="documentary",
                    tone="authoritative",
                    pacing="medium",
                    voice_count=1,
                    voice_roles=json.loads('{"primary": "narrator"}'),
                    style_instructions=(
                        "Use formal, educational tone. Structure chronologically. "
                        "Include dramatic pauses and emphasis on key moments. "
                        "Maintain scholarly credibility while being engaging."
                    ),
                    prompt_template_name="script_writer/documentary.jinja2",
                    is_system=1,
                    is_active=1,
                    created_at=now,
                    updated_at=now,
                ),
                ScriptPresetDB(
                    id="preset-podcast-historians",
                    name="Two Participants Debate",
                    description="Conversational podcast format with two participants debating alternate history",
                    script_type="podcast",
                    tone="casual",
                    pacing="medium",
                    voice_count=2,
                    voice_roles=json.loads('{"primary": "host", "secondary": "expert"}'),
                    style_instructions=(
                        "Create natural back-and-forth dialogue. Host asks questions, "
                        "expert provides analysis. Include occasional humor and tangents. "
                        "Make it feel like a real conversation."
                    ),
                    prompt_template_name="script_writer/podcast_debate.jinja2",
                    is_system=1,
                    is_active=1,
                    created_at=now,
                    updated_at=now,
                ),
                ScriptPresetDB(
                    id="preset-news",
                    name="Historical News Bulletin",
                    description="Fast-paced news report style covering key events",
                    script_type="news_report",
                    tone="neutral",
                    pacing="fast",
                    voice_count=1,
                    voice_roles=json.loads('{"primary": "anchor"}'),
                    style_instructions=(
                        "Concise, factual delivery. Inverted pyramid structure. "
                        "Lead with most important events. Use short, punchy sentences. "
                        "Professional broadcast tone."
                    ),
                    prompt_template_name="script_writer/news_bulletin.jinja2",
                    is_system=1,
                    is_active=1,
                    created_at=now,
                    updated_at=now,
                ),
                ScriptPresetDB(
                    id="preset-storytelling",
                    name="Narrative Storytelling",
                    description="Engaging storytelling with dramatic flair and emotional resonance",
                    script_type="storytelling",
                    tone="dramatic",
                    pacing="slow",
                    voice_count=1,
                    voice_roles=json.loads('{"primary": "storyteller"}'),
                    style_instructions=(
                        "Use vivid imagery and emotional language. Build tension and resolution. "
                        "Personal perspective on historical events. Slower pacing with dramatic pauses."
                    ),
                    prompt_template_name="script_writer/storytelling.jinja2",
                    is_system=1,
                    is_active=1,
                    created_at=now,
                    updated_at=now,
                ),
            ]

            # Add all presets
            for preset in system_presets:
                session.add(preset)

            await session.commit()

            logger.info(
                f"Seeded {len(system_presets)} system audio presets: "
                f"{', '.join([p.name for p in system_presets])}"
            )

        except Exception as e:
            logger.error(f"Error seeding audio presets: {e}")
            await session.rollback()
            raise