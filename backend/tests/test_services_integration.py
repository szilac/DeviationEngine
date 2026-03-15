"""
Integration tests for service layer functions.

These tests verify that the actual service functions work correctly with the
redesigned schema. Tests use the ACTUAL function signatures, not assumed ones.
"""

import pytest
from uuid import uuid4, UUID
from datetime import date, datetime, timezone

from app.models import (
    Timeline,
    Generation,
    ScenarioType,
    NarrativeMode,
    GenerationType,
    SkeletonType,
    SkeletonStatus,
)
from app.agents.historian_agent import TimelineOutput
from app.agents.skeleton_agent import SkeletonAgentOutput, SkeletonEventOutput
from app.services import timeline_service, skeleton_service, media_service


# ============================================================================
# Timeline Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_timeline_with_initial_generation_actual(db_session):
    """Test creating a timeline using actual function signature."""
    # Create Timeline Pydantic model with a generation
    generation = Generation(
        id=uuid4(),
        timeline_id=uuid4(),  # Will be set when timeline is created
        generation_order=1,
        generation_type=GenerationType.INITIAL,
        start_year=0,
        end_year=10,
        period_years=10,
        executive_summary="Test summary",
        political_changes="Test politics",
        conflicts_and_wars="Test conflicts",
        economic_impacts="Test economy",
        social_developments="Test society",
        technological_shifts="Test tech",
        key_figures="Test figures",
        long_term_implications="Test implications",
        narrative_mode=NarrativeMode.NONE,
    )

    timeline = Timeline(
        root_deviation_date=date(1914, 6, 28),
        root_deviation_description="Franz Ferdinand survives assassination attempt",
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        generations=[generation],
    )

    # Update generation's timeline_id to match
    generation.timeline_id = timeline.id

    # Create TimelineOutput for the agent output
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

    # Call actual function
    db_timeline = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    # Verify
    assert db_timeline.id == str(timeline.id)
    assert db_timeline.root_deviation_date == "1914-06-28"
    assert db_timeline.scenario_type == ScenarioType.LOCAL_DEVIATION.value


@pytest.mark.asyncio
async def test_get_timeline_by_id_actual(db_session, timeline_with_generation):
    """Test retrieving a timeline."""
    timeline = await timeline_service.get_timeline_by_id(
        db=db_session, timeline_id=UUID(timeline_with_generation.id)
    )

    assert timeline is not None
    assert timeline.id == timeline_with_generation.id


@pytest.mark.asyncio
async def test_extend_timeline_actual(db_session, timeline_with_generation):
    """Test extending a timeline using actual function signature."""
    extension_output = TimelineOutput(
        executive_summary="Extension period",
        political_changes="Continued stability",
        conflicts_and_wars="Regional tensions",
        economic_impacts="Economic boom",
        social_developments="Social progress",
        technological_shifts="Technological advances",
        key_figures="New leaders",
        long_term_implications="Long-term peace",
    )

    new_generation = await timeline_service.extend_timeline_with_new_generation(
        db=db_session,
        timeline_id=UUID(timeline_with_generation.id),
        extension_output=extension_output,
        additional_years=10,
        narrative_mode=NarrativeMode.NONE,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    assert new_generation is not None
    assert new_generation.generation_order == 2
    assert new_generation.generation_type == GenerationType.EXTENSION.value
    assert new_generation.period_years == 10


@pytest.mark.asyncio
async def test_delete_timeline_actual(db_session, timeline_with_generation):
    """Test deleting a timeline."""
    timeline_id = timeline_with_generation.id

    success = await timeline_service.delete_timeline(
        db=db_session, timeline_id=UUID(timeline_id)
    )

    assert success is True

    # Verify deleted
    timeline = await timeline_service.get_timeline_by_id(
        db=db_session, timeline_id=UUID(timeline_id)
    )
    assert timeline is None


# ============================================================================
# Skeleton Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_timeline_draft_skeleton_actual(db_session):
    """Test creating a timeline draft skeleton using actual signature."""
    # Create skeleton agent output
    agent_output = SkeletonAgentOutput(
        events=[
            SkeletonEventOutput(
                event_date="1914-06-28",
                location="Sarajevo, Bosnia",
                description="Assassination attempt fails",
            ),
            SkeletonEventOutput(
                event_date="1914-08-01",
                location="Vienna, Austria",
                description="Diplomatic success",
            ),
        ],
        summary="Timeline following survival of Franz Ferdinand"
    )

    skeleton = await skeleton_service.create_timeline_draft_skeleton(
        db=db_session,
        deviation_date=date(1914, 6, 28),
        deviation_description="Franz Ferdinand survives",
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        simulation_years=10,
        agent_output=agent_output,
        model_provider="google",
        model_name="gemini-pro",
    )

    assert skeleton.id is not None
    assert skeleton.skeleton_type == SkeletonType.TIMELINE_DRAFT
    assert skeleton.status == SkeletonStatus.PENDING
    assert len(skeleton.events) == 2


@pytest.mark.asyncio
async def test_create_extension_draft_skeleton_actual(db_session, timeline_with_generation):
    """Test creating an extension draft skeleton."""
    agent_output = SkeletonAgentOutput(
        events=[
            SkeletonEventOutput(
                event_date="1924-01-15",
                location="Geneva, Switzerland",
                description="International conference",
            ),
        ],
        summary="Extension period with international cooperation"
    )

    skeleton = await skeleton_service.create_extension_draft_skeleton(
        db=db_session,
        parent_timeline_id=UUID(timeline_with_generation.id),
        extension_start_year=10,
        extension_end_year=20,
        agent_output=agent_output,
        model_provider="google",
        model_name="gemini-pro",
    )

    assert skeleton.id is not None
    assert skeleton.skeleton_type == SkeletonType.EXTENSION_DRAFT
    assert str(skeleton.parent_timeline_id) == timeline_with_generation.id
    assert skeleton.extension_start_year == 10
    assert skeleton.extension_end_year == 20


@pytest.mark.asyncio
async def test_get_skeleton_actual(db_session, skeleton_with_events):
    """Test retrieving a skeleton."""
    skeleton = await skeleton_service.get_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_with_events.id)
    )

    assert skeleton is not None
    assert skeleton.id == UUID(skeleton_with_events.id)
    assert len(skeleton.events) == 3


@pytest.mark.asyncio
async def test_delete_skeleton_actual(db_session, skeleton_with_events):
    """Test deleting a skeleton."""
    skeleton_id = skeleton_with_events.id

    success = await skeleton_service.delete_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_id)
    )

    assert success is True

    # Verify deleted
    skeleton = await skeleton_service.get_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_id)
    )
    assert skeleton is None


@pytest.mark.asyncio
async def test_approve_skeleton_actual(db_session, skeleton_with_events):
    """Test approving a skeleton."""
    skeleton = await skeleton_service.approve_skeleton(
        db=db_session, skeleton_id=UUID(skeleton_with_events.id)
    )

    assert skeleton.status == SkeletonStatus.APPROVED
    assert skeleton.approved_at is not None


# ============================================================================
# Media Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_media_actual(db_session, timeline_with_generation):
    """Test creating media using actual signature."""
    generation_id = UUID(timeline_with_generation.generations[0].id)

    media = await media_service.create_media(
        db=db_session,
        generation_id=generation_id,
        media_type="image",
        media_url="https://example.com/image1.jpg",
        media_order=1,
        prompt_text="Portrait of Franz Ferdinand in 1920",
        event_year=6,
        title="Franz Ferdinand in 1920",
        description="The Archduke in his later years",
        model_provider="google",
        model_name="gemini-pro",
    )

    assert media["id"] is not None
    assert media["generation_id"] == generation_id
    assert media["media_type"] == "image"
    assert media["media_url"] == "https://example.com/image1.jpg"


@pytest.mark.asyncio
async def test_get_media_by_generation_actual(db_session, timeline_with_generation):
    """Test retrieving media by generation."""
    generation_id = UUID(timeline_with_generation.generations[0].id)

    # Create some media
    await media_service.create_media(
        db=db_session,
        generation_id=generation_id,
        media_type="image",
        media_url="https://example.com/image1.jpg",
        media_order=1,
    )

    await media_service.create_media(
        db=db_session,
        generation_id=generation_id,
        media_type="image",
        media_url="https://example.com/image2.jpg",
        media_order=2,
    )

    # Retrieve
    media_list = await media_service.get_media_by_generation(
        db=db_session, generation_id=generation_id
    )

    assert len(media_list) >= 2


@pytest.mark.asyncio
async def test_get_media_by_timeline_actual(db_session, timeline_with_generation):
    """Test retrieving all media for a timeline."""
    timeline_id = UUID(timeline_with_generation.id)
    generation_id = UUID(timeline_with_generation.generations[0].id)

    # Create media
    await media_service.create_media(
        db=db_session,
        generation_id=generation_id,
        media_type="image",
        media_url="https://example.com/image1.jpg",
        media_order=1,
    )

    # Retrieve
    media_list = await media_service.get_media_by_timeline(
        db=db_session, timeline_id=timeline_id
    )

    assert len(media_list) >= 1


@pytest.mark.asyncio
async def test_delete_media_actual(db_session, timeline_with_generation):
    """Test deleting media."""
    generation_id = UUID(timeline_with_generation.generations[0].id)

    # Create media
    media = await media_service.create_media(
        db=db_session,
        generation_id=generation_id,
        media_type="image",
        media_url="https://example.com/test.jpg",
        media_order=1,
    )

    media_id = media["id"]

    # Delete
    success = await media_service.delete_media(db=db_session, media_id=media_id)

    assert success is True

    # Verify deleted
    deleted_media = await media_service.get_media(db=db_session, media_id=media_id)
    assert deleted_media is None


# ============================================================================
# Skeleton Events Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_skeleton_events_add_actual(db_session, skeleton_with_events):
    """Test adding a new event to skeleton."""
    from app.models import SkeletonEventUpdate

    new_event = SkeletonEventUpdate(
        id=None,  # No ID means create new
        event_date=date(1916, 1, 1),
        location="Paris, France",
        description="International peace summit convened",
        event_order=3,
    )

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[new_event],
        deleted_event_ids=[],
    )

    # Should now have 4 events (3 original + 1 new)
    assert len(updated_skeleton.events) == 4


@pytest.mark.asyncio
async def test_update_skeleton_events_delete_actual(db_session, skeleton_with_events):
    """Test deleting an event from skeleton."""
    event_to_delete = skeleton_with_events.events[0]

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[],
        deleted_event_ids=[UUID(event_to_delete.id)],
    )

    # Should now have 2 events (3 - 1)
    assert len(updated_skeleton.events) == 2


@pytest.mark.asyncio
async def test_update_skeleton_events_modify_actual(db_session, skeleton_with_events):
    """Test modifying an existing event."""
    from app.models import SkeletonEventUpdate

    existing_event = skeleton_with_events.events[0]

    modified_event = SkeletonEventUpdate(
        id=UUID(existing_event.id),
        event_date=date.fromisoformat(existing_event.event_date),
        location="Updated Location",
        description="Updated description for this event",
        event_order=existing_event.event_order,
    )

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[modified_event],
        deleted_event_ids=[],
    )

    # Find the updated event
    updated_event = next(
        (e for e in updated_skeleton.events if e.id == UUID(existing_event.id)), None
    )

    assert updated_event is not None
    assert updated_event.location == "Updated Location"
    assert updated_event.description == "Updated description for this event"
