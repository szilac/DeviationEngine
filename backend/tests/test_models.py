"""
Tests for Pydantic models validation.

Tests request/response models to ensure they properly validate data and
handle the new schema fields correctly.
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError
from uuid import uuid4

from app.models import (
    TimelineCreationRequest,
    ScenarioType,
    NarrativeMode,
    TimelineOutput,
    SkeletonEventUpdate,
    SkeletonEventsUpdateRequest,
    GenerationType,
    SkeletonType,
    SkeletonStatus,
)


# ============================================================================
# TimelineCreationRequest Validation Tests
# ============================================================================


def test_timeline_creation_request_valid():
    """Test creating a valid TimelineCreationRequest."""
    request = TimelineCreationRequest(
        deviation_date=date(1914, 6, 28),
        deviation_description="Franz Ferdinand survives assassination attempt",
        simulation_years=10,
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        narrative_mode=NarrativeMode.NONE,
    )

    assert request.deviation_date == date(1914, 6, 28)
    assert request.simulation_years == 10
    assert request.scenario_type == ScenarioType.LOCAL_DEVIATION
    assert request.narrative_mode == NarrativeMode.NONE


def test_timeline_creation_request_with_custom_pov():
    """Test TimelineCreationRequest with custom POV narrative."""
    request = TimelineCreationRequest(
        deviation_date=date(1914, 6, 28),
        deviation_description="Franz Ferdinand survives",
        simulation_years=10,
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        narrative_mode=NarrativeMode.ADVANCED_CUSTOM_POV,
        narrative_custom_pov="A Viennese journalist",
    )

    assert request.narrative_mode == NarrativeMode.ADVANCED_CUSTOM_POV
    assert request.narrative_custom_pov == "A Viennese journalist"


def test_timeline_creation_request_description_too_short():
    """Test that deviation_description has minimum length."""
    with pytest.raises(ValidationError) as exc_info:
        TimelineCreationRequest(
            deviation_date=date(1914, 6, 28),
            deviation_description="Too short",  # Less than 20 chars
            simulation_years=10,
            scenario_type=ScenarioType.LOCAL_DEVIATION,
        )

    assert "deviation_description" in str(exc_info.value)


def test_timeline_creation_request_simulation_years_range():
    """Test that simulation_years is within valid range."""
    # Too small
    with pytest.raises(ValidationError):
        TimelineCreationRequest(
            deviation_date=date(1914, 6, 28),
            deviation_description="Franz Ferdinand survives assassination attempt",
            simulation_years=0,  # Must be >= 1
            scenario_type=ScenarioType.LOCAL_DEVIATION,
        )

    # Too large
    with pytest.raises(ValidationError):
        TimelineCreationRequest(
            deviation_date=date(1914, 6, 28),
            deviation_description="Franz Ferdinand survives assassination attempt",
            simulation_years=101,  # Must be <= 100
            scenario_type=ScenarioType.LOCAL_DEVIATION,
        )


# ============================================================================
# TimelineOutput Validation Tests
# ============================================================================


def test_timeline_output_valid():
    """Test creating a valid TimelineOutput."""
    output = TimelineOutput(
        executive_summary="WWI prevented",
        political_changes="Stability maintained",
        conflicts_and_wars="No major conflicts",
        economic_impacts="Continued growth",
        social_developments="Progressive reforms",
        technological_shifts="Aviation advances",
        key_figures="Franz Ferdinand",
        long_term_implications="Different Europe",
    )

    assert output.executive_summary == "WWI prevented"
    assert output.narrative_prose is None


def test_timeline_output_with_narrative():
    """Test TimelineOutput with narrative prose."""
    output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
        narrative_prose="This is the narrative story...",
    )

    assert output.narrative_prose == "This is the narrative story..."


def test_timeline_output_missing_required_fields():
    """Test that TimelineOutput requires all 8 report sections."""
    with pytest.raises(ValidationError) as exc_info:
        TimelineOutput(
            executive_summary="Test",
            political_changes="Test",
            # Missing other required fields
        )

    assert "conflicts_and_wars" in str(exc_info.value)


# ============================================================================
# SkeletonEventUpdate Validation Tests
# ============================================================================


def test_skeleton_event_update_new_event():
    """Test creating a new event (id=None)."""
    event = SkeletonEventUpdate(
        id=None,
        event_date=date(1914, 6, 28),
        location="Sarajevo, Bosnia",
        description="Assassination attempt fails",
        event_order=0,
    )

    assert event.id is None
    assert event.event_date == date(1914, 6, 28)
    assert event.location == "Sarajevo, Bosnia"


def test_skeleton_event_update_existing_event():
    """Test updating an existing event (has id)."""
    event_id = uuid4()
    event = SkeletonEventUpdate(
        id=event_id,
        event_date=date(1914, 6, 28),
        location="Vienna, Austria",
        description="Updated description",
        event_order=1,
    )

    assert event.id == event_id


def test_skeleton_event_update_location_too_short():
    """Test that location has minimum length."""
    with pytest.raises(ValidationError):
        SkeletonEventUpdate(
            id=None,
            event_date=date(1914, 6, 28),
            location="A",  # Less than 2 chars
            description="Test description that is long enough",
            event_order=0,
        )


def test_skeleton_event_update_description_too_short():
    """Test that description has minimum length."""
    with pytest.raises(ValidationError):
        SkeletonEventUpdate(
            id=None,
            event_date=date(1914, 6, 28),
            location="Vienna",
            description="Too short",  # Less than 10 chars
            event_order=0,
        )


def test_skeleton_event_update_negative_order():
    """Test that event_order cannot be negative."""
    with pytest.raises(ValidationError):
        SkeletonEventUpdate(
            id=None,
            event_date=date(1914, 6, 28),
            location="Vienna",
            description="Valid description",
            event_order=-1,  # Cannot be negative
        )


# ============================================================================
# SkeletonEventsUpdateRequest Validation Tests
# ============================================================================


def test_skeleton_events_update_request_empty():
    """Test creating an empty update request."""
    request = SkeletonEventsUpdateRequest(
        events_update=[],
        deleted_event_ids=[],
    )

    assert len(request.events_update) == 0
    assert len(request.deleted_event_ids) == 0


def test_skeleton_events_update_request_with_events():
    """Test update request with events."""
    event1 = SkeletonEventUpdate(
        id=None,
        event_date=date(1914, 6, 28),
        location="Vienna",
        description="New event added by user",
        event_order=0,
    )

    event2 = SkeletonEventUpdate(
        id=uuid4(),
        event_date=date(1914, 8, 1),
        location="Berlin",
        description="Updated existing event",
        event_order=1,
    )

    request = SkeletonEventsUpdateRequest(
        events_update=[event1, event2],
        deleted_event_ids=[],
    )

    assert len(request.events_update) == 2


def test_skeleton_events_update_request_with_deletions():
    """Test update request with deletions."""
    request = SkeletonEventsUpdateRequest(
        events_update=[],
        deleted_event_ids=[uuid4(), uuid4()],
    )

    assert len(request.deleted_event_ids) == 2


def test_skeleton_events_update_request_combined():
    """Test update request with creates, updates, and deletes."""
    new_event = SkeletonEventUpdate(
        id=None,
        event_date=date(1914, 6, 28),
        location="Vienna",
        description="New event added",
        event_order=0,
    )

    update_event = SkeletonEventUpdate(
        id=uuid4(),
        event_date=date(1914, 8, 1),
        location="Berlin",
        description="Updated event",
        event_order=1,
    )

    request = SkeletonEventsUpdateRequest(
        events_update=[new_event, update_event],
        deleted_event_ids=[uuid4()],
    )

    assert len(request.events_update) == 2
    assert len(request.deleted_event_ids) == 1


# ============================================================================
# Enum Validation Tests
# ============================================================================


def test_scenario_type_enum():
    """Test ScenarioType enum values."""
    assert ScenarioType.LOCAL_DEVIATION.value == "local_deviation"
    assert ScenarioType.GLOBAL_DEVIATION.value == "global_deviation"
    assert ScenarioType.REALITY_FRACTURE.value == "reality_fracture"
    assert ScenarioType.GEOLOGICAL_SHIFT.value == "geological_shift"
    assert ScenarioType.EXTERNAL_INTERVENTION.value == "external_intervention"


def test_narrative_mode_enum():
    """Test NarrativeMode enum values."""
    assert NarrativeMode.NONE.value == "none"
    assert NarrativeMode.BASIC.value == "basic"
    assert NarrativeMode.ADVANCED_OMNISCIENT.value == "advanced_omniscient"
    assert NarrativeMode.ADVANCED_CUSTOM_POV.value == "advanced_custom_pov"


def test_generation_type_enum():
    """Test GenerationType enum values."""
    assert GenerationType.INITIAL.value == "initial"
    assert GenerationType.EXTENSION.value == "extension"
    assert GenerationType.BRANCH_POINT.value == "branch_point"


def test_skeleton_type_enum():
    """Test SkeletonType enum values."""
    assert SkeletonType.TIMELINE_DRAFT.value == "timeline_draft"
    assert SkeletonType.EXTENSION_DRAFT.value == "extension_draft"
    assert SkeletonType.BRANCH_DRAFT.value == "branch_draft"


def test_skeleton_status_enum():
    """Test SkeletonStatus enum values."""
    assert SkeletonStatus.PENDING.value == "pending"
    assert SkeletonStatus.EDITING.value == "editing"
    assert SkeletonStatus.APPROVED.value == "approved"
    assert SkeletonStatus.GENERATED.value == "generated"


# ============================================================================
# Edge Cases and Data Validation
# ============================================================================


def test_timeline_creation_request_date_validation():
    """Test that deviation_date accepts valid dates within allowed range."""
    # Valid historical date (1914)
    request = TimelineCreationRequest(
        deviation_date=date(1914, 6, 28),
        deviation_description="Franz Ferdinand survives assassination attempt",
        simulation_years=10,
        scenario_type=ScenarioType.LOCAL_DEVIATION,
    )
    assert request.deviation_date.year == 1914

    # Earlier valid date (1880s)
    request = TimelineCreationRequest(
        deviation_date=date(1885, 3, 15),
        deviation_description="Historical deviation event in the late 19th century",
        simulation_years=10,
        scenario_type=ScenarioType.LOCAL_DEVIATION,
    )
    assert request.deviation_date.year == 1885

    # Later valid date (1960s)
    request = TimelineCreationRequest(
        deviation_date=date(1969, 7, 20),
        deviation_description="Apollo 11 moon landing fails or succeeds differently",
        simulation_years=10,
        scenario_type=ScenarioType.LOCAL_DEVIATION,
    )
    assert request.deviation_date.year == 1969


def test_event_date_format():
    """Test that event dates are properly handled."""
    event = SkeletonEventUpdate(
        id=None,
        event_date=date(2024, 10, 28),
        location="Future location",
        description="Future event description",
        event_order=0,
    )

    assert isinstance(event.event_date, date)
    assert event.event_date.year == 2024
    assert event.event_date.month == 10
    assert event.event_date.day == 28


def test_uuid_handling():
    """Test that UUID fields are properly handled."""
    event_id = uuid4()
    event = SkeletonEventUpdate(
        id=event_id,
        event_date=date(1914, 6, 28),
        location="Test location",
        description="Test description",
        event_order=0,
    )

    assert event.id == event_id
    assert isinstance(event.id, type(uuid4()))
