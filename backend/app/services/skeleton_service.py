"""
Skeleton service for redesigned schema with type support.

This module provides CRUD operations for skeletons with support for:
- Timeline drafts (new timelines)
- Extension drafts (timeline extensions)
- Branch drafts (timeline branches)
"""

import logging
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone, date as date_type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.db_models import SkeletonDB, SkeletonEventDB, GenerationDB
from app.models import (
    SkeletonResponse,
    SkeletonEventResponse,
    SkeletonEventUpdate,
    SkeletonStatus,
    SkeletonType,
    ScenarioType,
)
from app.agents.skeleton_agent import SkeletonAgentOutput

logger = logging.getLogger(__name__)


# ============================================================================
# Skeleton Creation
# ============================================================================


async def create_timeline_draft_skeleton(
    db: AsyncSession,
    deviation_date: date_type,
    deviation_description: str,
    scenario_type: ScenarioType,
    simulation_years: int,
    agent_output: SkeletonAgentOutput,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> SkeletonResponse:
    """
    Create a skeleton for a new timeline (timeline draft).

    Args:
        db: Database session
        deviation_date: Date of the historical deviation
        deviation_description: Description of what changed
        scenario_type: Type of scenario
        simulation_years: Number of years simulated
        agent_output: Output from skeleton agent
        model_provider: LLM provider used
        model_name: Specific model used

    Returns:
        SkeletonResponse: Created skeleton with events
    """
    skeleton_id = str(uuid4())

    # Create timeline draft skeleton
    db_skeleton = SkeletonDB(
        id=skeleton_id,
        skeleton_type=SkeletonType.TIMELINE_DRAFT.value,
        deviation_date=deviation_date.isoformat(),
        deviation_description=deviation_description,
        scenario_type=scenario_type.value,
        status=SkeletonStatus.PENDING.value,
        model_provider=model_provider,
        model_name=model_name,
        generated_at=datetime.now(timezone.utc),
    )

    db.add(db_skeleton)
    await db.flush()

    # Create event records
    db_events = []
    for i, event in enumerate(agent_output.events):
        # Calculate event year relative to deviation
        event_date = datetime.strptime(event.event_date, "%Y-%m-%d").date()
        event_year = event_date.year - deviation_date.year

        db_event = SkeletonEventDB(
            id=str(uuid4()),
            skeleton_id=skeleton_id,
            event_date=event.event_date,
            event_year=event_year,
            location=event.location,
            description=event.description,
            event_order=i,
            is_user_added=0,
            is_user_modified=0,
        )
        db.add(db_event)
        db_events.append(db_event)

    await db.flush()

    logger.info(
        f"Created timeline draft skeleton {skeleton_id} with {len(db_events)} events "
        f"(type: {SkeletonType.TIMELINE_DRAFT.value})"
    )

    return await get_skeleton(db, UUID(skeleton_id))


async def create_extension_draft_skeleton(
    db: AsyncSession,
    parent_timeline_id: UUID,
    extension_start_year: int,
    extension_end_year: int,
    agent_output: SkeletonAgentOutput,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> SkeletonResponse:
    """
    Create a skeleton for timeline extension (extension draft).

    Args:
        db: Database session
        parent_timeline_id: UUID of the timeline being extended
        extension_start_year: Year where extension begins (relative to deviation)
        extension_end_year: Year where extension ends
        agent_output: Output from skeleton agent
        model_provider: LLM provider used
        model_name: Specific model used

    Returns:
        SkeletonResponse: Created extension skeleton with events
    """
    skeleton_id = str(uuid4())

    # Get parent timeline for deviation info
    from app.services.timeline_service import get_timeline_by_id

    parent_timeline = await get_timeline_by_id(db, parent_timeline_id)
    if not parent_timeline:
        raise ValueError(f"Parent timeline not found: {parent_timeline_id}")

    deviation_date = datetime.fromisoformat(parent_timeline.root_deviation_date).date()

    # Create extension draft skeleton
    db_skeleton = SkeletonDB(
        id=skeleton_id,
        skeleton_type=SkeletonType.EXTENSION_DRAFT.value,
        parent_timeline_id=str(parent_timeline_id),
        extension_start_year=extension_start_year,
        extension_end_year=extension_end_year,
        status=SkeletonStatus.PENDING.value,
        model_provider=model_provider,
        model_name=model_name,
        generated_at=datetime.now(timezone.utc),
    )

    db.add(db_skeleton)
    await db.flush()

    # Create event records
    db_events = []
    for i, event in enumerate(agent_output.events):
        # Calculate event year relative to deviation
        event_date = datetime.strptime(event.event_date, "%Y-%m-%d").date()
        event_year = event_date.year - deviation_date.year

        db_event = SkeletonEventDB(
            id=str(uuid4()),
            skeleton_id=skeleton_id,
            event_date=event.event_date,
            event_year=event_year,
            location=event.location,
            description=event.description,
            event_order=i,
            is_user_added=0,
            is_user_modified=0,
        )
        db.add(db_event)
        db_events.append(db_event)

    await db.flush()

    logger.info(
        f"Created extension draft skeleton {skeleton_id} with {len(db_events)} events "
        f"for timeline {parent_timeline_id} "
        f"(type: {SkeletonType.EXTENSION_DRAFT.value}, years {extension_start_year}-{extension_end_year})"
    )

    return await get_skeleton(db, UUID(skeleton_id))


async def create_branch_draft_skeleton(
    db: AsyncSession,
    source_timeline_id: UUID,
    branch_point_year: int,
    branch_deviation_description: str,
    simulation_years: int,
    agent_output: SkeletonAgentOutput,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> SkeletonResponse:
    """
    Create a skeleton for timeline branch (branch draft).

    Args:
        db: Database session
        source_timeline_id: UUID of the timeline to branch from
        branch_point_year: Year where branch diverges
        branch_deviation_description: What changed at branch point
        simulation_years: Number of years to simulate after branch
        agent_output: Output from skeleton agent
        model_provider: LLM provider used
        model_name: Specific model used

    Returns:
        SkeletonResponse: Created branch skeleton with events
    """
    skeleton_id = str(uuid4())

    # Get source timeline for deviation info
    from app.services.timeline_service import get_timeline_by_id

    source_timeline = await get_timeline_by_id(db, source_timeline_id)
    if not source_timeline:
        raise ValueError(f"Source timeline not found: {source_timeline_id}")

    deviation_date = datetime.fromisoformat(source_timeline.root_deviation_date).date()

    # Create branch draft skeleton
    db_skeleton = SkeletonDB(
        id=skeleton_id,
        skeleton_type=SkeletonType.BRANCH_DRAFT.value,
        parent_timeline_id=str(source_timeline_id),
        branch_point_year=branch_point_year,
        branch_deviation_description=branch_deviation_description,
        status=SkeletonStatus.PENDING.value,
        model_provider=model_provider,
        model_name=model_name,
        generated_at=datetime.now(timezone.utc),
    )

    db.add(db_skeleton)
    await db.flush()

    # Create event records
    db_events = []
    for i, event in enumerate(agent_output.events):
        # Calculate event year relative to root deviation
        event_date = datetime.strptime(event.event_date, "%Y-%m-%d").date()
        event_year = event_date.year - deviation_date.year

        db_event = SkeletonEventDB(
            id=str(uuid4()),
            skeleton_id=skeleton_id,
            event_date=event.event_date,
            event_year=event_year,
            location=event.location,
            description=event.description,
            event_order=i,
            is_user_added=0,
            is_user_modified=0,
        )
        db.add(db_event)
        db_events.append(db_event)

    await db.flush()

    logger.info(
        f"Created branch draft skeleton {skeleton_id} with {len(db_events)} events "
        f"from timeline {source_timeline_id} at year {branch_point_year} "
        f"(type: {SkeletonType.BRANCH_DRAFT.value})"
    )

    return await get_skeleton(db, UUID(skeleton_id))


# ============================================================================
# Skeleton Retrieval
# ============================================================================


async def get_skeleton(db: AsyncSession, skeleton_id: UUID) -> Optional[SkeletonResponse]:
    """
    Get a skeleton by ID with all its events.

    Args:
        db: Database session
        skeleton_id: Skeleton UUID

    Returns:
        Optional[SkeletonResponse]: Skeleton if found, None otherwise
    """
    result = await db.execute(
        select(SkeletonDB)
        .options(selectinload(SkeletonDB.events))
        .where(SkeletonDB.id == str(skeleton_id))
    )
    skeleton = result.scalar_one_or_none()

    if not skeleton:
        logger.warning(f"Skeleton not found: {skeleton_id}")
        return None

    # Convert events
    events = [
        SkeletonEventResponse(
            id=UUID(event.id),
            skeleton_id=UUID(event.skeleton_id),
            event_date=datetime.fromisoformat(event.event_date).date(),
            event_year=event.event_year,
            location=event.location,
            description=event.description,
            event_order=event.event_order,
            is_user_added=bool(event.is_user_added),
            is_user_modified=bool(event.is_user_modified),
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        for event in sorted(skeleton.events, key=lambda e: e.event_order)
    ]

    # Convert skeleton
    response = SkeletonResponse(
        id=UUID(skeleton.id),
        timeline_id=UUID(skeleton.timeline_id) if skeleton.timeline_id else None,
        generation_id=UUID(skeleton.generation_id) if skeleton.generation_id else None,
        skeleton_type=SkeletonType(skeleton.skeleton_type),
        status=SkeletonStatus(skeleton.status),
        deviation_date=datetime.fromisoformat(skeleton.deviation_date).date()
        if skeleton.deviation_date
        else None,
        deviation_description=skeleton.deviation_description,
        scenario_type=ScenarioType(skeleton.scenario_type) if skeleton.scenario_type else None,
        parent_timeline_id=UUID(skeleton.parent_timeline_id)
        if skeleton.parent_timeline_id
        else None,
        extension_start_year=skeleton.extension_start_year,
        extension_end_year=skeleton.extension_end_year,
        branch_point_year=skeleton.branch_point_year,
        branch_deviation_description=skeleton.branch_deviation_description,
        model_provider=skeleton.model_provider,
        model_name=skeleton.model_name,
        generated_at=skeleton.generated_at,
        approved_at=skeleton.approved_at,
        created_at=skeleton.created_at,
        updated_at=skeleton.updated_at,
        events=events,
    )

    logger.info(f"Retrieved skeleton {skeleton_id} with {len(events)} events")
    return response


async def get_all_skeletons(db: AsyncSession) -> List[SkeletonResponse]:
    """
    Get all timeline draft skeletons with their events.

    Note: Only returns TIMELINE_DRAFT skeletons. Extension and branch skeletons
    are ephemeral and should only be accessed via their generation snapshots.

    Args:
        db: Database session

    Returns:
        List[SkeletonResponse]: All timeline draft skeletons ordered by creation date
    """
    result = await db.execute(
        select(SkeletonDB)
        .options(selectinload(SkeletonDB.events))
        .where(SkeletonDB.skeleton_type == SkeletonType.TIMELINE_DRAFT.value)  # Only timeline drafts
        .order_by(SkeletonDB.created_at.desc())
    )
    skeletons = result.scalars().all()

    responses = []
    for skeleton in skeletons:
        skeleton_response = await get_skeleton(db, UUID(skeleton.id))
        if skeleton_response:
            responses.append(skeleton_response)

    logger.info(f"Retrieved {len(responses)} timeline draft skeletons")
    return responses


async def get_skeleton_by_timeline(
    db: AsyncSession, timeline_id: UUID
) -> Optional[SkeletonResponse]:
    """
    Get skeleton associated with a timeline.

    Args:
        db: Database session
        timeline_id: Timeline UUID

    Returns:
        Optional[SkeletonResponse]: Skeleton if found, None otherwise
    """
    result = await db.execute(
        select(SkeletonDB)
        .options(selectinload(SkeletonDB.events))
        .where(SkeletonDB.timeline_id == str(timeline_id))
        .order_by(SkeletonDB.created_at.desc())
    )
    skeleton = result.scalars().first()

    if not skeleton:
        logger.info(f"No skeleton found for timeline {timeline_id}")
        return None

    return await get_skeleton(db, UUID(skeleton.id))


async def get_skeleton_by_generation(
    db: AsyncSession, generation_id: UUID
) -> Optional[SkeletonResponse]:
    """
    Get skeleton associated with a generation.

    Args:
        db: Database session
        generation_id: Generation UUID

    Returns:
        Optional[SkeletonResponse]: Skeleton if found, None otherwise
    """
    result = await db.execute(
        select(SkeletonDB)
        .options(selectinload(SkeletonDB.events))
        .where(SkeletonDB.generation_id == str(generation_id))
        .order_by(SkeletonDB.created_at.desc())
    )
    skeleton = result.scalars().first()

    if not skeleton:
        logger.info(f"No skeleton found for generation {generation_id}")
        return None

    return await get_skeleton(db, UUID(skeleton.id))


# ============================================================================
# Skeleton Updates
# ============================================================================


async def update_skeleton_events(
    db: AsyncSession,
    skeleton_id: UUID,
    events_update: List[SkeletonEventUpdate],
    deleted_event_ids: List[UUID],
) -> SkeletonResponse:
    """
    Update events in a skeleton (create, update, delete).

    Args:
        db: Database session
        skeleton_id: Skeleton UUID
        events_update: List of events to create or update (id=None for new events)
        deleted_event_ids: List of event IDs to delete

    Returns:
        SkeletonResponse: Updated skeleton

    Raises:
        ValueError: If skeleton not found or in wrong status
    """
    # Get skeleton with events
    result = await db.execute(
        select(SkeletonDB)
        .options(selectinload(SkeletonDB.events))
        .where(SkeletonDB.id == str(skeleton_id))
    )
    skeleton = result.scalar_one_or_none()

    if not skeleton:
        raise ValueError(f"Skeleton not found: {skeleton_id}")

    # NOTE: Removed GENERATED status check - skeletons should remain editable
    # even after generation to allow for re-generation with updated events.
    # The generation stores a reference via source_skeleton_id, not a snapshot.

    # Update skeleton status to editing
    skeleton.status = SkeletonStatus.EDITING.value
    skeleton.updated_at = datetime.now(timezone.utc)

    # Convert deleted_event_ids to set of strings for fast lookup
    deleted_ids_set = {str(event_id) for event_id in deleted_event_ids}

    # Delete events from the relationship and session
    for event in list(skeleton.events):  # Use list() to avoid modifying during iteration
        if event.id in deleted_ids_set:
            await db.delete(event)

    # Process event updates and creations
    created_events = []
    for event_update in events_update:
        if event_update.id:
            # Update existing event - find it in the skeleton's events
            event = next((e for e in skeleton.events if e.id == str(event_update.id)), None)

            if event:
                event.event_date = event_update.event_date.isoformat()
                event.location = event_update.location
                event.description = event_update.description
                event.event_order = event_update.event_order

                # Recalculate event_year if we have deviation_date
                if skeleton.deviation_date:
                    deviation_date = datetime.fromisoformat(skeleton.deviation_date).date()
                    event.event_year = event_update.event_date.year - deviation_date.year
                else:
                    # For extension/branch skeletons, calculate from parent timeline
                    event.event_year = 0  # Placeholder

                event.is_user_modified = 1
                event.updated_at = datetime.now(timezone.utc)
        else:
            # Create new event
            new_event_id = str(uuid4())

            # Calculate event_year
            if skeleton.deviation_date:
                deviation_date = datetime.fromisoformat(skeleton.deviation_date).date()
                event_year = event_update.event_date.year - deviation_date.year
            else:
                event_year = 0  # Placeholder for extension/branch skeletons

            new_event = SkeletonEventDB(
                id=new_event_id,
                skeleton_id=str(skeleton_id),
                event_date=event_update.event_date.isoformat(),
                event_year=event_year,
                location=event_update.location,
                description=event_update.description,
                event_order=event_update.event_order,
                is_user_added=1,
                is_user_modified=0,
            )
            db.add(new_event)
            created_events.append(new_event)

    await db.flush()

    logger.info(
        f"Updated skeleton {skeleton_id}: "
        f"{len(events_update)} events processed, {len(deleted_event_ids)} deleted"
    )

    # Build event list manually, filtering out deleted ones
    # We can't rely on refresh() because ORM deletes aren't visible until commit
    remaining_events = [
        event for event in skeleton.events
        if event.id not in deleted_ids_set
    ]

    # Add newly created events
    remaining_events.extend(created_events)

    # Convert to SkeletonResponse
    events = [
        SkeletonEventResponse(
            id=UUID(event.id),
            skeleton_id=UUID(event.skeleton_id),
            event_date=datetime.fromisoformat(event.event_date).date(),
            event_year=event.event_year,
            location=event.location,
            description=event.description,
            event_order=event.event_order,
            is_user_added=bool(event.is_user_added),
            is_user_modified=bool(event.is_user_modified),
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        for event in sorted(remaining_events, key=lambda e: e.event_order)
    ]

    response = SkeletonResponse(
        id=UUID(skeleton.id),
        timeline_id=UUID(skeleton.timeline_id) if skeleton.timeline_id else None,
        generation_id=UUID(skeleton.generation_id) if skeleton.generation_id else None,
        skeleton_type=SkeletonType(skeleton.skeleton_type),
        status=SkeletonStatus(skeleton.status),
        deviation_date=datetime.fromisoformat(skeleton.deviation_date).date()
        if skeleton.deviation_date
        else None,
        deviation_description=skeleton.deviation_description,
        scenario_type=ScenarioType(skeleton.scenario_type) if skeleton.scenario_type else None,
        parent_timeline_id=UUID(skeleton.parent_timeline_id)
        if skeleton.parent_timeline_id
        else None,
        extension_start_year=skeleton.extension_start_year,
        extension_end_year=skeleton.extension_end_year,
        branch_point_year=skeleton.branch_point_year,
        branch_deviation_description=skeleton.branch_deviation_description,
        model_provider=skeleton.model_provider,
        model_name=skeleton.model_name,
        generated_at=skeleton.generated_at,
        approved_at=skeleton.approved_at,
        created_at=skeleton.created_at,
        updated_at=skeleton.updated_at,
        events=events,
    )

    return response


async def approve_skeleton(db: AsyncSession, skeleton_id: UUID) -> SkeletonResponse:
    """
    Approve a skeleton for generation.

    Args:
        db: Database session
        skeleton_id: Skeleton UUID

    Returns:
        SkeletonResponse: Approved skeleton

    Raises:
        ValueError: If skeleton not found
    """
    result = await db.execute(
        select(SkeletonDB).where(SkeletonDB.id == str(skeleton_id))
    )
    skeleton = result.scalar_one_or_none()

    if not skeleton:
        raise ValueError(f"Skeleton not found: {skeleton_id}")

    skeleton.status = SkeletonStatus.APPROVED.value
    skeleton.approved_at = datetime.now(timezone.utc)
    skeleton.updated_at = datetime.now(timezone.utc)

    await db.flush()

    logger.info(f"Approved skeleton {skeleton_id}")

    return await get_skeleton(db, skeleton_id)


async def link_skeleton_to_timeline(
    db: AsyncSession, skeleton_id: UUID, timeline_id: UUID
) -> None:
    """
    Link a skeleton to a timeline after generation.

    Args:
        db: Database session
        skeleton_id: Skeleton UUID
        timeline_id: Timeline UUID

    Raises:
        ValueError: If skeleton not found
    """
    result = await db.execute(
        select(SkeletonDB).where(SkeletonDB.id == str(skeleton_id))
    )
    skeleton = result.scalar_one_or_none()

    if not skeleton:
        raise ValueError(f"Skeleton not found: {skeleton_id}")

    skeleton.timeline_id = str(timeline_id)
    # NOTE: Do NOT change status to GENERATED - skeleton should remain editable
    # for re-generation. The timeline stores source_skeleton_id as a reference.
    skeleton.updated_at = datetime.now(timezone.utc)

    await db.flush()

    logger.info(f"Linked skeleton {skeleton_id} to timeline {timeline_id} (status unchanged: {skeleton.status})")


async def link_skeleton_to_generation(
    db: AsyncSession, skeleton_id: UUID, generation_id: UUID
) -> None:
    """
    Link a skeleton to a generation after generation.

    Args:
        db: Database session
        skeleton_id: Skeleton UUID
        generation_id: Generation UUID

    Raises:
        ValueError: If skeleton not found
    """
    result = await db.execute(
        select(SkeletonDB).where(SkeletonDB.id == str(skeleton_id))
    )
    skeleton = result.scalar_one_or_none()

    if not skeleton:
        raise ValueError(f"Skeleton not found: {skeleton_id}")

    skeleton.generation_id = str(generation_id)
    # NOTE: Do NOT change status to GENERATED - skeleton should remain editable
    # for re-generation. The generation stores source_skeleton_id as a reference.
    skeleton.updated_at = datetime.now(timezone.utc)

    await db.flush()

    logger.info(f"Linked skeleton {skeleton_id} to generation {generation_id} (status unchanged: {skeleton.status})")


# ============================================================================
# Skeleton Deletion
# ============================================================================


async def delete_skeleton(db: AsyncSession, skeleton_id: UUID) -> bool:
    """
    Delete a skeleton and all its events.

    Args:
        db: Database session
        skeleton_id: Skeleton UUID

    Returns:
        bool: True if deleted, False if not found
    """
    result = await db.execute(
        select(SkeletonDB)
        .options(selectinload(SkeletonDB.events))
        .where(SkeletonDB.id == str(skeleton_id))
    )
    skeleton = result.scalar_one_or_none()

    if not skeleton:
        logger.warning(f"Cannot delete - skeleton not found: {skeleton_id}")
        return False

    skeleton_type = skeleton.skeleton_type
    event_count = len(skeleton.events)

    await db.delete(skeleton)
    await db.flush()

    logger.info(
        f"Deleted skeleton {skeleton_id} (type: {skeleton_type}) "
        f"with {event_count} events (cascade)"
    )
    return True


async def get_skeleton_snapshot(
    db: AsyncSession,
    timeline_id: UUID,
    generation_id: Optional[UUID] = None,
) -> Optional[dict]:
    """
    Get the skeleton snapshot used to generate a timeline or specific generation.

    Args:
        db: Database session
        timeline_id: Timeline UUID
        generation_id: Optional generation UUID (if None, uses first generation)

    Returns:
        Optional[dict]: Skeleton snapshot data with events and metadata, or None if not found
    """
    # Get the generation (either specified or first in timeline)
    if generation_id:
        result = await db.execute(
            select(GenerationDB).where(GenerationDB.id == str(generation_id))
        )
        generation = result.scalar_one_or_none()

        if not generation:
            logger.warning(f"Generation {generation_id} not found")
            return None

        # Verify generation belongs to timeline
        if generation.timeline_id != str(timeline_id):
            logger.warning(
                f"Generation {generation_id} does not belong to timeline {timeline_id}"
            )
            return None
    else:
        # Get first generation of timeline
        result = await db.execute(
            select(GenerationDB)
            .where(GenerationDB.timeline_id == str(timeline_id))
            .order_by(GenerationDB.generation_order.asc())
        )
        generation = result.scalars().first()

        if not generation:
            logger.warning(f"No generations found for timeline {timeline_id}")
            return None

    # Check if generation has a source skeleton
    if not generation.source_skeleton_id:
        logger.info(
            f"Generation {generation.id} was not generated from a skeleton"
        )
        return None

    # Get the source skeleton with its events
    skeleton_result = await db.execute(
        select(SkeletonDB)
        .options(selectinload(SkeletonDB.events))
        .where(SkeletonDB.id == generation.source_skeleton_id)
    )
    skeleton = skeleton_result.scalar_one_or_none()

    if not skeleton:
        logger.warning(
            f"Source skeleton {generation.source_skeleton_id} not found for generation {generation.id}"
        )
        return None

    # Build snapshot response
    events_snapshot = []
    for event in sorted(skeleton.events, key=lambda e: e.event_order):
        events_snapshot.append({
            "event_date": event.event_date,
            "location": event.location,
            "description": event.description,
            "event_order": event.event_order,
        })

    snapshot = {
        "skeleton_id": skeleton.id,
        "skeleton_type": skeleton.skeleton_type,
        "status": skeleton.status,
        "created_at": skeleton.created_at.isoformat() if skeleton.created_at else None,
        "generation_id": generation.id,
        "generation_order": generation.generation_order,
        "model_provider": skeleton.model_provider,
        "model_name": skeleton.model_name,
        "events": events_snapshot,
        "event_count": len(events_snapshot),
    }

    logger.info(
        f"Retrieved skeleton snapshot for generation {generation.id} "
        f"(skeleton {skeleton.id}, {len(events_snapshot)} events)"
    )
    return snapshot
