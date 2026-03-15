"""
Admin API endpoints for vector store management.

Provides endpoints for:
- Manual re-indexing of failed generations
- Vector store statistics
- Health checks
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.services.vector_store_service import get_vector_store_service

router = APIRouter(prefix="/api/vector-store", tags=["vector-store"])


class ReindexGenerationRequest(BaseModel):
    """Request to manually re-index a generation."""
    generation_id: str
    timeline_id: str
    force: bool = False


class ReindexGenerationResponse(BaseModel):
    """Response from re-indexing request."""
    success: bool
    message: str
    indexed_sections: Optional[int] = None
    failed_sections: Optional[list[str]] = None


class VectorStoreStatsResponse(BaseModel):
    """Vector store statistics."""
    enabled: bool
    embedding_model: Optional[str] = None
    collections: Optional[dict] = None
    index_records: Optional[dict] = None


class GenerationIndexStatusResponse(BaseModel):
    """Index status for a generation."""
    generation_id: str
    is_indexed: bool
    chunk_count: Optional[int] = None


@router.get("/stats", response_model=VectorStoreStatsResponse)
async def get_vector_store_stats(db: AsyncSession = Depends(get_db)):
    """
    Get vector store statistics.

    Returns collection sizes, index records, and configuration.
    """
    vector_service = get_vector_store_service()
    stats = await vector_service.get_stats(db)
    return stats


@router.get("/generation/{generation_id}/status", response_model=GenerationIndexStatusResponse)
async def check_generation_index_status(
    generation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a generation has been indexed in the vector store.

    Useful for checking if background indexing completed or failed.
    """
    vector_service = get_vector_store_service()

    if not vector_service.enabled:
        raise HTTPException(status_code=503, detail="Vector store is disabled")

    is_indexed = await vector_service.is_generation_indexed(generation_id, db)

    # Get chunk count if indexed
    chunk_count = None
    if is_indexed:
        from app.db_models import VectorStoreIndexDB
        from sqlalchemy import select

        result = await db.execute(
            select(VectorStoreIndexDB).where(
                VectorStoreIndexDB.content_type == "report",
                VectorStoreIndexDB.content_id == generation_id
            )
        )
        index_record = result.scalar_one_or_none()
        if index_record:
            chunk_count = index_record.chunk_count

    return GenerationIndexStatusResponse(
        generation_id=generation_id,
        is_indexed=is_indexed,
        chunk_count=chunk_count
    )


@router.post("/generation/reindex", response_model=ReindexGenerationResponse)
async def reindex_generation(
    request: ReindexGenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger re-indexing of a generation.

    Useful when:
    - Background indexing failed due to rate limits
    - Want to ensure generation is indexed before extension
    - Testing RAG retrieval

    Args:
        request: ReindexGenerationRequest with generation_id, timeline_id
        force: If true, re-index even if already indexed
    """
    vector_service = get_vector_store_service()

    if not vector_service.enabled:
        raise HTTPException(status_code=503, detail="Vector store is disabled")

    # Check if already indexed
    if not request.force:
        is_indexed = await vector_service.is_generation_indexed(request.generation_id, db)
        if is_indexed:
            return ReindexGenerationResponse(
                success=True,
                message="Generation already indexed. Use force=true to re-index.",
                indexed_sections=0
            )

    # Get generation data from database
    from app.db_models import GenerationDB
    from sqlalchemy import select

    result = await db.execute(
        select(GenerationDB).where(GenerationDB.id == request.generation_id)
    )
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    # Extract report sections
    report_sections = {
        "executive_summary": generation.executive_summary or "",
        "political_landscape": generation.political_landscape or "",
        "economic_overview": generation.economic_overview or "",
        "social_cultural": generation.social_cultural or "",
        "technological_progress": generation.technological_progress or "",
        "conflicts_wars": generation.conflicts_wars or "",
        "key_figures_leaders": generation.key_figures_leaders or "",
        "long_term_implications": generation.long_term_implications or ""
    }

    # Filter out empty sections
    report_sections = {k: v for k, v in report_sections.items() if v}

    # Index in background - FIXED: Added missing year_start and year_end parameters
    try:
        await vector_service.index_generation_background(
            generation_id=request.generation_id,
            timeline_id=request.timeline_id,
            report_sections=report_sections,
            narrative=generation.narrative_text,
            year_start=generation.year_start,  # FIXED: Added missing parameter
            year_end=generation.year_end,      # FIXED: Added missing parameter
            db=db
        )

        return ReindexGenerationResponse(
            success=True,
            message=f"Successfully indexed {len(report_sections)} sections",
            indexed_sections=len(report_sections)
        )

    except Exception as e:
        return ReindexGenerationResponse(
            success=False,
            message=f"Re-indexing failed: {str(e)}",
            indexed_sections=0,
            failed_sections=list(report_sections.keys())
        )


@router.post("/ground-truth/reindex")
async def reindex_ground_truth(
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger re-indexing of ground truth data.

    This runs the same indexing as the CLI script but via API.
    Use with caution as it may take several minutes and hit rate limits.
    """
    vector_service = get_vector_store_service()

    if not vector_service.enabled:
        raise HTTPException(status_code=503, detail="Vector store is disabled")

    try:
        stats = await vector_service.index_ground_truth_reports(
            ground_truth_dir="data/ground_truth",
            db=db,
            force_reindex=force
        )

        return {
            "success": True,
            "message": "Ground truth re-indexing completed",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Re-indexing failed: {str(e)}"
        )
