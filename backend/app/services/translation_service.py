"""
Translation service with caching using Generation JSON fields.

This module handles translation requests, caching translations in the Generation model's
JSON fields (report_translations and narrative_translations), and tracking usage statistics.

Supports both DeepL API and LLM-based translation.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timezone
from uuid import UUID
from enum import Enum
from pydantic_ai.models import Model
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.services.deepl_service import DeepLClient
from app.db_models import GenerationDB, TranslationUsageDB, TranslationConfigDB
from app.exceptions import (
    TranslationError,
    GenerationNotFoundError,
    TranslationQuotaExceededError,
    TranslationNotConfiguredError
)

logger = logging.getLogger(__name__)


class TranslationMethod(Enum):
    """Available translation methods."""
    DEEPL = "deepl"
    LLM = "llm"


class TranslationService:
    """Handles translation requests with caching in Generation JSON fields."""

    def __init__(self, deepl_client: DeepLClient):
        """
        Initialize translation service.

        Args:
            deepl_client: DeepL API client instance
        """
        self.deepl = deepl_client

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = 'en',
        method: TranslationMethod = TranslationMethod.DEEPL,
        content_type: str = 'generic',
        metadata: Optional[Dict[str, Any]] = None,
        db = None
    ) -> str:
        """
        Unified translation interface supporting both DeepL and LLM.

        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'hu', 'de', 'es')
            source_language: Source language code (default: 'en')
            method: Translation method (DEEPL or LLM)
            content_type: Type of content for LLM context
            metadata: Additional context for LLM translation
            db: Database session (required for LLM method)

        Returns:
            Translated text

        Raises:
            TranslationError: If translation fails
        """
        if method == TranslationMethod.DEEPL:
            # Use DeepL API
            try:
                return await self.deepl.translate_text(
                    text=text,
                    target_lang=target_language.upper()
                )
            except Exception as e:
                logger.error(f"DeepL translation error: {e}")
                raise TranslationError(f"DeepL translation failed: {str(e)}")
        else:
            # Use LLM translator
            from app.agents.translator_agent import translate_with_llm, ContentType
            from app.services.llm_service import create_pydantic_ai_model_for_agent
            from app.models import AgentType

            try:
                # Map string content type to enum
                content_type_enum = ContentType.GENERIC
                try:
                    content_type_enum = ContentType[content_type.upper()]
                except (KeyError, AttributeError):
                    logger.warning(f"Unknown content type '{content_type}', using GENERIC")

                # Get model for translator agent
                model = await create_pydantic_ai_model_for_agent(db, AgentType.TRANSLATOR)

                return await translate_with_llm(
                    text=text,
                    target_language=target_language,
                    source_language=source_language,
                    content_type=content_type_enum,
                    metadata=metadata,
                    model=model
                )
            except Exception as e:
                logger.error(f"LLM translation error: {e}")
                raise TranslationError(f"LLM translation failed: {str(e)}")

    async def translate_generation(
        self,
        db: AsyncSession,
        generation_id: UUID,
        target_language: str,
        method: TranslationMethod = TranslationMethod.DEEPL,
        model: Optional[Model] = None
    ) -> Dict[str, str]:
        """
        Translate all sections of a generation.

        Args:
            db: Database session
            generation_id: Generation UUID
            target_language: Target language code (e.g., 'hu', 'de', 'es', 'it')

        Returns:
            Dictionary of translated sections with keys:
            - executive_summary
            - political_changes
            - conflicts_and_wars
            - economic_impacts
            - social_developments
            - technological_shifts
            - key_figures
            - long_term_implications

        Raises:
            GenerationNotFoundError: If generation doesn't exist
            TranslationQuotaExceededError: If monthly quota exceeded
            TranslationError: If translation fails
        """
        # Normalize language code to lowercase
        target_lang = target_language.lower()

        # Get generation from database
        generation = await self._get_generation(db, generation_id)

        if not generation:
            raise GenerationNotFoundError(str(generation_id))

        # Check if translations already exist in JSON field (cache hit)
        if generation.report_translations:
            existing = generation.report_translations.get(target_lang)
            if existing:
                logger.info(
                    f"Cache hit: Using cached translation for generation {generation_id}, "
                    f"language {target_lang}"
                )
                return existing

        # Define sections to translate
        sections_to_translate = [
            "executive_summary",
            "political_changes",
            "conflicts_and_wars",
            "economic_impacts",
            "social_developments",
            "technological_shifts",
            "key_figures",
            "long_term_implications"
        ]

        translations = {}
        total_chars = 0

        # For LLM: batch translate all sections at once for consistency
        if method == TranslationMethod.LLM:
            # Concatenate all sections with unique delimiters that won't be translated
            batch_text = ""
            for field_name in sections_to_translate:
                source_text = getattr(generation, field_name)
                # Use a marker format that LLM won't translate
                batch_text += f"###SECTION:{field_name}###\n\n{source_text}\n\n###END:{field_name}###\n\n"
                total_chars += len(source_text)

            # Translate entire batch
            try:
                translated_batch = await self.translate_text(
                    text=batch_text,
                    target_language=target_lang,
                    source_language='en',
                    method=method,
                    content_type='generation_report',
                    metadata={'batch': True, 'sections': len(sections_to_translate)},
                    db=db
                )
            except Exception as e:
                logger.error(f"LLM batch translation error: {e}")
                raise TranslationError(f"Failed to translate generation: {str(e)}")

            # Parse translated batch back into sections using markers
            current_section = None
            current_content = []

            for line in translated_batch.split('\n'):
                if line.startswith('###SECTION:') and line.endswith('###'):
                    # Extract section name from marker
                    section_name = line[11:-3]  # Remove ###SECTION: and ###
                    if section_name in sections_to_translate:
                        current_section = section_name
                        current_content = []
                elif line.startswith('###END:') and line.endswith('###'):
                    # End of section - save it
                    if current_section:
                        translations[current_section] = '\n'.join(current_content).strip()
                        current_section = None
                        current_content = []
                elif current_section is not None:
                    # Content line - add to current section
                    current_content.append(line)

        else:
            # DeepL: translate sections individually
            for field_name in sections_to_translate:
                source_text = getattr(generation, field_name)

                try:
                    translated_text = await self.translate_text(
                        text=source_text,
                        target_language=target_lang,
                        source_language='en',
                        method=method,
                        content_type='generation_report',
                        metadata={'section_name': field_name.replace('_', ' ').title()},
                        db=db
                    )
                except Exception as e:
                    logger.error(f"Translation error for {field_name}: {e}")
                    raise TranslationError(f"Failed to translate {field_name}: {str(e)}")

                translations[field_name] = translated_text
                total_chars += len(source_text)

        # Store in generation.report_translations JSON field
        if generation.report_translations is None:
            generation.report_translations = {}

        generation.report_translations[target_lang] = translations

        # Update the generation in database
        await db.execute(
            update(GenerationDB)
            .where(GenerationDB.id == str(generation_id))
            .values(
                report_translations=generation.report_translations,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()

        # Update usage tracking
        await self._update_usage(db, total_chars)

        logger.info(
            f"Translated generation {generation_id} to {target_lang}, "
            f"{total_chars:,} characters"
        )

        return translations

    async def translate_narrative(
        self,
        db: AsyncSession,
        generation_id: UUID,
        target_language: str,
        method: TranslationMethod = TranslationMethod.DEEPL,
        model: Optional[Model] = None
    ) -> str:
        """
        Translate narrative prose for a generation using DeepL or LLM.

        Args:
            db: Database session
            generation_id: Generation UUID
            target_language: Target language code (e.g., 'hu', 'de', 'es', 'it')
            method: Translation method (DEEPL or LLM, default: DEEPL)

        Returns:
            Translated narrative text

        Raises:
            GenerationNotFoundError: If generation doesn't exist
            TranslationError: If generation has no narrative or translation fails
        """
        target_lang = target_language.lower()

        # Get generation from database
        generation = await self._get_generation(db, generation_id)

        if not generation:
            raise GenerationNotFoundError(str(generation_id))

        if not generation.narrative_prose:
            raise TranslationError(
                "Generation has no narrative prose to translate",
                details={"generation_id": str(generation_id)}
            )

        # Check if translation already exists in JSON field (cache hit)
        if generation.narrative_translations:
            existing = generation.narrative_translations.get(target_lang)
            if existing:
                logger.info(
                    f"Cache hit: Using cached narrative translation for generation {generation_id}, "
                    f"language {target_lang}"
                )
                return existing

        # Translate narrative
        try:
            translated_narrative = await self.translate_text(
                text=generation.narrative_prose,
                target_language=target_lang,
                source_language='en',
                method=method,
                content_type='narrative_prose',
                db=db
            )
        except Exception as e:
            logger.error(f"Translation error for narrative: {e}")
            raise TranslationError(f"Failed to translate narrative: {str(e)}")

        # Store in generation.narrative_translations JSON field
        if generation.narrative_translations is None:
            generation.narrative_translations = {}

        generation.narrative_translations[target_lang] = translated_narrative

        # Update the generation in database
        await db.execute(
            update(GenerationDB)
            .where(GenerationDB.id == str(generation_id))
            .values(
                narrative_translations=generation.narrative_translations,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()

        # Update usage tracking
        char_count = len(generation.narrative_prose)
        await self._update_usage(db, char_count)

        logger.info(
            f"Translated narrative for generation {generation_id} to {target_lang}, "
            f"{char_count:,} characters"
        )

        return translated_narrative

    async def get_usage_stats(
        self,
        db: AsyncSession,
        year_month: Optional[str] = None
    ) -> Dict:
        """
        Get translation usage statistics for a specific month.

        Args:
            db: Database session
            year_month: Month in YYYY-MM format (defaults to current month)

        Returns:
            Dictionary with usage statistics:
            - year_month: Month identifier
            - characters_used: Characters translated
            - characters_limit: Monthly character limit
            - percentage_used: Percentage of limit used
            - api_calls: Number of API calls made
        """
        if year_month is None:
            year_month = datetime.now(timezone.utc).strftime("%Y-%m")

        result = await db.execute(
            select(TranslationUsageDB).where(
                TranslationUsageDB.year_month == year_month
            )
        )
        usage = result.scalar_one_or_none()

        if usage:
            return {
                "year_month": usage.year_month,
                "characters_used": usage.characters_used,
                "characters_limit": usage.characters_limit,
                "percentage_used": round(
                    (usage.characters_used / usage.characters_limit * 100), 2
                ) if usage.characters_limit > 0 else 0,
                "api_calls": usage.api_calls
            }
        else:
            # No usage for this month yet
            return {
                "year_month": year_month,
                "characters_used": 0,
                "characters_limit": 500000,
                "percentage_used": 0.0,
                "api_calls": 0
            }

    async def _get_generation(
        self,
        db: AsyncSession,
        generation_id: UUID
    ) -> Optional[GenerationDB]:
        """
        Get generation from database.

        Args:
            db: Database session
            generation_id: Generation UUID

        Returns:
            GenerationDB instance or None if not found
        """
        result = await db.execute(
            select(GenerationDB).where(GenerationDB.id == str(generation_id))
        )
        return result.scalar_one_or_none()

    async def _update_usage(self, db: AsyncSession, character_count: int):
        """
        Update monthly usage statistics.

        Args:
            db: Database session
            character_count: Number of characters translated
        """
        now = datetime.now(timezone.utc)
        year_month = now.strftime("%Y-%m")

        # Get or create usage record for this month
        result = await db.execute(
            select(TranslationUsageDB).where(
                TranslationUsageDB.year_month == year_month
            )
        )
        usage = result.scalar_one_or_none()

        if usage:
            # Update existing record
            await db.execute(
                update(TranslationUsageDB)
                .where(TranslationUsageDB.year_month == year_month)
                .values(
                    characters_used=TranslationUsageDB.characters_used + character_count,
                    api_calls=TranslationUsageDB.api_calls + 1,
                    updated_at=now
                )
            )
        else:
            # Create new record
            new_usage = TranslationUsageDB(
                year_month=year_month,
                characters_used=character_count,
                api_calls=1,
                characters_limit=500000,
                created_at=now,
                updated_at=now
            )
            db.add(new_usage)

        await db.commit()


async def get_translation_service(db: AsyncSession) -> TranslationService:
    """
    Get configured translation service instance.

    Args:
        db: Database session

    Returns:
        TranslationService instance

    Raises:
        TranslationNotConfiguredError: If translation is not configured or disabled
    """
    # Get config from database
    result = await db.execute(
        select(TranslationConfigDB).where(TranslationConfigDB.id == 1)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise TranslationNotConfiguredError(
            "Translation service is not configured. Please add DeepL API key in settings."
        )

    if not config.enabled:
        raise TranslationNotConfiguredError(
            "Translation service is disabled. Please enable it in settings."
        )

    if not config.api_key or config.api_key == "not_configured":
        raise TranslationNotConfiguredError(
            "DeepL API key is not configured. Please add it in settings."
        )

    # Create DeepL client
    deepl_client = DeepLClient(
        api_key=config.api_key,
        tier=config.api_tier
    )

    return TranslationService(deepl_client)
