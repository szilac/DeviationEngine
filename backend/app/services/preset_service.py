"""
Audio script preset management service.

This service handles CRUD operations for script presets, including
both system presets (built-in) and user-created custom presets.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
import logging

from app.db_models import ScriptPresetDB
from app.models import ScriptPreset, PresetCreateRequest, PresetUpdateRequest
from app.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


# ===== GET PRESETS =====


async def get_all_presets(
    db: AsyncSession,
    include_inactive: bool = False
) -> List[ScriptPreset]:
    """
    Get all script presets, ordered by system first then by name.

    Args:
        db: Database session
        include_inactive: If True, include soft-deleted presets

    Returns:
        List of ScriptPreset models

    Example:
        >>> presets = await get_all_presets(db)
        >>> len([p for p in presets if p.is_system])
        4  # 4 system presets
    """
    query = select(ScriptPresetDB)

    if not include_inactive:
        query = query.where(ScriptPresetDB.is_active == 1)

    # Order: system presets first, then alphabetically
    query = query.order_by(
        ScriptPresetDB.is_system.desc(),
        ScriptPresetDB.name
    )

    result = await db.execute(query)
    db_presets = result.scalars().all()

    logger.debug(f"Retrieved {len(db_presets)} presets")
    return [ScriptPreset.model_validate(p) for p in db_presets]


async def get_presets_by_type(
    db: AsyncSession,
    script_type: str
) -> List[ScriptPreset]:
    """
    Get presets filtered by script type.

    Args:
        db: Database session
        script_type: Type to filter by (podcast, documentary, etc.)

    Returns:
        List of matching presets

    Example:
        >>> podcasts = await get_presets_by_type(db, "podcast")
        >>> all(p.script_type == "podcast" for p in podcasts)
        True
    """
    query = (
        select(ScriptPresetDB)
        .where(ScriptPresetDB.script_type == script_type)
        .where(ScriptPresetDB.is_active == 1)
        .order_by(ScriptPresetDB.is_system.desc(), ScriptPresetDB.name)
    )

    result = await db.execute(query)
    db_presets = result.scalars().all()

    logger.debug(f"Retrieved {len(db_presets)} presets for type '{script_type}'")
    return [ScriptPreset.model_validate(p) for p in db_presets]


async def get_preset_by_id(
    db: AsyncSession,
    preset_id: Union[str, UUID]
) -> ScriptPreset:
    """
    Get specific preset by ID.

    Args:
        db: Database session
        preset_id: Preset UUID

    Returns:
        ScriptPreset model

    Raises:
        NotFoundError: If preset doesn't exist

    Example:
        >>> preset = await get_preset_by_id(db, preset_id)
        >>> preset.name
        'Documentary Narration'
    """
    result = await db.execute(
        select(ScriptPresetDB).where(ScriptPresetDB.id == str(preset_id))
    )
    db_preset = result.scalar_one_or_none()

    if not db_preset:
        logger.warning(f"Preset not found: {preset_id}")
        raise NotFoundError(
            f"Script preset not found: {preset_id}",
            details={"preset_id": str(preset_id)}
        )

    return ScriptPreset.model_validate(db_preset)


async def get_system_presets(db: AsyncSession) -> List[ScriptPreset]:
    """
    Get only system (built-in) presets.

    Args:
        db: Database session

    Returns:
        List of system presets
    """
    query = (
        select(ScriptPresetDB)
        .where(ScriptPresetDB.is_system == 1)
        .where(ScriptPresetDB.is_active == 1)
        .order_by(ScriptPresetDB.name)
    )

    result = await db.execute(query)
    db_presets = result.scalars().all()

    return [ScriptPreset.model_validate(p) for p in db_presets]
