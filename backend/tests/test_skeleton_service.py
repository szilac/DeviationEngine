"""
Tests for skeleton service CRUD operations.

Tests the skeleton workflow system with the redesigned schema:
- Skeleton creation (timeline drafts, extension drafts)
- Skeleton retrieval
- Skeleton event CRUD operations
- Skeleton status management
- Skeleton deletion
"""

import pytest
from uuid import uuid4, UUID
from datetime import date
from sqlalchemy import select

from app.services import skeleton_service
from app.db_models import SkeletonDB, SkeletonEventDB
from app.models import (
    SkeletonType,
    SkeletonStatus,
    ScenarioType,
    SkeletonEventUpdate,
)
from app.agents.skeleton_agent import SkeletonAgentOutput, SkeletonEventOutput

from datetime import date as date_type


# ============================================================================
# Helper Functions
# ============================================================================


def _make_skeleton_agent_output(event_dicts):
    """Convert list of event dicts to SkeletonAgentOutput."""
    events = [
        SkeletonEventOutput(
            event_date=e["event_date"],
            location=e["location"],
            description=e["description"],
        )
        for e in event_dicts
    ]
    return SkeletonAgentOutput(events=events, summary="Test skeleton summary.")


# ============================================================================
# Skeleton Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_timeline_draft_skeleton(db_session):
    """Test creating a timeline draft skeleton."""
    skeleton_events = [
        {
            "event_date": "1914-06-28",
            "location": "Sarajevo",
            "description": "Assassination attempt prevented by intervention",
        },
        {
            "event_date": "1914-08-01",
            "location": "Vienna",
            "description": "Diplomatic success resolves the tension",
        },
    ]

    skeleton = await skeleton_service.create_timeline_draft_skeleton(
        db=db_session,
        deviation_date=date_type.fromisoformat("1914-06-28"),
        deviation_description="Franz Ferdinand survives assassination attempt",
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        simulation_years=10,
        agent_output=_make_skeleton_agent_output(skeleton_events),
        model_provider="google",
        model_name="gemini-pro",
    )

    assert skeleton.id is not None
    assert skeleton.skeleton_type == SkeletonType.TIMELINE_DRAFT
    assert skeleton.deviation_date == date_type.fromisoformat("1914-06-28")
    assert skeleton.deviation_description == "Franz Ferdinand survives assassination attempt"
    assert skeleton.scenario_type == ScenarioType.LOCAL_DEVIATION
    assert skeleton.status == SkeletonStatus.PENDING
    assert len(skeleton.events) == 2


@pytest.mark.asyncio
async def test_create_extension_draft_skeleton(db_session, timeline_with_generation):
    """Test creating an extension draft skeleton."""
    skeleton_events = [
        {
            "event_date": "1924-01-15",
            "location": "Geneva",
            "description": "International conference convenes to discuss peace",
        },
    ]

    skeleton = await skeleton_service.create_extension_draft_skeleton(
        db=db_session,
        parent_timeline_id=UUID(timeline_with_generation.id),
        extension_start_year=10,
        extension_end_year=20,
        agent_output=_make_skeleton_agent_output(skeleton_events),
        model_provider="google",
        model_name="gemini-pro",
    )

    assert skeleton.id is not None
    assert skeleton.skeleton_type == SkeletonType.EXTENSION_DRAFT
    assert str(skeleton.parent_timeline_id) == timeline_with_generation.id
    assert skeleton.extension_start_year == 10
    assert skeleton.extension_end_year == 20
    assert skeleton.status == SkeletonStatus.PENDING
    assert len(skeleton.events) == 1


# ============================================================================
# Skeleton Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_skeleton_by_id(db_session, skeleton_with_events):
    """Test retrieving a skeleton by ID."""
    skeleton = await skeleton_service.get_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_with_events.id)
    )

    assert skeleton is not None
    assert str(skeleton.id) == skeleton_with_events.id
    assert len(skeleton.events) == 3


@pytest.mark.asyncio
async def test_get_skeleton_not_found(db_session):
    """Test retrieving a non-existent skeleton."""
    fake_id = uuid4()
    skeleton = await skeleton_service.get_skeleton(db=db_session, skeleton_id=fake_id)

    assert skeleton is None


@pytest.mark.asyncio
async def test_get_all_skeletons(db_session, skeleton_with_events):
    """Test retrieving all timeline draft skeletons (not extension drafts)."""
    # Create another timeline draft
    skeleton_events = [
        {
            "event_date": "1939-09-01",
            "location": "Poland",
            "description": "WWII prevented by early diplomatic intervention",
        },
    ]

    await skeleton_service.create_timeline_draft_skeleton(
        db=db_session,
        deviation_date=date_type.fromisoformat("1939-09-01"),
        deviation_description="WWII prevented",
        scenario_type=ScenarioType.GLOBAL_DEVIATION,
        simulation_years=10,
        agent_output=_make_skeleton_agent_output(skeleton_events),
        model_provider="google",
        model_name="gemini-pro",
    )

    # Create an extension draft (should NOT be included)
    from app.services.timeline_service import create_timeline_with_initial_generation
    from app.models import Timeline, Generation, GenerationType, TimelineOutput, NarrativeMode

    timeline_output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
    )

    timeline_id = uuid4()
    gen = Generation(
        timeline_id=timeline_id,
        generation_order=1,
        generation_type=GenerationType.INITIAL,
        start_year=0,
        end_year=10,
        period_years=10,
        executive_summary="placeholder",
        political_changes="placeholder",
        conflicts_and_wars="placeholder",
        economic_impacts="placeholder",
        social_developments="placeholder",
        technological_shifts="placeholder",
        key_figures="placeholder",
        long_term_implications="placeholder",
        narrative_mode=NarrativeMode.NONE,
    )
    timeline_obj = Timeline(
        id=timeline_id,
        root_deviation_date=date_type.fromisoformat("1900-01-01"),
        root_deviation_description="Test timeline",
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        generations=[gen],
    )

    timeline = await create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    extension_events = [
        {
            "event_date": "1910-01-01",
            "location": "Test",
            "description": "Test event for the extension period",
        },
    ]

    await skeleton_service.create_extension_draft_skeleton(
        db=db_session,
        parent_timeline_id=UUID(timeline.id),
        extension_start_year=10,
        extension_end_year=20,
        agent_output=_make_skeleton_agent_output(extension_events),
        model_provider="google",
        model_name="gemini-pro",
    )

    # Get all skeletons - should only return timeline drafts
    skeletons = await skeleton_service.get_all_skeletons(db=db_session)

    # Should only have 2 timeline drafts, not the extension draft
    assert len(skeletons) == 2
    for skeleton in skeletons:
        assert skeleton.skeleton_type == SkeletonType.TIMELINE_DRAFT


# ============================================================================
# Skeleton Status Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_skeleton_status(db_session, skeleton_db):
    """Test updating skeleton status via service functions."""
    # update_skeleton_events sets status to EDITING
    updated = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_db.id),
        events_update=[],
        deleted_event_ids=[],
    )
    assert updated.status == SkeletonStatus.EDITING

    # approve_skeleton sets status to APPROVED
    updated = await skeleton_service.approve_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_db.id)
    )
    assert updated.status == SkeletonStatus.APPROVED


@pytest.mark.asyncio
async def test_approve_skeleton_sets_timestamp(db_session, skeleton_db):
    """Test that approving a skeleton sets the approved_at timestamp."""
    updated = await skeleton_service.approve_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_db.id)
    )

    assert updated.status == SkeletonStatus.APPROVED
    assert updated.approved_at is not None


# ============================================================================
# Skeleton Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_skeleton(db_session, skeleton_with_events):
    """Test deleting a skeleton."""
    skeleton_id = skeleton_with_events.id

    # Delete skeleton
    success = await skeleton_service.delete_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_id)
    )

    assert success is True

    # Verify skeleton deleted
    skeleton = await skeleton_service.get_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_id)
    )
    assert skeleton is None

    # Verify events also deleted (cascade)
    result = await db_session.execute(
        select(SkeletonEventDB).where(SkeletonEventDB.skeleton_id == skeleton_id)
    )
    events = result.scalars().all()
    assert len(events) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_skeleton(db_session):
    """Test deleting a non-existent skeleton."""
    fake_id = uuid4()
    success = await skeleton_service.delete_skeleton(db=db_session, skeleton_id=fake_id)

    assert success is False


# ============================================================================
# Skeleton Linking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_link_skeleton_to_timeline(db_session, skeleton_db, timeline_db):
    """Test linking a skeleton to a timeline."""
    await skeleton_service.link_skeleton_to_timeline(
        db=db_session,
        skeleton_id=UUID(skeleton_db.id),
        timeline_id=UUID(timeline_db.id),
    )
    updated = await skeleton_service.get_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_db.id)
    )
    assert str(updated.timeline_id) == timeline_db.id


@pytest.mark.asyncio
async def test_link_skeleton_to_generation(db_session, skeleton_db, timeline_with_generation):
    """Test linking a skeleton to a generation."""
    generation = timeline_with_generation.generations[0]

    await skeleton_service.link_skeleton_to_generation(
        db=db_session,
        skeleton_id=UUID(skeleton_db.id),
        generation_id=UUID(generation.id),
    )
    updated = await skeleton_service.get_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_db.id)
    )
    assert str(updated.generation_id) == generation.id


# ============================================================================
# Skeleton Type Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_timeline_draft_requires_deviation_fields(db_session):
    """Test that timeline draft requires deviation fields."""
    skeleton_events = [
        {
            "event_date": "1914-06-28",
            "location": "Test",
            "description": "Test event with enough description length",
        },
    ]

    # Should succeed with all required fields
    skeleton = await skeleton_service.create_timeline_draft_skeleton(
        db=db_session,
        deviation_date=date_type.fromisoformat("1914-06-28"),
        deviation_description="Test deviation",
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        simulation_years=10,
        agent_output=_make_skeleton_agent_output(skeleton_events),
        model_provider="google",
        model_name="gemini-pro",
    )

    assert skeleton.deviation_date is not None
    assert skeleton.deviation_description is not None
    assert skeleton.scenario_type is not None


@pytest.mark.asyncio
async def test_extension_draft_requires_extension_fields(db_session, timeline_with_generation):
    """Test that extension draft requires extension fields."""
    skeleton_events = [
        {
            "event_date": "1924-01-01",
            "location": "Test",
            "description": "Test event for the extension period here",
        },
    ]

    skeleton = await skeleton_service.create_extension_draft_skeleton(
        db=db_session,
        parent_timeline_id=UUID(timeline_with_generation.id),
        extension_start_year=10,
        extension_end_year=20,
        agent_output=_make_skeleton_agent_output(skeleton_events),
        model_provider="google",
        model_name="gemini-pro",
    )

    assert skeleton.parent_timeline_id is not None
    assert skeleton.extension_start_year == 10
    assert skeleton.extension_end_year == 20


# ============================================================================
# Skeleton Model Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_skeleton_tracks_model_used(db_session):
    """Test that skeleton tracks which model was used to generate it."""
    skeleton_events = [
        {
            "event_date": "1914-06-28",
            "location": "Test",
            "description": "Test event with sufficient description text",
        },
    ]

    skeleton = await skeleton_service.create_timeline_draft_skeleton(
        db=db_session,
        deviation_date=date_type.fromisoformat("1914-06-28"),
        deviation_description="Test",
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        simulation_years=10,
        agent_output=_make_skeleton_agent_output(skeleton_events),
        model_provider="openrouter",
        model_name="anthropic/claude-3-opus",
    )

    assert skeleton.model_provider == "openrouter"
    assert skeleton.model_name == "anthropic/claude-3-opus"
