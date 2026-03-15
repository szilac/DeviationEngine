"""
Novella API endpoints.

This module handles:
- Generating standalone novellas from timeline generations
- Continuing novellas into series
- Listing, retrieving, and deleting novellas
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import NovellaGenerateRequest, NovellaContinueRequest, NovellaResponse, AgentType
from app.services import llm_service
from app.services.novella_service import (
    generate_novella,
    generate_continuation,
    get_timeline_novellas,
    get_novella,
    get_novella_series,
    delete_novella,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["novellas"])


@router.post("/timelines/{timeline_id}/novellas", response_model=NovellaResponse)
async def generate_timeline_novella(
    timeline_id: str,
    request: NovellaGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new standalone novella from selected generations."""
    model = await llm_service.create_pydantic_ai_model_for_agent(db, AgentType.STORYTELLER)
    return await generate_novella(db, timeline_id, request, model=model)


@router.post("/novellas/{novella_id}/continue", response_model=NovellaResponse)
async def continue_novella(
    novella_id: str,
    request: NovellaContinueRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a plot-continuous continuation of an existing novella."""
    model = await llm_service.create_pydantic_ai_model_for_agent(db, AgentType.STORYTELLER)
    return await generate_continuation(db, novella_id, request, model=model)


@router.get("/timelines/{timeline_id}/novellas", response_model=list[NovellaResponse])
async def list_timeline_novellas(
    timeline_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all novellas for a timeline."""
    return await get_timeline_novellas(db, timeline_id)


@router.get("/novellas/{novella_id}", response_model=NovellaResponse)
async def get_single_novella(
    novella_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single novella by ID."""
    return await get_novella(db, novella_id)


@router.get("/novellas/{novella_id}/series", response_model=list[NovellaResponse])
async def get_novella_series_endpoint(
    novella_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all members of a novella's series in order."""
    return await get_novella_series(db, novella_id)


@router.delete("/novellas/{novella_id}", status_code=204)
async def delete_novella_endpoint(
    novella_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a novella. Cleans up series linkage if last member."""
    await delete_novella(db, novella_id)
