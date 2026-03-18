"""
Import service for timeline data with redesigned schema.

This module provides functionality to import timelines from JSON format (.devtl files)
with support for:
- New format v2.0.0 (generations + branching)
- Legacy format v1.0.0 (reports) - auto-converted to generations
"""

import logging
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import TimelineDB, GenerationDB, MediaDB
from app.exceptions import ValidationError
from app.models import NarrativeMode, ScenarioType, GenerationType

logger = logging.getLogger(__name__)

# Supported format versions (including legacy)
SUPPORTED_FORMAT_VERSIONS = ["1.0.0", "2.0.0"]


class ImportError(Exception):
    """Base exception for import-related errors."""

    pass


class InvalidFileFormatError(ImportError):
    """Raised when file format is invalid or corrupted."""

    pass


class UnsupportedVersionError(ImportError):
    """Raised when format version is not supported."""

    pass


async def import_timeline_from_json(
    db: AsyncSession, timeline_data: Dict[str, Any]
) -> UUID:
    """
    Import timeline from JSON data (supports v1.0.0 and v2.0.0 formats).

    This function validates the imported data, generates new UUIDs,
    and creates a complete timeline with all generations in the database.
    Legacy v1.0.0 files are automatically converted to the new schema.

    Args:
        db: Database session
        timeline_data: Parsed JSON timeline data from .devtl file

    Returns:
        UUID: ID of the newly created timeline

    Raises:
        InvalidFileFormatError: If data format is invalid
        UnsupportedVersionError: If format version is not supported
        ValidationError: If data validation fails

    Example:
        >>> timeline_id = await import_timeline_from_json(db, json_data)
        >>> # Timeline created with new UUID
    """
    logger.info("Starting timeline import from JSON data")

    # Validate top-level structure
    _validate_import_structure(timeline_data)

    # Validate format version
    format_version = timeline_data.get("format_version")
    if format_version not in SUPPORTED_FORMAT_VERSIONS:
        raise UnsupportedVersionError(
            f"Format version {format_version} is not supported. "
            f"Supported versions: {', '.join(SUPPORTED_FORMAT_VERSIONS)}"
        )

    # Route to appropriate importer based on version
    if format_version == "2.0.0":
        return await _import_v2_timeline(db, timeline_data)
    else:
        # Legacy v1.0.0 format - convert to new schema
        return await _import_v1_timeline_convert(db, timeline_data)


async def _import_v2_timeline(
    db: AsyncSession, timeline_data: Dict[str, Any]
) -> UUID:
    """
    Import timeline from v2.0.0 format (new schema with generations).

    Args:
        db: Database session
        timeline_data: Parsed JSON timeline data

    Returns:
        UUID: ID of the newly created timeline
    """
    timeline_obj = timeline_data.get("timeline", {})

    # Extract root deviation
    root_deviation = timeline_obj.get("root_deviation", {})
    deviation_date = root_deviation.get("deviation_date")
    deviation_description = root_deviation.get("deviation_description")
    scenario_type = root_deviation.get("scenario_type")

    # Extract branching metadata (may be None for root timelines)
    branching = timeline_obj.get("branching")

    # Generate new timeline UUID
    new_timeline_id = uuid4()

    # Create timeline record
    db_timeline = TimelineDB(
        id=str(new_timeline_id),
        timeline_name=timeline_obj.get("timeline_name"),
        parent_timeline_id=branching.get("parent_timeline_id") if branching else None,
        branch_point_year=branching.get("branch_point_year") if branching else None,
        branch_deviation_description=branching.get("branch_deviation_description")
        if branching
        else None,
        root_deviation_date=deviation_date,
        root_deviation_description=deviation_description,
        scenario_type=scenario_type,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_timeline)
    await db.flush()

    logger.info(
        f"Created timeline {new_timeline_id} "
        f"(branched: {branching is not None})"
    )

    # Import all generations
    generations_data = timeline_obj.get("generations", [])
    for generation_data in sorted(
        generations_data, key=lambda g: g.get("generation_order", 0)
    ):
        await _import_generation(db, new_timeline_id, generation_data)

    logger.info(
        f"Successfully imported timeline {new_timeline_id} with "
        f"{len(generations_data)} generations"
    )

    await db.commit()
    return new_timeline_id


async def _import_generation(
    db: AsyncSession, timeline_id: UUID, generation_data: Dict[str, Any]
) -> None:
    """
    Import a single generation.

    Args:
        db: Database session
        timeline_id: Parent timeline UUID
        generation_data: Generation data from JSON
    """
    # Generate new generation UUID
    new_generation_id = uuid4()

    # Extract period info
    period = generation_data.get("period", {})

    # Extract structured report
    report = generation_data.get("structured_report", {})

    # Extract narrative
    narrative = generation_data.get("narrative", {})

    # Extract source
    source = generation_data.get("source", {})

    # Extract metadata
    metadata = generation_data.get("metadata", {})

    # Create generation record
    db_generation = GenerationDB(
        id=str(new_generation_id),
        timeline_id=str(timeline_id),
        generation_order=generation_data.get("generation_order", 1),
        generation_type=generation_data.get("generation_type", GenerationType.INITIAL.value),
        start_year=period.get("start_year", 0),
        end_year=period.get("end_year", 0),
        period_years=period.get("period_years", 0),
        executive_summary=report.get("executive_summary", ""),
        political_changes=report.get("political_changes", ""),
        conflicts_and_wars=report.get("conflicts_and_wars", ""),
        economic_impacts=report.get("economic_impacts", ""),
        social_developments=report.get("social_developments", ""),
        technological_shifts=report.get("technological_shifts", ""),
        key_figures=report.get("key_figures", ""),
        long_term_implications=report.get("long_term_implications", ""),
        narrative_mode=narrative.get("narrative_mode"),
        narrative_prose=narrative.get("narrative_prose"),
        narrative_custom_pov=narrative.get("narrative_custom_pov"),
        source_skeleton_id=source.get("source_skeleton_id"),
        source_context=source.get("source_context"),
        report_model_provider=metadata.get("report_model_provider"),
        report_model_name=metadata.get("report_model_name"),
        narrative_model_provider=metadata.get("narrative_model_provider"),
        narrative_model_name=metadata.get("narrative_model_name"),
        report_translations=generation_data.get("report_translations"),
        narrative_translations=generation_data.get("narrative_translations"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Handle audio if present
    audio = generation_data.get("audio")
    if audio:
        db_generation.audio_script = audio.get("audio_script")
        db_generation.audio_script_format = audio.get("audio_script_format")
        db_generation.audio_url = audio.get("audio_url")
        db_generation.audio_local_path = audio.get("audio_local_path")
        db_generation.audio_duration_seconds = audio.get("audio_duration_seconds")
        db_generation.audio_voice_model = audio.get("audio_voice_model")
        db_generation.audio_voice_settings = audio.get("audio_voice_settings")
        db_generation.audio_translations = audio.get("audio_translations")
        db_generation.audio_model_provider = audio.get("audio_model_provider")
        db_generation.audio_model_name = audio.get("audio_model_name")

    db.add(db_generation)
    await db.flush()

    # Import media if present
    media_list = generation_data.get("media", [])
    for media_data in media_list:
        await _import_media(db, new_generation_id, media_data)

    logger.info(
        f"Imported generation {new_generation_id} "
        f"(order: {db_generation.generation_order}, "
        f"type: {db_generation.generation_type}) "
        f"with {len(media_list)} media items"
    )


async def _import_media(
    db: AsyncSession, generation_id: UUID, media_data: Dict[str, Any]
) -> None:
    """
    Import a single media item.

    Args:
        db: Database session
        generation_id: Parent generation UUID
        media_data: Media data from JSON
    """
    new_media_id = uuid4()

    db_media = MediaDB(
        id=str(new_media_id),
        generation_id=str(generation_id),
        media_type=media_data.get("media_type", "image"),
        media_order=media_data.get("media_order", 0),
        prompt_text=media_data.get("prompt_text"),
        media_url=media_data.get("media_url", ""),
        media_local_path=media_data.get("media_local_path"),
        event_year=media_data.get("event_year"),
        title=media_data.get("title"),
        description=media_data.get("description"),
        is_user_added=1 if media_data.get("is_user_added", False) else 0,
        is_user_modified=1 if media_data.get("is_user_modified", False) else 0,
        model_provider=media_data.get("model_provider"),
        model_name=media_data.get("model_name"),
        created_at=datetime.now(timezone.utc),
    )

    db.add(db_media)
    await db.flush()


async def _import_v1_timeline_convert(
    db: AsyncSession, timeline_data: Dict[str, Any]
) -> UUID:
    """
    Import timeline from legacy v1.0.0 format (reports) and convert to new schema.

    Args:
        db: Database session
        timeline_data: Parsed JSON timeline data in v1.0.0 format

    Returns:
        UUID: ID of the newly created timeline
    """
    logger.info("Importing legacy v1.0.0 timeline - converting to new schema")

    timeline_obj = timeline_data.get("timeline", {})

    # Extract deviation point (v1.0.0 format)
    deviation_point = timeline_obj.get("deviation_point", {})
    deviation_date = deviation_point.get("deviation_date")
    deviation_description = deviation_point.get("deviation_description")
    scenario_type = deviation_point.get("scenario_type", "local_deviation")

    # Generate new timeline UUID
    new_timeline_id = uuid4()

    # Create timeline record (no branching in v1.0.0)
    db_timeline = TimelineDB(
        id=str(new_timeline_id),
        timeline_name=timeline_obj.get("timeline_name"),
        parent_timeline_id=None,
        branch_point_year=None,
        branch_deviation_description=None,
        root_deviation_date=deviation_date,
        root_deviation_description=deviation_description,
        scenario_type=scenario_type,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_timeline)
    await db.flush()

    logger.info(f"Created timeline {new_timeline_id} from legacy format")

    # Convert reports to generations
    reports_data = timeline_obj.get("reports", [])
    for report_data in sorted(reports_data, key=lambda r: r.get("report_order", 0)):
        await _convert_report_to_generation(db, new_timeline_id, report_data)

    logger.info(
        f"Successfully converted and imported timeline {new_timeline_id} with "
        f"{len(reports_data)} reports → generations"
    )

    await db.commit()
    return new_timeline_id


async def _convert_report_to_generation(
    db: AsyncSession, timeline_id: UUID, report_data: Dict[str, Any]
) -> None:
    """
    Convert a legacy report to a generation.

    Args:
        db: Database session
        timeline_id: Parent timeline UUID
        report_data: Report data from v1.0.0 JSON
    """
    new_generation_id = uuid4()

    # Extract structured analysis
    analysis = report_data.get("structured_analysis", {})

    # Extract metadata
    metadata = report_data.get("metadata", {})

    # Determine generation type based on report_order
    report_order = report_data.get("report_order", 1)
    generation_type = (
        GenerationType.INITIAL.value
        if report_order == 1
        else GenerationType.EXTENSION.value
    )

    # Create generation record
    db_generation = GenerationDB(
        id=str(new_generation_id),
        timeline_id=str(timeline_id),
        generation_order=report_order,
        generation_type=generation_type,
        start_year=report_data.get("start_year", 0),
        end_year=report_data.get("end_year", 0),
        period_years=report_data.get("period_years", 0),
        executive_summary=analysis.get("executive_summary", ""),
        political_changes=analysis.get("political_changes", ""),
        conflicts_and_wars=analysis.get("conflicts_and_wars", ""),
        economic_impacts=analysis.get("economic_impacts", ""),
        social_developments=analysis.get("social_developments", ""),
        technological_shifts=analysis.get("technological_shifts", ""),
        key_figures=analysis.get("key_figures", ""),
        long_term_implications=analysis.get("long_term_implications", ""),
        narrative_mode=NarrativeMode.BASIC.value
        if report_data.get("narrative_prose")
        else None,
        narrative_prose=report_data.get("narrative_prose"),
        narrative_custom_pov=None,
        source_skeleton_id=None,
        source_context=None,
        report_model_provider=metadata.get("model_provider"),
        report_model_name=metadata.get("model_name"),
        narrative_model_provider=metadata.get("narrative_model_provider"),
        narrative_model_name=metadata.get("narrative_model_name"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_generation)
    await db.flush()

    logger.info(
        f"Converted report (order {report_order}) to generation "
        f"{new_generation_id} (type: {generation_type})"
    )


def _validate_import_structure(timeline_data: Dict[str, Any]) -> None:
    """
    Validate basic structure of import data.

    Args:
        timeline_data: Parsed JSON data

    Raises:
        InvalidFileFormatError: If structure is invalid
    """
    required_keys = ["format_version", "timeline"]

    for key in required_keys:
        if key not in timeline_data:
            raise InvalidFileFormatError(
                f"Invalid file format: missing required key '{key}'"
            )

    timeline_obj = timeline_data.get("timeline")
    if not isinstance(timeline_obj, dict):
        raise InvalidFileFormatError("Invalid file format: 'timeline' must be an object")

    # Check for either v1.0.0 or v2.0.0 required fields
    format_version = timeline_data.get("format_version")

    if format_version == "2.0.0":
        # v2.0.0 requires root_deviation and generations
        if "root_deviation" not in timeline_obj:
            raise InvalidFileFormatError(
                "Invalid v2.0.0 format: missing 'root_deviation'"
            )
        if "generations" not in timeline_obj:
            raise InvalidFileFormatError(
                "Invalid v2.0.0 format: missing 'generations'"
            )
    elif format_version == "1.0.0":
        # v1.0.0 requires deviation_point and reports
        if "deviation_point" not in timeline_obj:
            raise InvalidFileFormatError(
                "Invalid v1.0.0 format: missing 'deviation_point'"
            )
        if "reports" not in timeline_obj:
            raise InvalidFileFormatError("Invalid v1.0.0 format: missing 'reports'")
