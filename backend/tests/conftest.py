"""
Pytest configuration and fixtures for DeviationEngine tests.

Provides shared fixtures for database testing with the redesigned schema.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, date
from uuid import uuid4

from app.database import Base
from app.db_models import (
    TimelineDB,
    GenerationDB,
    SkeletonDB,
    SkeletonEventDB,
    MediaDB,
    LLMConfigDB,
    AgentLLMConfigDB,
)
from app.models import ScenarioType, GenerationType, SkeletonType, SkeletonStatus


# ============================================================================
# Database Setup Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def async_engine():
    """Create an in-memory SQLite database engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    """Create a database session for testing."""
    async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# ============================================================================
# Data Fixtures - Timeline
# ============================================================================


@pytest.fixture
def sample_timeline_data():
    """Sample data for creating a timeline."""
    return {
        "id": str(uuid4()),
        "root_deviation_date": "1914-06-28",
        "root_deviation_description": "Archduke Franz Ferdinand survives the assassination attempt",
        "scenario_type": ScenarioType.LOCAL_DEVIATION.value,
    }


@pytest_asyncio.fixture
async def timeline_db(db_session: AsyncSession, sample_timeline_data):
    """Create a timeline in the database for testing."""
    timeline = TimelineDB(**sample_timeline_data)
    db_session.add(timeline)
    await db_session.commit()
    await db_session.refresh(timeline)
    return timeline


@pytest_asyncio.fixture
async def timeline_with_generation(db_session: AsyncSession, timeline_db: TimelineDB):
    """Create a timeline with an initial generation."""
    generation = GenerationDB(
        id=str(uuid4()),
        timeline_id=timeline_db.id,
        generation_order=1,
        generation_type=GenerationType.INITIAL.value,
        start_year=0,
        end_year=10,
        period_years=10,
        executive_summary="WWI prevented, European stability maintained",
        political_changes="Austro-Hungarian Empire remains stable",
        conflicts_and_wars="No major European conflict",
        economic_impacts="Continued industrial growth",
        social_developments="Progressive social reforms continue",
        technological_shifts="Earlier development of aviation",
        key_figures="Franz Ferdinand remains heir apparent",
        long_term_implications="Different path for Europe",
        report_model_provider="google",
        report_model_name="gemini-pro",
    )
    db_session.add(generation)
    await db_session.commit()

    # Refresh with eager loading of relationships
    result = await db_session.execute(
        select(TimelineDB)
        .where(TimelineDB.id == timeline_db.id)
        .options(selectinload(TimelineDB.generations))
    )
    return result.scalar_one()


# ============================================================================
# Data Fixtures - Generation
# ============================================================================


@pytest.fixture
def sample_generation_data(timeline_db: TimelineDB):
    """Sample data for creating a generation."""
    return {
        "id": str(uuid4()),
        "timeline_id": timeline_db.id,
        "generation_order": 1,
        "generation_type": GenerationType.INITIAL.value,
        "start_year": 0,
        "end_year": 10,
        "period_years": 10,
        "executive_summary": "Test executive summary",
        "political_changes": "Test political changes",
        "conflicts_and_wars": "Test conflicts",
        "economic_impacts": "Test economic impacts",
        "social_developments": "Test social developments",
        "technological_shifts": "Test technological shifts",
        "key_figures": "Test key figures",
        "long_term_implications": "Test implications",
    }


# ============================================================================
# Data Fixtures - Skeleton
# ============================================================================


@pytest.fixture
def sample_skeleton_data():
    """Sample data for creating a timeline draft skeleton."""
    return {
        "id": str(uuid4()),
        "skeleton_type": SkeletonType.TIMELINE_DRAFT.value,
        "deviation_date": "1914-06-28",
        "deviation_description": "Franz Ferdinand survives",
        "scenario_type": ScenarioType.LOCAL_DEVIATION.value,
        "status": SkeletonStatus.PENDING.value,
        "model_provider": "google",
        "model_name": "gemini-pro",
    }


@pytest_asyncio.fixture
async def skeleton_db(db_session: AsyncSession, sample_skeleton_data):
    """Create a skeleton in the database for testing."""
    skeleton = SkeletonDB(**sample_skeleton_data)
    db_session.add(skeleton)
    await db_session.commit()
    await db_session.refresh(skeleton)
    return skeleton


@pytest_asyncio.fixture
async def skeleton_with_events(db_session: AsyncSession, skeleton_db: SkeletonDB):
    """Create a skeleton with events."""
    events = [
        SkeletonEventDB(
            id=str(uuid4()),
            skeleton_id=skeleton_db.id,
            event_date="1914-06-28",
            event_year=0,
            location="Sarajevo, Bosnia",
            description="Assassination attempt fails, Franz Ferdinand survives",
            event_order=0,
            is_user_added=0,
            is_user_modified=0,
        ),
        SkeletonEventDB(
            id=str(uuid4()),
            skeleton_id=skeleton_db.id,
            event_date="1914-08-01",
            event_year=0,
            location="Vienna, Austria-Hungary",
            description="Diplomatic efforts prevent escalation",
            event_order=1,
            is_user_added=0,
            is_user_modified=0,
        ),
        SkeletonEventDB(
            id=str(uuid4()),
            skeleton_id=skeleton_db.id,
            event_date="1915-01-15",
            event_year=1,
            location="Berlin, Germany",
            description="Peace conference convened",
            event_order=2,
            is_user_added=0,
            is_user_modified=0,
        ),
    ]
    for event in events:
        db_session.add(event)
    await db_session.commit()

    # Refresh with eager loading of relationships
    result = await db_session.execute(
        select(SkeletonDB)
        .where(SkeletonDB.id == skeleton_db.id)
        .options(selectinload(SkeletonDB.events))
    )
    return result.scalar_one()


@pytest.fixture
def sample_extension_skeleton_data(timeline_db: TimelineDB):
    """Sample data for creating an extension draft skeleton."""
    return {
        "id": str(uuid4()),
        "skeleton_type": SkeletonType.EXTENSION_DRAFT.value,
        "parent_timeline_id": timeline_db.id,
        "extension_start_year": 10,
        "extension_end_year": 20,
        "status": SkeletonStatus.PENDING.value,
        "model_provider": "google",
        "model_name": "gemini-pro",
    }


# ============================================================================
# Data Fixtures - Media
# ============================================================================


@pytest.fixture
def sample_media_data(timeline_with_generation):
    """Sample data for creating media."""
    generation = timeline_with_generation.generations[0]
    return {
        "id": str(uuid4()),
        "generation_id": generation.id,
        "media_type": "image",
        "media_order": 1,
        "prompt_text": "Portrait of Franz Ferdinand in 1920",
        "media_url": "https://example.com/image1.jpg",
        "event_year": 6,
        "title": "Franz Ferdinand in 1920",
        "description": "The Archduke in his later years",
        "is_user_added": 0,
        "is_user_modified": 0,
    }


@pytest_asyncio.fixture
async def media_db(db_session: AsyncSession, timeline_with_generation, sample_media_data):
    """Create media in the database for testing."""
    media = MediaDB(**sample_media_data)
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)
    return media


# ============================================================================
# Data Fixtures - LLM Config
# ============================================================================


@pytest_asyncio.fixture
async def llm_config(db_session: AsyncSession):
    """Create default LLM configuration."""
    config = LLMConfigDB(
        id=1,
        provider="google",
        model_name="gemini-pro",
        api_key_google="test-api-key",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest_asyncio.fixture
async def agent_llm_config(db_session: AsyncSession):
    """Create agent-specific LLM configuration."""
    config = AgentLLMConfigDB(
        agent_type="historian",
        provider="google",
        model_name="gemini-pro",
        enabled=1,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config
