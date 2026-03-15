"""
NotebookLM Studio Integration Router.

Endpoints:
  GET  /api/notebooklm/available         — check nlm CLI install + auth
  POST /api/notebooklm/jobs              — start a generation job
  GET  /api/notebooklm/jobs              — list jobs (optional ?timeline_id=)
  GET  /api/notebooklm/jobs/{job_id}     — poll single job status
  DELETE /api/notebooklm/jobs/{job_id}   — cancel/delete job
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_models import NotebookLMJobDB
from app.models import NLMAvailabilityResponse, NotebookLMGenerateRequest, NotebookLMJob
from app.services import notebooklm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notebooklm", tags=["notebooklm"])


@router.get("/available", response_model=NLMAvailabilityResponse)
async def check_nlm_available():
    """Check if nlm CLI is installed and the user is authenticated."""
    result = await notebooklm_service.check_available()
    return NLMAvailabilityResponse(**result)


@router.post("/jobs", response_model=NotebookLMJob, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: NotebookLMGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a NotebookLM studio generation job.

    Returns immediately with the job record (status=pending).
    The pipeline runs in a background task — poll GET /jobs/{job_id} for status.
    """
    now = datetime.now(timezone.utc)
    job = NotebookLMJobDB(
        id=str(uuid4()),
        timeline_id=request.timeline_id,
        generation_ids=request.generation_ids,
        content_type=request.content_type,
        nlm_format=request.nlm_format.value,
        nlm_length=request.nlm_length.value,
        nlm_focus=request.nlm_focus,
        language_code=request.language_code,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Fire background task (non-blocking)
    asyncio.create_task(
        notebooklm_service.run_notebooklm_job(
            job_id=job.id,
            include_reports=request.include_reports,
            include_narratives=request.include_narratives,
        )
    )

    logger.info(f"NLM job created: {job.id} ({request.nlm_format}/{request.nlm_length})")
    return NotebookLMJob.model_validate(job)


@router.get("/jobs", response_model=List[NotebookLMJob])
async def list_jobs(
    timeline_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List all NotebookLM jobs, optionally filtered by timeline."""
    query = select(NotebookLMJobDB).order_by(NotebookLMJobDB.created_at.desc())
    if timeline_id:
        query = query.where(NotebookLMJobDB.timeline_id == timeline_id)

    result = await db.execute(query)
    jobs = result.scalars().all()
    return [NotebookLMJob.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=NotebookLMJob)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get current status of a NotebookLM job (use for polling)."""
    result = await db.execute(
        select(NotebookLMJobDB).where(NotebookLMJobDB.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return NotebookLMJob.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a job record (does not cancel in-progress NLM generation).

    Note: if a background job is still running when deleted, it will silently fail
    when it tries to update the now-missing row — this is acceptable for v1.
    """
    result = await db.execute(sql_delete(NotebookLMJobDB).where(NotebookLMJobDB.id == job_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    await db.commit()
    logger.info(f"NLM job deleted: {job_id}")
