"""
Custom exception handlers for the FastAPI application.

This module defines how different types of exceptions are handled and formatted
in API responses.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import DeviationEngineError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all custom exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(DeviationEngineError)
    async def deviation_engine_error_handler(
        request: Request, exc: DeviationEngineError
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
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": type(exc).__name__,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """
        Handle ValueError exceptions (often from validation).

        Args:
            request: The incoming request
            exc: The raised exception

        Returns:
            JSON response with error details
        """
        logger.warning(f"Validation error: {str(exc)}", extra={"path": request.url.path})

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "ValidationError",
                "message": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred. Please try again later.",
            },
        )

    logger.info("Exception handlers registered")
