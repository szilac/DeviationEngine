"""
Tests for skeleton event CRUD operations.

Critical tests for the skeleton event update/edit/add functionality that had
"a lot of missing/incorrect parts" in the previous implementation.

This tests the completely rewritten update_skeleton_events function.
"""

import pytest
from uuid import uuid4, UUID
from datetime import date

from app.services import skeleton_service
from app.models import SkeletonEventUpdate


# ============================================================================
# Event Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_new_event_to_skeleton(db_session, skeleton_with_events):
    """Test adding a new event to an existing skeleton."""
    # Current skeleton has 3 events
    assert len(skeleton_with_events.events) == 3

    # Create new event (no id means it's new)
    new_event = SkeletonEventUpdate(
        id=None,  # No ID means create new
        event_date=date(1916, 1, 1),
        location="Paris, France",
        description="International peace summit convened by major powers",
        event_order=3,
    )

    # Update skeleton with new event
    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[new_event],
        deleted_event_ids=[],
    )

    # Should now have 4 events
    assert len(updated_skeleton.events) == 4

    # Find the new event
    new_event_db = next(
        (e for e in updated_skeleton.events if e.description == "International peace summit convened by major powers"),
        None,
    )
    assert new_event_db is not None
    assert new_event_db.location == "Paris, France"
    assert new_event_db.event_year == 2  # 1916 - 1914 = 2
    assert new_event_db.event_order == 3
    assert new_event_db.is_user_added == 1
    assert new_event_db.is_user_modified == 0


@pytest.mark.asyncio
async def test_add_multiple_new_events(db_session, skeleton_with_events):
    """Test adding multiple new events at once."""
    new_events = [
        SkeletonEventUpdate(
            id=None,
            event_date=date(1916, 1, 1),
            location="Paris",
            description="Event one - detailed description of events in Paris",
            event_order=3,
        ),
        SkeletonEventUpdate(
            id=None,
            event_date=date(1917, 1, 1),
            location="London",
            description="Event two - detailed description of events in London",
            event_order=4,
        ),
        SkeletonEventUpdate(
            id=None,
            event_date=date(1918, 1, 1),
            location="Berlin",
            description="Event three - detailed description of events in Berlin",
            event_order=5,
        ),
    ]

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=new_events,
        deleted_event_ids=[],
    )

    # Should have 3 original + 3 new = 6 events
    assert len(updated_skeleton.events) == 6


# ============================================================================
# Event Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_existing_event(db_session, skeleton_with_events):
    """Test updating an existing event."""
    # Get an existing event
    existing_event = skeleton_with_events.events[0]
    original_description = existing_event.description

    # Update the event - use UUID() to convert string id
    updated_event = SkeletonEventUpdate(
        id=UUID(existing_event.id),
        event_date=date.fromisoformat(existing_event.event_date),
        location="Updated Location",
        description="Updated description with enough length",
        event_order=existing_event.event_order,
    )

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[updated_event],
        deleted_event_ids=[],
    )

    # Should still have 3 events
    assert len(updated_skeleton.events) == 3

    # Find the updated event
    updated_event_db = next(
        (e for e in updated_skeleton.events if str(e.id) == existing_event.id), None
    )
    assert updated_event_db is not None
    assert updated_event_db.location == "Updated Location"
    assert updated_event_db.description == "Updated description with enough length"
    assert updated_event_db.description != original_description
    assert updated_event_db.is_user_modified == 1


@pytest.mark.asyncio
async def test_update_event_date_recalculates_year(db_session, skeleton_with_events):
    """Test that updating event date recalculates event_year correctly."""
    existing_event = skeleton_with_events.events[0]
    original_year = existing_event.event_year

    # Change the date
    updated_event = SkeletonEventUpdate(
        id=UUID(existing_event.id),
        event_date=date(1920, 1, 1),  # 6 years after 1914
        location=existing_event.location,
        description=existing_event.description,
        event_order=existing_event.event_order,
    )

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[updated_event],
        deleted_event_ids=[],
    )

    updated_event_db = next(
        (e for e in updated_skeleton.events if str(e.id) == existing_event.id), None
    )
    assert updated_event_db.event_year == 6
    assert updated_event_db.event_year != original_year


@pytest.mark.asyncio
async def test_update_multiple_events(db_session, skeleton_with_events):
    """Test updating multiple events at once."""
    event1 = skeleton_with_events.events[0]
    event2 = skeleton_with_events.events[1]

    updates = [
        SkeletonEventUpdate(
            id=UUID(event1.id),
            event_date=date.fromisoformat(event1.event_date),
            location="Updated Location 1",
            description=event1.description,
            event_order=event1.event_order,
        ),
        SkeletonEventUpdate(
            id=UUID(event2.id),
            event_date=date.fromisoformat(event2.event_date),
            location="Updated Location 2",
            description=event2.description,
            event_order=event2.event_order,
        ),
    ]

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=updates,
        deleted_event_ids=[],
    )

    # Check both updates applied
    event1_updated = next((e for e in updated_skeleton.events if str(e.id) == event1.id), None)
    event2_updated = next((e for e in updated_skeleton.events if str(e.id) == event2.id), None)

    assert event1_updated.location == "Updated Location 1"
    assert event2_updated.location == "Updated Location 2"


# ============================================================================
# Event Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_event_from_skeleton(db_session, skeleton_with_events):
    """Test deleting an event from a skeleton."""
    # Current skeleton has 3 events
    assert len(skeleton_with_events.events) == 3

    # Delete the first event
    event_to_delete = skeleton_with_events.events[0]

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[],
        deleted_event_ids=[UUID(event_to_delete.id)],
    )

    # Should now have 2 events
    assert len(updated_skeleton.events) == 2

    # Deleted event should not exist
    deleted_event = next(
        (e for e in updated_skeleton.events if str(e.id) == event_to_delete.id), None
    )
    assert deleted_event is None


@pytest.mark.asyncio
async def test_delete_multiple_events(db_session, skeleton_with_events):
    """Test deleting multiple events at once."""
    event1 = skeleton_with_events.events[0]
    event2 = skeleton_with_events.events[1]

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[],
        deleted_event_ids=[UUID(event1.id), UUID(event2.id)],
    )

    # Should now have 1 event (3 - 2)
    assert len(updated_skeleton.events) == 1

    # Neither deleted event should exist
    assert not any(str(e.id) == event1.id for e in updated_skeleton.events)
    assert not any(str(e.id) == event2.id for e in updated_skeleton.events)


@pytest.mark.asyncio
async def test_delete_all_events(db_session, skeleton_with_events):
    """Test deleting all events from a skeleton."""
    all_event_ids = [UUID(event.id) for event in skeleton_with_events.events]

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[],
        deleted_event_ids=all_event_ids,
    )

    # Should have no events
    assert len(updated_skeleton.events) == 0


# ============================================================================
# Combined Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_update_and_delete_in_single_operation(db_session, skeleton_with_events):
    """Test creating, updating, and deleting events in a single operation."""
    # Delete first event
    event_to_delete = skeleton_with_events.events[0]

    # Update second event
    event_to_update = skeleton_with_events.events[1]
    updated_event = SkeletonEventUpdate(
        id=UUID(event_to_update.id),
        event_date=date.fromisoformat(event_to_update.event_date),
        location="Updated in combo",
        description=event_to_update.description,
        event_order=event_to_update.event_order,
    )

    # Create new event
    new_event = SkeletonEventUpdate(
        id=None,
        event_date=date(1920, 1, 1),
        location="New in combo",
        description="Created in combo operation with enough length",
        event_order=3,
    )

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[updated_event, new_event],
        deleted_event_ids=[UUID(event_to_delete.id)],
    )

    # Started with 3, deleted 1, added 1 = still 3
    assert len(updated_skeleton.events) == 3

    # Verify deletion
    assert not any(str(e.id) == event_to_delete.id for e in updated_skeleton.events)

    # Verify update
    updated = next((e for e in updated_skeleton.events if str(e.id) == event_to_update.id), None)
    assert updated is not None
    assert updated.location == "Updated in combo"

    # Verify creation
    created = next(
        (e for e in updated_skeleton.events if e.description == "Created in combo operation with enough length"),
        None,
    )
    assert created is not None
    assert created.location == "New in combo"
    assert created.is_user_added == 1


@pytest.mark.asyncio
async def test_reorder_events(db_session, skeleton_with_events):
    """Test reordering events by updating event_order."""
    event1 = skeleton_with_events.events[0]
    event2 = skeleton_with_events.events[1]
    event3 = skeleton_with_events.events[2]

    # Reverse the order
    updates = [
        SkeletonEventUpdate(
            id=UUID(event1.id),
            event_date=date.fromisoformat(event1.event_date),
            location=event1.location,
            description=event1.description,
            event_order=2,  # Was 0, now 2
        ),
        SkeletonEventUpdate(
            id=UUID(event2.id),
            event_date=date.fromisoformat(event2.event_date),
            location=event2.location,
            description=event2.description,
            event_order=1,  # Was 1, stays 1
        ),
        SkeletonEventUpdate(
            id=UUID(event3.id),
            event_date=date.fromisoformat(event3.event_date),
            location=event3.location,
            description=event3.description,
            event_order=0,  # Was 2, now 0
        ),
    ]

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=updates,
        deleted_event_ids=[],
    )

    # Verify new order
    event1_updated = next((e for e in updated_skeleton.events if str(e.id) == event1.id), None)
    event2_updated = next((e for e in updated_skeleton.events if str(e.id) == event2.id), None)
    event3_updated = next((e for e in updated_skeleton.events if str(e.id) == event3.id), None)

    assert event1_updated.event_order == 2
    assert event2_updated.event_order == 1
    assert event3_updated.event_order == 0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_update_with_empty_lists(db_session, skeleton_with_events):
    """Test that calling update with empty lists doesn't change anything."""
    original_count = len(skeleton_with_events.events)

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[],
        deleted_event_ids=[],
    )

    assert len(updated_skeleton.events) == original_count


@pytest.mark.asyncio
async def test_delete_nonexistent_event_id(db_session, skeleton_with_events):
    """Test that deleting a non-existent event ID doesn't cause errors."""
    fake_id = uuid4()

    # Should not raise an error
    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=UUID(skeleton_with_events.id),
        events_update=[],
        deleted_event_ids=[fake_id],
    )

    # Should still have all original events
    assert len(updated_skeleton.events) == 3


@pytest.mark.asyncio
async def test_user_tracking_flags(db_session, skeleton_db):
    """Test that user tracking flags are set correctly."""
    # Add AI-generated event (is_user_added=0)
    ai_event = SkeletonEventUpdate(
        id=None,
        event_date=date(1914, 6, 28),
        location="AI Location",
        description="AI generated event with enough detail",
        event_order=0,
    )

    # Capture skeleton_id before any expire_all() calls
    skeleton_id = UUID(skeleton_db.id)

    # Note: The current implementation sets is_user_added=1 for all new events
    # This might need to be adjusted based on whether the event came from AI or user
    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=skeleton_id,
        events_update=[ai_event],
        deleted_event_ids=[],
    )

    new_event = updated_skeleton.events[0]
    # Currently all new events are marked as user_added=1
    assert new_event.is_user_added == 1
    assert new_event.is_user_modified == 0

    # Expire all cached objects so next DB query gets fresh data
    db_session.expire_all()

    # Now modify it
    modify_event = SkeletonEventUpdate(
        id=new_event.id,
        event_date=date(1914, 6, 28),
        location="Modified Location",
        description="Modified description with enough length",
        event_order=0,
    )

    updated_skeleton = await skeleton_service.update_skeleton_events(
        db=db_session,
        skeleton_id=skeleton_id,
        events_update=[modify_event],
        deleted_event_ids=[],
    )

    modified_event = updated_skeleton.events[0]
    assert modified_event.is_user_modified == 1
