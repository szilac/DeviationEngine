"""
Main FastAPI application entry point for Deviation Engine.

This module sets up the FastAPI application with CORS middleware
and implements all API endpoints for timeline generation and retrieval.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from dotenv import load_dotenv
from pathlib import Path
import logging
import os

from app.database import init_db, AsyncSessionLocal
from app.services.history_service import get_history_service
from app.services.llm_service import get_current_llm_config

from app.exceptions import (
    DeviationEngineError,
)
from app.middleware import RequestLoggingMiddleware
# NEW: Import routers for refactoring
from app.api import health as health_router
from app.api import historical as historical_router
from app.api import translation as translation_router
from app.api import settings as settings_router
from app.api import import_export as import_export_router
from app.api import images as images_router
from app.api import skeletons as skeletons_router
from app.api import timelines as timelines_router
from app.api import audio as audio_router
from app.api import vector_store as vector_store_router
from app.api import characters as characters_router
from app.api import ripple_maps as ripple_maps_router
from app.api import notebooklm as notebooklm_router
from app.api import novellas as novellas_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title="Deviation Engine API",
    description="Generate plausible alternate history timelines through AI-powered simulation",
    version="1.0.0",
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000"],  # Docker nginx (port 80) and Vite dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the audio directory for serving generated files
audio_dir = Path(__file__).parent.parent / "data" / "audio"
if not audio_dir.exists():
    audio_dir.mkdir(parents=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

# NEW: Include routers for refactoring (keep old endpoints for now)
app.include_router(health_router.router)
app.include_router(historical_router.router)
app.include_router(translation_router.router)
app.include_router(settings_router.router)
app.include_router(import_export_router.router)
app.include_router(images_router.router)
app.include_router(skeletons_router.router)
app.include_router(timelines_router.router)
app.include_router(audio_router.router)
app.include_router(vector_store_router.router)  # Vector Store / RAG Admin
app.include_router(characters_router.router)  # Historical Figure Chat
app.include_router(ripple_maps_router.router)  # Ripple Map
app.include_router(notebooklm_router.router)  # NotebookLM Studio Integration
app.include_router(novellas_router.router)  # Multi-generation Novella

# Serve React frontend (production build via start.py)
# IMPORTANT: This catch-all must stay AFTER all app.include_router() calls and
# StaticFiles mounts — FastAPI matches routes in registration order.
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        # Serve existing static files directly; fall back to index.html for SPA routes
        candidate = _frontend_dist / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_frontend_dist / "index.html"))


# Custom exception handlers
@app.exception_handler(DeviationEngineError)
async def deviation_engine_error_handler(
    request: Request,
    exc: DeviationEngineError
) -> JSONResponse:
    """
    Handle custom application exceptions.

    Args:
        request: The incoming request
        exc: The raised exception

    Returns:
        JSON response with error details
    """
    logger.error(
        f"Application error: {exc.message}",
        extra={
            "error_type": type(exc).__name__,
            "details": exc.details,
            "path": request.url.path,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request,
    exc: ValueError
) -> JSONResponse:
    """
    Handle ValueError exceptions (often from validation).

    Args:
        request: The incoming request
        exc: The raised exception

    Returns:
        JSON response with error details
    """
    logger.warning(
        f"Validation error: {str(exc)}",
        extra={"path": request.url.path}
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "ValidationError",
            "message": str(exc),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Args:
        request: The incoming request
        exc: The raised exception

    Returns:
        JSON response with generic error message
    """
    logger.exception(
        f"Unexpected error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please try again later.",
        }
    )

# Database storage (replaces in-memory storage)
# NOTE: Health endpoints (/, /api/health) moved to app/api/health.py
# NOTE: Historical endpoints (/api/historical-events, /api/ground-truth-reports*) moved to app/api/historical.py
# NOTE: Translation endpoints (/api/generations/*/translate, /api/translation/*) moved to app/api/translation.py
# NOTE: Image endpoints (9 total: /api/image-prompts/*, /api/images/*, /api/timelines/*/images) moved to app/api/images.py
# NOTE: Import/Export endpoints (/api/timeline/{id}/export, /api/timeline/import) moved to app/api/import_export.py
# NOTE: Settings endpoints (/api/llm-config, /api/llm-models, /api/llm/agents/*) moved to app/api/settings.py
# NOTE: Audio endpoints (20 total) moved to app/api/audio.py
# NOTE: Skeleton endpoints ( total) moved to app/api/skeleton.py
# NOTE: Timeline endpoints (7 total: /api/generate-timeline, /api/timelines, /api/timeline/*, /api/extend-timeline) moved to app/api/timelines.py


# ============================================================================
# Startup/Shutdown Event Handlers
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.

    Initializes services and logs startup information.
    """
    logger.info("="*80)
    logger.info("Deviation Engine API Starting...")
    logger.info("="*80)

    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")

        # Load API keys from database into environment so services like
        # vector_store_service can access them before the first LLM request
        try:
            async with AsyncSessionLocal() as db:
                config = await get_current_llm_config(db)
                if config.api_key_google and not os.getenv("GEMINI_API_KEY"):
                    os.environ["GEMINI_API_KEY"] = config.api_key_google
                    logger.info("Loaded GEMINI_API_KEY from database config")
                if config.api_key_openrouter and not os.getenv("OPENROUTER_API_KEY"):
                    os.environ["OPENROUTER_API_KEY"] = config.api_key_openrouter
                    logger.info("Loaded OPENROUTER_API_KEY from database config")
        except Exception as key_err:
            logger.warning(f"Could not pre-load API keys from database: {key_err}")

        # Initialize history service
        history_service = get_history_service()
        available_reports = history_service.get_available_reports()
        logger.info(f"Loaded {len(available_reports)} historical reports")

        logger.info("API ready to accept requests")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler.

    Cleans up resources on shutdown.
    """
    logger.info("Deviation Engine API shutting down...")
