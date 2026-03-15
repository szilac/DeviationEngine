"""
Translation API endpoints.

This module handles:
- Generation report translation
- Narrative translation
- Translation usage statistics
- Translation configuration management (DeepL API)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
import logging

from app.database import get_db
from app.models import (
    TranslationRequest,
    TranslationResponse,
    NarrativeTranslationResponse,
    TranslationUsageResponse,
    TranslationConfigRequest,
    TranslationConfigResponse,
)
from app.db_models import GenerationDB, TranslationConfigDB
from app.exceptions import (
    GenerationNotFoundError,
    TranslationError,
    TranslationNotConfiguredError,
)

logger = logging.getLogger(__name__)

# Create router with /api prefix
router = APIRouter(prefix="/api", tags=["translation"])


@router.post(
    "/generations/{generation_id}/translate",
    response_model=TranslationResponse,
    summary="Translate generation to target language",
    description="Translate all 8 sections of a generation to the specified language. Uses caching.",
)
async def translate_generation(
    generation_id: UUID,
    request: TranslationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Translate all sections of a generation.

    Args:
        generation_id: UUID of the generation to translate
        request: Translation request with target language
        db: Database session

    Returns:
        TranslationResponse with translations for all 8 sections

    Raises:
        HTTPException: If generation not found or translation fails
    """
    from app.services.translation_service import get_translation_service
    from datetime import datetime, timezone

    try:
        # Get translation service
        translation_service = await get_translation_service(db)

        # Get generation to check if translation exists (for cached flag)
        result = await db.execute(
            select(GenerationDB).where(GenerationDB.id == str(generation_id))
        )
        generation = result.scalar_one_or_none()

        if not generation:
            raise GenerationNotFoundError(str(generation_id))

        # Check if already cached
        cached = False
        if generation.report_translations:
            cached = request.target_language in generation.report_translations

        # Translate (will use cache if available)
        from app.services.translation_service import TranslationMethod

        method = (
            TranslationMethod.LLM
            if request.method == "llm"
            else TranslationMethod.DEEPL
        )

        translations = await translation_service.translate_generation(
            db=db,
            generation_id=generation_id,
            target_language=request.target_language,
            method=method,
        )

        # Calculate character count
        char_count = sum(len(text) for text in translations.values())

        return TranslationResponse(
            generation_id=generation_id,
            timeline_id=UUID(generation.timeline_id),
            generation_order=generation.generation_order,
            target_language=request.target_language,
            translations=translations,
            character_count=char_count,
            cached=cached,
            translated_at=datetime.now(timezone.utc),
        )

    except GenerationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except TranslationNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e.message)
        )
    except TranslationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Unexpected error translating generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}",
        )


@router.post(
    "/generations/{generation_id}/narrative/translate",
    response_model=NarrativeTranslationResponse,
    summary="Translate generation narrative to target language",
    description="Translate the narrative prose of a generation to the specified language.",
)
async def translate_narrative(
    generation_id: UUID,
    request: TranslationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Translate narrative prose of a generation.

    Args:
        generation_id: UUID of the generation
        request: Translation request with target language
        db: Database session

    Returns:
        NarrativeTranslationResponse with translated narrative

    Raises:
        HTTPException: If generation not found, has no narrative, or translation fails
    """
    from app.services.translation_service import get_translation_service
    from datetime import datetime, timezone

    try:
        # Get translation service
        translation_service = await get_translation_service(db)

        # Get generation to check cached status
        result = await db.execute(
            select(GenerationDB).where(GenerationDB.id == str(generation_id))
        )
        generation = result.scalar_one_or_none()

        if not generation:
            raise GenerationNotFoundError(str(generation_id))

        # Check if already cached
        cached = False
        if generation.narrative_translations:
            cached = request.target_language in generation.narrative_translations

        # Translate narrative
        from app.services.translation_service import TranslationMethod

        method = (
            TranslationMethod.LLM
            if request.method == "llm"
            else TranslationMethod.DEEPL
        )

        narrative_text = await translation_service.translate_narrative(
            db=db,
            generation_id=generation_id,
            target_language=request.target_language,
            method=method,
        )

        return NarrativeTranslationResponse(
            generation_id=generation_id,
            timeline_id=UUID(generation.timeline_id),
            generation_order=generation.generation_order,
            target_language=request.target_language,
            narrative_prose=narrative_text,
            character_count=len(narrative_text),
            cached=cached,
            translated_at=datetime.now(timezone.utc),
        )

    except GenerationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except TranslationNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e.message)
        )
    except TranslationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Unexpected error translating narrative: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}",
        )


@router.get(
    "/translation/usage",
    response_model=TranslationUsageResponse,
    summary="Get translation usage statistics",
    description="Get character usage statistics for a specific month",
)
async def get_translation_usage(
    month: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    """
    Get translation usage statistics.

    Args:
        month: Optional month in YYYY-MM format (defaults to current month)
        db: Database session

    Returns:
        TranslationUsageResponse with usage statistics
    """
    from app.services.translation_service import get_translation_service

    try:
        translation_service = await get_translation_service(db)
        usage_stats = await translation_service.get_usage_stats(db, month)

        return TranslationUsageResponse(**usage_stats)

    except Exception as e:
        logger.error(f"Error fetching translation usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch usage statistics: {str(e)}",
        )


@router.get(
    "/translation/config",
    response_model=TranslationConfigResponse,
    summary="Get translation configuration",
    description="Get current translation service configuration",
)
async def get_translation_config(db: AsyncSession = Depends(get_db)):
    """
    Get translation configuration.

    Args:
        db: Database session

    Returns:
        TranslationConfigResponse with configuration details
    """
    try:
        result = await db.execute(
            select(TranslationConfigDB).where(TranslationConfigDB.id == 1)
        )
        config = result.scalar_one_or_none()

        if not config:
            # Return default empty config
            from datetime import datetime, timezone

            return TranslationConfigResponse(
                enabled=False,
                api_tier="free",
                api_key_set=False,
                updated_at=datetime.now(timezone.utc),
            )

        return TranslationConfigResponse(
            enabled=bool(config.enabled),
            api_tier=config.api_tier,
            api_key_set=bool(config.api_key and config.api_key != "not_configured"),
            updated_at=config.updated_at,
        )

    except Exception as e:
        logger.error(f"Error fetching translation config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch configuration: {str(e)}",
        )


@router.put(
    "/translation/config",
    response_model=TranslationConfigResponse,
    summary="Update translation configuration",
    description="Update DeepL API configuration",
)
async def update_translation_config(
    request: TranslationConfigRequest, db: AsyncSession = Depends(get_db)
):
    """
    Update translation configuration.

    Args:
        request: Translation configuration update request
        db: Database session

    Returns:
        TranslationConfigResponse with updated configuration
    """
    from datetime import datetime, timezone
    from sqlalchemy import update as sql_update

    try:
        # Check if config exists
        result = await db.execute(
            select(TranslationConfigDB).where(TranslationConfigDB.id == 1)
        )
        existing_config = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing_config:
            # Update existing config
            await db.execute(
                sql_update(TranslationConfigDB)
                .where(TranslationConfigDB.id == 1)
                .values(
                    api_key=request.api_key,
                    api_tier=request.api_tier,
                    enabled=request.enabled,
                    updated_at=now,
                )
            )
        else:
            # Create new config
            new_config = TranslationConfigDB(
                id=1,
                api_key=request.api_key,
                api_tier=request.api_tier,
                enabled=request.enabled,
                updated_at=now,
            )
            db.add(new_config)

        await db.commit()

        # Return updated config
        result = await db.execute(
            select(TranslationConfigDB).where(TranslationConfigDB.id == 1)
        )
        config = result.scalar_one()

        return TranslationConfigResponse(
            enabled=bool(config.enabled),
            api_tier=config.api_tier,
            api_key_set=bool(config.api_key and config.api_key != "not_configured"),
            updated_at=config.updated_at,
        )

    except Exception as e:
        logger.error(f"Error updating translation config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}",
        )
