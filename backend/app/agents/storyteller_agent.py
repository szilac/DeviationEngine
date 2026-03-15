"""
Pydantic-AI agent for generating advanced narrative prose from structured reports.

This module implements a specialized storyteller agent that takes structured
historical analysis and transforms it into engaging narrative prose.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model
import logging

from app.models import StructuredReport, TimelineCreationRequest
from app.exceptions import ConfigurationError, AIGenerationError
from app.prompt_templates import render_prompt

# Configure logging
logger = logging.getLogger(__name__)


class NarrativeOutput(BaseModel):
    """
    Output model for narrative generation.

    Attributes:
        narrative_prose: The generated narrative prose (800-1200 words)
    """
    narrative_prose: str = Field(
        ...,
        description="Engaging narrative prose that brings the alternate history to life"
    )


class NovellaOutput(BaseModel):
    """
    Output model for novella generation.

    Attributes:
        title: AI-generated novella title (or series installment title)
        content: 2,000-5,000 words of literary prose with titled chapters
    """

    title: str = Field(..., description="Evocative title for this novella or installment")
    content: str = Field(..., description="Full novella prose with titled chapters")


# REMOVED: System prompts now in template files storyteller/system_omniscient.jinja2 and storyteller/system_custom_pov.jinja2


def create_storyteller_agent(
    use_custom_pov: bool = False,
    model: Optional[Model] = None
) -> Agent[None, NarrativeOutput]:
    """
    Create and configure the storyteller agent.

    Args:
        use_custom_pov: If True, use custom POV system prompt; otherwise omniscient
        model: Optional Pydantic-AI model instance. If None, will use default configuration.
               Typically provided by llm_service.create_pydantic_ai_model().

    Returns:
        Configured Agent instance for narrative generation

    Raises:
        ConfigurationError: If model is None and default configuration is unavailable
    """
    if model is None:
        # Fallback to legacy behavior for backward compatibility
        from pydantic_ai.models.google import GoogleModel

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable not set")
            raise ConfigurationError(
                "GEMINI_API_KEY environment variable is required",
                details={"missing_config": "GEMINI_API_KEY"}
            )

        # Create default Gemini model instance
        # Note: GoogleModel reads API key from GEMINI_API_KEY environment variable
        model = GoogleModel(model_name="gemini-2.5-flash-lite")
        logger.warning("Using legacy default model configuration. Consider using llm_service.")

    # Render appropriate system prompt from Jinja2 template
    template_name = "storyteller/system_custom_pov.jinja2" if use_custom_pov else "storyteller/system_omniscient.jinja2"
    system_prompt = render_prompt(template_name)

    # Create agent with provided/default model
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            'max_tokens': 16000,  # Increase output token limit for longer narratives
            'temperature': 0.8,   # Slightly higher creativity for storytelling
        },
        retries=3,  # Increase retries for structured output validation
    )

    mode = "custom POV" if use_custom_pov else "omniscient"
    logger.info(f"Storyteller agent created successfully (mode: {mode}, model: {type(model).__name__})")
    return agent


def create_novella_agent(model: Optional[Model] = None) -> Agent[None, NovellaOutput]:
    """
    Create and configure the novella storyteller agent.

    Args:
        model: Optional Pydantic-AI model instance.

    Returns:
        Configured Agent instance for novella generation
    """
    if model is None:
        from pydantic_ai.models.google import GoogleModel
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY environment variable is required",
                details={"missing_config": "GEMINI_API_KEY"},
            )
        model = GoogleModel(model_name="gemini-2.5-flash-lite")
        logger.warning("Using legacy default model for novella agent.")

    system_prompt = render_prompt("storyteller/system_novella.jinja2")

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            "max_tokens": 16000,
            "temperature": 0.85,
        },
        retries=3,
    )
    logger.info(f"Novella agent created (model: {type(model).__name__})")
    return agent


def construct_novella_prompt(
    generations: list[dict],
    deviation_date: str,
    deviation_description: str,
    scenario_type: str,
    focus_instructions: Optional[str] = None,
    previous_novella_title: Optional[str] = None,
    previous_novella_content: Optional[str] = None,
    series_order: int = 1,
) -> str:
    """
    Construct the prompt for novella generation using Jinja2 template.

    Args:
        generations: List of dicts with generation report fields
        deviation_date: Deviation point date string
        deviation_description: What changed
        scenario_type: Scenario type string
        focus_instructions: Optional user creative brief
        previous_novella_title: Title of previous installment (continuation only)
        previous_novella_content: Full text of previous installment (continuation only)
        series_order: 1-based position in series

    Returns:
        Rendered prompt string
    """
    return render_prompt(
        "storyteller/user_novella.jinja2",
        generations=generations,
        deviation_date=deviation_date,
        deviation_description=deviation_description,
        scenario_type=scenario_type,
        focus_instructions=focus_instructions,
        previous_novella_title=previous_novella_title,
        previous_novella_content=previous_novella_content,
        series_order=series_order,
    )


async def generate_novella_prose(
    generations: list[dict],
    deviation_date: str,
    deviation_description: str,
    scenario_type: str,
    focus_instructions: Optional[str] = None,
    previous_novella_title: Optional[str] = None,
    previous_novella_content: Optional[str] = None,
    series_order: int = 1,
    model: Optional[Model] = None,
) -> NovellaOutput:
    """
    Generate novella prose from structured generation data.

    Returns:
        NovellaOutput with title and content

    Raises:
        AIGenerationError: If generation fails
    """
    logger.info(f"Generating novella (series_order={series_order}, generations={len(generations)})")

    try:
        agent = create_novella_agent(model=model)
        prompt = construct_novella_prompt(
            generations=generations,
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            focus_instructions=focus_instructions,
            previous_novella_title=previous_novella_title,
            previous_novella_content=previous_novella_content,
            series_order=series_order,
        )
        result = await agent.run(prompt, output_type=NovellaOutput)
        logger.info(f"Novella generated: '{result.output.title}' ({len(result.output.content)} chars)")
        return result.output

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Novella generation failed: {e}", exc_info=True)
        raise AIGenerationError(
            "Failed to generate novella",
            details={"error": str(e), "error_type": type(e).__name__},
        ) from e


def construct_storyteller_prompt(
    structured_report: StructuredReport,
    deviation_request: TimelineCreationRequest,
    custom_pov: Optional[str] = None
) -> str:
    """
    Construct the prompt for narrative generation from structured analysis using Jinja2 template.

    Args:
        structured_report: The structured analytical report to narrativize
        deviation_request: Original deviation parameters for context
        custom_pov: Optional custom perspective instructions

    Returns:
        Formatted prompt string for the storyteller agent
    """
    end_year = deviation_request.deviation_date.year + deviation_request.simulation_years

    return render_prompt(
        "storyteller/user_narrative.jinja2",
        deviation_date=deviation_request.deviation_date,
        deviation_description=deviation_request.deviation_description,
        simulation_years=deviation_request.simulation_years,
        end_year=end_year,
        scenario_type=deviation_request.scenario_type.value,
        custom_pov=custom_pov,
        executive_summary=structured_report.executive_summary,
        political_changes=structured_report.political_changes,
        economic_impacts=structured_report.economic_impacts,
        social_developments=structured_report.social_developments,
        technological_shifts=structured_report.technological_shifts,
        key_figures=structured_report.key_figures,
        long_term_implications=structured_report.long_term_implications
    )


async def generate_narrative(
    structured_report: StructuredReport,
    deviation_request: TimelineCreationRequest,
    custom_pov: Optional[str] = None,
    model: Optional[Model] = None
) -> str:
    """
    Generate narrative prose from structured analysis.

    Args:
        structured_report: The structured report to narrativize
        deviation_request: Original deviation parameters
        custom_pov: Optional custom perspective instructions
        model: Optional Pydantic-AI model instance. If None, will use default configuration.

    Returns:
        Generated narrative prose string

    Raises:
        AIGenerationError: If narrative generation fails
    """
    logger.info(
        f"Generating narrative for {deviation_request.deviation_date}: "
        f"{'custom POV' if custom_pov else 'omniscient'}"
    )

    try:
        # Create agent with appropriate mode and model
        agent = create_storyteller_agent(use_custom_pov=bool(custom_pov), model=model)

        # Construct prompt
        prompt = construct_storyteller_prompt(
            structured_report,
            deviation_request,
            custom_pov
        )

        logger.debug(f"Storyteller prompt constructed. Length: {len(prompt)} chars")

        # Run agent
        logger.info("Calling Gemini API to generate narrative...")
        result = await agent.run(prompt, output_type=NarrativeOutput)

        narrative = result.output.narrative_prose

        logger.info(
            f"Successfully generated narrative. Length: {len(narrative)} chars",
            extra={
                "narrative_length": len(narrative),
                "word_count": len(narrative.split()),
                "has_custom_pov": custom_pov is not None
            }
        )

        return narrative

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(
            f"Error generating narrative: {e}",
            exc_info=True,
            extra={
                "deviation_date": str(deviation_request.deviation_date),
                "has_custom_pov": custom_pov is not None
            }
        )
        raise AIGenerationError(
            "Failed to generate narrative with storyteller agent",
            details={
                "error": str(e),
                "error_type": type(e).__name__
            }
        ) from e
