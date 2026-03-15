"""
Pydantic-AI agent for in-character historical figure conversations.

This module handles conversational responses as a historical figure,
using the character's profile chunks and RAG-retrieved timeline context.
"""

import os
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model
import logging

from app.exceptions import ConfigurationError, AIGenerationError
from app.prompt_templates import render_prompt

logger = logging.getLogger(__name__)


class ImpersonatorOutput(BaseModel):
    """Output model for impersonator agent responses."""

    response: str = Field(
        ...,
        description="In-character response from the historical figure",
    )


def create_impersonator_agent(
    character_name: str,
    character_title: Optional[str],
    short_bio: str,
    role_summary: Optional[str],
    profile_chunks_text: str,
    character_year_context: int,
    model: Optional[Model] = None,
) -> Agent[Any, ImpersonatorOutput]:
    """
    Create an impersonator agent for a specific character.

    Args:
        character_name: Character's full name.
        character_title: Title or role.
        short_bio: Short biography summary.
        role_summary: Brief role description.
        profile_chunks_text: Formatted profile chunks text for the system prompt.
        character_year_context: The year the character is "speaking from".
        model: Optional Pydantic-AI model instance.

    Returns:
        Configured Agent for in-character conversation.

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
        logger.warning("Using legacy default model for impersonator.")

    system_prompt = render_prompt(
        "impersonator/system.jinja2",
        character_name=character_name,
        character_title=character_title,
        short_bio=short_bio,
        role_summary=role_summary or "",
        profile_chunks=profile_chunks_text,
        character_year_context=character_year_context,
    )

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            "max_tokens": 2048,
            "temperature": 0.8,
        },
        retries=2,
    )

    logger.info(f"Impersonator agent created for: {character_name} (year {character_year_context})")
    return agent


def format_profile_chunks(chunks: List[dict]) -> str:
    """
    Format character profile chunks into readable text for the system prompt.

    Args:
        chunks: List of chunk dicts with chunk_type, content, etc.

    Returns:
        Formatted text string.
    """
    parts = []
    for chunk in chunks:
        chunk_type = chunk.get("chunk_type", "unknown").replace("_", " ").title()
        content = chunk.get("content", "")
        parts.append(f"### {chunk_type}\n{content}")
    return "\n\n".join(parts)


async def generate_response(
    character_name: str,
    character_title: Optional[str],
    short_bio: str,
    role_summary: Optional[str],
    profile_chunks: List[dict],
    character_year_context: int,
    user_message: str,
    conversation_history: Optional[str] = None,
    context_chunks: Optional[str] = None,
    model: Optional[Model] = None,
) -> str:
    """
    Generate an in-character response to a user message.

    Args:
        character_name: Character's full name.
        character_title: Title or role.
        short_bio: Short biography.
        role_summary: Brief role description.
        profile_chunks: List of chunk dicts from CharacterChunkDB.
        character_year_context: Year the character speaks from.
        user_message: The user's message.
        conversation_history: Previous messages formatted as text.
        context_chunks: RAG-retrieved timeline context.
        model: Optional Pydantic-AI model instance.

    Returns:
        In-character response string.

    Raises:
        AIGenerationError: If response generation fails.
    """
    logger.info(f"Generating response as {character_name} (year {character_year_context})")

    try:
        profile_text = format_profile_chunks(profile_chunks)

        agent = create_impersonator_agent(
            character_name=character_name,
            character_title=character_title,
            short_bio=short_bio,
            role_summary=role_summary,
            profile_chunks_text=profile_text,
            character_year_context=character_year_context,
            model=model,
        )

        prompt = render_prompt(
            "impersonator/user_message.jinja2",
            user_message=user_message,
            conversation_history=conversation_history,
            context_chunks=context_chunks,
        )

        logger.debug(f"Impersonator prompt length: {len(prompt)} chars")

        result = await agent.run(prompt, output_type=ImpersonatorOutput)
        response_text = result.output.response

        logger.info(
            f"Generated response as {character_name}: {len(response_text)} chars"
        )

        return response_text

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(
            f"Error generating response as {character_name}: {e}", exc_info=True
        )
        raise AIGenerationError(
            f"Failed to generate in-character response for {character_name}",
            details={"error": str(e), "error_type": type(e).__name__},
        ) from e
