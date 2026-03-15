"""
Custom exception classes for Deviation Engine.

This module defines domain-specific exceptions for better error handling
and user feedback throughout the application.
"""

from typing import Any, Dict, Optional


class DeviationEngineError(Exception):
    """Base exception for all Deviation Engine errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error context and details
            status_code: HTTP status code to return
        """
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class HistoricalContextError(DeviationEngineError):
    """Raised when historical context cannot be loaded or is invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=400
        )


class AIGenerationError(DeviationEngineError):
    """Raised when AI timeline generation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=500
        )


class NotFoundError(DeviationEngineError):
    """Raised when a requested resource cannot be found."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=404
        )


class TimelineNotFoundError(DeviationEngineError):
    """Raised when a requested timeline cannot be found."""

    def __init__(self, timeline_id: str):
        super().__init__(
            message=f"Timeline with ID {timeline_id} not found",
            details={"timeline_id": timeline_id},
            status_code=404
        )


class ValidationError(DeviationEngineError):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=422
        )


class ConfigurationError(DeviationEngineError):
    """Raised when there's a configuration problem (e.g., missing API keys)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=500
        )


class TranslationError(DeviationEngineError):
    """Base exception for translation errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=500
        )


class GenerationNotFoundError(DeviationEngineError):
    """Raised when a requested generation cannot be found."""

    def __init__(self, generation_id: str):
        super().__init__(
            message=f"Generation with ID {generation_id} not found",
            details={"generation_id": generation_id},
            status_code=404
        )


class TranslationQuotaExceededError(TranslationError):
    """Raised when monthly DeepL translation quota is exceeded."""

    def __init__(self, chars_used: int, chars_limit: int):
        super().__init__(
            message=f"Translation quota exceeded: {chars_used:,}/{chars_limit:,} characters used this month",
            details={
                "chars_used": chars_used,
                "chars_limit": chars_limit,
                "percentage": round((chars_used / chars_limit * 100), 2) if chars_limit > 0 else 0
            }
        )
        self.status_code = 403


class TranslationNotConfiguredError(TranslationError):
    """Raised when translation service is not properly configured."""

    def __init__(self, message: str = "Translation service is not configured"):
        super().__init__(
            message=message,
            details={"hint": "Please configure DeepL API key in settings"}
        )
        self.status_code = 503