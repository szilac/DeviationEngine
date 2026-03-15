"""
Pydantic-AI agent for generating historical character profiles.

This module creates structured character profiles from timeline content,
enabling the Impersonator Agent to convincingly portray historical figures.
The output includes chunks suitable for vectorization and RAG retrieval.
"""

import os
from typing import Any, Optional
from pydantic_ai import Agent
from pydantic_ai.models import Model
import logging

from app.models import CharacterProfileOutput
from app.exceptions import ConfigurationError, AIGenerationError
from app.prompt_templates import render_prompt

logger = logging.getLogger(__name__)


def create_character_profiler_agent(
    model: Optional[Model] = None,
) -> Agent[Any, CharacterProfileOutput]:
    """
    Create the character profiler agent.

    Args:
        model: Optional Pydantic-AI model instance. If None, uses default Gemini.

    Returns:
        Configured Agent for character profile generation.

    Raises:
        ConfigurationError: If model is None and default config unavailable.
    """
    if model is None:
        from pydantic_ai.models.google import GoogleModel

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY environment variable is required",
                details={"missing_config": "GEMINI_API_KEY"},
            )
        model = GoogleModel(model_name="gemini-2.5-flash")
        logger.warning("Using legacy default model for character profiler.")

    system_prompt = render_prompt("character_profiler/system.jinja2")

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            "max_tokens": 8192,
            "temperature": 0.7,
        },
        retries=3,
    )

    logger.info(f"Character profiler agent created with model: {type(model).__name__}")
    return agent


async def generate_character_profile(
    character_name: str,
    character_title: Optional[str],
    character_era: Optional[str],
    timeline_content: str,
    deviation_date: str,
    deviation_description: str,
    scenario_type: str,
    existing_biography: Optional[str] = None,
    model: Optional[Model] = None,
) -> CharacterProfileOutput:
    """
    Generate a structured character profile with chunks for vectorization.

    Args:
        character_name: Full name of the historical figure.
        character_title: Title or role.
        character_era: Active time period string (e.g., "1900-1940").
        timeline_content: Combined timeline content for context.
        deviation_date: Timeline deviation date.
        deviation_description: What changed.
        scenario_type: Type of scenario.
        existing_biography: Biography text from the nearest existing profile,
            used as a consistency reference. None if no prior profile exists.
        model: Optional Pydantic-AI model instance.

    Returns:
        CharacterProfileOutput with chunks, short_bio, role_summary, etc.

    Raises:
        AIGenerationError: If profile generation fails.
    """
    logger.info(f"Generating character profile for: {character_name}")

    try:
        agent = create_character_profiler_agent(model=model)

        prompt = render_prompt(
            "character_profiler/user_generate.jinja2",
            character_name=character_name,
            character_title=character_title,
            character_era=character_era,
            timeline_content=timeline_content,
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            existing_biography=existing_biography,
        )

        logger.debug(f"Character profile prompt length: {len(prompt)} chars")

        result = await agent.run(prompt, output_type=CharacterProfileOutput)
        output = result.output

        logger.info(
            f"Generated profile for {character_name}: "
            f"{len(output.chunks)} chunks, "
            f"importance: {output.importance_score:.2f}"
        )

        return output

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Error generating character profile for {character_name}: {e}", exc_info=True)
        raise AIGenerationError(
            f"Failed to generate character profile for {character_name}",
            details={"error": str(e), "error_type": type(e).__name__},
        ) from e
