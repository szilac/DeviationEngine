"""
Timeline API Router

This module handles all timeline-related endpoints including:
- Timeline generation from deviation parameters
- Timeline listing and retrieval
- Timeline extension
- Timeline and generation deletion
- Skeleton snapshot retrieval
"""

import json
import asyncio
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db
from app.services import generation_progress
from app.models import (
    Timeline,
    TimelineListItem,
    TimelineCreationRequest,
    TimelineExtensionRequest,
    TimelineOutput,
    Generation,
    GenerationType,
)
from app.db_models import GenerationDB as GenerationDB
from app.services import timeline_service, skeleton_service
from app.services.history_service import get_history_service
from app.agents.workflows import (
    execute_timeline_generation,
    execute_timeline_extension,
)
from app.exceptions import (
    TimelineNotFoundError,
    HistoricalContextError,
    AIGenerationError,
    ValidationError,
)

router = APIRouter(prefix="/api", tags=["timelines"])
logger = logging.getLogger(__name__)


# ============================================================================
# SSE Progress Stream
# ============================================================================


@router.get("/timelines/progress/{progress_token}")
async def generation_progress_stream(progress_token: str):
    """SSE endpoint for streaming generation step progress to the frontend."""
    async def event_stream():
        try:
            async for event in generation_progress.subscribe(progress_token):
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("step") == "done":
                    break
        except asyncio.CancelledError:
            pass  # Client disconnected — clean up handled by subscribe()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Timeline Generation
# ============================================================================


@router.post(
    "/generate-timeline",
    response_model=Timeline,
    status_code=status.HTTP_201_CREATED,
)
async def generate_timeline_endpoint(
    request: TimelineCreationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new alternate history timeline.

    This endpoint takes a historical deviation point and generates a comprehensive
    alternate history timeline using AI-powered analysis.

    Args:
        request: Deviation parameters including date, description, and simulation length

    Returns:
        Timeline: Complete generated timeline with structured report and narrative

    Raises:
        HTTPException: 400 if validation fails, 500 if generation fails
    """
    logger.info(
        f"Received timeline generation request: {request.deviation_date} - "
        f"{request.deviation_description[:50]}..."
    )

    try:
        # Publish context retrieval started
        await generation_progress.publish(request.progress_token, {
            "step": "context_retrieval", "status": "started", "label": "Retrieving historical context"
        })

        # Get historical context from ground truth service (uses RAG if available)
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
                    "simulation_years": request.simulation_years
                }
            )

        await generation_progress.publish(request.progress_token, {
            "step": "context_retrieval", "status": "completed", "label": "Historical context retrieved"
        })

        # Generate timeline using orchestrator
        logger.info(
            "Generating timeline with orchestrator...",
            extra={
                "deviation_date": str(request.deviation_date),
                "simulation_years": request.simulation_years,
                "scenario_type": request.scenario_type.value,
                "narrative_mode": request.narrative_mode.value
            }
        )
        workflow_result = await execute_timeline_generation(
            request, historical_context, db_session=db, progress_token=request.progress_token
        )

        # Extract results
        structured_report = workflow_result["structured_report"]
        narrative_prose = workflow_result["narrative_prose"]
        timeline_name = workflow_result.get("timeline_name", "Alternate Timeline")  # Get timeline name from workflow
        workflow_metadata = workflow_result["workflow_metadata"]
        historian_provider = workflow_result.get("historian_provider")
        historian_model_name = workflow_result.get("historian_model_name")
        storyteller_provider = workflow_result.get("storyteller_provider")
        storyteller_model_name = workflow_result.get("storyteller_model_name")

        logger.info(
            f"Workflow completed in {workflow_metadata.get('duration_seconds', 0):.2f}s",
            extra=workflow_metadata
        )

        # Create Timeline object first to get its ID
        timeline = Timeline(
            root_deviation_date=request.deviation_date,
            root_deviation_description=request.deviation_description,
            scenario_type=request.scenario_type,
            generations=[]
        )

        # Create initial generation from workflow results
        initial_generation = Generation(
            timeline_id=timeline.id,
            generation_order=1,
            generation_type=GenerationType.INITIAL,
            start_year=0,
            end_year=request.simulation_years,
            period_years=request.simulation_years,
            executive_summary=structured_report.executive_summary,
            political_changes=structured_report.political_changes,
            conflicts_and_wars=structured_report.conflicts_and_wars,
            economic_impacts=structured_report.economic_impacts,
            social_developments=structured_report.social_developments,
            technological_shifts=structured_report.technological_shifts,
            key_figures=structured_report.key_figures,
            long_term_implications=structured_report.long_term_implications,
            narrative_mode=request.narrative_mode,
            narrative_prose=narrative_prose,
            narrative_custom_pov=request.narrative_custom_pov if hasattr(request, 'narrative_custom_pov') else None,
            report_model_provider=historian_provider,
            report_model_name=historian_model_name,
            narrative_model_provider=storyteller_provider,
            narrative_model_name=storyteller_model_name
        )

        # Add generation to timeline
        timeline.generations = [initial_generation]

        # Create TimelineOutput for database storage
        timeline_output_for_db = TimelineOutput(
            timeline_name=timeline_name,  # Use timeline_name from workflow
            executive_summary=structured_report.executive_summary,
            political_changes=structured_report.political_changes,
            conflicts_and_wars=structured_report.conflicts_and_wars,
            economic_impacts=structured_report.economic_impacts,
            social_developments=structured_report.social_developments,
            technological_shifts=structured_report.technological_shifts,
            key_figures=structured_report.key_figures,
            long_term_implications=structured_report.long_term_implications,
            narrative_prose=narrative_prose
        )

        await generation_progress.publish(request.progress_token, {
            "step": "saving", "status": "started", "label": "Saving to library"
        })
        # Store in database with model tracking information
        await timeline_service.create_timeline_with_initial_generation(
            db,
            timeline,
            timeline_output_for_db,
            historian_provider=historian_provider,
            historian_model_name=historian_model_name,
            storyteller_provider=storyteller_provider,
            storyteller_model_name=storyteller_model_name
        )

        # Index generated content in background for future RAG retrieval
        try:
            from app.services.vector_store_service import get_vector_store_service
            import asyncio

            vector_service = get_vector_store_service()
            if vector_service.enabled:
                # Extract report sections from structured report
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
                        generation_id=str(initial_generation.id),
                        timeline_id=str(timeline.id),
                        report_sections=report_sections,
                        narrative=narrative_prose,
                        year_start=request.deviation_date.year,
                        year_end=request.deviation_date.year + request.simulation_years,
                        db=db
                    )
                )
                logger.info(f"Started background indexing for generation {initial_generation.id}")
        except Exception as e:
            # Don't fail timeline generation if indexing fails
            logger.warning(f"Failed to start background indexing: {e}", exc_info=True)

        narrative_length = len(narrative_prose) if narrative_prose else 0
        logger.info(
            f"Successfully generated timeline with ID: {timeline.id}",
            extra={
                "timeline_id": str(timeline.id),
                "narrative_length": narrative_length,
                "has_narrative": narrative_prose is not None,
                "narrative_mode": request.narrative_mode.value
            }
        )
        await generation_progress.publish(request.progress_token, {
            "step": "done", "timeline_id": str(timeline.id)
        })
        return timeline

    except (HistoricalContextError, AIGenerationError, ValidationError):
        # Re-raise custom exceptions (handled by exception handlers)
        raise
    except ValueError as e:
        # Pydantic validation errors
        raise ValidationError(
            str(e),
            details={"field_validation": True}
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during timeline generation: {e}",
            exc_info=True,
            extra={
                "deviation_date": str(request.deviation_date),
                "scenario_type": request.scenario_type.value
            }
        )
        raise AIGenerationError(
            "Timeline generation failed due to an unexpected error",
            details={"error": str(e)}
        )


# ============================================================================
# Timeline Retrieval
# ============================================================================


@router.get(
    "/timelines",
    response_model=List[TimelineListItem],
)
async def list_timelines(db: AsyncSession = Depends(get_db)):
    """
    List all generated timelines.

    Returns simplified timeline information for all stored timelines.

    Returns:
        List[TimelineListItem]: List of timeline summaries with basic info
    """
    db_timelines = await timeline_service.get_all_timelines(db)
    logger.info(f"Listing {len(db_timelines)} timelines")

    timeline_list = []

    for db_timeline in db_timelines:
        # Get all generation IDs for this timeline
        generation_ids = [str(g.id) for g in db_timeline.generations]

        # Count audio scripts for all generations of this timeline
        audio_script_count = 0
        if generation_ids:
            # Query audio scripts table to count scripts for these generations
            # The generation_ids column is a JSON array, so we need to check if any of our generation_ids are contained
            conditions = []
            params = {}

            for i, gen_id in enumerate(generation_ids):
                param_name = f"gen_id_{i}"
                conditions.append(f"generation_ids LIKE '%{gen_id}%'")
                params[param_name] = gen_id

            where_clause = " OR ".join(conditions)
            query = f"SELECT COUNT(*) FROM audio_scripts WHERE {where_clause}"

            result = await db.execute(text(query), params)
            audio_script_count = result.scalar() or 0

        timeline_list.append(
            TimelineListItem(
                id=db_timeline.id,
                parent_timeline_id=db_timeline.parent_timeline_id,
                branch_point_year=db_timeline.branch_point_year,
                root_deviation_date=db_timeline.root_deviation_date,
                root_deviation_description=db_timeline.root_deviation_description,
                scenario_type=db_timeline.scenario_type,
                timeline_name=db_timeline.timeline_name,
                total_years_simulated=max((g.end_year for g in db_timeline.generations), default=0),
                generation_count=len(db_timeline.generations),
                audio_script_count=audio_script_count,
                created_at=db_timeline.created_at
            )
        )

    return timeline_list


@router.get(
    "/timeline/{timeline_id}",
    response_model=Timeline,
)
async def get_timeline(
    timeline_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific timeline by ID.

    Args:
        timeline_id: UUID of the timeline to retrieve

    Returns:
        Timeline: Complete timeline with all sections

    Raises:
        HTTPException: 404 if timeline not found
    """
    logger.info(f"Retrieving timeline: {timeline_id}")

    db_timeline = await timeline_service.get_timeline_by_id(db, timeline_id)

    if db_timeline is None:
        logger.warning(
            f"Timeline not found: {timeline_id}",
            extra={"timeline_id": str(timeline_id)}
        )
        raise TimelineNotFoundError(str(timeline_id))

    logger.debug(
        f"Retrieved timeline: {timeline_id}",
        extra={"timeline_id": str(timeline_id)}
    )
    return Timeline.model_validate(db_timeline)


@router.get(
    "/timelines/{timeline_id}/skeleton-snapshot",
)
async def get_timeline_skeleton_snapshot(
    timeline_id: UUID,
    generation_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the skeleton events snapshot used to generate a timeline or specific generation.

    Returns the immutable snapshot of skeleton events that were used when
    this timeline or generation was generated. This allows viewing the exact source material
    even if the original skeleton has been modified or deleted.

    Args:
        timeline_id: Timeline UUID
        generation_id: Optional generation UUID. If provided, returns the skeleton for that specific generation.
                       If not provided, returns the timeline-level skeleton (for initial generations).

    Returns:
        dict: Snapshot data with skeleton events and metadata

    Raises:
        HTTPException: 404 if timeline/generation not found or was not generated from skeleton
    """
    if generation_id:
        # Get skeleton snapshot from specific generation
        logger.info(f"Retrieving skeleton snapshot for generation {generation_id} in timeline {timeline_id}")

        result = await db.execute(
            select(GenerationDB).where(
                GenerationDB.id == str(generation_id),
                GenerationDB.timeline_id == str(timeline_id)
            )
        )
        generation = result.scalar_one_or_none()

        if not generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Generation {generation_id} not found in timeline {timeline_id}"
            )

        if not generation.source_skeleton_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This generation was not generated from a skeleton"
            )

        # Retrieve the actual skeleton using the FK
        skeleton = await skeleton_service.get_skeleton(db, UUID(generation.source_skeleton_id))

        if not skeleton:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source skeleton {generation.source_skeleton_id} not found"
            )

        # Convert skeleton events to snapshot format
        events_snapshot = [
            {
                "id": str(event.id),
                "event_date": event.event_date.isoformat(),
                "event_year": event.event_year,
                "location": event.location,
                "description": event.description,
                "event_order": event.event_order,
                "is_user_added": event.is_user_added,
                "is_user_modified": event.is_user_modified,
            }
            for event in skeleton.events
        ]

        return {
            "timeline_id": str(timeline_id),
            "generation_id": str(generation.id),
            "skeleton_id": str(skeleton.id),
            "events": events_snapshot,
            "snapshot_created_at": generation.created_at.isoformat() if generation.created_at else None,
        }
    else:
        # Fallback: Get skeleton from first generation (for backward compatibility)
        logger.info(f"Retrieving skeleton snapshot for timeline: {timeline_id}")

        # Get timeline's first generation
        result = await db.execute(
            select(GenerationDB).where(
                GenerationDB.timeline_id == str(timeline_id),
                GenerationDB.generation_order == 1
            )
        )
        first_generation = result.scalar_one_or_none()

        if not first_generation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timeline {timeline_id} has no generations"
            )

        if not first_generation.source_skeleton_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This timeline was not generated from a skeleton"
            )

        # Retrieve the actual skeleton using the FK
        skeleton = await skeleton_service.get_skeleton(db, UUID(first_generation.source_skeleton_id))

        if not skeleton:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source skeleton {first_generation.source_skeleton_id} not found"
            )

        # Convert skeleton events to snapshot format
        events_snapshot = [
            {
                "id": str(event.id),
                "event_date": event.event_date.isoformat(),
                "event_year": event.event_year,
                "location": event.location,
                "description": event.description,
                "event_order": event.event_order,
                "is_user_added": event.is_user_added,
                "is_user_modified": event.is_user_modified,
            }
            for event in skeleton.events
        ]

        return {
            "timeline_id": str(timeline_id),
            "generation_id": str(first_generation.id),
            "skeleton_id": str(skeleton.id),
            "events": events_snapshot,
            "snapshot_created_at": first_generation.created_at.isoformat() if first_generation.created_at else None,
        }


# ============================================================================
# Timeline Deletion
# ============================================================================


@router.delete(
    "/timeline/{timeline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_timeline(
    timeline_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific timeline.

    Args:
        timeline_id: UUID of the timeline to delete

    Raises:
        HTTPException: 404 if timeline not found
    """
    logger.info(f"Deleting timeline: {timeline_id}")

    deleted = await timeline_service.delete_timeline(db, timeline_id)

    if not deleted:
        logger.warning(
            f"Timeline not found for deletion: {timeline_id}",
            extra={"timeline_id": str(timeline_id)}
        )
        raise TimelineNotFoundError(str(timeline_id))

    logger.info(
        f"Successfully deleted timeline: {timeline_id}",
        extra={"timeline_id": str(timeline_id)}
    )


@router.delete(
    "/timeline/{timeline_id}/generation/{generation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_generation(
    timeline_id: UUID,
    generation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific generation from a timeline.

    Args:
        timeline_id: UUID of the timeline containing the generation
        generation_id: UUID of the generation to delete

    Raises:
        HTTPException: 404 if timeline or generation not found
        HTTPException: 400 if trying to delete the last generation
    """
    logger.info(f"Deleting generation {generation_id} from timeline {timeline_id}")

    # Check if timeline exists and has more than one generation
    db_timeline = await timeline_service.get_timeline_by_id(db, timeline_id)

    if not db_timeline:
        logger.warning(
            f"Timeline not found: {timeline_id}",
            extra={"timeline_id": str(timeline_id)}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeline {timeline_id} not found"
        )

    if len(db_timeline.generations) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last generation of a timeline"
        )

    deleted = await timeline_service.delete_generation(db, generation_id, timeline_id)

    if not deleted:
        logger.warning(
            f"Generation not found for deletion: {generation_id} in timeline {timeline_id}",
            extra={"timeline_id": str(timeline_id), "generation_id": str(generation_id)}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation {generation_id} not found in timeline {timeline_id}"
        )

    logger.info(
        f"Successfully deleted generation: {generation_id} from timeline: {timeline_id}",
        extra={"timeline_id": str(timeline_id), "generation_id": str(generation_id)}
    )


# ============================================================================
# Timeline Extension
# ============================================================================


@router.post(
    "/extend-timeline",
    response_model=Timeline,
    status_code=status.HTTP_200_OK,
)
async def extend_timeline_endpoint(
    request: TimelineExtensionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Extend an existing timeline by additional years.

    This endpoint takes an existing timeline and extends it by the specified
    number of additional years, using the established timeline as context.

    Args:
        request: Extension parameters including timeline ID and additional years

    Returns:
        Timeline: Updated timeline with extended simulation period

    Raises:
        HTTPException: 404 if timeline not found, 500 if extension fails
    """
    logger.info(
        f"Received timeline extension request: {request.timeline_id} "
        f"(+{request.additional_years} years)"
    )

    try:
        # Get existing timeline
        db_timeline = await timeline_service.get_timeline_by_id(db, request.timeline_id)
        if not db_timeline:
            logger.warning(
                f"Timeline not found for extension: {request.timeline_id}",
                extra={"timeline_id": str(request.timeline_id)}
            )
            raise TimelineNotFoundError(str(request.timeline_id))

        # Convert to Pydantic model
        original_timeline = Timeline.model_validate(db_timeline)

        # Publish context retrieval started
        await generation_progress.publish(request.progress_token, {
            "step": "context_retrieval", "status": "started", "label": "Retrieving historical context"
        })

        # Get context from previous generations in this timeline using RAG
        history_service = get_history_service()
        original_end_year = (
            original_timeline.root_deviation_date.year +
            original_timeline.total_years_simulated
        )
        extension_end_year = original_end_year + request.additional_years

        # Get context from previous generations (NOT ground truth)
        historical_context = ""
        try:
            # Use extension-specific RAG to retrieve from previous generations
            historical_context, debug_info = await history_service.get_context_for_extension_rag(
                timeline_id=str(request.timeline_id),
                extension_start_year=original_end_year,
                deviation_description=original_timeline.root_deviation_description,
                scenario_type=original_timeline.scenario_type,
                use_rag=request.use_rag,
                db=db
            )

            if debug_info and debug_info.get("final_chunks", 0) > 0:
                logger.info(
                    f"Extension RAG retrieval: {debug_info['final_chunks']} chunks "
                    f"from previous generations, ~{debug_info.get('total_tokens', 0):.0f} tokens"
                )
        except Exception as e:
            logger.warning(
                f"Could not retrieve previous generation context for extension: {e}"
            )

        # Generate timeline extension using orchestrator
        logger.info(
            "Extending timeline with orchestrator...",
            extra={
                "timeline_id": str(request.timeline_id),
                "original_period": f"{original_timeline.root_deviation_date}-{original_end_year}",
                "extension_period": f"{original_end_year}-{extension_end_year}",
                "additional_years": request.additional_years,
                "narrative_mode": request.narrative_mode.value
            }
        )
        await generation_progress.publish(request.progress_token, {
            "step": "context_retrieval", "status": "completed", "label": "Historical context retrieved"
        })

        workflow_result = await execute_timeline_extension(
            request,
            original_timeline,
            historical_context,
            db_session=db,
            progress_token=request.progress_token,
        )

        # Extract results
        structured_report = workflow_result["structured_report"]
        narrative_prose = workflow_result["narrative_prose"]
        timeline_name = workflow_result.get("timeline_name", "Alternate Timeline")  # Get timeline name from workflow
        workflow_metadata = workflow_result["workflow_metadata"]
        historian_provider = workflow_result.get("historian_provider")
        historian_model_name = workflow_result.get("historian_model_name")
        storyteller_provider = workflow_result.get("storyteller_provider")
        storyteller_model_name = workflow_result.get("storyteller_model_name")

        logger.info(
            f"Extension workflow completed in {workflow_metadata.get('duration_seconds', 0):.2f}s",
            extra=workflow_metadata
        )

        # Create TimelineOutput for database storage
        extension_output = TimelineOutput(
            executive_summary=structured_report.executive_summary,
            political_changes=structured_report.political_changes,
            conflicts_and_wars=structured_report.conflicts_and_wars,
            economic_impacts=structured_report.economic_impacts,
            social_developments=structured_report.social_developments,
            technological_shifts=structured_report.technological_shifts,
            key_figures=structured_report.key_figures,
            long_term_implications=structured_report.long_term_implications,
            narrative_prose=narrative_prose
        )

        await generation_progress.publish(request.progress_token, {
            "step": "saving", "status": "started", "label": "Saving to library"
        })
        # Add new generation to timeline in database with model tracking information
        new_generation = await timeline_service.extend_timeline_with_new_generation(
            db,
            request.timeline_id,
            extension_output,
            request.additional_years,
            historian_provider=historian_provider,
            historian_model_name=historian_model_name,
            storyteller_provider=storyteller_provider,
            storyteller_model_name=storyteller_model_name
        )

        # Index extension content in background for future RAG retrieval
        if new_generation:
            try:
                from app.services.vector_store_service import get_vector_store_service
                import asyncio

                vector_service = get_vector_store_service()
                if vector_service.enabled:
                    # Extract report sections from structured report
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
                            year_start=original_end_year,
                            year_end=extension_end_year,
                            db=db
                        )
                    )
                    logger.info(f"Started background indexing for extension generation {new_generation.id}")
            except Exception as e:
                # Don't fail extension if indexing fails
                logger.warning(f"Failed to start background indexing for extension: {e}", exc_info=True)

        if not new_generation:
            raise AIGenerationError(
                "Failed to create extension generation in database",
                details={"timeline_id": str(request.timeline_id)}
            )

        # Get updated timeline with all generations for response
        updated_db_timeline = await timeline_service.get_timeline_by_id(db, request.timeline_id)
        extended_timeline = Timeline.model_validate(updated_db_timeline)

        narrative_length = len(extension_output.narrative_prose) if extension_output.narrative_prose else 0
        logger.info(
            f"Successfully extended timeline {request.timeline_id} by {request.additional_years} years",
            extra={
                "timeline_id": str(request.timeline_id),
                "additional_years": request.additional_years,
                "new_total_years": extended_timeline.total_years_simulated,
                "extension_narrative_length": narrative_length,
                "has_extension_narrative": extension_output.narrative_prose is not None
            }
        )
        await generation_progress.publish(request.progress_token, {
            "step": "done", "timeline_id": str(request.timeline_id)
        })
        return extended_timeline

    except (TimelineNotFoundError, AIGenerationError, ValidationError):
        # Re-raise custom exceptions (handled by exception handlers)
        raise
    except ValueError as e:
        # Pydantic validation errors
        raise ValidationError(
            str(e),
            details={"field_validation": True}
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during timeline extension: {e}",
            exc_info=True,
            extra={
                "timeline_id": str(request.timeline_id),
                "additional_years": request.additional_years
            }
        )
        raise AIGenerationError(
            "Timeline extension failed due to an unexpected error",
            details={
                "error": str(e),
                "timeline_id": str(request.timeline_id)
            }
        )
