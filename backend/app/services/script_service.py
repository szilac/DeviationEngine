"""
Audio script generation and management service.

This service handles:
- Script generation from timeline content using Script Writer Agent
- Script CRUD operations
- Script approval workflow
- Association with generations
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
import logging
import json

from app.db_models import AudioScriptDB, GenerationDB, ScriptTranslationDB
from app.models import (
    AudioScript, ScriptGenerationRequest, ScriptUpdateRequest,
    ScriptStatus, ScriptTranslation
)
from app.agents.script_writer_agent import generate_script, estimate_duration_from_word_count, count_words
from app.services import llm_service
from app.services import preset_service
from app.exceptions import ValidationError, NotFoundError, AIGenerationError

logger = logging.getLogger(__name__)


# ===== SCRIPT GENERATION =====


async def generate_audio_script(
    db: AsyncSession,
    request: ScriptGenerationRequest
) -> AudioScript:
    """
    Generate new audio script from generation content.

    This is the main entry point for script generation. It:
    1. Validates generation IDs exist
    2. Fetches generation content
    3. Loads preset configuration
    4. Calls Script Writer Agent
    5. Saves draft script to database

    Args:
        db: Database session
        request: Script generation request with generation_ids, preset_id, custom_instructions

    Returns:
        Created AudioScript in 'draft' status

    Raises:
        ValidationError: If generation IDs invalid or preset not found
        AIGenerationError: If script generation fails

    Example:
        >>> request = ScriptGenerationRequest(
        ...     generation_ids=[gen1_id, gen2_id],
        ...     preset_id=preset_id,
        ...     custom_instructions="Focus on economic impacts"
        ... )
        >>> script = await generate_audio_script(db, request)
        >>> script.status
        <ScriptStatus.DRAFT: 'draft'>
    """
    logger.info(
        f"Generating script: {len(request.generation_ids)} generations, "
        f"preset={request.preset_id}"
    )

    # 1. Validate and fetch generations
    generations_content = await _fetch_generations_content(
        db, request.generation_ids
    )

    # 2. Load preset
    preset = await preset_service.get_preset_by_id(db, request.preset_id)
    preset_dict = preset.model_dump()

    # 3. Get appropriate LLM model
    from app.models import AgentType
    model = await llm_service.create_pydantic_ai_model_for_agent(
        db,
        agent_type=AgentType.SCRIPT_WRITER
    )

    # 4. Generate script using agent
    try:
        script_output = await generate_script(
            generations_content=generations_content,
            preset=preset_dict,
            custom_instructions=request.custom_instructions,
            model=model
        )
    except Exception as e:
        logger.error(f"Script generation failed: {e}", exc_info=True)
        raise AIGenerationError(
            "Failed to generate audio script",
            details={"error": str(e), "generations": len(request.generation_ids)}
        ) from e

    # 5. Determine script structure from preset
    script_structure = 'dual_voice' if preset.voice_count == 2 else 'single_voice'

    # 6. Create script record
    now = datetime.now(timezone.utc)

    db_script = AudioScriptDB(
        id=str(uuid4()),
        generation_ids=json.dumps([str(gid) for gid in request.generation_ids]),
        title=request.title or script_output.suggested_title,
        description=None,
        preset_id=str(request.preset_id),
        custom_instructions=request.custom_instructions,
        script_content=script_output.script_content,
        script_structure=script_structure,
        word_count=script_output.word_count,
        estimated_duration_seconds=script_output.estimated_duration_seconds,
        status='draft',
        model_provider=model.name() if hasattr(model, 'name') else 'unknown',
        model_name=str(model),
        created_at=now,
        approved_at=None,
        updated_at=now
    )

    db.add(db_script)
    await db.flush()

    logger.info(
        f"Script created: {db_script.id}, "
        f"{db_script.word_count} words, "
        f"~{db_script.estimated_duration_seconds}s"
    )

    return await _db_script_to_pydantic(db, db_script)


async def _fetch_generations_content(
    db: AsyncSession,
    generation_ids: List[UUID]
) -> List[Dict[str, Any]]:
    """
    Fetch generation content for script generation.

    Args:
        db: Database session
        generation_ids: List of generation UUIDs

    Returns:
        List of generation content dicts with all fields needed for script generation

    Raises:
        ValidationError: If any generation ID is invalid
    """
    if not generation_ids:
        raise ValidationError("At least one generation ID required")

    if len(generation_ids) > 10:
        raise ValidationError("Maximum 10 generations per script")

    # Fetch all generations
    query = select(GenerationDB).where(
        GenerationDB.id.in_([str(gid) for gid in generation_ids])
    )
    result = await db.execute(query)
    db_generations = result.scalars().all()

    # Validate all IDs found
    found_ids = {g.id for g in db_generations}
    requested_ids = {str(gid) for gid in generation_ids}

    if found_ids != requested_ids:
        missing = requested_ids - found_ids
        raise ValidationError(
            f"Generation(s) not found: {missing}",
            details={"missing_ids": list(missing)}
        )

    # Sort by generation_order
    db_generations_sorted = sorted(db_generations, key=lambda g: g.generation_order)

    # Extract content
    generations_content = []
    for gen in db_generations_sorted:
        generations_content.append({
            'id': gen.id,
            'start_year': gen.start_year,
            'end_year': gen.end_year,
            'period_years': gen.period_years,
            'executive_summary': gen.executive_summary,
            'political_changes': gen.political_changes,
            'conflicts_and_wars': gen.conflicts_and_wars or '',
            'economic_impacts': gen.economic_impacts,
            'social_developments': gen.social_developments,
            'technological_shifts': gen.technological_shifts,
            'key_figures': gen.key_figures,
            'long_term_implications': gen.long_term_implications,
            'narrative_prose': gen.narrative_prose
        })

    logger.debug(f"Fetched {len(generations_content)} generations for script")
    return generations_content


# ===== SCRIPT CRUD =====


async def get_script_by_id(
    db: AsyncSession,
    script_id: UUID
) -> AudioScript:
    """
    Get script by ID with preset populated.

    Args:
        db: Database session
        script_id: Script UUID

    Returns:
        AudioScript with preset relationship loaded

    Raises:
        NotFoundError: If script doesn't exist
    """
    result = await db.execute(
        select(AudioScriptDB).where(AudioScriptDB.id == str(script_id))
    )
    db_script = result.scalar_one_or_none()

    if not db_script:
        raise NotFoundError(f"Script not found: {script_id}")

    return await _db_script_to_pydantic(db, db_script)


async def update_script_content(
    db: AsyncSession,
    script_id: UUID,
    update_data: ScriptUpdateRequest
) -> AudioScript:
    """
    Update script content.

    Scripts can be edited in 'draft' or 'approved' status. When editing an
    approved script, it will be reset to 'draft' status and must be re-approved
    before generating audio.

    Args:
        db: Database session
        script_id: Script to update
        update_data: New content

    Returns:
        Updated AudioScript (status reset to 'draft' if was 'approved')

    Raises:
        NotFoundError: If script doesn't exist
    """
    # Get script
    result = await db.execute(
        select(AudioScriptDB).where(AudioScriptDB.id == str(script_id))
    )
    db_script = result.scalar_one_or_none()

    if not db_script:
        raise NotFoundError(f"Script not found: {script_id}")

    # If script was approved or audio_generated, reset to draft
    # (user must re-approve after editing)
    was_approved = db_script.status in ('approved', 'audio_generated')
    if was_approved:
        db_script.status = 'draft'
        db_script.approved_at = None
        logger.info(f"Script was '{db_script.status}', resetting to 'draft' after edit")

    # Update content
    db_script.script_content = update_data.script_content
    if update_data.title:
        db_script.title = update_data.title
    if update_data.description:
        db_script.description = update_data.description

    # Recalculate word count and duration
    db_script.word_count = count_words(update_data.script_content)

    # Get preset to determine pacing
    preset = await preset_service.get_preset_by_id(db, db_script.preset_id)
    db_script.estimated_duration_seconds = estimate_duration_from_word_count(
        db_script.word_count,
        pacing=preset.pacing.value
    )

    db_script.updated_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"Updated script content: {script_id}")

    return await _db_script_to_pydantic(db, db_script)


async def approve_script(
    db: AsyncSession,
    script_id: UUID
) -> AudioScript:
    """
    Approve script for audio generation.

    Status: draft → approved (or re-approve if already approved)

    Args:
        db: Database session
        script_id: Script to approve

    Returns:
        Approved AudioScript

    Raises:
        NotFoundError: If script doesn't exist
    """
    # Get script
    result = await db.execute(
        select(AudioScriptDB).where(AudioScriptDB.id == str(script_id))
    )
    db_script = result.scalar_one_or_none()

    if not db_script:
        raise NotFoundError(f"Script not found: {script_id}")

    # Allow approving from draft or re-approving already approved scripts
    # (useful after editing and needing to re-approve)
    db_script.status = 'approved'
    db_script.approved_at = datetime.now(timezone.utc)
    db_script.updated_at = db_script.approved_at
    await db.flush()

    logger.info(f"Approved script: {script_id}")

    return await _db_script_to_pydantic(db, db_script)


async def mark_script_audio_generated(
    db: AsyncSession,
    script_id: UUID
) -> AudioScript:
    """
    Mark script as having audio generated.

    Status: approved → audio_generated

    Called internally after successful audio file creation.

    Args:
        db: Database session
        script_id: Script ID

    Returns:
        Updated AudioScript
    """
    result = await db.execute(
        select(AudioScriptDB).where(AudioScriptDB.id == str(script_id))
    )
    db_script = result.scalar_one_or_none()

    if not db_script:
        raise NotFoundError(f"Script not found: {script_id}")

    db_script.status = 'audio_generated'
    db_script.updated_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"Marked script as audio_generated: {script_id}")

    return await _db_script_to_pydantic(db, db_script)


# ===== LIST & SEARCH =====


async def list_scripts(
    db: AsyncSession,
    status: Optional[ScriptStatus] = None,
    preset_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0
) -> List[AudioScript]:
    """
    List scripts with optional filtering.

    Args:
        db: Database session
        status: Filter by status
        preset_id: Filter by preset
        limit: Maximum results
        offset: Pagination offset

    Returns:
        List of AudioScript models
    """
    query = select(AudioScriptDB).order_by(AudioScriptDB.created_at.desc())

    if status:
        query = query.where(AudioScriptDB.status == status.value)

    if preset_id:
        query = query.where(AudioScriptDB.preset_id == str(preset_id))

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    db_scripts = result.scalars().all()

    return [await _db_script_to_pydantic(db, s) for s in db_scripts]


async def get_scripts_for_generation(
    db: AsyncSession,
    generation_id: UUID
) -> List[AudioScript]:
    """
    Get all scripts that include a specific generation.

    Since generation_ids is stored as JSON array, we need to
    check if the ID is in the array.

    Args:
        db: Database session
        generation_id: Generation UUID

    Returns:
        List of scripts that include this generation
    """
    # Get all scripts
    result = await db.execute(select(AudioScriptDB))
    all_scripts = result.scalars().all()

    # Filter by generation ID presence
    matching_scripts = []
    target_id = str(generation_id)

    for script in all_scripts:
        gen_ids = json.loads(script.generation_ids)
        if target_id in gen_ids:
            matching_scripts.append(script)

    logger.debug(
        f"Found {len(matching_scripts)} scripts for generation {generation_id}"
    )

    return [await _db_script_to_pydantic(db, s) for s in matching_scripts]


# ===== TRANSLATION =====


async def translate_script(
    db: AsyncSession,
    script_id: UUID,
    language_code: str,
    language_name: str,
    method: str = 'deepl'
) -> 'ScriptTranslation':
    """
    Translate audio script to target language using DeepL or LLM.

    This function:
    1. Checks if translation already exists (returns cached if found)
    2. Validates script exists
    3. Translates script content using selected method (DeepL or LLM)
    4. Preserves markdown structure and speaker markers
    5. Stores translation in script_translations table

    Args:
        db: Database session
        script_id: Script UUID
        language_code: ISO 639-1 language code (e.g., 'es', 'fr', 'de')
        language_name: Human-readable language name (e.g., 'Spanish', 'French')
        method: Translation method ('deepl' or 'llm', default: 'deepl')

    Returns:
        ScriptTranslation with translated content

    Raises:
        NotFoundError: If script doesn't exist
        TranslationError: If translation fails

    Example:
        >>> translation = await translate_script(
        ...     db, script_id, language_code="es", language_name="Spanish", method="llm"
        ... )
        >>> print(translation.translated_content)
    """
    from app.db_models import ScriptTranslationDB
    from app.models import ScriptTranslation
    from app.services.translation_service import get_translation_service
    from app.exceptions import TranslationError

    # Normalize language code to lowercase
    lang_code = language_code.lower()

    logger.info(f"Translating script {script_id} to {lang_code} ({language_name})")

    # 1. Get script from database
    result = await db.execute(
        select(AudioScriptDB).where(AudioScriptDB.id == str(script_id))
    )
    db_script = result.scalar_one_or_none()

    if not db_script:
        raise NotFoundError(f"Script not found: {script_id}")

    # 2. Check if translation already exists (cache)
    existing_result = await db.execute(
        select(ScriptTranslationDB).where(
            ScriptTranslationDB.script_id == str(script_id),
            ScriptTranslationDB.language_code == lang_code
        )
    )
    existing_translation = existing_result.scalar_one_or_none()

    if existing_translation:
        logger.info(
            f"Cache hit: Using cached translation for script {script_id}, "
            f"language {lang_code}"
        )
        return _db_translation_to_pydantic(existing_translation)

    # 3. Determine content type from preset for LLM translation
    # Note: We don't load the preset relationship to avoid async SQLAlchemy issues
    # Default to generic content type to ensure translation works
    content_type = 'generic'
    if hasattr(db_script, 'preset_id') and db_script.preset_id:
        # Only try to get preset if we have a preset_id, but don't fail if relationship loading fails
        try:
            content_type_map = {
                'podcast': 'podcast_script',
                'documentary': 'documentary_script',
                'news': 'news_script',
                'storytelling': 'storytelling_script',
            }
            # We can't safely access db_script.preset in async context, so we default
            # This is a limitation but ensures the translation functionality works
            content_type = 'generic'  # Keep as generic to be safe
        except Exception:
            # If there's any issue with preset loading, default to generic
            content_type = 'generic'

    # 4. Translate script content using selected method
    if method == 'llm':
        # Use LLM translation
        from app.agents.translator_agent import translate_with_llm, ContentType
        from app.models import AgentType

        try:
            # Create translator model
            translator_model = await llm_service.create_pydantic_ai_model_for_agent(
                db,
                agent_type=AgentType.TRANSLATOR
            )
            
            # Map string content type to enum
            content_type_enum = ContentType.GENERIC
            try:
                content_type_enum = ContentType[content_type.upper()]
            except (KeyError, AttributeError):
                logger.warning(f"Unknown content type '{content_type}', using GENERIC")

            translated_content = await translate_with_llm(
                text=db_script.script_content,
                target_language=lang_code,
                source_language='en',
                content_type=content_type_enum,
                metadata={'tone': 'casual'} if content_type == 'podcast_script' else {},
                model=translator_model
            )
        except Exception as e:
            logger.error(f"LLM translation error: {e}", exc_info=True)
            raise TranslationError(
                f"Failed to translate script with LLM: {str(e)}",
                details={
                    "script_id": str(script_id),
                    "target_language": lang_code,
                    "error_type": type(e).__name__
                }
            )
    else:
        # Use DeepL translation
        try:
            translation_service = await get_translation_service(db)
        except Exception as e:
            logger.error(f"Failed to get translation service: {e}")
            raise TranslationError(
                "Translation service not configured. Please configure DeepL API key.",
                details={"error": str(e)}
            )

        try:
            translated_content = await translation_service.deepl.translate_text(
                text=db_script.script_content,
                target_lang=lang_code.upper(),
                source_lang="EN"
            )
        except Exception as e:
            logger.error(f"DeepL API error: {e}", exc_info=True)
            raise TranslationError(
                f"Failed to translate script with DeepL: {str(e)}",
                details={
                    "script_id": str(script_id),
                    "target_language": lang_code,
                    "error_type": type(e).__name__
                }
            )

    # 5. Create translation record
    now = datetime.now(timezone.utc)
    word_count = len(translated_content.split())

    db_translation = ScriptTranslationDB(
        id=str(uuid4()),
        script_id=str(script_id),
        language_code=lang_code,
        language_name=language_name,
        translated_content=translated_content,
        word_count=word_count,
        translation_method=method,
        is_human_translated=0,  # AI-translated
        translation_quality_score=None,
        translation_model_provider=method,
        translation_model_name="llm" if method == "llm" else "deepl-translate",
        created_at=now,
        updated_at=now
    )

    db.add(db_translation)
    await db.flush()

    logger.info(
        f"Script translated successfully: {script_id} -> {lang_code}, "
        f"{len(translated_content)} chars"
    )

    return _db_translation_to_pydantic(db_translation)


async def list_translations_for_script(
    db: AsyncSession,
    script_id: UUID
) -> List['ScriptTranslation']:
    """
    List all translations for a specific script.

    Args:
        db: Database session
        script_id: Script UUID

    Returns:
        List of ScriptTranslation models

    Example:
        >>> translations = await list_translations_for_script(db, script_id)
        >>> for t in translations:
        ...     print(f"{t.language_name} ({t.language_code})")
    """
    from app.db_models import ScriptTranslationDB
    from app.models import ScriptTranslation

    query = (
        select(ScriptTranslationDB)
        .where(ScriptTranslationDB.script_id == str(script_id))
        .order_by(ScriptTranslationDB.created_at.desc())
    )

    result = await db.execute(query)
    db_translations = result.scalars().all()

    logger.debug(f"Found {len(db_translations)} translations for script {script_id}")

    return [_db_translation_to_pydantic(t) for t in db_translations]


async def update_translation(
    db: AsyncSession,
    translation_id: UUID,
    translated_content: str
) -> 'ScriptTranslation':
    """
    Update the content of an existing script translation.

    This allows manual editing of translated content. The word count
    is recalculated and updated_at timestamp is set.

    Args:
        db: Database session
        translation_id: Translation UUID
        translated_content: Updated translation content

    Returns:
        Updated ScriptTranslation model

    Raises:
        NotFoundError: If translation doesn't exist

    Example:
        >>> translation = await update_translation(
        ...     db, translation_id, "Updated content..."
        ... )
    """
    from app.db_models import ScriptTranslationDB
    from app.models import ScriptTranslation

    # Find existing translation
    query = select(ScriptTranslationDB).where(
        ScriptTranslationDB.id == str(translation_id)
    )
    result = await db.execute(query)
    db_translation = result.scalar_one_or_none()

    if not db_translation:
        raise NotFoundError(f"Translation not found: {translation_id}")

    # Update content and metadata
    db_translation.translated_content = translated_content
    db_translation.updated_at = datetime.now(timezone.utc)

    # Mark as human-modified if it was previously AI-translated
    if not db_translation.is_human_translated:
        db_translation.is_human_translated = True

    await db.flush()

    logger.info(f"Translation updated: {translation_id}")

    return _db_translation_to_pydantic(db_translation)


# ===== DELETE =====


async def delete_script(
    db: AsyncSession,
    script_id: UUID
) -> None:
    """
    Delete script and all associated translations/audio files.

    Also deletes physical audio files from filesystem.
    Cascade delete will handle database records for translations and audio_files.

    Args:
        db: Database session
        script_id: Script to delete

    Raises:
        NotFoundError: If script doesn't exist
    """
    from pathlib import Path
    from app.db_models import AudioFileDB

    result = await db.execute(
        select(AudioScriptDB).where(AudioScriptDB.id == str(script_id))
    )
    db_script = result.scalar_one_or_none()

    if not db_script:
        raise NotFoundError(f"Script not found: {script_id}")

    # Get all audio files for this script to delete physical files
    audio_files_result = await db.execute(
        select(AudioFileDB).where(AudioFileDB.script_id == str(script_id))
    )
    audio_files = audio_files_result.scalars().all()

    # Delete physical audio files from filesystem
    for audio_file in audio_files:
        try:
            file_path = Path(audio_file.audio_local_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted audio file from filesystem: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete audio file {audio_file.id} from filesystem: {e}")

    # Delete script (cascade will handle audio_files and translations in DB)
    await db.delete(db_script)
    await db.flush()

    logger.info(f"Deleted script {script_id} and {len(audio_files)} associated audio files")


# ===== HELPERS =====


async def _db_script_to_pydantic(
    db: AsyncSession,
    db_script: AudioScriptDB
) -> AudioScript:
    """
    Convert DB model to Pydantic model with preset populated.

    Args:
        db: Database session
        db_script: SQLAlchemy model

    Returns:
        Pydantic AudioScript with preset loaded
    """
    # Load preset if exists
    preset = None
    if db_script.preset_id:
        try:
            preset = await preset_service.get_preset_by_id(
                db, db_script.preset_id  # Can be string ID or UUID
            )
        except NotFoundError:
            logger.warning(f"Preset not found for script: {db_script.preset_id}")

    # Parse generation_ids from JSON
    generation_ids = [UUID(gid) for gid in json.loads(db_script.generation_ids)]

    return AudioScript(
        id=UUID(db_script.id),
        generation_ids=generation_ids,
        title=db_script.title,
        description=db_script.description,
        preset_id=db_script.preset_id,  # Keep as string
        preset=preset,
        custom_instructions=db_script.custom_instructions,
        script_content=db_script.script_content,
        script_structure=db_script.script_structure,
        word_count=db_script.word_count,
        estimated_duration_seconds=db_script.estimated_duration_seconds,
        status=ScriptStatus(db_script.status),
        model_provider=db_script.model_provider,
        model_name=db_script.model_name,
        created_at=db_script.created_at,
        approved_at=db_script.approved_at,
        updated_at=db_script.updated_at
    )


def _db_translation_to_pydantic(
    db_translation: 'ScriptTranslationDB'
) -> 'ScriptTranslation':
    """
    Convert DB translation model to Pydantic model.

    Args:
        db_translation: SQLAlchemy model

    Returns:
        Pydantic ScriptTranslation
    """
    from app.models import ScriptTranslation

    return ScriptTranslation(
        id=UUID(db_translation.id),
        script_id=UUID(db_translation.script_id),
        language_code=db_translation.language_code,
        language_name=db_translation.language_name,
        translated_content=db_translation.translated_content,
        is_human_translated=bool(db_translation.is_human_translated),
        translation_quality_score=db_translation.translation_quality_score,
        translation_model_provider=db_translation.translation_model_provider,
        translation_model_name=db_translation.translation_model_name,
        created_at=db_translation.created_at,
        updated_at=db_translation.updated_at
    )
