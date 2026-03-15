"""
Audio Router - Audio script generation, presets, and TTS operations.

This module handles:
- Script preset management (CRUD)
- Audio script generation from timeline content
- Script translation
- TTS audio generation
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sql_delete

from app.database import get_db
from app.models import (
    ScriptPreset,
    AudioScript,
    ScriptTranslation,
    AudioFile,
    ScriptGenerationRequest,
    ScriptUpdateRequest,
    ScriptTranslationRequest,
    AudioGenerationRequest,
    PresetCreateRequest,
    PresetUpdateRequest,
    ScriptStatus,
    ScriptType,
    LANGUAGES,
)
from app.db_models import GenerationDB, ScriptTranslationDB
from app.services import preset_service, script_service, audio_service
from app.exceptions import (
    AIGenerationError,
    ValidationError,
    NotFoundError,
    TranslationError,
    TranslationNotConfiguredError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["audio-scripts"])


# ============================================================================
# Preset Management Endpoints
# ============================================================================


@router.get("/audio/presets", response_model=List[ScriptPreset])
async def list_presets_endpoint(
    script_type: Optional[ScriptType] = None, db: AsyncSession = Depends(get_db)
):
    """
    List all script presets (system + custom).

    Args:
        script_type: Optional filter by script type
        db: Database session

    Returns:
        List[ScriptPreset]: List of all active presets
    """
    logger.info(f"Listing presets" + (f" (type: {script_type})" if script_type else ""))

    if script_type:
        presets = await preset_service.get_presets_by_type(db, script_type.value)
    else:
        presets = await preset_service.get_all_presets(db)

    return presets


@router.get("/audio/presets/{preset_id}", response_model=ScriptPreset)
async def get_preset_endpoint(preset_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get specific preset by ID.

    Args:
        preset_id: Preset UUID
        db: Database session

    Returns:
        ScriptPreset: Preset details

    Raises:
        HTTPException: 404 if preset not found
    """
    logger.info(f"Getting preset: {preset_id}")

    try:
        preset = await preset_service.get_preset_by_id(db, preset_id)
        return preset
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Preset not found: {preset_id}"
        )


@router.post(
    "/audio/presets",
    response_model=ScriptPreset,
    status_code=status.HTTP_201_CREATED,
)
async def create_preset_endpoint(
    request: PresetCreateRequest, db: AsyncSession = Depends(get_db)
):
    """
    Create custom preset.

    Args:
        request: Preset creation request
        db: Database session

    Returns:
        ScriptPreset: Created preset

    Raises:
        HTTPException: 400 if validation fails
    """
    logger.info(f"Creating custom preset: {request.name}")

    try:
        preset = await preset_service.create_preset(db, request)
        await db.commit()
        logger.info(f"Preset created: {preset.id}")
        return preset
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Error creating preset: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create preset",
        )


@router.put("/audio/presets/{preset_id}", response_model=ScriptPreset)
async def update_preset_endpoint(
    preset_id: str,
    request: PresetUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update custom preset (system presets cannot be modified).

    Args:
        preset_id: Preset UUID
        request: Preset update request
        db: Database session

    Returns:
        ScriptPreset: Updated preset

    Raises:
        HTTPException: 404 if not found, 400 if system preset
    """
    logger.info(f"Updating preset: {preset_id}")

    try:
        preset = await preset_service.update_preset(db, preset_id, request)
        await db.commit()
        logger.info(f"Preset updated: {preset_id}")
        return preset
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Error updating preset: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Preset not found: {preset_id}"
        )


@router.delete("/audio/presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset_endpoint(preset_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete custom preset (system presets cannot be deleted).

    Args:
        preset_id: Preset UUID
        db: Database session

    Raises:
        HTTPException: 404 if not found, 400 if system preset
    """
    logger.info(f"Deleting preset: {preset_id}")

    try:
        await preset_service.delete_preset(db, preset_id)
        await db.commit()
        logger.info(f"Preset deleted: {preset_id}")
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting preset: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Preset not found: {preset_id}"
        )


# ============================================================================
# Script Management Endpoints
# ============================================================================


@router.post(
    "/audio/scripts/generate",
    response_model=AudioScript,
    status_code=status.HTTP_201_CREATED,
)
async def generate_script_endpoint(
    request: ScriptGenerationRequest, db: AsyncSession = Depends(get_db)
):
    """
    Generate audio script from generation content.

    Args:
        request: Script generation request
        db: Database session

    Returns:
        AudioScript: Generated script in draft status

    Raises:
        HTTPException: 400 if validation fails, 500 if generation fails
    """
    logger.info(
        f"Generating script: {len(request.generation_ids)} generations, "
        f"preset={request.preset_id}"
    )

    try:
        script = await script_service.generate_audio_script(db, request)
        await db.commit()
        logger.info(f"Script generated: {script.id}")
        return script
    except ValidationError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except AIGenerationError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
        )
    except Exception as e:
        logger.error(f"Error generating script: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate script",
        )


@router.get("/audio/scripts", response_model=List[AudioScript])
async def list_scripts_endpoint(
    status: Optional[ScriptStatus] = None,
    preset_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List audio scripts with optional filtering.

    Args:
        status: Optional filter by status
        preset_id: Optional filter by preset
        limit: Maximum results (default: 50)
        offset: Pagination offset (default: 0)
        db: Database session

    Returns:
        List[AudioScript]: List of scripts
    """
    logger.info(f"Listing scripts (status={status}, preset={preset_id}, limit={limit})")

    scripts = await script_service.list_scripts(db, status, preset_id, limit, offset)
    return scripts


@router.get("/audio/scripts/{script_id}", response_model=AudioScript)
async def get_script_endpoint(script_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get script by ID.

    Args:
        script_id: Script UUID
        db: Database session

    Returns:
        AudioScript: Script details

    Raises:
        HTTPException: 404 if script not found
    """
    logger.info(f"Getting script: {script_id}")

    try:
        script = await script_service.get_script_by_id(db, script_id)
        return script
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Script not found: {script_id}"
        )


@router.put("/audio/scripts/{script_id}", response_model=AudioScript)
async def update_script_endpoint(
    script_id: UUID,
    request: ScriptUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update script content (draft scripts only).

    Args:
        script_id: Script UUID
        request: Script update request
        db: Database session

    Returns:
        AudioScript: Updated script

    Raises:
        HTTPException: 404 if not found, 400 if not draft status
    """
    logger.info(f"Updating script: {script_id}")

    try:
        script = await script_service.update_script_content(db, script_id, request)
        await db.commit()
        logger.info(f"Script updated: {script_id}")
        return script
    except ValidationError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Error updating script: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Script not found: {script_id}"
        )


@router.post("/audio/scripts/{script_id}/approve", response_model=AudioScript)
async def approve_script_endpoint(script_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Approve script for audio generation.

    Args:
        script_id: Script UUID
        db: Database session

    Returns:
        AudioScript: Approved script

    Raises:
        HTTPException: 404 if not found, 400 if not draft status
    """
    logger.info(f"Approving script: {script_id}")

    try:
        script = await script_service.approve_script(db, script_id)
        await db.commit()
        logger.info(f"Script approved: {script_id}")
        return script
    except ValidationError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Error approving script: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Script not found: {script_id}"
        )


@router.delete("/audio/scripts/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script_endpoint(script_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete script and all associated audio files.

    Args:
        script_id: Script UUID
        db: Database session

    Raises:
        HTTPException: 404 if script not found
    """
    logger.info(f"Deleting script: {script_id}")

    try:
        await script_service.delete_script(db, script_id)
        await db.commit()
        logger.info(f"Script deleted: {script_id}")
    except Exception as e:
        logger.error(f"Error deleting script: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Script not found: {script_id}"
        )


# ============================================================================
# Script Translation Endpoints
# ============================================================================


@router.post(
    "/audio/scripts/{script_id}/translate",
    response_model=List[ScriptTranslation],
    status_code=status.HTTP_201_CREATED,
)
async def translate_script_endpoint(
    script_id: UUID,
    request: ScriptTranslationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Translate script to target languages using DeepL or LLM.

    Supports batch translation to multiple languages. Translations are cached
    in the database. If a translation already exists for a requested language,
    an error will be raised.

    Args:
        script_id: Script UUID
        request: Translation request with target_languages and method
        db: Database session

    Returns:
        List[ScriptTranslation]: Translated scripts with preserved markdown structure

    Raises:
        HTTPException: 404 if script not found, 400 if translation exists or not configured,
                      500 if translation fails
    """
    logger.info(
        f"Translating script {script_id} to {len(request.target_languages)} languages "
        f"using {request.method}"
    )

    language_map = {lang["code"]: lang["name"] for lang in LANGUAGES}
    translations = []

    try:
        for lang_code in request.target_languages:
            language_name = language_map.get(lang_code, lang_code.upper())

            translation = await script_service.translate_script(
                db=db,
                script_id=script_id,
                language_code=lang_code,
                language_name=language_name,
                method=request.method,
            )

            translations.append(translation)

        await db.commit()

        logger.info(
            f"Script translation completed: {script_id} -> "
            f"{len(translations)} languages using {request.method}"
        )

        return translations

    except NotFoundError as e:
        logger.warning(f"Script not found: {script_id}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TranslationNotConfiguredError as e:
        logger.warning(f"Translation service not configured: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TranslationError as e:
        logger.error(f"Translation failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error translating script: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to translate script",
        )


@router.get(
    "/audio/scripts/{script_id}/translations", response_model=List[ScriptTranslation]
)
async def list_script_translations_endpoint(
    script_id: UUID, db: AsyncSession = Depends(get_db)
):
    """
    List all translations for a specific script.

    Returns all languages that this script has been translated to,
    with the full translated content for each language.

    Args:
        script_id: Script UUID
        db: Database session

    Returns:
        List of ScriptTranslation models
    """
    logger.info(f"Listing translations for script {script_id}")

    try:
        translations = await script_service.list_translations_for_script(
            db=db, script_id=script_id
        )

        logger.info(f"Found {len(translations)} translations for script {script_id}")
        return translations

    except Exception as e:
        logger.error(f"Error listing translations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list translations",
        )


@router.delete(
    "/audio/scripts/{script_id}/translations/{language_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_script_translation_endpoint(
    script_id: UUID, language_code: str, db: AsyncSession = Depends(get_db)
):
    """Delete a script translation for a specific language."""
    result = await db.execute(
        sql_delete(ScriptTranslationDB).where(
            ScriptTranslationDB.script_id == str(script_id),
            ScriptTranslationDB.language_code == language_code,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Translation not found")

    logger.info(f"Deleted script translation: {script_id} -> {language_code}")
    return None


@router.put("/audio/translations/{translation_id}", response_model=ScriptTranslation)
async def update_translation_endpoint(
    translation_id: UUID,
    request: ScriptUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update the content of an existing script translation.

    Allows manual editing of translated script content. Marks the translation
    as human-modified.

    Args:
        translation_id: Translation UUID
        request: Update request with script_content
        db: Database session

    Returns:
        Updated ScriptTranslation model

    Raises:
        HTTPException: 404 if translation not found
    """
    logger.info(f"Updating translation {translation_id}")

    try:
        translation = await script_service.update_translation(
            db=db, translation_id=translation_id, translated_content=request.script_content
        )

        await db.commit()

        logger.info(f"Translation updated successfully: {translation_id}")
        return translation

    except NotFoundError as e:
        logger.warning(f"Translation not found: {translation_id}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating translation: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update translation",
        )


# ============================================================================
# Audio Generation Endpoints
# ============================================================================


@router.post(
    "/audio/generate",
    response_model=AudioFile,
    status_code=status.HTTP_201_CREATED,
    tags=["audio-generation"],
)
async def generate_audio_endpoint(
    script_id: UUID,
    request: AudioGenerationRequest,
    language_code: str = "en",
    db: AsyncSession = Depends(get_db),
):
    """
    Generate audio from approved script using Google TTS.

    Args:
        script_id: Script UUID
        request: Audio generation request
        language_code: Language code (default: 'en')
        db: Database session

    Returns:
        AudioFile: Generated audio file metadata

    Raises:
        HTTPException: 404 if script not found, 400 if not approved, 500 if generation fails
    """
    logger.info(f"Generating audio for script {script_id} (language: {language_code})")

    try:
        audio_file = await audio_service.generate_audio_from_script(
            db, script_id, request, language_code
        )
        await db.commit()
        logger.info(f"Audio generated: {audio_file.id}")
        return audio_file
    except ValidationError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except AIGenerationError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
        )
    except Exception as e:
        logger.error(f"Error generating audio: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate audio",
        )


@router.get(
    "/audio/scripts/{script_id}/audio",
    response_model=List[AudioFile],
    tags=["audio-generation"],
)
async def list_script_audio_endpoint(script_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    List all audio files for a script (all languages).

    Args:
        script_id: Script UUID
        db: Database session

    Returns:
        List[AudioFile]: Audio files for this script
    """
    logger.info(f"Listing audio files for script: {script_id}")

    audio_files = await audio_service.list_audio_files_for_script(db, script_id)
    return audio_files


@router.delete(
    "/audio/{audio_file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["audio-generation"],
)
async def delete_audio_endpoint(audio_file_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete audio file (removes from database and filesystem).

    Args:
        audio_file_id: Audio file UUID
        db: Database session

    Raises:
        HTTPException: 404 if audio file not found
    """
    logger.info(f"Deleting audio file: {audio_file_id}")

    try:
        await audio_service.delete_audio_file(db, audio_file_id)
        await db.commit()
        logger.info(f"Audio file deleted: {audio_file_id}")
    except Exception as e:
        logger.error(f"Error deleting audio file: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {audio_file_id}",
        )


# ============================================================================
# Cross-Resource Endpoints
# ============================================================================


@router.get(
    "/generations/{generation_id}/scripts",
    response_model=List[AudioScript],
    tags=["timelines"],
)
async def get_generation_scripts_endpoint(
    generation_id: UUID, db: AsyncSession = Depends(get_db)
):
    """
    Get all scripts that include a specific generation.

    Args:
        generation_id: Generation UUID
        db: Database session

    Returns:
        List[AudioScript]: Scripts using this generation
    """
    logger.info(f"Getting scripts for generation: {generation_id}")

    scripts = await script_service.get_scripts_for_generation(db, generation_id)
    return scripts


@router.delete(
    "/generations/{generation_id}/translations/{language_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["generations"],
)
async def delete_generation_translation_endpoint(
    generation_id: UUID,
    language_code: str,
    content_type: str = Query(..., pattern="^(report|narrative)$"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a generation translation (report or narrative)."""
    from sqlalchemy.orm.attributes import flag_modified

    generation = await db.get(GenerationDB, str(generation_id))
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if content_type == "report":
        if (
            not generation.report_translations
            or language_code not in generation.report_translations
        ):
            raise HTTPException(status_code=404, detail="Report translation not found")
        del generation.report_translations[language_code]
        flag_modified(generation, "report_translations")
    else:
        if (
            not generation.narrative_translations
            or language_code not in generation.narrative_translations
        ):
            raise HTTPException(status_code=404, detail="Narrative translation not found")
        del generation.narrative_translations[language_code]
        flag_modified(generation, "narrative_translations")

    await db.commit()
    logger.info(
        f"Deleted generation {content_type} translation: {generation_id} -> {language_code}"
    )
    return None
