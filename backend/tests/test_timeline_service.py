"""
Tests for timeline service CRUD operations.

Tests the redesigned timeline service with new schema:
- Timeline creation with generations
- Timeline retrieval
- Timeline extension
- Timeline branching
- Timeline deletion
"""

import pytest
from uuid import uuid4
from datetime import date
from sqlalchemy import select

from app.services import timeline_service
from app.db_models import TimelineDB, GenerationDB
from app.models import (
    Timeline,
    Generation,
    GenerationType,
    TimelineCreationRequest,
    ScenarioType,
    NarrativeMode,
    TimelineOutput,
)


# ============================================================================
# Helper Functions
# ============================================================================


def _make_timeline(
    deviation_date,
    deviation_description,
    scenario_type,
    period_years=10,
    narrative_mode=NarrativeMode.NONE,
    narrative_custom_pov=None,
    source_skeleton_id=None,
    storyteller_provider=None,
    storyteller_model_name=None,
):
    """Helper to create a Timeline pydantic object for service tests."""
    timeline_id = uuid4()
    gen = Generation(
        timeline_id=timeline_id,
        generation_order=1,
        generation_type=GenerationType.INITIAL,
        start_year=0,
        end_year=period_years,
        period_years=period_years,
        executive_summary="placeholder",
        political_changes="placeholder",
        conflicts_and_wars="placeholder",
        economic_impacts="placeholder",
        social_developments="placeholder",
        technological_shifts="placeholder",
        key_figures="placeholder",
        long_term_implications="placeholder",
        narrative_mode=narrative_mode,
        narrative_custom_pov=narrative_custom_pov,
        source_skeleton_id=source_skeleton_id,
    )
    return Timeline(
        id=timeline_id,
        root_deviation_date=deviation_date if isinstance(deviation_date, date) else date.fromisoformat(deviation_date),
        root_deviation_description=deviation_description,
        scenario_type=scenario_type,
        generations=[gen],
    )


# ============================================================================
# Timeline Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_timeline_with_initial_generation(db_session, sample_timeline_data):
    """Test creating a timeline with an initial generation."""
    # Create TimelineOutput for the generation
    timeline_output = TimelineOutput(
        executive_summary="WWI prevented",
        political_changes="Austro-Hungarian stability",
        conflicts_and_wars="No major conflict",
        economic_impacts="Continued growth",
        social_developments="Progressive reforms",
        technological_shifts="Aviation advances",
        key_figures="Franz Ferdinand",
        long_term_implications="Different Europe",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.NONE,
    )

    # Create timeline
    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )
    # Reload with eager-loaded generations
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    # Verify timeline created
    assert timeline.id is not None
    assert timeline.root_deviation_date == "1914-06-28"
    assert timeline.root_deviation_description == sample_timeline_data["root_deviation_description"]
    assert timeline.scenario_type == ScenarioType.LOCAL_DEVIATION.value

    # Verify generation created
    assert len(timeline.generations) == 1
    generation = timeline.generations[0]
    assert generation.generation_order == 1
    assert generation.generation_type == GenerationType.INITIAL.value
    assert generation.start_year == 0
    assert generation.end_year == 10
    assert generation.period_years == 10
    assert generation.executive_summary == "WWI prevented"


@pytest.mark.asyncio
async def test_create_timeline_with_narrative(db_session, sample_timeline_data):
    """Test creating a timeline with narrative mode."""
    timeline_output = TimelineOutput(
        executive_summary="WWI prevented",
        political_changes="Austro-Hungarian stability",
        conflicts_and_wars="No major conflict",
        economic_impacts="Continued growth",
        social_developments="Progressive reforms",
        technological_shifts="Aviation advances",
        key_figures="Franz Ferdinand",
        long_term_implications="Different Europe",
        narrative_prose="The year 1914 began differently in this world...",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.BASIC,
        narrative_custom_pov="A Viennese journalist",
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert generation.narrative_mode == NarrativeMode.BASIC.value
    assert generation.narrative_prose == "The year 1914 began differently in this world..."
    assert generation.narrative_custom_pov == "A Viennese journalist"


@pytest.mark.asyncio
async def test_create_timeline_with_skeleton(db_session, skeleton_with_events):
    """Test creating a timeline from a skeleton."""
    timeline_output = TimelineOutput(
        executive_summary="Based on skeleton events",
        political_changes="Diplomatic efforts succeed",
        conflicts_and_wars="Peace maintained",
        economic_impacts="Stable growth",
        social_developments="Cultural development",
        technological_shifts="Gradual innovation",
        key_figures="Franz Ferdinand, diplomats",
        long_term_implications="Peaceful Europe",
    )

    from uuid import UUID
    timeline_obj = _make_timeline(
        deviation_date=skeleton_with_events.deviation_date,
        deviation_description=skeleton_with_events.deviation_description,
        scenario_type=ScenarioType(skeleton_with_events.scenario_type),
        period_years=10,
        narrative_mode=NarrativeMode.NONE,
        source_skeleton_id=UUID(skeleton_with_events.id),
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert str(generation.source_skeleton_id) == skeleton_with_events.id


# ============================================================================
# Timeline Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_timeline_by_id(db_session, timeline_with_generation):
    """Test retrieving a timeline by ID."""
    timeline = await timeline_service.get_timeline_by_id(
        db=db_session, timeline_id=timeline_with_generation.id
    )

    assert timeline is not None
    assert timeline.id == timeline_with_generation.id
    assert len(timeline.generations) == 1


@pytest.mark.asyncio
async def test_get_timeline_not_found(db_session):
    """Test retrieving a non-existent timeline."""
    fake_id = str(uuid4())
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=fake_id)

    assert timeline is None


@pytest.mark.asyncio
async def test_get_all_timelines(db_session, timeline_with_generation):
    """Test retrieving all timelines."""
    # Create another timeline
    timeline_output = TimelineOutput(
        executive_summary="Different scenario",
        political_changes="Different politics",
        conflicts_and_wars="Different conflicts",
        economic_impacts="Different economy",
        social_developments="Different society",
        technological_shifts="Different tech",
        key_figures="Different figures",
        long_term_implications="Different implications",
    )

    timeline_obj = _make_timeline(
        deviation_date="1939-09-01",
        deviation_description="WWII prevented",
        scenario_type=ScenarioType.GLOBAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.NONE,
    )

    await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    timelines = await timeline_service.get_all_timelines(db=db_session)


    assert len(timelines) == 2
    # Should be ordered by created_at desc (newest first)
    assert timelines[0].root_deviation_date == "1939-09-01"
    assert timelines[1].root_deviation_date == "1914-06-28"


# ============================================================================
# Timeline Extension Tests
# ============================================================================


@pytest.mark.asyncio
async def test_extend_timeline_with_new_generation(db_session, timeline_with_generation):
    """Test extending a timeline with a new generation."""
    timeline_id = timeline_with_generation.id  # Capture before expire_all()

    extension_output = TimelineOutput(
        executive_summary="Continuation of peaceful timeline",
        political_changes="Further democratization",
        conflicts_and_wars="Regional tensions managed",
        economic_impacts="Industrial boom",
        social_developments="Women's suffrage advances",
        technological_shifts="Radio and aviation",
        key_figures="New generation of leaders",
        long_term_implications="Stable international order",
    )

    new_generation = await timeline_service.extend_timeline_with_new_generation(
        db=db_session,
        timeline_id=timeline_id,
        extension_output=extension_output,
        additional_years=10,
        narrative_mode=NarrativeMode.NONE,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    # Verify new generation
    assert new_generation.generation_order == 2
    assert new_generation.generation_type == GenerationType.EXTENSION.value
    assert new_generation.start_year == 10
    assert new_generation.end_year == 20
    assert new_generation.period_years == 10

    # Expire cached objects so get_timeline_by_id fetches fresh data
    db_session.expire_all()
    # Verify timeline now has 2 generations
    timeline = await timeline_service.get_timeline_by_id(
        db=db_session, timeline_id=timeline_id
    )
    assert len(timeline.generations) == 2


@pytest.mark.asyncio
async def test_extend_timeline_with_skeleton(db_session, timeline_with_generation):
    """Test extending a timeline using a skeleton."""
    # Create extension skeleton
    from app.db_models import SkeletonDB
    from app.models import SkeletonType, SkeletonStatus
    from uuid import UUID

    extension_skeleton = SkeletonDB(
        id=str(uuid4()),
        skeleton_type=SkeletonType.EXTENSION_DRAFT.value,
        parent_timeline_id=timeline_with_generation.id,
        extension_start_year=10,
        extension_end_year=20,
        status=SkeletonStatus.APPROVED.value,
    )
    db_session.add(extension_skeleton)
    await db_session.commit()

    extension_output = TimelineOutput(
        executive_summary="Extension from skeleton",
        political_changes="Skeleton-based politics",
        conflicts_and_wars="Skeleton-based conflicts",
        economic_impacts="Skeleton-based economy",
        social_developments="Skeleton-based society",
        technological_shifts="Skeleton-based tech",
        key_figures="Skeleton-based figures",
        long_term_implications="Skeleton-based implications",
    )

    new_generation = await timeline_service.extend_timeline_with_new_generation(
        db=db_session,
        timeline_id=timeline_with_generation.id,
        extension_output=extension_output,
        additional_years=10,
        narrative_mode=NarrativeMode.NONE,
        historian_provider="google",
        historian_model_name="gemini-pro",
        source_skeleton_id=UUID(extension_skeleton.id),
    )

    assert str(new_generation.source_skeleton_id) == extension_skeleton.id


# ============================================================================
# Timeline Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_timeline(db_session, timeline_with_generation):
    """Test deleting a timeline."""
    timeline_id = timeline_with_generation.id

    # Delete timeline
    success = await timeline_service.delete_timeline(db=db_session, timeline_id=timeline_id)

    assert success is True

    # Verify timeline deleted
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=timeline_id)
    assert timeline is None

    # Verify generations also deleted (cascade)
    result = await db_session.execute(
        select(GenerationDB).where(GenerationDB.timeline_id == timeline_id)
    )
    generations = result.scalars().all()
    assert len(generations) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_timeline(db_session):
    """Test deleting a non-existent timeline."""
    fake_id = str(uuid4())
    success = await timeline_service.delete_timeline(db=db_session, timeline_id=fake_id)

    assert success is False


# ============================================================================
# Timeline Metadata Tests
# ============================================================================


@pytest.mark.asyncio
async def test_timeline_total_years_simulated(db_session, timeline_with_generation):
    """Test calculating total years simulated in a timeline."""
    timeline_id = timeline_with_generation.id  # Capture before expire_all()

    # Add extension
    extension_output = TimelineOutput(
        executive_summary="Extension",
        political_changes="Politics",
        conflicts_and_wars="Conflicts",
        economic_impacts="Economy",
        social_developments="Society",
        technological_shifts="Tech",
        key_figures="Figures",
        long_term_implications="Implications",
    )

    await timeline_service.extend_timeline_with_new_generation(
        db=db_session,
        timeline_id=timeline_id,
        extension_output=extension_output,
        additional_years=15,
        narrative_mode=NarrativeMode.NONE,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    # Expire cached objects then refresh timeline
    db_session.expire_all()
    timeline = await timeline_service.get_timeline_by_id(
        db=db_session, timeline_id=timeline_id
    )

    # Verify total years: first generation (0-10) + extension (10-25) = 25 years total
    # total_years_simulated should be max end_year
    latest_gen = max(timeline.generations, key=lambda g: g.generation_order)
    assert latest_gen.end_year == 25
