"""
Ripple Maps Router — causal web visualization endpoints.

Provides CRUD and generation endpoints for timeline ripple maps.
One ripple map per timeline; grows as generations are added.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AIGenerationError, NotFoundError, ValidationError
from app.models import (
    AddGenerationsRequest,
    CausalEdge,
    CausalNode,
    RippleMapGenerateRequest,
    RippleMapResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ripple-maps"])


def _to_response(ripple_map) -> RippleMapResponse:
    """Convert a RippleMapDB record to RippleMapResponse."""
    nodes = [CausalNode(**n) for n in (ripple_map.nodes or [])]
    edges = [CausalEdge(**e) for e in (ripple_map.edges or [])]

    return RippleMapResponse(
        id=ripple_map.id,
        timeline_id=ripple_map.timeline_id,
        nodes=nodes,
        edges=edges,
        included_generation_ids=ripple_map.included_generation_ids or [],
        total_nodes=ripple_map.total_nodes,
        dominant_domain=ripple_map.dominant_domain,
        max_ripple_depth=ripple_map.max_ripple_depth,
        model_provider=ripple_map.model_provider,
        model_name=ripple_map.model_name,
        created_at=ripple_map.created_at,
        updated_at=ripple_map.updated_at,
    )


@router.post(
    "/api/timelines/{timeline_id}/ripple-map",
    response_model=RippleMapResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate ripple map",
    description="Generate a causal web visualization for a timeline from selected generations.",
)
async def generate_ripple_map(
    timeline_id: str,
    request: RippleMapGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> RippleMapResponse:
    """Generate a new ripple map for a timeline."""
    from app.services import ripple_map_service

    try:
        ripple_map = await ripple_map_service.generate_ripple_map(
            db=db,
            timeline_id=timeline_id,
            generation_ids=request.generation_ids,
        )
        return _to_response(ripple_map)

    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except AIGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error generating ripple map: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate ripple map",
        )


@router.get(
    "/api/timelines/{timeline_id}/ripple-map",
    response_model=RippleMapResponse,
    summary="Get ripple map",
    description="Retrieve the causal web visualization for a timeline.",
)
async def get_ripple_map(
    timeline_id: str,
    db: AsyncSession = Depends(get_db),
) -> RippleMapResponse:
    """Get the ripple map for a timeline."""
    from app.services import ripple_map_service

    ripple_map = await ripple_map_service.get_ripple_map(db=db, timeline_id=timeline_id)
    if not ripple_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ripple map found for timeline {timeline_id}",
        )
    return _to_response(ripple_map)


@router.post(
    "/api/timelines/{timeline_id}/ripple-map/add-generations",
    response_model=RippleMapResponse,
    summary="Add generations to ripple map",
    description="Extend an existing ripple map with additional timeline generations.",
)
async def add_generations(
    timeline_id: str,
    request: AddGenerationsRequest,
    db: AsyncSession = Depends(get_db),
) -> RippleMapResponse:
    """Add new generations to an existing ripple map."""
    from app.services import ripple_map_service

    try:
        ripple_map = await ripple_map_service.add_generations(
            db=db,
            timeline_id=timeline_id,
            generation_ids=request.generation_ids,
        )
        return _to_response(ripple_map)

    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AIGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error adding generations to ripple map: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add generations to ripple map",
        )


@router.delete(
    "/api/timelines/{timeline_id}/ripple-map",
    summary="Delete ripple map",
    description="Delete a timeline's ripple map to allow regeneration.",
)
async def delete_ripple_map(
    timeline_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete the ripple map for a timeline."""
    from app.services import ripple_map_service

    deleted = await ripple_map_service.delete_ripple_map(db=db, timeline_id=timeline_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ripple map found for timeline {timeline_id}",
        )
    return {"deleted": True}
