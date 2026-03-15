"""
Export service for timeline data with redesigned schema.

This module provides functionality to export timelines to JSON format (.devtl files)
with support for:
- Multiple generations (replaces reports)
- Timeline branching metadata
- Future translation and audio fields
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.timeline_service import get_timeline_by_id
from app.exceptions import TimelineNotFoundError

logger = logging.getLogger(__name__)

# Export format version (incremented for schema redesign)
EXPORT_FORMAT_VERSION = "2.0.0"  # Updated for generations + branching
APP_VERSION = "2.0.0"


async def export_timeline_to_json(
    db: AsyncSession, timeline_id: UUID
) -> Dict[str, Any]:
    """
    Export timeline to JSON-serializable dictionary.

    This function converts a complete timeline (including all generations,
    media, and branching metadata) into a portable JSON format that can be
    reimported into any Deviation Engine installation.

    Args:
        db: Database session
        timeline_id: UUID of the timeline to export

    Returns:
        dict: Complete timeline data in export format v2.0.0

    Raises:
        TimelineNotFoundError: If timeline does not exist

    Example:
        >>> export_data = await export_timeline_to_json(db, timeline_id)
        >>> # Save to .devtl file or return to user
    """
    # Fetch complete timeline with all generations and media
    db_timeline = await get_timeline_by_id(db, timeline_id)

    if not db_timeline:
        raise TimelineNotFoundError(str(timeline_id))

    logger.info(
        f"Exporting timeline {timeline_id} with {len(db_timeline.generations)} generations"
    )

    # Build export structure
    export_data = {
        "format_version": EXPORT_FORMAT_VERSION,
        "export_date": datetime.now(timezone.utc).isoformat(),
        "exported_by": f"DeviationEngine v{APP_VERSION}",
        "schema_version": "redesigned",  # Marker for new schema
        "timeline": _serialize_timeline(db_timeline),
    }

    logger.info(
        f"Successfully exported timeline {timeline_id}: "
        f"{len(db_timeline.generations)} generations, "
        f"format version {EXPORT_FORMAT_VERSION}"
    )

    return export_data


def _serialize_timeline(db_timeline) -> Dict[str, Any]:
    """
    Serialize timeline database model to export format.

    Args:
        db_timeline: TimelineDB instance with generations loaded

    Returns:
        dict: Serialized timeline data with branching metadata
    """
    # Branching metadata (NEW)
    branching = None
    if db_timeline.parent_timeline_id:
        branching = {
            "parent_timeline_id": db_timeline.parent_timeline_id,
            "branch_point_year": db_timeline.branch_point_year,
            "branch_deviation_description": db_timeline.branch_deviation_description,
        }

    # Root deviation
    root_deviation = {
        "deviation_date": db_timeline.root_deviation_date,
        "deviation_description": db_timeline.root_deviation_description,
        "scenario_type": db_timeline.scenario_type,
    }

    # Calculate total years from generations
    total_years = 0
    if db_timeline.generations:
        total_years = max(g.end_year for g in db_timeline.generations)

    # Serialize all generations (sorted by generation_order)
    generations = []
    for db_generation in sorted(
        db_timeline.generations, key=lambda g: g.generation_order
    ):
        generation_data = _serialize_generation(db_generation)
        generations.append(generation_data)

    return {
        "id": db_timeline.id,
        "branching": branching,
        "root_deviation": root_deviation,
        "total_years_simulated": total_years,
        "created_at": db_timeline.created_at.isoformat()
        if db_timeline.created_at
        else None,
        "updated_at": db_timeline.updated_at.isoformat()
        if db_timeline.updated_at
        else None,
        "generations": generations,
    }


def _serialize_generation(db_generation) -> Dict[str, Any]:
    """
    Serialize generation database model to export format.

    Args:
        db_generation: GenerationDB instance with media loaded

    Returns:
        dict: Serialized generation data including all fields
    """
    generation_data = {
        "id": db_generation.id,
        "generation_order": db_generation.generation_order,
        "generation_type": db_generation.generation_type,
        "period": {
            "start_year": db_generation.start_year,
            "end_year": db_generation.end_year,
            "period_years": db_generation.period_years,
        },
        "structured_report": {
            "executive_summary": db_generation.executive_summary,
            "political_changes": db_generation.political_changes,
            "conflicts_and_wars": db_generation.conflicts_and_wars,
            "economic_impacts": db_generation.economic_impacts,
            "social_developments": db_generation.social_developments,
            "technological_shifts": db_generation.technological_shifts,
            "key_figures": db_generation.key_figures,
            "long_term_implications": db_generation.long_term_implications,
        },
        "narrative": {
            "narrative_mode": db_generation.narrative_mode,
            "narrative_prose": db_generation.narrative_prose,
            "narrative_custom_pov": db_generation.narrative_custom_pov,
        },
        "source": {
            "source_skeleton_id": db_generation.source_skeleton_id,
            "source_context": db_generation.source_context,
        },
        "metadata": {
            "report_model_provider": db_generation.report_model_provider,
            "report_model_name": db_generation.report_model_name,
            "narrative_model_provider": db_generation.narrative_model_provider,
            "narrative_model_name": db_generation.narrative_model_name,
            "created_at": db_generation.created_at.isoformat()
            if db_generation.created_at
            else None,
            "updated_at": db_generation.updated_at.isoformat()
            if db_generation.updated_at
            else None,
        },
    }

    # Include media if present
    if db_generation.media:
        generation_data["media"] = [
            _serialize_media(media) for media in db_generation.media
        ]

    # Include translations if present (future feature)
    if db_generation.report_translations:
        generation_data["report_translations"] = db_generation.report_translations

    if db_generation.narrative_translations:
        generation_data["narrative_translations"] = (
            db_generation.narrative_translations
        )

    # Include audio if present (future feature)
    if db_generation.audio_script:
        generation_data["audio"] = {
            "audio_script": db_generation.audio_script,
            "audio_script_format": db_generation.audio_script_format,
            "audio_url": db_generation.audio_url,
            "audio_local_path": db_generation.audio_local_path,
            "audio_duration_seconds": db_generation.audio_duration_seconds,
            "audio_voice_model": db_generation.audio_voice_model,
            "audio_voice_settings": db_generation.audio_voice_settings,
            "audio_translations": db_generation.audio_translations,
            "audio_model_provider": db_generation.audio_model_provider,
            "audio_model_name": db_generation.audio_model_name,
        }

    return generation_data


def _serialize_media(db_media) -> Dict[str, Any]:
    """
    Serialize media database model to export format.

    Args:
        db_media: MediaDB instance

    Returns:
        dict: Serialized media data
    """
    return {
        "id": db_media.id,
        "media_type": db_media.media_type,
        "media_order": db_media.media_order,
        "prompt_text": db_media.prompt_text,
        "media_url": db_media.media_url,
        "media_local_path": db_media.media_local_path,
        "event_year": db_media.event_year,
        "title": db_media.title,
        "description": db_media.description,
        "is_user_added": bool(db_media.is_user_added),
        "is_user_modified": bool(db_media.is_user_modified),
        "model_provider": db_media.model_provider,
        "model_name": db_media.model_name,
        "created_at": db_media.created_at.isoformat() if db_media.created_at else None,
    }


def generate_export_filename(db_timeline) -> str:
    """
    Generate a user-friendly filename for the exported timeline.

    Creates a filename based on the deviation description and date,
    sanitized for filesystem compatibility.

    Args:
        db_timeline: TimelineDB instance

    Returns:
        str: Filename with .devtl extension

    Example:
        >>> generate_export_filename(timeline)
        'titanic_never_sank_1912_04_15.devtl'
    """
    # Extract deviation description and sanitize
    description = db_timeline.root_deviation_description[:50]  # Limit length

    # Replace spaces with underscores, remove special characters
    safe_description = "".join(
        c if c.isalnum() or c in (" ", "_", "-") else "" for c in description
    ).strip().replace(" ", "_").lower()

    # Truncate if too long
    if len(safe_description) > 40:
        safe_description = safe_description[:40]

    # Add date for uniqueness
    date_part = db_timeline.root_deviation_date.replace("-", "_")

    # Add branch indicator if this is a branched timeline
    branch_suffix = ""
    if db_timeline.parent_timeline_id:
        branch_suffix = f"_branch_y{db_timeline.branch_point_year}"

    # Combine parts
    filename = f"{safe_description}_{date_part}{branch_suffix}.devtl"

    return filename
