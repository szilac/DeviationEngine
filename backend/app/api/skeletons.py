"""
Skeleton API endpoints.

This module handles:
- Skeleton generation from deviation parameters
- Extension skeleton generation
- Skeleton event editing and approval
- Timeline generation from approved skeletons
- Timeline extension from approved extension skeletons
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date as date_type

from app.database import get_db
from app.services import generation_progress
from app.models import (
    TimelineCreationRequest,
    SkeletonResponse,
    SkeletonEventsUpdateRequest,
    Timeline,
    GenerationType,
    Generation,
    ScenarioType,
    SkeletonType,
    TimelineExtensionRequest,
    GenerateFromSkeletonRequest,
    ExtendFromSkeletonRequest,
)
from app.db_models import SkeletonDB
from app.services import timeline_service, skeleton_service, llm_service
from app.services.history_service import get_history_service
from app.agents.workflows import (
    execute_skeleton_generation,
    execute_report_from_skeleton,
    execute_extension_skeleton_generation,
    execute_extension_from_skeleton,
)
from app.agents.historian_agent import TimelineOutput
from app.exceptions import HistoricalContextError, AIGenerationError

logger = logging.getLogger(__name__)

# Create router with /api prefix
router = APIRouter(prefix="/api", tags=["skeleton-timelines"])


@router.post(
    "/generate-skeleton", response_model=SkeletonResponse, status_code=status.HTTP_201_CREATED
)
async def generate_skeleton_endpoint(request: TimelineCreationRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a skeleton timeline with key events.

    This endpoint creates an editable skeleton of 15-25 key events
    that can be reviewed and modified before generating the full report.

    Args:
        request: Skeleton generation parameters

    Returns:
        SkeletonResponse: Generated skeleton with events

    Raises:
        HTTPException: 400 if validation fails, 500 if generation fails
    """
    logger.info(
        f"Received skeleton generation request: {request.deviation_date} - "
        f"{request.deviation_description[:50]}..."
    )

    try:
        # Get historical context using RAG
        history_service = get_history_service()
        historical_context = await history_service.get_context_for_deviation(
            deviation_date=request.deviation_date,
            simulation_years=request.simulation_years,
            deviation_description=request.deviation_description,
            scenario_type=request.scenario_type.value,
            use_rag=request.use_rag,
            db=db
        )

        if not historical_context:
            raise HistoricalContextError(
                "No historical context available for the specified date range",
                details={
                    "deviation_date": str(request.deviation_date),
                    "simulation_years": request.simulation_years,
                },
            )

        # Execute skeleton generation workflow
        result = await execute_skeleton_generation(
            skeleton_request=request, historical_context=historical_context, db_session=db
        )

        skeleton_output = result["skeleton_output"]

        # Get LLM config for model tracking
        llm_config = await llm_service.get_current_llm_config(db)

        # Save skeleton to database
        skeleton = await skeleton_service.create_timeline_draft_skeleton(
            db=db,
            deviation_date=request.deviation_date,
            deviation_description=request.deviation_description,
            scenario_type=request.scenario_type,
            simulation_years=request.simulation_years,
            agent_output=skeleton_output,
            model_provider=llm_config.provider if llm_config else None,
            model_name=llm_config.model_name if llm_config else None,
        )

        await db.commit()

        logger.info(f"Skeleton generated successfully: {skeleton.id}")
        return skeleton

    except HistoricalContextError as e:
        logger.error(f"Historical context error: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except AIGenerationError as e:
        logger.error(f"AI generation error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during skeleton generation: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during skeleton generation",
        )


@router.get("/skeletons", response_model=List[SkeletonResponse])
async def get_all_skeletons_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Get all skeleton timelines sorted by created date (newest first).

    Returns:
        List[SkeletonResponse]: List of all skeletons with their events
    """
    logger.info("Retrieving all skeletons")
    skeletons = await skeleton_service.get_all_skeletons(db)
    return skeletons


@router.get("/skeleton/{skeleton_id}", response_model=SkeletonResponse)
async def get_skeleton_endpoint(skeleton_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a skeleton by ID.

    Args:
        skeleton_id: Skeleton UUID

    Returns:
        SkeletonResponse: Skeleton with all events

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(f"Retrieving skeleton: {skeleton_id}")

    skeleton = await skeleton_service.get_skeleton(db, skeleton_id)

    if not skeleton:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skeleton with ID {skeleton_id} not found",
        )

    return skeleton


@router.put("/skeleton/{skeleton_id}/events", response_model=SkeletonResponse)
async def update_skeleton_events_endpoint(
    skeleton_id: UUID, request: SkeletonEventsUpdateRequest, db: AsyncSession = Depends(get_db)
):
    """
    Update skeleton events (create, update, delete).

    Allows user to edit the skeleton before generating the full report.

    Args:
        skeleton_id: Skeleton UUID
        request: Update request with events and deletions

    Returns:
        SkeletonResponse: Updated skeleton

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(
        f"Updating skeleton {skeleton_id}: {len(request.events_update)} events, "
        f"{len(request.deleted_event_ids)} deletions"
    )

    skeleton = await skeleton_service.update_skeleton_events(
        db=db,
        skeleton_id=skeleton_id,
        events_update=request.events_update,
        deleted_event_ids=request.deleted_event_ids,
    )

    if not skeleton:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skeleton with ID {skeleton_id} not found",
        )

    await db.commit()
    logger.info(f"Skeleton {skeleton_id} updated successfully")

    return skeleton


@router.post("/skeleton/{skeleton_id}/approve", response_model=SkeletonResponse)
async def approve_skeleton_endpoint(skeleton_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Mark skeleton as approved by user.

    Args:
        skeleton_id: Skeleton UUID

    Returns:
        SkeletonResponse: Approved skeleton

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(f"Approving skeleton: {skeleton_id}")

    skeleton = await skeleton_service.approve_skeleton(db, skeleton_id)

    if not skeleton:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skeleton with ID {skeleton_id} not found",
        )

    await db.commit()
    logger.info(f"Skeleton {skeleton_id} approved")

    return skeleton


@router.post("/generate-from-skeleton", response_model=Timeline, status_code=status.HTTP_201_CREATED)
async def generate_from_skeleton_endpoint(
    request: "GenerateFromSkeletonRequest", db: AsyncSession = Depends(get_db)
):
    """
    Generate comprehensive timeline report from approved skeleton.

    This endpoint takes a user-approved skeleton and generates the full
    analytical report and optional narrative.

    Args:
        request: Contains skeleton_id and narrative preferences

    Returns:
        Timeline: Complete generated timeline

    Raises:
        HTTPException: 404 if skeleton not found, 500 if generation fails
    """

    logger.info(f"Generating report from skeleton: {request.skeleton_id}")

    try:
        # Retrieve skeleton
        skeleton = await skeleton_service.get_skeleton(db, request.skeleton_id)

        if not skeleton:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skeleton with ID {request.skeleton_id} not found",
            )

        # Check skeleton type - this endpoint is only for TIMELINE_DRAFT skeletons
        if skeleton.skeleton_type != SkeletonType.TIMELINE_DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This endpoint is for timeline draft skeletons only. "
                f"Skeleton {request.skeleton_id} is a {skeleton.skeleton_type.value}. "
                f"Use /api/extend-from-skeleton for extension skeletons.",
            )

        # Create timeline creation request for workflow
        scenario_type = skeleton.scenario_type if skeleton.scenario_type else ScenarioType.LOCAL_DEVIATION

        deviation_request = TimelineCreationRequest(
            deviation_date=skeleton.deviation_date,
            deviation_description=skeleton.deviation_description,
            simulation_years=skeleton.period_years,
            scenario_type=scenario_type,
            narrative_mode=request.narrative_mode,
            narrative_custom_pov=request.narrative_custom_pov,
            use_rag=request.use_rag,
        )

        # Execute report from skeleton workflow
        result = await execute_report_from_skeleton(
            skeleton=skeleton,
            deviation_request=deviation_request,
            db_session=db,
            progress_token=request.progress_token,
        )

        structured_report = result["structured_report"]
        narrative_prose = result["narrative_prose"]
        timeline_name = result.get("timeline_name", "Alternate Timeline")  # Get timeline name from workflow
        historian_provider = result.get("historian_provider")
        historian_model_name = result.get("historian_model_name")
        storyteller_provider = result.get("storyteller_provider")
        storyteller_model_name = result.get("storyteller_model_name")

        # Create Timeline object first to get its ID
        timeline = Timeline(
            root_deviation_date=skeleton.deviation_date,
            root_deviation_description=skeleton.deviation_description,
            scenario_type=deviation_request.scenario_type,
            generations=[],
        )

        # Create initial generation from workflow results
        initial_generation = Generation(
            timeline_id=timeline.id,
            generation_order=1,
            generation_type=GenerationType.INITIAL,
            start_year=0,
            end_year=deviation_request.simulation_years,
            period_years=deviation_request.simulation_years,
            executive_summary=structured_report.executive_summary,
            political_changes=structured_report.political_changes,
            conflicts_and_wars=structured_report.conflicts_and_wars,
            economic_impacts=structured_report.economic_impacts,
            social_developments=structured_report.social_developments,
            technological_shifts=structured_report.technological_shifts,
            key_figures=structured_report.key_figures,
            long_term_implications=structured_report.long_term_implications,
            narrative_mode=deviation_request.narrative_mode,
            narrative_prose=narrative_prose,
            narrative_custom_pov=deviation_request.narrative_custom_pov,
            source_skeleton_id=skeleton.id,
            report_model_provider=historian_provider,
            report_model_name=historian_model_name,
            narrative_model_provider=storyteller_provider,
            narrative_model_name=storyteller_model_name,
        )

        # Add generation to timeline
        timeline.generations = [initial_generation]

        # Create TimelineOutput for database storage
        timeline_output_for_db = TimelineOutput(
            timeline_name=timeline_name,  # Use timeline_name from workflow result
            executive_summary=structured_report.executive_summary,
            political_changes=structured_report.political_changes,
            conflicts_and_wars=structured_report.conflicts_and_wars,
            economic_impacts=structured_report.economic_impacts,
            social_developments=structured_report.social_developments,
            technological_shifts=structured_report.technological_shifts,
            key_figures=structured_report.key_figures,
            long_term_implications=structured_report.long_term_implications,
            narrative_prose=narrative_prose,
        )

        # Save timeline to database
        db_timeline = await timeline_service.create_timeline_with_initial_generation(
            db=db,
            timeline=timeline,
            initial_generation_output=timeline_output_for_db,
            historian_provider=historian_provider,
            historian_model_name=historian_model_name,
            storyteller_provider=storyteller_provider,
            storyteller_model_name=storyteller_model_name,
        )
        timeline_id = UUID(db_timeline.id)  # Extract UUID from TimelineDB object

        # Link skeleton to timeline
        await skeleton_service.link_skeleton_to_timeline(
            db=db,
            skeleton_id=request.skeleton_id,
            timeline_id=timeline_id
        )

        # Index generated content for RAG
        try:
            from app.services.vector_store_service import get_vector_store_service
            import asyncio

            vector_service = get_vector_store_service()
            if vector_service.enabled:
                # Extract report sections
                report_sections = {
                    "executive_summary": structured_report.executive_summary,
                    "political_changes": structured_report.political_changes,
                    "conflicts_and_wars": structured_report.conflicts_and_wars,
                    "economic_impacts": structured_report.economic_impacts,
                    "social_developments": structured_report.social_developments,
                    "technological_shifts": structured_report.technological_shifts,
                    "key_figures": structured_report.key_figures,
                    "long_term_implications": structured_report.long_term_implications
                }

                # Get the generation ID from the timeline
                generation_id = str(initial_generation.id)

                # Start background indexing (non-blocking)
                asyncio.create_task(
                    vector_service.index_generation_background(
                        generation_id=generation_id,
                        timeline_id=str(timeline_id),
                        report_sections=report_sections,
                        narrative=narrative_prose,
                        year_start=skeleton.deviation_date.year,
                        year_end=skeleton.deviation_date.year + skeleton.period_years,
                        db=db
                    )
                )
                logger.info(f"Started background indexing for skeleton-based generation {generation_id}")
        except Exception as e:
            logger.warning(f"Failed to start background indexing for skeleton generation: {e}", exc_info=True)

        # Fetch the timeline with proper eager loading for relationships
        db_timeline_with_relations = await timeline_service.get_timeline_by_id(db, timeline_id)
        if db_timeline_with_relations is None:
            logger.error(f"Timeline {timeline_id} was created but not found in database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Timeline creation succeeded but retrieval failed"
            )

        # Convert to Pydantic model and return
        created_timeline = Timeline.model_validate(db_timeline_with_relations)

        logger.info(f"Timeline generated successfully from skeleton: {timeline_id}")
        await generation_progress.publish(request.progress_token, {
            "step": "done", "timeline_id": str(timeline_id)
        })
        return created_timeline

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating from skeleton: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during generation",
        )


@router.delete("/skeleton/{skeleton_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skeleton_endpoint(skeleton_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a skeleton and all its events.

    Args:
        skeleton_id: Skeleton UUID

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(f"Deleting skeleton: {skeleton_id}")

    deleted = await skeleton_service.delete_skeleton(db, skeleton_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skeleton with ID {skeleton_id} not found",
        )

    await db.commit()
    logger.info(f"Skeleton {skeleton_id} deleted")


@router.post(
    "/generate-extension-skeleton",
    response_model=SkeletonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_extension_skeleton_endpoint(
    request: TimelineExtensionRequest, db: AsyncSession = Depends(get_db)
):
    """
    Generate an extension skeleton for an existing timeline.

    This endpoint creates a hidden extension skeleton that allows users to
    review and edit key events before extending the timeline.

    Args:
        request: Extension skeleton parameters (timeline_id, additional_years)

    Returns:
        SkeletonResponse: Generated extension skeleton with events

    Raises:
        HTTPException: 404 if timeline not found, 500 if generation fails
    """
    logger.info(
        f"Received extension skeleton request for timeline {request.timeline_id}: "
        f"+{request.additional_years} years"
    )

    try:
        # Retrieve the timeline from database
        db_timeline = await timeline_service.get_timeline_by_id(db, request.timeline_id)

        if not db_timeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timeline with ID {request.timeline_id} not found",
            )

        # Get historical context
        deviation_date = date_type.fromisoformat(db_timeline.root_deviation_date)

        # Calculate total years simulated so far
        timeline_pydantic = Timeline.model_validate(db_timeline)
        current_total_years = timeline_pydantic.total_years_simulated
        extension_start_year = deviation_date.year + current_total_years

        # Get context from previous generations (NOT ground truth)
        history_service = get_history_service()
        historical_context, debug_info = await history_service.get_context_for_extension_rag(
            timeline_id=str(request.timeline_id),
            extension_start_year=extension_start_year,
            deviation_description=db_timeline.root_deviation_description,
            scenario_type=db_timeline.scenario_type,
            use_rag=request.use_rag,
            db=db
        )

        if not historical_context:
            logger.warning(
                f"No previous generation context found for extension skeleton, "
                f"proceeding without prior context (mode may be legacy or RAG disabled)"
            )

        # Execute extension skeleton generation workflow
        result = await execute_extension_skeleton_generation(
            timeline=timeline_pydantic,
            extension_request=request,
            historical_context=historical_context,
            db_session=db,
        )

        skeleton_output = result["skeleton_output"]
        extension_start_year = result["extension_start_year"]

        # Get LLM config for model tracking
        llm_config = await llm_service.get_current_llm_config(db)

        # Calculate extension end year
        extension_end_year = extension_start_year + request.additional_years

        # Save extension skeleton to database
        skeleton = await skeleton_service.create_extension_draft_skeleton(
            db=db,
            parent_timeline_id=request.timeline_id,
            extension_start_year=extension_start_year,
            extension_end_year=extension_end_year,
            agent_output=skeleton_output,
            model_provider=llm_config.provider if llm_config else None,
            model_name=llm_config.model_name if llm_config else None,
        )

        await db.commit()

        logger.info(
            f"Extension skeleton generated successfully: {skeleton.id} for timeline {request.timeline_id}"
        )
        return skeleton

    except HistoricalContextError as e:
        logger.error(f"Historical context error: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except AIGenerationError as e:
        logger.error(f"AI generation error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during extension skeleton generation: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during extension skeleton generation",
        )


@router.post("/extend-from-skeleton", response_model=Timeline, status_code=status.HTTP_201_CREATED)
async def extend_from_skeleton_endpoint(
    request: "ExtendFromSkeletonRequest", db: AsyncSession = Depends(get_db)
):
    """
    Extend a timeline from an approved extension skeleton.

    This endpoint takes a user-approved extension skeleton and generates
    a comprehensive extension report that is added to the parent timeline.

    Args:
        request: Contains timeline_id, skeleton_id, and narrative preferences

    Returns:
        Timeline: Updated timeline with new extension report

    Raises:
        HTTPException: 404 if timeline or skeleton not found, 500 if generation fails
    """

    logger.info(f"Extending timeline {request.timeline_id} from skeleton {request.skeleton_id}")

    try:
        # Retrieve the timeline from database
        db_timeline = await timeline_service.get_timeline_by_id(db, request.timeline_id)

        if not db_timeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timeline with ID {request.timeline_id} not found",
            )

        # Retrieve the extension skeleton
        skeleton = await skeleton_service.get_skeleton(db, request.skeleton_id)

        if not skeleton:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skeleton with ID {request.skeleton_id} not found",
            )

        # Verify skeleton is an extension skeleton for this timeline
        result = await db.execute(select(SkeletonDB).where(SkeletonDB.id == str(request.skeleton_id)))
        db_skeleton = result.scalar_one_or_none()

        if not db_skeleton or not db_skeleton.parent_timeline_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Skeleton {request.skeleton_id} is not an extension skeleton",
            )

        if db_skeleton.parent_timeline_id != str(request.timeline_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Skeleton {request.skeleton_id} is not an extension skeleton for timeline {request.timeline_id}",
            )

        # Convert DB timeline to Pydantic model for workflow
        timeline_pydantic = Timeline.model_validate(db_timeline)

        # Execute extension from skeleton workflow
        result = await execute_extension_from_skeleton(
            timeline=timeline_pydantic, skeleton=skeleton, extension_request=request, db_session=db
        )

        structured_report = result["structured_report"]
        narrative_prose = result["narrative_prose"]
        timeline_name = result.get("timeline_name", "Alternate Timeline")  # Get timeline name from workflow
        historian_provider = result.get("historian_provider")
        historian_model_name = result.get("historian_model_name")
        storyteller_provider = result.get("storyteller_provider")
        storyteller_model_name = result.get("storyteller_model_name")

        # Create TimelineOutput for database storage
        timeline_output_for_db = TimelineOutput(
            executive_summary=structured_report.executive_summary,
            political_changes=structured_report.political_changes,
            conflicts_and_wars=structured_report.conflicts_and_wars,
            economic_impacts=structured_report.economic_impacts,
            social_developments=structured_report.social_developments,
            technological_shifts=structured_report.technological_shifts,
            key_figures=structured_report.key_figures,
            long_term_implications=structured_report.long_term_implications,
            narrative_prose=narrative_prose,  # Include generated narrative
        )

        # Calculate extension years and metadata
        extension_start_year = skeleton.extension_start_year
        extension_end_year = skeleton.extension_end_year
        extension_years = extension_end_year - extension_start_year

        # Add extension generation to timeline
        new_generation = await timeline_service.extend_timeline_with_new_generation(
            db=db,
            timeline_id=request.timeline_id,
            extension_output=timeline_output_for_db,
            additional_years=extension_years,
            narrative_mode=request.narrative_mode,
            narrative_custom_pov=request.narrative_custom_pov,
            historian_provider=historian_provider,
            historian_model_name=historian_model_name,
            storyteller_provider=storyteller_provider,
            storyteller_model_name=storyteller_model_name,
            source_skeleton_id=request.skeleton_id,  # Link generation to source skeleton
        )

        await db.commit()

        # Index generated content for RAG
        try:
            from app.services.vector_store_service import get_vector_store_service
            import asyncio

            vector_service = get_vector_store_service()
            if vector_service.enabled:
                # Extract report sections
                report_sections = {
                    "executive_summary": structured_report.executive_summary,
                    "political_changes": structured_report.political_changes,
                    "conflicts_and_wars": structured_report.conflicts_and_wars,
                    "economic_impacts": structured_report.economic_impacts,
                    "social_developments": structured_report.social_developments,
                    "technological_shifts": structured_report.technological_shifts,
                    "key_figures": structured_report.key_figures,
                    "long_term_implications": structured_report.long_term_implications
                }

                # Start background indexing (non-blocking)
                asyncio.create_task(
                    vector_service.index_generation_background(
                        generation_id=str(new_generation.id),
                        timeline_id=str(request.timeline_id),
                        report_sections=report_sections,
                        narrative=narrative_prose,
                        year_start=extension_start_year,
                        year_end=extension_end_year,
                        db=db
                    )
                )
                logger.info(f"Started background indexing for skeleton-based extension {new_generation.id}")
        except Exception as e:
            logger.warning(f"Failed to start background indexing for skeleton extension: {e}", exc_info=True)

        # Retrieve updated timeline
        updated_db_timeline = await timeline_service.get_timeline_by_id(db, request.timeline_id)
        updated_timeline = Timeline.model_validate(updated_db_timeline)

        logger.info(f"Timeline {request.timeline_id} extended successfully from skeleton {request.skeleton_id}")
        return updated_timeline

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error extending from skeleton: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during extension",
        )


@router.get("/timelines/{timeline_id}/skeleton-snapshot")
async def get_timeline_skeleton_snapshot(
    timeline_id: UUID, generation_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)
):
    """
    Get the skeleton events snapshot used to generate a timeline or specific generation.

    Returns the immutable snapshot of skeleton events that were used when
    this timeline or generation was generated.

    Args:
        timeline_id: Timeline UUID
        generation_id: Optional generation UUID

    Returns:
        dict: Snapshot data with skeleton events and metadata

    Raises:
        HTTPException: 404 if timeline/generation not found or was not generated from skeleton
    """
    if generation_id:
        logger.info(f"Retrieving skeleton snapshot for generation {generation_id} in timeline {timeline_id}")
    else:
        logger.info(f"Retrieving skeleton snapshot for timeline {timeline_id}")

    try:
        snapshot = await skeleton_service.get_skeleton_snapshot(
            db=db, timeline_id=timeline_id, generation_id=generation_id
        )

        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No skeleton snapshot found for this timeline/generation",
            )

        return snapshot

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving skeleton snapshot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve skeleton snapshot",
        )
