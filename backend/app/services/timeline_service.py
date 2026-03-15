"""
Timeline service for redesigned schema with branching support.

This module provides database operations for timelines with:
- Multiple generations (replaces reports)
- Timeline branching support
- Unified generation model for initial/extension/branch content
"""

import logging
import json
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from app.db_models import TimelineDB, GenerationDB, MediaDB
from app.models import (
    Timeline,
    Generation,
    TimelineCreationRequest,
    TimelineExtensionRequest,
    TimelineBranchRequest,
    GenerationType,
    NarrativeMode,
)
from app.agents.historian_agent import TimelineOutput

logger = logging.getLogger(__name__)


# ============================================================================
# Timeline Creation
# ============================================================================


async def create_timeline_with_initial_generation(
    db: AsyncSession,
    timeline: Timeline,
    initial_generation_output: TimelineOutput,
    historian_provider: Optional[str] = None,
    historian_model_name: Optional[str] = None,
    storyteller_provider: Optional[str] = None,
    storyteller_model_name: Optional[str] = None,
    source_skeleton_id: Optional[UUID] = None,
) -> TimelineDB:
    """
    Create a new timeline with its initial generation.

    Args:
        db: Database session
        timeline: Timeline with deviation point information
        initial_generation_output: AI-generated content for initial generation
        historian_provider: Provider used for structured report (optional)
        historian_model_name: Model name used for structured report (optional)
        storyteller_provider: Provider used for narrative (optional)
        storyteller_model_name: Model name used for narrative (optional)
        source_skeleton_id: Skeleton used for generation (optional)

    Returns:
        TimelineDB: Created timeline with initial generation
    """
    # Use provided model info or fall back to global config
    model_provider = historian_provider
    model_name = historian_model_name

    if model_provider is None or model_name is None:
        from app.services import llm_service

        try:
            llm_config = await llm_service.get_current_llm_config(db)
            model_provider = llm_config.provider.value
            model_name = llm_config.model_name
        except Exception as e:
            logger.warning(f"Could not fetch LLM config for model tracking: {e}")
            model_provider = None
            model_name = None

    # Generate a fallback timeline name if the LLM didn't provide a good one
    timeline_name = initial_generation_output.timeline_name
    if not timeline_name or timeline_name == "Alternate Timeline" or len(timeline_name.strip()) < 3:
        # Create a name from the deviation description (first 5 significant words)
        words = [w for w in timeline.root_deviation_description.split() if len(w) > 3][:5]
        timeline_name = ' '.join(words).title() if words else "Alternate Timeline"
        logger.warning(
            f"LLM did not generate timeline_name, using fallback: '{timeline_name}'"
        )

    # Create timeline record
    db_timeline = TimelineDB(
        id=str(timeline.id),
        parent_timeline_id=str(timeline.parent_timeline_id) if timeline.parent_timeline_id else None,
        branch_point_year=timeline.branch_point_year,
        branch_deviation_description=timeline.branch_deviation_description,
        root_deviation_date=timeline.root_deviation_date.isoformat(),
        root_deviation_description=timeline.root_deviation_description,
        scenario_type=timeline.scenario_type.value,
        timeline_name=timeline_name,
        created_at=timeline.created_at,
        updated_at=timeline.updated_at,
    )

    db.add(db_timeline)
    await db.flush()  # Get the timeline ID

    # Determine narrative model info
    has_narrative = initial_generation_output.narrative_prose is not None
    if has_narrative:
        narrative_model_provider = (
            storyteller_provider if storyteller_provider else model_provider
        )
        narrative_model_name = (
            storyteller_model_name if storyteller_model_name else model_name
        )
    else:
        narrative_model_provider = None
        narrative_model_name = None

    # Create initial generation (always starts at year 0 for root timelines)
    first_gen = timeline.generations[0]
    initial_generation = GenerationDB(
        id=str(first_gen.id),
        timeline_id=str(timeline.id),
        generation_order=1,
        generation_type=GenerationType.INITIAL.value,
        start_year=first_gen.start_year,
        end_year=first_gen.end_year,
        period_years=first_gen.period_years,
        executive_summary=initial_generation_output.executive_summary,
        political_changes=initial_generation_output.political_changes,
        conflicts_and_wars=initial_generation_output.conflicts_and_wars,
        economic_impacts=initial_generation_output.economic_impacts,
        social_developments=initial_generation_output.social_developments,
        technological_shifts=initial_generation_output.technological_shifts,
        key_figures=initial_generation_output.key_figures,
        long_term_implications=initial_generation_output.long_term_implications,
        narrative_mode=first_gen.narrative_mode.value if first_gen.narrative_mode else None,
        narrative_prose=initial_generation_output.narrative_prose,
        narrative_custom_pov=first_gen.narrative_custom_pov,
        source_skeleton_id=str(first_gen.source_skeleton_id) if first_gen.source_skeleton_id else (str(source_skeleton_id) if source_skeleton_id else None),
        report_model_provider=model_provider,
        report_model_name=model_name,
        narrative_model_provider=narrative_model_provider,
        narrative_model_name=narrative_model_name,
        created_at=first_gen.created_at,
        updated_at=first_gen.updated_at,
    )

    db.add(initial_generation)
    await db.flush()

    logger.info(
        f"Created timeline {timeline.id} with initial generation covering "
        f"{first_gen.period_years} years (type: {GenerationType.INITIAL.value})"
    )
    return db_timeline


# ============================================================================
# Timeline Extension
# ============================================================================


async def extend_timeline_with_new_generation(
    db: AsyncSession,
    timeline_id: UUID,
    extension_output: TimelineOutput,
    additional_years: int,
    narrative_mode: NarrativeMode = NarrativeMode.BASIC,
    narrative_custom_pov: Optional[str] = None,
    historian_provider: Optional[str] = None,
    historian_model_name: Optional[str] = None,
    storyteller_provider: Optional[str] = None,
    storyteller_model_name: Optional[str] = None,
    source_skeleton_id: Optional[UUID] = None,
) -> Optional[GenerationDB]:
    """
    Add a new generation to an existing timeline (extension).

    Args:
        db: Database session
        timeline_id: UUID of the timeline to extend
        extension_output: AI-generated content for the extension generation
        additional_years: Number of years being added
        narrative_mode: Mode for narrative generation
        narrative_custom_pov: Custom POV instructions (optional)
        historian_provider: Provider used for structured report (optional)
        historian_model_name: Model name used for structured report (optional)
        storyteller_provider: Provider used for narrative (optional)
        storyteller_model_name: Model name used for narrative (optional)
        source_skeleton_id: Skeleton used for generation (optional)

    Returns:
        GenerationDB: New extension generation if successful, None otherwise
    """
    # Use provided model info or fall back to global config
    model_provider = historian_provider
    model_name = historian_model_name

    if model_provider is None or model_name is None:
        from app.services import llm_service

        try:
            llm_config = await llm_service.get_current_llm_config(db)
            model_provider = llm_config.provider.value
            model_name = llm_config.model_name
        except Exception as e:
            logger.warning(f"Could not fetch LLM config for model tracking: {e}")
            model_provider = None
            model_name = None

    # Get existing timeline with all generations
    timeline = await get_timeline_by_id(db, timeline_id)
    if not timeline:
        logger.warning(f"Cannot extend timeline - not found: {timeline_id}")
        return None

    # Calculate the new generation details
    # Get max end_year from existing generations
    max_year_result = await db.execute(
        select(func.max(GenerationDB.end_year)).where(
            GenerationDB.timeline_id == str(timeline_id)
        )
    )
    current_max_year = max_year_result.scalar() or 0

    new_start_year = current_max_year
    new_end_year = current_max_year + additional_years

    # Get next generation order
    max_order_result = await db.execute(
        select(func.max(GenerationDB.generation_order)).where(
            GenerationDB.timeline_id == str(timeline_id)
        )
    )
    next_order = (max_order_result.scalar() or 0) + 1

    # Determine narrative model info
    has_narrative = extension_output.narrative_prose is not None
    if has_narrative:
        narrative_model_provider = (
            storyteller_provider if storyteller_provider else model_provider
        )
        narrative_model_name = (
            storyteller_model_name if storyteller_model_name else model_name
        )
    else:
        narrative_model_provider = None
        narrative_model_name = None

    # Create extension generation
    extension_generation = GenerationDB(
        timeline_id=str(timeline_id),
        generation_order=next_order,
        generation_type=GenerationType.EXTENSION.value,
        start_year=new_start_year,
        end_year=new_end_year,
        period_years=additional_years,
        executive_summary=extension_output.executive_summary,
        political_changes=extension_output.political_changes,
        conflicts_and_wars=extension_output.conflicts_and_wars,
        economic_impacts=extension_output.economic_impacts,
        social_developments=extension_output.social_developments,
        technological_shifts=extension_output.technological_shifts,
        key_figures=extension_output.key_figures,
        long_term_implications=extension_output.long_term_implications,
        narrative_mode=narrative_mode.value if narrative_mode != NarrativeMode.NONE else None,
        narrative_prose=extension_output.narrative_prose,
        narrative_custom_pov=narrative_custom_pov,
        source_skeleton_id=str(source_skeleton_id) if source_skeleton_id else None,
        report_model_provider=model_provider,
        report_model_name=model_name,
        narrative_model_provider=narrative_model_provider,
        narrative_model_name=narrative_model_name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(extension_generation)
    await db.flush()

    # Update timeline updated_at
    timeline.updated_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        f"Extended timeline {timeline_id}: added generation {next_order} "
        f"covering years {new_start_year}-{new_end_year} "
        f"(type: {GenerationType.EXTENSION.value})"
    )
    return extension_generation


# ============================================================================
# Timeline Branching (NEW)
# ============================================================================


async def create_branch_from_timeline(
    db: AsyncSession,
    source_timeline_id: UUID,
    branch_point_year: int,
    branch_deviation_description: str,
    branch_generation_output: TimelineOutput,
    simulation_years: int,
    scenario_type: str,
    narrative_mode: NarrativeMode = NarrativeMode.BASIC,
    narrative_custom_pov: Optional[str] = None,
    historian_provider: Optional[str] = None,
    historian_model_name: Optional[str] = None,
    storyteller_provider: Optional[str] = None,
    storyteller_model_name: Optional[str] = None,
    source_skeleton_id: Optional[UUID] = None,
) -> Optional[TimelineDB]:
    """
    Create a new timeline that branches from an existing timeline.

    Args:
        db: Database session
        source_timeline_id: Timeline to branch from
        branch_point_year: Year where branch diverges
        branch_deviation_description: What changed at branch point
        branch_generation_output: AI-generated content for branch
        simulation_years: Years to simulate after branch point
        scenario_type: Type of scenario
        narrative_mode: Mode for narrative generation
        narrative_custom_pov: Custom POV instructions (optional)
        historian_provider: Provider used for structured report (optional)
        historian_model_name: Model name used for structured report (optional)
        storyteller_provider: Provider used for narrative (optional)
        storyteller_model_name: Model name used for narrative (optional)
        source_skeleton_id: Skeleton used for generation (optional)

    Returns:
        TimelineDB: New branched timeline if successful, None otherwise
    """
    # Get source timeline
    source_timeline = await get_timeline_by_id(db, source_timeline_id)
    if not source_timeline:
        logger.warning(f"Cannot create branch - source timeline not found: {source_timeline_id}")
        return None

    # Use provided model info or fall back to global config
    model_provider = historian_provider
    model_name = historian_model_name

    if model_provider is None or model_name is None:
        from app.services import llm_service

        try:
            llm_config = await llm_service.get_current_llm_config(db)
            model_provider = llm_config.provider.value
            model_name = llm_config.model_name
        except Exception as e:
            logger.warning(f"Could not fetch LLM config for model tracking: {e}")
            model_provider = None
            model_name = None

    # Create new branched timeline (inherits root deviation from parent)
    branched_timeline = TimelineDB(
        parent_timeline_id=str(source_timeline_id),
        branch_point_year=branch_point_year,
        branch_deviation_description=branch_deviation_description,
        root_deviation_date=source_timeline.root_deviation_date,
        root_deviation_description=source_timeline.root_deviation_description,
        scenario_type=scenario_type,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(branched_timeline)
    await db.flush()

    # Determine narrative model info
    has_narrative = branch_generation_output.narrative_prose is not None
    if has_narrative:
        narrative_model_provider = (
            storyteller_provider if storyteller_provider else model_provider
        )
        narrative_model_name = (
            storyteller_model_name if storyteller_model_name else model_name
        )
    else:
        narrative_model_provider = None
        narrative_model_name = None

    # Create branch point generation
    branch_generation = GenerationDB(
        timeline_id=str(branched_timeline.id),
        generation_order=1,
        generation_type=GenerationType.BRANCH_POINT.value,
        start_year=branch_point_year,
        end_year=branch_point_year + simulation_years,
        period_years=simulation_years,
        executive_summary=branch_generation_output.executive_summary,
        political_changes=branch_generation_output.political_changes,
        conflicts_and_wars=branch_generation_output.conflicts_and_wars,
        economic_impacts=branch_generation_output.economic_impacts,
        social_developments=branch_generation_output.social_developments,
        technological_shifts=branch_generation_output.technological_shifts,
        key_figures=branch_generation_output.key_figures,
        long_term_implications=branch_generation_output.long_term_implications,
        narrative_mode=narrative_mode.value if narrative_mode != NarrativeMode.NONE else None,
        narrative_prose=branch_generation_output.narrative_prose,
        narrative_custom_pov=narrative_custom_pov,
        source_skeleton_id=str(source_skeleton_id) if source_skeleton_id else None,
        report_model_provider=model_provider,
        report_model_name=model_name,
        narrative_model_provider=narrative_model_provider,
        narrative_model_name=narrative_model_name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(branch_generation)
    await db.flush()

    logger.info(
        f"Created branch timeline {branched_timeline.id} from {source_timeline_id} "
        f"at year {branch_point_year} (type: {GenerationType.BRANCH_POINT.value})"
    )
    return branched_timeline


# ============================================================================
# Retrieval Operations
# ============================================================================


async def get_all_timelines(db: AsyncSession) -> List[TimelineDB]:
    """
    Get all timelines from database.

    Args:
        db: Database session

    Returns:
        List[TimelineDB]: All timelines with their generations and media
    """
    result = await db.execute(
        select(TimelineDB)
        .options(
            selectinload(TimelineDB.generations).selectinload(GenerationDB.media)
        )
        .order_by(TimelineDB.created_at.desc())
    )
    timelines = result.scalars().all()

    logger.info(f"Retrieved {len(timelines)} timelines")
    return list(timelines)


async def get_timeline_by_id(
    db: AsyncSession, timeline_id: UUID
) -> Optional[TimelineDB]:
    """
    Get a specific timeline by ID with all its generations and media.

    Args:
        db: Database session
        timeline_id: Timeline UUID

    Returns:
        Optional[TimelineDB]: Timeline if found, None otherwise
    """
    result = await db.execute(
        select(TimelineDB)
        .options(
            selectinload(TimelineDB.generations).selectinload(GenerationDB.media)
        )
        .where(TimelineDB.id == str(timeline_id))
    )
    timeline = result.scalar_one_or_none()

    if timeline:
        logger.info(
            f"Retrieved timeline {timeline_id} with {len(timeline.generations)} generations"
        )
    else:
        logger.warning(f"Timeline not found: {timeline_id}")

    return timeline


async def get_timeline_with_children(
    db: AsyncSession, timeline_id: UUID
) -> Optional[TimelineDB]:
    """
    Get a timeline with its child timelines (branches).

    Args:
        db: Database session
        timeline_id: Timeline UUID

    Returns:
        Optional[TimelineDB]: Timeline with children if found, None otherwise
    """
    result = await db.execute(
        select(TimelineDB)
        .options(
            selectinload(TimelineDB.generations).selectinload(GenerationDB.media),
            selectinload(TimelineDB.children),
        )
        .where(TimelineDB.id == str(timeline_id))
    )
    timeline = result.scalar_one_or_none()

    if timeline:
        logger.info(
            f"Retrieved timeline {timeline_id} with {len(timeline.children)} child timelines"
        )
    else:
        logger.warning(f"Timeline not found: {timeline_id}")

    return timeline


# ============================================================================
# Deletion Operations
# ============================================================================


async def delete_timeline(db: AsyncSession, timeline_id: UUID) -> bool:
    """
    Delete a timeline and all its generations and media (cascade).

    Args:
        db: Database session
        timeline_id: Timeline UUID

    Returns:
        bool: True if deleted, False if not found
    """
    result = await db.execute(
        select(TimelineDB).where(TimelineDB.id == str(timeline_id))
    )
    timeline = result.scalar_one_or_none()

    if not timeline:
        logger.warning(f"Cannot delete - timeline not found: {timeline_id}")
        return False

    # Count generations before deletion
    gen_count_result = await db.execute(
        select(func.count(GenerationDB.id)).where(
            GenerationDB.timeline_id == str(timeline_id)
        )
    )
    gen_count = gen_count_result.scalar()

    await db.delete(timeline)
    await db.flush()

    # Clean up vector store chunks
    try:
        from app.services.vector_store_service import get_vector_store_service
        vector_service = get_vector_store_service()
        if vector_service.enabled:
            cleanup_result = await vector_service.delete_timeline_vectors(
                str(timeline_id), db
            )
            logger.info(
                f"Deleted {cleanup_result.get('deleted', 0)} vector chunks for timeline {timeline_id}"
            )
    except Exception as e:
        logger.warning(f"Failed to clean up vector store for timeline {timeline_id}: {e}")

    logger.info(
        f"Deleted timeline {timeline_id} with {gen_count} generations (cascade)"
    )
    return True


async def delete_generation(
    db: AsyncSession, generation_id: UUID, timeline_id: UUID
) -> bool:
    """
    Delete a specific generation from a timeline.

    Note: This may leave gaps in generation_order, but that's acceptable.
    Consider reordering remaining generations if needed.

    Args:
        db: Database session
        generation_id: Generation UUID
        timeline_id: Timeline UUID (for verification)

    Returns:
        bool: True if deleted, False if not found
    """
    result = await db.execute(
        select(GenerationDB).where(
            GenerationDB.id == str(generation_id),
            GenerationDB.timeline_id == str(timeline_id),
        )
    )
    generation = result.scalar_one_or_none()

    if not generation:
        logger.warning(
            f"Cannot delete - generation not found: {generation_id} "
            f"in timeline {timeline_id}"
        )
        return False

    gen_order = generation.generation_order
    gen_type = generation.generation_type

    await db.delete(generation)
    await db.flush()

    # Clean up vector store chunks
    try:
        from app.services.vector_store_service import get_vector_store_service
        vector_service = get_vector_store_service()
        if vector_service.enabled:
            cleanup_result = await vector_service.delete_generation_vectors(
                str(generation_id), db
            )
            logger.info(
                f"Deleted {cleanup_result.get('deleted', 0)} vector chunks for generation {generation_id}"
            )
    except Exception as e:
        logger.warning(f"Failed to clean up vector store for generation {generation_id}: {e}")

    logger.info(
        f"Deleted generation {generation_id} (order: {gen_order}, "
        f"type: {gen_type}) from timeline {timeline_id}"
    )
    return True
