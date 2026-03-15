"""
Pydantic-AI agent for generating timeline skeletons.

This module implements the skeleton agent that generates a list of 15-25 key events
for an alternate history timeline. These events serve as an editable outline that
users can review and modify before generating the full report.
"""

import logging
import re
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent
from pydantic_ai.models import Model

from app.exceptions import AIGenerationError
from app.prompt_templates import render_prompt

# Configure logging
logger = logging.getLogger(__name__)


# Output models for skeleton agent
class SkeletonEventOutput(BaseModel):
    """Single event in the timeline skeleton."""
    event_date: str = Field(..., description="Date of the event (YYYY-MM-DD)")
    location: str = Field(..., description="Geographic location (city, country/region)")
    description: str = Field(
        ...,
        description="Brief description of the event and its significance (2-3 sentences)"
    )

    @field_validator("event_date", mode="before")
    @classmethod
    def extract_date(cls, v: str) -> str:
        """Extract YYYY-MM-DD from LLM output that may include extra text."""
        match = re.search(r"\d{4}-\d{2}-\d{2}", str(v))
        if match:
            return match.group(0)
        raise ValueError(f"Cannot extract a valid YYYY-MM-DD date from: {v!r}")


class SkeletonAgentOutput(BaseModel):
    """Complete skeleton output from the agent."""
    events: List[SkeletonEventOutput] = Field(
        ...,
        description="List of 15-25 key events in chronological order"
    )
    summary: str = Field(
        ...,
        description="Brief overview of the skeleton timeline (2-3 sentences)"
    )


# REMOVED: System prompt now in template file skeleton/system.jinja2


def create_skeleton_agent(model: Model, scenario_type: str) -> Agent:
    """
    Create and configure the skeleton generation agent.

    Args:
        model: Pydantic-AI model instance (required)
        scenario_type: Type of deviation scenario (for scenario-specific instructions)

    Returns:
        Configured Agent instance for skeleton generation
    """
    # Render system prompt from Jinja2 template with scenario_type
    system_prompt = render_prompt("skeleton/system.jinja2", scenario_type=scenario_type)

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
    )

    logger.info(f"Skeleton agent created successfully with model: {type(model).__name__}, scenario: {scenario_type}")
    return agent


def construct_skeleton_prompt(
    deviation_date: date,
    deviation_description: str,
    scenario_type: str,
    simulation_years: int,
    historical_context: str
) -> str:
    """
    Construct the user prompt for skeleton generation using Jinja2 template.

    Args:
        deviation_date: Date of the historical deviation
        deviation_description: Description of what changed
        scenario_type: Type of deviation scenario
        simulation_years: Number of years to simulate
        historical_context: Ground truth historical context

    Returns:
        Formatted prompt string for the agent
    """
    end_year = deviation_date.year + simulation_years

    return render_prompt(
        "skeleton/user_main.jinja2",
        historical_context=historical_context,
        deviation_date=deviation_date,
        deviation_description=deviation_description,
        scenario_type=scenario_type,
        simulation_years=simulation_years,
        end_year=end_year
    )


def construct_extension_skeleton_prompt(
    original_deviation_date: date,
    original_deviation_description: str,
    scenario_type: str,
    extension_start_year: int,
    extension_years: int,
    last_report_context: str,
    historical_context: str = ""
) -> str:
    """
    Construct the prompt for generating an extension skeleton using Jinja2 template.

    Args:
        original_deviation_date: Original deviation point date
        original_deviation_description: Original deviation description
        scenario_type: Type of deviation scenario
        extension_start_year: Year the extension starts (years from original deviation)
        extension_years: Number of additional years to simulate
        last_report_context: Summary of the last report's state
        historical_context: Ground truth historical context for extension period

    Returns:
        Formatted prompt string for the agent
    """
    original_end_year = original_deviation_date.year + extension_start_year
    new_end_year = original_end_year + extension_years

    return render_prompt(
        "skeleton/user_extension.jinja2",
        original_deviation_description=original_deviation_description,
        original_deviation_date=original_deviation_date,
        scenario_type=scenario_type,
        extension_start_year=extension_start_year,
        extension_years=extension_years,
        original_end_year=original_end_year,
        new_end_year=new_end_year,
        last_report_context=last_report_context,
        historical_context=historical_context
    )


async def generate_skeleton(
    deviation_date: date,
    deviation_description: str,
    scenario_type: str,
    simulation_years: int,
    historical_context: str,
    model: Model,
    is_extension: bool = False,
    extension_start_year: int = 0,
    last_report_context: str = ""
) -> SkeletonAgentOutput:
    """
    Generate a timeline skeleton using the AI agent.

    Args:
        deviation_date: Date of the historical deviation (or original deviation for extensions)
        deviation_description: Description of what changed
        scenario_type: Type of deviation scenario
        simulation_years: Number of years to simulate (extension years if is_extension=True)
        historical_context: Ground truth historical context
        model: Pydantic-AI model instance
        is_extension: Whether this is an extension skeleton (default: False)
        extension_start_year: If extension, years already simulated from deviation (default: 0)
        last_report_context: If extension, summary of the last report state (default: "")

    Returns:
        Generated skeleton with events and summary

    Raises:
        AIGenerationError: If skeleton generation fails
    """
    if is_extension:
        logger.info(
            f"Generating EXTENSION skeleton: extending {extension_start_year} year timeline "
            f"by {simulation_years} additional years"
        )
    else:
        logger.info(
            f"Generating skeleton for deviation on {deviation_date}: "
            f"{deviation_description[:50]}... ({simulation_years} years)"
        )

    try:
        # Create skeleton agent with scenario_type for specialized instructions
        logger.debug(f"Creating skeleton agent for scenario type: {scenario_type}")
        agent = create_skeleton_agent(model=model, scenario_type=scenario_type)

        # Get system prompt for logging (with scenario_type)
        system_prompt_text = render_prompt("skeleton/system.jinja2", scenario_type=scenario_type)

        # Construct appropriate prompt based on whether this is an extension
        if is_extension:
            logger.debug("Constructing EXTENSION skeleton prompt")
            prompt = construct_extension_skeleton_prompt(
                original_deviation_date=deviation_date,
                original_deviation_description=deviation_description,
                scenario_type=scenario_type,
                extension_start_year=extension_start_year,
                extension_years=simulation_years,
                last_report_context=last_report_context,
                historical_context=historical_context
            )
        else:
            logger.debug("Constructing skeleton prompt")
            prompt = construct_skeleton_prompt(
                deviation_date,
                deviation_description,
                scenario_type,
                simulation_years,
                historical_context
            )

        logger.debug(
            f"Prompt constructed. Length: {len(prompt)} chars, "
            f"Historical context: {len(historical_context)} chars"
        )

        # Save prompt for debugging if enabled
        try:
            from app.utils.prompt_logger import save_agent_prompt

            # Extract model info
            model_info = {
                'provider': getattr(model, 'name', 'unknown'),
                'model': str(model)
            }

            save_agent_prompt(
                agent_name='skeleton',
                system_prompt=system_prompt_text,
                user_prompt=prompt,
                model_info=model_info,
                context_info={
                    'source': 'RAG Ground Truth' if 'Context from Ground Truth' in historical_context else 'Legacy',
                    'tokens': len(historical_context.split()) * 1.3
                },
                metadata={
                    'deviation_date': str(deviation_date),
                    'simulation_years': simulation_years,
                    'is_extension': is_extension,
                    'extension_start_year': extension_start_year if is_extension else 'N/A'
                }
            )
        except Exception as e:
            logger.debug(f"Failed to save prompt for debugging: {e}")

        # Run agent with structured output
        logger.info("Calling LLM API to generate skeleton...")
        result = await agent.run(prompt, output_type=SkeletonAgentOutput)

        # Extract output
        output_data = result.output

        logger.info(
            f"Successfully generated skeleton with {len(output_data.events)} events",
            extra={
                "event_count": len(output_data.events),
                "summary_length": len(output_data.summary),
                "deviation_date": str(deviation_date),
                "simulation_years": simulation_years
            }
        )

        # Validate event count
        if len(output_data.events) < 15:
            logger.warning(
                f"Skeleton has fewer than 15 events ({len(output_data.events)}). "
                "This may indicate incomplete generation."
            )
        elif len(output_data.events) > 30:
            logger.warning(
                f"Skeleton has more than 30 events ({len(output_data.events)}). "
                "Trimming to first 30 events."
            )
            output_data.events = output_data.events[:30]

        return output_data

    except Exception as e:
        logger.error(
            f"Error generating skeleton: {e}",
            exc_info=True,
            extra={
                "deviation_date": str(deviation_date),
                "simulation_years": simulation_years
            }
        )
        raise AIGenerationError(
            "Failed to generate timeline skeleton with AI agent",
            details={
                "error": str(e),
                "error_type": type(e).__name__
            }
        ) from e
