"""
DeepL API client for translation services.

This module provides a simple async client for interacting with the DeepL Translation API.
Supports both free and pro tiers.
"""

import httpx
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DeepLClient:
    """Simple DeepL API client for translation."""

    def __init__(self, api_key: str, tier: str = "free"):
        """
        Initialize DeepL client.

        Args:
            api_key: DeepL API authentication key (ends with :fx for free tier)
            tier: API tier ('free' or 'pro')
        """
        self.api_key = api_key
        self.tier = tier
        self.base_url = (
            "https://api-free.deepl.com/v2" if tier == "free"
            else "https://api.deepl.com/v2"
        )
        logger.info(f"DeepL client initialized with {tier} tier")

    async def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "EN"
    ) -> str:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'HU', 'DE', 'ES', 'IT')
            source_lang: Source language code (default: 'EN')

        Returns:
            Translated text

        Raises:
            httpx.HTTPStatusError: If API request fails
            httpx.TimeoutException: If request times out
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/translate",
                    headers={
                        "Authorization": f"DeepL-Auth-Key {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": [text],
                        "target_lang": target_lang.upper(),
                        "source_lang": source_lang.upper()
                    }
                )

                response.raise_for_status()
                data = response.json()

                translated_text = data["translations"][0]["text"]
                logger.debug(
                    f"Translated {len(text)} chars from {source_lang} to {target_lang}"
                )

                return translated_text

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"DeepL API error: {e.response.status_code} - {e.response.text}"
                )
                raise
            except httpx.TimeoutException:
                logger.error("DeepL API request timed out")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during translation: {e}")
                raise

    async def get_usage(self) -> Dict:
        """
        Get current API usage statistics from DeepL.

        Returns:
            Dictionary with character_count and character_limit

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/usage",
                    headers={
                        "Authorization": f"DeepL-Auth-Key {self.api_key}"
                    }
                )

                response.raise_for_status()
                usage_data = response.json()

                logger.debug(f"DeepL usage: {usage_data}")
                return usage_data

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"DeepL usage API error: {e.response.status_code} - {e.response.text}"
                )
                raise
            except Exception as e:
                logger.error(f"Error fetching DeepL usage: {e}")
                raise

    async def check_connection(self) -> bool:
        """
        Test the connection to DeepL API.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get usage info as a connection test
            await self.get_usage()
            logger.info("DeepL API connection test successful")
            return True
        except Exception as e:
            logger.error(f"DeepL API connection test failed: {e}")
            return False
