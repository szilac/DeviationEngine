"""
Image Generation API endpoints.

This module handles:
- Image prompt skeleton generation and management
- Image prompt editing and approval workflow
- Image generation from approved prompts
- Timeline image retrieval and deletion
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import (
    ImagePromptSkeletonCreate,
    ImagePromptSkeletonResponse,
    ImagePromptUpdate,
    TimelineImageResponse,
    GenerateImagesRequest,
)
from app.db_models import GenerationDB
from app.services import timeline_service, media_service
from app.agents.workflows import execute_image_prompt_generation
from app.exceptions import AIGenerationError

logger = logging.getLogger(__name__)

# Create router with /api prefix
router = APIRouter(prefix="/api", tags=["image-generation"])


@router.post(
    "/image-prompts/generate",
    response_model=ImagePromptSkeletonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_image_prompts_endpoint(
    request: ImagePromptSkeletonCreate, db: AsyncSession = Depends(get_db)
):
    """
    Generate image prompt skeleton for a timeline.

    This endpoint creates an editable skeleton of image prompts
    that can be reviewed and modified before generating actual images.

    Args:
        request: Image prompt generation parameters (timeline_id, num_images, focus_areas)

    Returns:
        ImagePromptSkeletonResponse: Generated skeleton with image prompts

    Raises:
        HTTPException: 404 if timeline not found, 500 if generation fails
    """
    logger.info(
        f"Received image prompt generation request for timeline {request.timeline_id}: "
        f"{request.num_images} images"
    )

    try:
        # Retrieve timeline from database
        db_timeline = await timeline_service.get_timeline_by_id(db, request.timeline_id)

        if not db_timeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timeline with ID {request.timeline_id} not found",
            )

        # Get report if specified
        if request.generation_id:
            result = await db.execute(
                select(GenerationDB).where(
                    GenerationDB.id == str(request.generation_id),
                    GenerationDB.timeline_id == str(request.timeline_id),
                )
            )
            db_generation = result.scalar_one_or_none()

            if not db_generation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generation {request.generation_id} not found in timeline {request.timeline_id}",
                )

            generation_data = {
                "executive_summary": db_generation.executive_summary,
                "political_changes": db_generation.political_changes,
                "conflicts_and_wars": db_generation.conflicts_and_wars,
                "economic_impacts": db_generation.economic_impacts,
                "social_developments": db_generation.social_developments,
                "technological_shifts": db_generation.technological_shifts,
                "key_figures": db_generation.key_figures,
                "long_term_implications": db_generation.long_term_implications,
            }
            narrative_prose = db_generation.narrative_prose
            # For a specific generation, simulation_years should be from deviation to end of THIS generation
            deviation_year = int(db_timeline.root_deviation_date.split("-")[0])
            simulation_years = db_generation.end_year - deviation_year
            generation_id_for_data = db_generation.id
            generation_start_year = db_generation.start_year - deviation_year
        else:
            # Use timeline's first generation as default
            if not db_timeline.generations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Timeline {request.timeline_id} has no generations",
                )

            first_generation = db_timeline.generations[0]
            generation_data = {
                "executive_summary": first_generation.executive_summary,
                "political_changes": first_generation.political_changes,
                "conflicts_and_wars": first_generation.conflicts_and_wars,
                "economic_impacts": first_generation.economic_impacts,
                "social_developments": first_generation.social_developments,
                "technological_shifts": first_generation.technological_shifts,
                "key_figures": first_generation.key_figures,
                "long_term_implications": first_generation.long_term_implications,
            }
            narrative_prose = first_generation.narrative_prose
            # For first generation, simulation_years should be from deviation to end of first generation
            deviation_year = int(db_timeline.root_deviation_date.split("-")[0])
            simulation_years = first_generation.end_year - deviation_year
            generation_id_for_data = first_generation.id
            generation_start_year = first_generation.start_year - deviation_year

        # Prepare timeline data for workflow
        timeline_data = {
            "generation": generation_data,
            "narrative": narrative_prose,
            "deviation_date": db_timeline.root_deviation_date,
            "deviation_description": db_timeline.root_deviation_description,
            "timeline_id": request.timeline_id,
            "generation_id": generation_id_for_data,
            "simulation_years": simulation_years,
            "generation_start_year": generation_start_year,
        }

        # Execute image prompt generation workflow
        result = await execute_image_prompt_generation(
            image_request=request, timeline_data=timeline_data, db_session=db
        )

        illustrator_output = result["illustrator_output"]
        illustrator_provider = result.get("illustrator_provider")
        illustrator_model_name = result.get("illustrator_model_name")

        # Convert agent output to list of dicts with prompt_order
        prompts_with_order = []
        for idx, prompt in enumerate(illustrator_output.prompts):
            prompts_with_order.append(
                {
                    "prompt_text": prompt.prompt_text,
                    "event_year": prompt.event_year,
                    "title": prompt.title,
                    "description": prompt.description,
                    "style_notes": prompt.style_notes,
                    "prompt_order": idx + 1,
                    # "is_user_modified": False
                }
            )

        # Save skeleton to database
        skeleton = await media_service.create_image_prompt_skeleton(
            db=db,
            timeline_id=request.timeline_id,
            generation_id=request.generation_id,
            num_images=request.num_images,
            focus_areas=request.focus_areas,
            prompts=prompts_with_order,
            model_provider=illustrator_provider,
            model_name=illustrator_model_name,
        )

        await db.commit()

        logger.info(
            f"Image prompt skeleton generated successfully: {skeleton['id']} "
            f"for timeline {request.timeline_id}"
        )
        return skeleton

    except AIGenerationError as e:
        logger.error(f"AI generation error: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image prompt generation: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during image prompt generation",
        )


@router.get("/image-prompts/{skeleton_id}", response_model=ImagePromptSkeletonResponse)
async def get_image_prompt_skeleton_endpoint(skeleton_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get an image prompt skeleton by ID.

    Args:
        skeleton_id: Skeleton UUID

    Returns:
        ImagePromptSkeletonResponse: Skeleton with prompts

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(f"Retrieving image prompt skeleton: {skeleton_id}")

    skeleton = await media_service.get_image_prompt_skeleton(db, skeleton_id)

    if not skeleton:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image prompt skeleton with ID {skeleton_id} not found",
        )

    return skeleton


@router.get(
    "/timelines/{timeline_id}/image-prompts", response_model=List[ImagePromptSkeletonResponse]
)
async def get_timeline_image_prompts_endpoint(
    timeline_id: UUID, db: AsyncSession = Depends(get_db)
):
    """
    Get all image prompt skeletons for a timeline.

    Args:
        timeline_id: Timeline UUID

    Returns:
        List[ImagePromptSkeletonResponse]: List of skeletons for the timeline

    Raises:
        HTTPException: 404 if timeline not found
    """
    logger.info(f"Retrieving image prompt skeletons for timeline: {timeline_id}")

    # Verify timeline exists
    db_timeline = await timeline_service.get_timeline_by_id(db, timeline_id)
    if not db_timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeline with ID {timeline_id} not found",
        )

    skeletons = await media_service.get_image_prompt_skeletons_by_timeline(db, timeline_id)
    return skeletons


@router.put("/image-prompts/{skeleton_id}", response_model=ImagePromptSkeletonResponse)
async def update_image_prompts_endpoint(
    skeleton_id: UUID,
    prompts_update: List[ImagePromptUpdate],
    deleted_prompt_indices: List[int] = [],
    db: AsyncSession = Depends(get_db),
):
    """
    Update image prompts (create, update, delete).

    Allows user to edit the image prompts before generating actual images.

    Args:
        skeleton_id: Skeleton UUID
        prompts_update: List of prompts to create or update
        deleted_prompt_indices: List of prompt indices to delete

    Returns:
        ImagePromptSkeletonResponse: Updated skeleton with prompts

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(
        f"Updating image prompt skeleton {skeleton_id}: {len(prompts_update)} prompts, "
        f"{len(deleted_prompt_indices)} deletions"
    )

    skeleton = await media_service.update_image_prompts(
        db=db,
        skeleton_id=skeleton_id,
        prompts_update=prompts_update,
        deleted_prompt_indices=deleted_prompt_indices,
    )

    if not skeleton:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image prompt skeleton with ID {skeleton_id} not found",
        )

    await db.commit()
    logger.info(f"Image prompt skeleton {skeleton_id} updated successfully")

    return skeleton


@router.post("/image-prompts/{skeleton_id}/approve", response_model=ImagePromptSkeletonResponse)
async def approve_image_prompt_skeleton_endpoint(
    skeleton_id: UUID, db: AsyncSession = Depends(get_db)
):
    """
    Mark image prompt skeleton as approved by user.

    Args:
        skeleton_id: Skeleton UUID

    Returns:
        ImagePromptSkeletonResponse: Approved skeleton

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(f"Approving image prompt skeleton: {skeleton_id}")

    skeleton = await media_service.approve_image_prompt_skeleton(db, skeleton_id)

    if not skeleton:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image prompt skeleton with ID {skeleton_id} not found",
        )

    await db.commit()
    logger.info(f"Image prompt skeleton {skeleton_id} approved")

    return skeleton


@router.post(
    "/images/generate",
    response_model=List[TimelineImageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_images_endpoint(request: GenerateImagesRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate actual images from approved image prompt skeleton.

    This endpoint takes a user-approved skeleton and generates images
    using pollinations.ai (or other image generation services).

    Args:
        request: Contains skeleton_id for approved prompts

    Returns:
        List[TimelineImageResponse]: Generated timeline images

    Raises:
        HTTPException: 404 if skeleton not found, 400 if not approved, 500 if generation fails
    """
    logger.info(f"Generating images from skeleton: {request.skeleton_id}")

    try:
        # Retrieve skeleton
        skeleton = await media_service.get_image_prompt_skeleton(db, request.skeleton_id)

        if not skeleton:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image prompt skeleton with ID {request.skeleton_id} not found",
            )

        # Check if skeleton is approved
        if skeleton["status"] != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image prompt skeleton must be approved before generating images. Current status: {skeleton['status']}",
            )

        # Mark skeleton as generating
        await media_service.mark_skeleton_generating(db, request.skeleton_id)
        await db.commit()

        # Generate images using pollinations.ai
        generated_images = []

        # Get Pollinations API key from environment (optional)
        import os

        pollinations_api_key = os.getenv("POLLINATIONS_API_KEY")

        for prompt in skeleton["prompts"]:
            try:
                # Create gen.pollinations.ai URL with parameters
                # Format: https://gen.pollinations.ai/image/{prompt}?key=...&width=...&height=...&model=...
                from urllib.parse import quote

                encoded_prompt = quote(prompt["prompt_text"])

                # Build URL with query parameters
                image_url = f"https://gen.pollinations.ai/image/{encoded_prompt}"

                params = []
                if pollinations_api_key:
                    params.append(f"key={pollinations_api_key}")
                params.append("width=1024")
                params.append("height=1024")
                params.append("model=imagen-4")

                image_url += "?" + "&".join(params)

                logger.debug(f"Generated image URL: {image_url}")

                # Create media record (image) - uses new redesigned schema
                image_record = await media_service.create_media(
                    db=db,
                    generation_id=skeleton["generation_id"],
                    media_type="image",
                    media_url=image_url,
                    media_order=prompt["prompt_order"],
                    prompt_text=prompt["prompt_text"],
                    event_year=prompt.get("event_year"),
                    title=prompt.get("title"),
                    description=prompt.get("description"),
                    is_user_added=False,
                    model_provider=skeleton.get("model_provider"),
                    model_name=skeleton.get("model_name"),
                )

                generated_images.append(image_record)

                prompt_title = prompt.get("title", "unknown")
                logger.debug(f"Generated image for prompt '{prompt_title}': {image_url}")

            except Exception as e:
                prompt_title = prompt.get("title", "unknown")
                logger.error(
                    f"Error generating image for prompt '{prompt_title}': {e}", exc_info=True
                )
                # Continue with other images even if one fails
                continue

        # Mark skeleton as completed
        await media_service.mark_skeleton_completed(db, request.skeleton_id)
        await db.commit()

        logger.info(
            f"Successfully generated {len(generated_images)} images from skeleton {request.skeleton_id}"
        )

        return generated_images

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating images: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during image generation",
        )


@router.get("/timelines/{timeline_id}/images", response_model=List[TimelineImageResponse])
async def get_timeline_images_endpoint(
    timeline_id: UUID, generation_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)
):
    """
    Get all images for a timeline, optionally filtered by generation.

    Args:
        timeline_id: Timeline UUID
        generation_id: Optional generation UUID to filter by

    Returns:
        List[TimelineImageResponse]: List of timeline images

    Raises:
        HTTPException: 404 if timeline not found
    """
    logger.info(
        f"Retrieving images for timeline: {timeline_id}"
        f"{f' (generation: {generation_id})' if generation_id else ''}"
    )

    # Verify timeline exists
    db_timeline = await timeline_service.get_timeline_by_id(db, timeline_id)
    if not db_timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeline with ID {timeline_id} not found",
        )

    # Get images - filter by generation if specified, otherwise get all for timeline
    if generation_id:
        images = await media_service.get_media_by_generation(db, generation_id)
    else:
        images = await media_service.get_media_by_timeline(db, timeline_id)

    return images


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timeline_image_endpoint(image_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a timeline image.

    Args:
        image_id: Image UUID

    Raises:
        HTTPException: 404 if image not found
    """
    logger.info(f"Deleting media (image): {image_id}")

    deleted = await media_service.delete_media(db, image_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Media with ID {image_id} not found"
        )

    await db.commit()
    logger.info(f"Media (image) {image_id} deleted")


@router.delete("/image-prompts/{skeleton_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_prompt_skeleton_endpoint(
    skeleton_id: UUID, db: AsyncSession = Depends(get_db)
):
    """
    Delete an image prompt skeleton.

    Args:
        skeleton_id: Skeleton UUID

    Raises:
        HTTPException: 404 if skeleton not found
    """
    logger.info(f"Deleting image prompt skeleton: {skeleton_id}")

    deleted = await media_service.delete_image_prompt_skeleton(db, skeleton_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image prompt skeleton with ID {skeleton_id} not found",
        )

    await db.commit()
    logger.info(f"Image prompt skeleton {skeleton_id} deleted")
