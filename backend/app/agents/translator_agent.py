"""
Translator Agent for LLM-based translation.

Provides context-aware, native-quality translation as an alternative to DeepL.
Supports multiple content types: audio scripts, generation reports, narrative prose.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model
from app.prompt_templates.template_loader import render_prompt
import logging

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content types that require different translation approaches."""
    PODCAST_SCRIPT = "podcast_script"
    DOCUMENTARY_SCRIPT = "documentary_script"
    NEWS_SCRIPT = "news_script"
    STORYTELLING_SCRIPT = "storytelling_script"
    GENERATION_REPORT = "generation_report"
    NARRATIVE_PROSE = "narrative_prose"
    GENERIC = "generic"


class TranslationOutput(BaseModel):
    """Output schema for translation agent."""
    translated_text: str = Field(
        ...,
        description="The translated text in the target language"
    )
    source_language: str = Field(
        ...,
        description="ISO 639-1 source language code (e.g., 'en')"
    )
    target_language: str = Field(
        ...,
        description="ISO 639-1 target language code (e.g., 'hu', 'de')"
    )
    word_count: int = Field(
        ...,
        description="Word count of the translated text"
    )


def create_translator_agent(model: Model) -> Agent[Any, TranslationOutput]:
    """
    Create translator agent with specialized system prompt.

    Args:
        model: Pydantic-AI model instance

    Returns:
        Configured translator agent
    """
    system_prompt = render_prompt("translator/translate.jinja2")

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            'max_tokens': 16384,  # Large for batch translations
            'temperature': 0.3,   # Lower for consistency and accuracy
        }
    )

    logger.info("Translator agent created")
    return agent


async def translate_with_llm(
    text: str,
    target_language: str,
    source_language: str = 'en',
    content_type: ContentType = ContentType.GENERIC,
    metadata: Optional[Dict[str, Any]] = None,
    model: Optional[Model] = None
) -> str:
    """
    Translate text using LLM agent.

    For batch translations (e.g., all report sections), pass concatenated text
    with clear delimiters. The agent will translate the entire batch at once.

    Args:
        text: Source text to translate
        target_language: Target language code (e.g., 'hu', 'de', 'es')
        source_language: Source language code (default: 'en')
        content_type: Type of content for context-aware translation
        metadata: Optional metadata for additional context
        model: Optional model override (uses default if not provided)

    Returns:
        Translated text

    Raises:
        Exception: If translation fails

    Example:
        >>> translated = await translate_with_llm(
        ...     text="Hello world",
        ...     target_language='hu',
        ...     content_type=ContentType.PODCAST_SCRIPT
        ... )
    """
    logger.info(
        f"Starting LLM translation: {source_language} -> {target_language}, "
        f"content_type={content_type.value}, length={len(text)} chars"
    )

    # Get model configuration
    if model is None:
        raise ValueError("Database session is required to get LLM model configuration")

    agent = create_translator_agent(model)

    # Get language names for prompts
    source_lang_name = get_language_name(source_language)
    target_lang_name = get_language_name(target_language)

    # Construct user prompt
    prompt = render_prompt(
        "translator/user_translate.jinja2",
        text=text,
        source_language=source_language,
        target_language=target_language,
        source_language_name=source_lang_name,
        target_language_name=target_lang_name,
        content_type=content_type.value,
        metadata=metadata or {}
    )

    logger.info(f"Translation prompt constructed: {len(prompt)} chars")

    # Run translation without output_type to get raw text response
    # Avoids Gemini's MALFORMED_FUNCTION_CALL errors with section markers
    result = await agent.run(prompt)

    # For pydantic-ai agents without output_type, use result.output
    translated = result.output

    logger.info(
        f"Translation complete: {len(translated)} chars"
    )

    return translated


def get_language_name(language_code: str) -> str:
    """
    Get language name from code.

    Args:
        language_code: ISO 639-1 language code

    Returns:
        Language name (e.g., 'Hungarian', 'German')
    """
    language_map = {
        'en': 'English',
        'hu': 'Hungarian',
        'de': 'German',
        'es': 'Spanish',
        'it': 'Italian',
        'fr': 'French',
        'pt': 'Portuguese',
        'pl': 'Polish',
        'nl': 'Dutch',
        'ja': 'Japanese',
        'zh': 'Chinese',
    }
    return language_map.get(language_code, language_code.upper())
