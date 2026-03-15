"""
Application startup and shutdown event handlers.

This module manages initialization and cleanup of application resources.
"""

import logging
from fastapi import FastAPI

from app.database import init_db
from app.services.history_service import get_history_service

logger = logging.getLogger(__name__)


def register_startup_handler(app: FastAPI) -> None:
    """
    Register startup event handler with the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.on_event("startup")
    async def startup_event():
        """
        Startup event handler.

        Initializes services and logs startup information.
        """
        logger.info("=" * 80)
        logger.info("Deviation Engine API Starting...")
        logger.info("=" * 80)

        try:
            # Initialize database
            logger.info("Initializing database...")
            await init_db()
            logger.info("Database initialized successfully")

            # Initialize history service
            history_service = get_history_service()
            available_reports = history_service.get_available_reports()
            logger.info(f"Loaded {len(available_reports)} historical reports")

            logger.info("API ready to accept requests")
        except Exception as e:
            logger.error(f"Error during startup: {e}", exc_info=True)
            raise


def register_shutdown_handler(app: FastAPI) -> None:
    """
    Register shutdown event handler with the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.on_event("shutdown")
    async def shutdown_event():
        """
        Shutdown event handler.

        Cleans up resources on shutdown.
        """
        logger.info("Deviation Engine API shutting down...")
        # Add any cleanup logic here if needed
        logger.info("Shutdown complete")
