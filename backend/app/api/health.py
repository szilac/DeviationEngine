"""
Health and info API endpoints.

This module handles:
- Root endpoint (/) - API information
- Health check endpoint (/api/health) - Service health status
"""

from fastapi import APIRouter
import logging

from app.models import HealthResponse

logger = logging.getLogger(__name__)

# Create router without prefix (root endpoint is at /)
router = APIRouter(tags=["info"])



@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        HealthResponse: Health status and version information
    """
    return HealthResponse(status="healthy", version="1.0.0")
