"""
Service for multi-generation novella generation and series management.
"""

from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from app.db_models import TimelineNovellaDB, GenerationDB, TimelineDB
from app.models import NovellaGenerateRequest, NovellaContinueRequest, NovellaResponse
from app.agents.storyteller_agent import generate_novella_prose
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)


def _generation_to_dict(gen: GenerationDB) -> dict:
    """Extract structured report fields from a GenerationDB row."""
    return {
        "start_year": gen.start_year,
        "end_year": gen.end_year,
        "executive_summary": gen.executive_summary or "",
        "political_changes": gen.political_changes or "",
        "economic_impacts": gen.economic_impacts or "",
        "social_developments": gen.social_developments or "",
        "technological_shifts": gen.technological_shifts or "",
        "key_figures": gen.key_figures or "",
        "long_term_implications": gen.long_term_implications or "",
    }


def _get_model_info(model) -> tuple[str, str]:
    if model is None:
        return "google", "gemini-2.5-flash-lite"
    return type(model).__name__.lower(), getattr(model, "model_name", "unknown")


async def generate_novella(
    db: AsyncSession,
    timeline_id: str,
    request: NovellaGenerateRequest,
    model=None,
) -> NovellaResponse:
    """Generate a new standalone novella from selected generations.

    Args:
        db: Database session
        timeline_id: ID of the parent timeline
        request: Novella generation request with generation IDs and focus instructions
        model: Optional Pydantic-AI model instance to use for generation

    Returns:
        NovellaResponse: The created novella record

    Raises:
        NotFoundError: If timeline or any generation is not found
    """
    timeline = await db.get(TimelineDB, timeline_id)
    if not timeline:
        raise NotFoundError("Timeline not found", details={"timeline_id": timeline_id})

    generations = []
    for gid in request.generation_ids:
        gen = await db.get(GenerationDB, gid)
        if not gen:
            raise NotFoundError("Generation not found", details={"generation_id": gid})
        generations.append(_generation_to_dict(gen))

    output = await generate_novella_prose(
        generations=generations,
        deviation_date=str(timeline.root_deviation_date),
        deviation_description=timeline.root_deviation_description,
        scenario_type=timeline.scenario_type,
        focus_instructions=request.focus_instructions,
        series_order=1,
        model=model,
    )

    provider, model_name = _get_model_info(model)
    row = TimelineNovellaDB(
        timeline_id=timeline_id,
        series_id=None,
        series_order=1,
        generation_ids=request.generation_ids,
        title=output.title,
        content=output.content,
        focus_instructions=request.focus_instructions,
        model_provider=provider,
        model_name=model_name,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return NovellaResponse.model_validate(row)


async def generate_continuation(
    db: AsyncSession,
    source_novella_id: str,
    request: NovellaContinueRequest,
    model=None,
) -> NovellaResponse:
    """Generate a plot-continuous continuation of an existing novella.

    Backfills series_id on the source novella if it was standalone.

    Args:
        db: Database session
        source_novella_id: ID of the novella to continue from
        request: Continuation request with new generation IDs and focus instructions
        model: Optional Pydantic-AI model instance to use for generation

    Returns:
        NovellaResponse: The created continuation novella record

    Raises:
        NotFoundError: If source novella or any generation is not found
    """
    source = await db.get(TimelineNovellaDB, source_novella_id)
    if not source:
        raise NotFoundError("Novella not found", details={"novella_id": source_novella_id})

    timeline = await db.get(TimelineDB, source.timeline_id)

    # Determine series_id and next order
    if source.series_id is None:
        new_series_id = str(uuid4())
        await db.execute(
            update(TimelineNovellaDB)
            .where(TimelineNovellaDB.id == source_novella_id)
            .values(series_id=new_series_id, series_order=1)
        )
        next_order = 2
    else:
        new_series_id = source.series_id
        result = await db.execute(
            select(TimelineNovellaDB)
            .where(TimelineNovellaDB.series_id == new_series_id)
            .order_by(TimelineNovellaDB.series_order.desc())
            .limit(1)
        )
        last = result.scalar_one()
        next_order = last.series_order + 1

    generations = []
    for gid in request.generation_ids:
        gen = await db.get(GenerationDB, gid)
        if not gen:
            raise NotFoundError("Generation not found", details={"generation_id": gid})
        generations.append(_generation_to_dict(gen))

    output = await generate_novella_prose(
        generations=generations,
        deviation_date=str(timeline.root_deviation_date),
        deviation_description=timeline.root_deviation_description,
        scenario_type=timeline.scenario_type,
        focus_instructions=request.focus_instructions,
        previous_novella_title=source.title,
        previous_novella_content=source.content,
        series_order=next_order,
        model=model,
    )

    provider, model_name = _get_model_info(model)
    row = TimelineNovellaDB(
        timeline_id=source.timeline_id,
        series_id=new_series_id,
        series_order=next_order,
        generation_ids=request.generation_ids,
        title=output.title,
        content=output.content,
        focus_instructions=request.focus_instructions,
        model_provider=provider,
        model_name=model_name,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return NovellaResponse.model_validate(row)


async def get_timeline_novellas(db: AsyncSession, timeline_id: str) -> list[NovellaResponse]:
    """List all novellas for a given timeline, ordered by creation date.

    Args:
        db: Database session
        timeline_id: ID of the parent timeline

    Returns:
        List of NovellaResponse objects
    """
    result = await db.execute(
        select(TimelineNovellaDB)
        .where(TimelineNovellaDB.timeline_id == timeline_id)
        .order_by(TimelineNovellaDB.created_at)
    )
    rows = result.scalars().all()
    return [NovellaResponse.model_validate(r) for r in rows]


async def get_novella(db: AsyncSession, novella_id: str) -> NovellaResponse:
    """Get a single novella by ID.

    Args:
        db: Database session
        novella_id: ID of the novella to retrieve

    Returns:
        NovellaResponse object

    Raises:
        NotFoundError: If novella is not found
    """
    row = await db.get(TimelineNovellaDB, novella_id)
    if not row:
        raise NotFoundError("Novella not found", details={"novella_id": novella_id})
    return NovellaResponse.model_validate(row)


async def get_novella_series(db: AsyncSession, novella_id: str) -> list[NovellaResponse]:
    """Get all members of a novella's series in order.

    If the novella is standalone (no series_id), returns just that novella.

    Args:
        db: Database session
        novella_id: ID of any novella in the series

    Returns:
        List of NovellaResponse objects ordered by series_order

    Raises:
        NotFoundError: If novella is not found
    """
    row = await db.get(TimelineNovellaDB, novella_id)
    if not row:
        raise NotFoundError("Novella not found", details={"novella_id": novella_id})
    if not row.series_id:
        return [NovellaResponse.model_validate(row)]
    result = await db.execute(
        select(TimelineNovellaDB)
        .where(TimelineNovellaDB.series_id == row.series_id)
        .order_by(TimelineNovellaDB.series_order)
    )
    return [NovellaResponse.model_validate(r) for r in result.scalars().all()]


async def delete_novella(db: AsyncSession, novella_id: str) -> None:
    """Delete a novella and clean up series linkage if it was the last member.

    Args:
        db: Database session
        novella_id: ID of the novella to delete

    Raises:
        NotFoundError: If novella is not found
    """
    row = await db.get(TimelineNovellaDB, novella_id)
    if not row:
        raise NotFoundError("Novella not found", details={"novella_id": novella_id})

    series_id = row.series_id
    await db.delete(row)
    await db.flush()

    if series_id:
        result = await db.execute(
            select(TimelineNovellaDB).where(TimelineNovellaDB.series_id == series_id)
        )
        remaining = result.scalars().all()
        if len(remaining) == 1:
            await db.execute(
                update(TimelineNovellaDB)
                .where(TimelineNovellaDB.id == remaining[0].id)
                .values(series_id=None, series_order=1)
            )
    await db.commit()
