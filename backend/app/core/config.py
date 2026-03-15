"""
Application configuration and settings.

This module centralizes all application configuration including
CORS settings, environment variables, and feature flags.
"""

from functools import lru_cache
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_title: str = "Deviation Engine API"
    api_version: str = "1.0.0"
    api_description: str = (
        "Generate plausible alternate history timelines through AI-powered simulation"
    )

    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:3000",
    ]

    # Logging
    log_level: str = "INFO"
    log_format: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False

    def configure_logging(self) -> None:
        """Configure structured logging for the application."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format,
        )
        logger.info("Logging configured")

    def configure_cors(self, app: FastAPI) -> None:
        """
        Configure CORS middleware on the FastAPI app.

        Args:
            app: FastAPI application instance
        """
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"CORS configured for origins: {', '.join(self.cors_origins)}")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton).

    Returns:
        Settings: Application settings
    """
    return Settings()
