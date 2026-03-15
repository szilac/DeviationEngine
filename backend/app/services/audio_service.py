"""
Audio generation service using Google Gemini TTS.

This service handles:
- Audio generation from approved scripts using Google TTS
- PCM to WAV/MP3 conversion
- Audio file storage and management
- Single and multi-speaker voice configuration
"""

import os
import re
import base64
import wave
import logging
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from google import genai
from google.genai import types

from app.db_models import AudioScriptDB, AudioFileDB, ScriptTranslationDB
from app.models import AudioFile, AudioGenerationRequest
from app.services import script_service
from app.exceptions import ValidationError, NotFoundError, AIGenerationError

logger = logging.getLogger(__name__)

# Audio storage configuration
AUDIO_DIR = Path(__file__).parent.parent.parent / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Voice mapping for different styles (from Google TTS guide)
VOICE_RECOMMENDATIONS = {
    'documentary': 'Kore',  # Firm, authoritative
    'podcast': 'Zephyr',  # Energetic, engaging
    'podcast_secondary': 'Charon',  # Deep, knowledgeable
    'news_report': 'Algenib',  # Professional, clear
    'storytelling': 'Aoede',  # Melodic, expressive
    'narrator': 'Orus',  # Clear, neutral
}


# ===== AUDIO GENERATION =====


async def generate_audio_from_script(
    db: AsyncSession,
    script_id: UUID,
    request: AudioGenerationRequest,
    language_code: str = 'en'
) -> AudioFile:
    """
    Generate audio from approved script (original or translated).

    Args:
        db: Database session
        script_id: Script UUID
        request: Audio generation request with voice settings
        language_code: Language code (default: 'en')

    Returns:
        AudioFile model with generated audio metadata

    Raises:
        NotFoundError: If script doesn't exist
        ValidationError: If script not approved
        AIGenerationError: If TTS generation fails

    Example:
        >>> request = AudioGenerationRequest(
        ...     voice_settings={'stability': 0.7},
        ...     voice_ids={'narrator': 'Kore'}
        ... )
        >>> audio_file = await generate_audio_from_script(db, script_id, request)
    """
    logger.info(f"Generating audio for script: {script_id}, language: {language_code}")

    # 1. Get script
    script_pydantic = await script_service.get_script_by_id(db, script_id)

    result = await db.execute(
        select(AudioScriptDB).where(AudioScriptDB.id == str(script_id))
    )
    db_script = result.scalar_one_or_none()

    if not db_script:
        raise NotFoundError(f"Script not found: {script_id}")

    # 2. Validate script status (allow both 'approved' and 'audio_generated')
    if db_script.status not in ('approved', 'audio_generated'):
        raise ValidationError(
            f"Can only generate audio from approved scripts. Current status: {db_script.status}",
            details={"script_id": str(script_id), "status": db_script.status}
        )

    # 3. Get script content (original or translated)
    script_content = db_script.script_content
    translation_id = None

    if language_code != 'en':
        # Get translation
        result = await db.execute(
            select(ScriptTranslationDB).where(
                ScriptTranslationDB.script_id == str(script_id),
                ScriptTranslationDB.language_code == language_code
            )
        )
        translation = result.scalar_one_or_none()

        if not translation:
            raise NotFoundError(
                f"Translation not found for language: {language_code}",
                details={"script_id": str(script_id), "language_code": language_code}
            )

        script_content = translation.translated_content
        translation_id = translation.id

    # 4. Determine voice configuration
    voice_count = script_pydantic.preset.voice_count if script_pydantic.preset else 1
    voice_config = _determine_voice_config(
        script_type=script_pydantic.preset.script_type.value if script_pydantic.preset else 'documentary',
        voice_count=voice_count,
        voice_ids_override=request.voice_ids
    )

    # 5. Generate audio using Google TTS
    logger.info(f"Script length: {len(script_content)} chars, {len(script_content.split())} words")

    try:
        audio_bytes, duration_seconds = await _generate_tts_audio(
            script_content=script_content,
            voice_config=voice_config,
            voice_count=voice_count
        )
    except Exception as e:
        logger.error(f"TTS generation failed: {e}", exc_info=True)
        raise AIGenerationError(
            "Failed to generate audio with Google TTS",
            details={"error": str(e), "script_id": str(script_id)}
        ) from e

    # 6. Check if audio already exists for this script+language and delete it
    existing_audio = await _get_audio_file_by_lang(db, script_id, language_code)
    if existing_audio:
        logger.info(
            f"Deleting existing audio file for script {script_id}, language {language_code}: "
            f"{existing_audio.id}"
        )
        # Delete file from filesystem
        try:
            old_file_path = Path(existing_audio.audio_local_path)
            if old_file_path.exists():
                old_file_path.unlink()
                logger.info(f"Deleted old audio file from filesystem: {old_file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete old audio file from filesystem: {e}")

        # Delete from database
        await db.delete(existing_audio)
        await db.flush()
        logger.info(f"Deleted old audio file from database: {existing_audio.id}")

    # 7. Convert PCM to WAV
    audio_file_id = str(uuid4())
    output_path = AUDIO_DIR / f"{audio_file_id}.wav"

    try:
        _pcm_to_wav(audio_bytes, output_path)
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}", exc_info=True)
        raise AIGenerationError(
            "Failed to convert audio to WAV format",
            details={"error": str(e)}
        ) from e

    # 8. Get file metadata
    file_size = output_path.stat().st_size

    # 9. Create audio file record
    now = datetime.now(timezone.utc)

    db_audio_file = AudioFileDB(
        id=audio_file_id,
        script_id=str(script_id),
        source_type='translation' if translation_id else 'original',
        script_translation_id=translation_id,
        language_code=language_code,
        audio_local_path=str(output_path.absolute()),
        audio_url=f"/audio/{audio_file_id}.wav",
        file_size_bytes=file_size,
        duration_seconds=duration_seconds,
        format='wav',
        sample_rate=24000,
        bit_rate=None,  # WAV doesn't use bit rate
        voice_model='gemini-2.5-flash-preview-tts',
        voice_settings=request.voice_settings,
        voice_ids=voice_config,
        model_provider='google',
        model_name='gemini-2.5-flash-preview-tts',
        generated_at=now
    )

    db.add(db_audio_file)

    # NOTE: We no longer change script status to 'audio_generated'
    # Scripts remain in 'approved' status, allowing users to edit and regenerate audio

    await db.flush()

    logger.info(
        f"Audio generated successfully: {audio_file_id}, "
        f"size={file_size} bytes, duration={duration_seconds}s"
    )

    return AudioFile.model_validate(db_audio_file)

def _chunk_script(script_content: str, max_chunk_size: int = 8000) -> list[str]:
    """
    Split script into chunks smaller than max_chunk_size, respecting sentence boundaries.
    Skips empty or whitespace-only lines.
    """
    # Normalize whitespace and split by sentences (preserve punctuation)
    text = re.sub(r'\s+', ' ', script_content.strip())
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if not sentence.strip():
            continue

        if len(current_chunk) + len(sentence) + 1 > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    logger.info(f"Split script into {len(chunks)} chunks for TTS processing.")
    return chunks

# ===== GOOGLE TTS FUNCTIONS =====


async def _generate_tts_audio(
    script_content: str,
    voice_config: Dict[str, str],
    voice_count: int
) -> tuple[bytes, int]:
    """
    Generate audio using Google Gemini TTS API, handling long scripts by chunking.

    Args:
        script_content: Script markdown with speaker markers
        voice_config: Voice IDs mapping
        voice_count: 1 or 2

    Returns:
        Tuple of (audio_bytes, duration_seconds)

    Raises:
        Exception: If TTS API call fails
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValidationError(
            "GEMINI_API_KEY not configured",
            details={"env_var": "GEMINI_API_KEY"}
        )

    client = genai.Client(api_key=api_key)

    # Configure speech config based on voice count
    if voice_count == 1:
        # Single voice configuration
        voice_name = list(voice_config.values())[0]
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        )
    else:
        # Multi-speaker configuration
        speaker_configs = []
        for speaker, voice_name in voice_config.items():
            speaker_configs.append(
                types.SpeakerVoiceConfig(
                    speaker=speaker,
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )

        speech_config = types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=speaker_configs
            )
        )

    # Split script into manageable chunks
    script_chunks = _chunk_script(script_content)

    pcm_parts = []
    for i, chunk in enumerate(script_chunks):
        logger.info(f"Generating audio for chunk {i+1}/{len(script_chunks)} ({len(chunk)} chars)...")
        logger.info(f"Chunk {i+1}: len={len(chunk)}\n{chunk[:200]}...")
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash-preview-tts',
                contents=chunk,
                config=types.GenerateContentConfig(
                    response_modalities=['AUDIO'],
                    speech_config=speech_config
                )
            )

            inline_data = response.candidates[0].content.parts[0].inline_data
            audio_data = inline_data.data

            # Decode to PCM bytes immediately (don't concatenate base64 strings!)
            if isinstance(audio_data, str):
                # It's base64-encoded, decode it
                pcm_bytes = base64.b64decode(audio_data)
            else:
                # It's already binary data
                pcm_bytes = audio_data

            logger.info(f"Chunk {i+1} PCM size: {len(pcm_bytes)} bytes")
            pcm_parts.append(pcm_bytes)

        except Exception as e:
            logger.error(f"TTS generation for chunk {i+1} failed: {e}", exc_info=True)
            raise AIGenerationError(
                f"TTS generation failed on chunk {i+1}",
                details={"error": str(e), "chunk_index": i+1}
            )

    # Concatenate raw PCM bytes (this preserves sample alignment)
    combined_pcm = b''.join(pcm_parts)

    # sanity check: even length
    if len(combined_pcm) % 2 != 0:
        logger.warning("combined PCM has odd length; trimming 1 byte")
        combined_pcm = combined_pcm[:-1]

    logger.info(f"TTS response: size={len(combined_pcm)} bytes")

    # Calculate total duration
    sample_rate = 24000
    bytes_per_sample = 2
    duration_seconds = len(combined_pcm) // (sample_rate * bytes_per_sample)

    logger.info(f"TTS generation complete: {len(combined_pcm)} bytes, ~{duration_seconds}s")

    if duration_seconds < 1 and len(script_content) > 50:
        logger.warning(
            f"Generated audio is very short ({duration_seconds}s) for a script of {len(script_content)} chars. "
            "This may indicate a problem with the TTS service or input text."
        )

    return combined_pcm, duration_seconds


def _determine_voice_config(
    script_type: str,
    voice_count: int,
    voice_ids_override: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Determine voice configuration based on script type and count.

    Args:
        script_type: Type of script (documentary, podcast, etc.)
        voice_count: Number of voices (1 or 2)
        voice_ids_override: Optional user-provided voice IDs

    Returns:
        Dict mapping speaker names to voice IDs

    Example:
        >>> _determine_voice_config('documentary', 1)
        {'NARRATOR': 'Kore'}
        >>> _determine_voice_config('podcast', 2)
        {'HOST': 'Zephyr', 'EXPERT': 'Charon'}
    """
    if voice_ids_override:
        return voice_ids_override

    if voice_count == 1:
        # Single voice
        voice = VOICE_RECOMMENDATIONS.get(script_type, 'Orus')
        return {'NARRATOR': voice}
    else:
        # Two voices (podcast)
        return {
            'HOST': VOICE_RECOMMENDATIONS.get('podcast', 'Zephyr'),
            'EXPERT': VOICE_RECOMMENDATIONS.get('podcast_secondary', 'Charon')
        }


def _pcm_to_wav(pcm_bytes: bytes, output_path: Path) -> None:
    """
    Convert PCM audio bytes to WAV file.

    Args:
        pcm_bytes: Raw PCM audio data
        output_path: Path to save WAV file

    Raises:
        Exception: If conversion fails
    """
    with wave.open(str(output_path), 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(24000)  # 24 kHz sample rate
        wav_file.writeframes(pcm_bytes)

    logger.debug(f"Converted PCM to WAV: {output_path}")


# ===== AUDIO FILE CRUD =====


async def _get_audio_file_by_lang(
    db: AsyncSession,
    script_id: UUID,
    language_code: str
) -> Optional[AudioFileDB]:
    """
    Get an audio file for a specific script and language.
    """
    result = await db.execute(
        select(AudioFileDB).where(
            AudioFileDB.script_id == str(script_id),
            AudioFileDB.language_code == language_code
        )
    )
    return result.scalar_one_or_none()


async def get_audio_file_by_id(
    db: AsyncSession,
    audio_file_id: UUID
) -> AudioFile:
    """
    Get audio file by ID.

    Args:
        db: Database session
        audio_file_id: Audio file UUID

    Returns:
        AudioFile model

    Raises:
        NotFoundError: If audio file doesn't exist
    """
    result = await db.execute(
        select(AudioFileDB).where(AudioFileDB.id == str(audio_file_id))
    )
    db_audio_file = result.scalar_one_or_none()

    if not db_audio_file:
        raise NotFoundError(f"Audio file not found: {audio_file_id}")

    return AudioFile.model_validate(db_audio_file)


async def list_audio_files_for_script(
    db: AsyncSession,
    script_id: UUID
) -> list[AudioFile]:
    """
    List all audio files for a script (all languages).

    Args:
        db: Database session
        script_id: Script UUID

    Returns:
        List of AudioFile models
    """
    query = (
        select(AudioFileDB)
        .where(AudioFileDB.script_id == str(script_id))
        .order_by(AudioFileDB.generated_at.desc())
    )

    result = await db.execute(query)
    db_audio_files = result.scalars().all()

    return [AudioFile.model_validate(af) for af in db_audio_files]


async def delete_audio_file(
    db: AsyncSession,
    audio_file_id: UUID
) -> None:
    """
    Delete audio file and remove from filesystem.

    Args:
        db: Database session
        audio_file_id: Audio file UUID

    Raises:
        NotFoundError: If audio file doesn't exist
    """
    result = await db.execute(
        select(AudioFileDB).where(AudioFileDB.id == str(audio_file_id))
    )
    db_audio_file = result.scalar_one_or_none()

    if not db_audio_file:
        raise NotFoundError(f"Audio file not found: {audio_file_id}")

    # Delete from filesystem
    try:
        file_path = Path(db_audio_file.audio_local_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted audio file from filesystem: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to delete audio file from filesystem: {e}")

    # Delete from database
    await db.delete(db_audio_file)
    await db.flush()

    logger.info(f"Deleted audio file: {audio_file_id}")
