"""
Pydantic-AI agent for generating alternate history timelines.

This module implements the AI agent that generates plausible alternate
historical timelines using LLM
"""

import os
from typing import Any, Optional
from pydantic_ai import Agent, ToolOutput
from pydantic_ai.models import Model
import logging

from app.models import TimelineOutput, TimelineCreationRequest, Timeline, TimelineExtensionRequest
from app.exceptions import ConfigurationError, AIGenerationError
from app.prompt_templates import render_prompt

# Configure logging
logger = logging.getLogger(__name__)

# REMOVED: System prompt now in template file historian/system_main.jinja2


def create_historian_agent(
    model: Optional[Model] = None,
    scenario_type: str = "local_deviation"
) -> Agent[Any, TimelineOutput]:
    """
    Create and configure the Pydantic-AI historian agent.

    Args:
        model: Optional Pydantic-AI model instance. If None, will use default configuration.
               Typically provided by llm_service.create_pydantic_ai_model().
        scenario_type: Type of scenario (local_deviation, global_deviation, reality_fracture, geological_shift, external_intervention)

    Returns:
        Configured Agent instance for timeline generation

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
                "GEMINI_API_KEY environment variable is required. "
                "Please set it in your .env file.",
                details={"missing_config": "GEMINI_API_KEY"}
            )

        # Create default Gemini model instance
        # Note: GoogleModel reads API key from GEMINI_API_KEY environment variable
        model = GoogleModel(model_name="gemini-2.5-flash")
        logger.warning("Using legacy default model configuration. Consider using llm_service.")

    # Render system prompt from Jinja2 template
    system_prompt = render_prompt(
        "historian/system_main.jinja2",
        scenario_type=scenario_type
    )

    # Create agent with system prompt and provided/default model
    # Set higher token limits to avoid truncation
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            'max_tokens': 8192,  # Increase output token limit
            'temperature': 0.7,   # Consistent creativity
        },
        retries=3,  # Increase retries for complex structured output validation
    )

    logger.info(
        f"Historian agent created successfully with model: {type(model).__name__}, "
        f"scenario_type: {scenario_type}"
    )
    return agent


def construct_generation_prompt(
    deviation_request: TimelineCreationRequest,
    historical_context: str
) -> str:
    """
    Construct the user prompt for timeline generation using Jinja2 template.

    Combines the deviation parameters with historical ground truth context
    to create a comprehensive prompt for the AI agent.

    Args:
        deviation_request: The deviation parameters from the user
        historical_context: Combined historical reports providing context

    Returns:
        Formatted prompt string for the AI agent
    """
    end_year = deviation_request.deviation_date.year + deviation_request.simulation_years

    # Determine if historian should generate narrative
    # BASIC: historian generates narrative
    # ADVANCED: historian skips narrative (storyteller generates it later)
    # NONE: no narrative at all
    from app.models import NarrativeMode
    include_narrative = deviation_request.narrative_mode == NarrativeMode.BASIC

    return render_prompt(
        "historian/user_generation.jinja2",
        historical_context=historical_context,
        deviation_date=deviation_request.deviation_date,
        deviation_description=deviation_request.deviation_description,
        scenario_type=deviation_request.scenario_type.value,
        simulation_years=deviation_request.simulation_years,
        end_year=end_year,
        include_narrative=include_narrative
    )


async def generate_timeline(
    deviation_request: TimelineCreationRequest,
    historical_context: str,
    model: Optional[Model] = None,
) -> TimelineOutput:
    """
    Generate an alternate history timeline using the AI agent.

    Args:
        deviation_request: User's deviation parameters
        historical_context: Historical ground truth context
        model: Optional Pydantic-AI model instance. If None, will use default configuration.

    Returns:
        Generated timeline output with all sections

    Raises:
        Exception: If AI generation fails
    """
    logger.info(
        f"Generating timeline for deviation on {deviation_request.deviation_date}: "
        f"{deviation_request.deviation_description[:50]}..."
    )

    try:
        # Create agent with the provided model and scenario type
        logger.debug("Creating historian agent")
        agent = create_historian_agent(
            model=model,
            scenario_type=deviation_request.scenario_type.value
        )

        # Get system prompt for logging (before constructing user prompt)
        system_prompt_text = render_prompt(
            "historian/system_main.jinja2",
            scenario_type=deviation_request.scenario_type.value
        )

        # Construct prompt
        logger.debug("Constructing generation prompt")
        prompt = construct_generation_prompt(deviation_request, historical_context)

        logger.debug(
            f"Prompt constructed. Length: {len(prompt)} chars, "
            f"Historical context: {len(historical_context)} chars"
        )

        # Save prompt for debugging if enabled
        try:
            from app.utils.prompt_logger import save_agent_prompt

            # Extract model info if available
            model_info = None
            if model:
                model_info = {
                    'provider': getattr(model, 'name', 'unknown'),
                    'model': str(model)
                }

            save_agent_prompt(
                agent_name='historian',
                system_prompt=system_prompt_text,
                user_prompt=prompt,
                model_info=model_info,
                context_info={
                    'source': 'RAG Ground Truth' if 'Context from Ground Truth' in historical_context else 'Legacy',
                    'tokens': len(historical_context.split()) * 1.3
                },
                metadata={
                    'deviation_date': str(deviation_request.deviation_date),
                    'simulation_years': deviation_request.simulation_years,
                    'narrative_mode': deviation_request.narrative_mode.value
                }
            )
        except Exception as e:
            logger.error(f"Failed to save prompt for debugging: {e}", exc_info=True)

        # Run agent with structured output type (using await since we're in async context)
        logger.info("Calling LLM API to generate timeline...")
        result = await agent.run(prompt, output_type=ToolOutput(TimelineOutput))

        # Extract data from AgentRunResult - the actual output is in result.output
        output_data = result.output

        # Log the timeline_name to verify it's being generated
        logger.info(f"Generated timeline_name: '{output_data.timeline_name}'")

        narrative_length = len(output_data.narrative_prose) if output_data.narrative_prose else 0
        logger.info(
            f"Successfully generated timeline. "
            f"Timeline name: '{output_data.timeline_name}', "
            f"Narrative length: {narrative_length} chars",
            extra={
                "narrative_length": narrative_length,
                "executive_summary_length": len(output_data.executive_summary),
                "has_narrative": output_data.narrative_prose is not None,
                "has_all_required_sections": all([
                    output_data.executive_summary,
                    output_data.political_changes,
                    output_data.economic_impacts,
                    output_data.social_developments,
                    output_data.technological_shifts,
                    output_data.key_figures,
                    output_data.long_term_implications
                ])
            }
        )

        return output_data

    except ConfigurationError:
        # Re-raise configuration errors
        raise
    except Exception as e:
        logger.error(
            f"Error generating timeline: {e}",
            exc_info=True,
            extra={
                "deviation_date": str(deviation_request.deviation_date),
                "simulation_years": deviation_request.simulation_years
            }
        )
        raise AIGenerationError(
            "Failed to generate timeline with AI agent",
            details={
                "error": str(e),
                "error_type": type(e).__name__
            }
        ) from e


# REMOVED: Extension system prompt now in template file historian/system_extension.jinja2


def construct_extension_prompt(
    original_timeline: Timeline,
    extension_request: TimelineExtensionRequest,
    historical_context: str = ""
) -> str:
    """
    Construct the prompt for extending an existing timeline using Jinja2 template.

    Args:
        original_timeline: The existing timeline to extend
        extension_request: Extension parameters
        historical_context: Optional additional historical context for the extension period

    Returns:
        Formatted prompt string for the AI agent
    """
    # Get the root deviation date (handle both date object and string)
    from datetime import date as date_type
    deviation_date = (
        date_type.fromisoformat(original_timeline.root_deviation_date)
        if isinstance(original_timeline.root_deviation_date, str)
        else original_timeline.root_deviation_date
    )

    original_end_year = (
        deviation_date.year +
        original_timeline.total_years_simulated
    )
    new_end_year = original_end_year + extension_request.additional_years

    latest_generation = original_timeline.latest_generation

    # Prepare original narrative context if it exists
    original_narrative = None
    if latest_generation and latest_generation.narrative_prose:
        original_narrative = latest_generation.narrative_prose

    # Determine if historian should generate narrative for extension
    # BASIC: historian generates narrative
    # ADVANCED: historian skips narrative (storyteller generates it later)
    # NONE: no narrative at all
    from app.models import NarrativeMode
    include_narrative = extension_request.narrative_mode == NarrativeMode.BASIC

    return render_prompt(
        "historian/user_extension.jinja2",
        original_deviation_description=original_timeline.root_deviation_description,
        original_deviation_date=deviation_date,
        scenario_type=original_timeline.scenario_type.value if hasattr(original_timeline.scenario_type, 'value') else original_timeline.scenario_type,
        total_simulation_years=original_timeline.total_years_simulated,
        original_end_year=original_end_year,
        new_end_year=new_end_year,
        additional_years=extension_request.additional_years,
        executive_summary=latest_generation.executive_summary if latest_generation else "No reports available",
        political_changes=latest_generation.political_changes if latest_generation else "No reports available",
        conflicts_and_wars=latest_generation.conflicts_and_wars if latest_generation else "No reports available",
        economic_impacts=latest_generation.economic_impacts if latest_generation else "No reports available",
        social_developments=latest_generation.social_developments if latest_generation else "No reports available",
        technological_shifts=latest_generation.technological_shifts if latest_generation else "No reports available",
        key_figures=latest_generation.key_figures if latest_generation else "No reports available",
        long_term_implications=latest_generation.long_term_implications if latest_generation else "No reports available",
        original_narrative=original_narrative,
        extension_historical_context=historical_context,
        additional_context=extension_request.additional_context,
        include_narrative=include_narrative
    )


async def extend_timeline(
    original_timeline: Timeline,
    extension_request: TimelineExtensionRequest,
    historical_context: str = "",
    model: Optional[Model] = None
) -> TimelineOutput:
    """
    Extend an existing timeline by additional years.

    Args:
        original_timeline: The existing timeline to extend
        extension_request: Extension parameters
        historical_context: Optional historical context for extension period
        model: Optional Pydantic-AI model instance. If None, will use default configuration.

    Returns:
        Generated extension output with all sections

    Raises:
        AIGenerationError: If AI generation fails
    """
    # Get the root deviation date (handle both date object and string)
    from datetime import date as date_type
    deviation_date = (
        date_type.fromisoformat(original_timeline.root_deviation_date)
        if isinstance(original_timeline.root_deviation_date, str)
        else original_timeline.root_deviation_date
    )

    original_end_year = (
        deviation_date.year +
        original_timeline.total_years_simulated
    )
    new_end_year = original_end_year + extension_request.additional_years

    logger.info(
        f"Extending timeline {extension_request.timeline_id} from {original_end_year} "
        f"to {new_end_year} (+{extension_request.additional_years} years)"
    )

    try:
        # Create extension agent with specialized prompt
        if model is None:
            # Fallback to legacy behavior for backward compatibility
            from pydantic_ai.models.google import GoogleModel

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ConfigurationError(
                    "GEMINI_API_KEY environment variable is required",
                    details={"missing_config": "GEMINI_API_KEY"}
                )

            model = GoogleModel(model_name="gemini-2.5-flash")
            logger.warning("Using legacy default model for timeline extension. Consider using llm_service.")

        # Render extension system prompt from Jinja2 template
        system_prompt = render_prompt(
            "historian/system_extension.jinja2",
            scenario_type=original_timeline.scenario_type.value if hasattr(original_timeline.scenario_type, 'value') else original_timeline.scenario_type
        )

        agent = Agent(
            model=model,
            system_prompt=system_prompt,
            model_settings={
                'max_tokens': 8192,  # Increase output token limit
                'temperature': 0.7,   # Consistent creativity
            },
            retries=3,  # Increase retries for complex structured output validation
        )

        # Construct extension prompt
        logger.debug("Constructing extension prompt")
        prompt = construct_extension_prompt(original_timeline, extension_request, historical_context)

        logger.debug(
            f"Extension prompt constructed. Length: {len(prompt)} chars, "
            f"Extension period: {original_end_year}-{new_end_year}"
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
                agent_name='historian_extension',
                system_prompt=system_prompt,
                user_prompt=prompt,
                model_info=model_info,
                context_info={
                    'source': 'RAG Ground Truth' if 'Context from Ground Truth' in historical_context else 'Legacy',
                    'tokens': len(historical_context.split()) * 1.3
                },
                metadata={
                    'timeline_id': str(extension_request.timeline_id),
                    'original_end_year': original_end_year,
                    'new_end_year': new_end_year,
                    'extension_years': extension_request.additional_years,
                    'narrative_mode': extension_request.narrative_mode.value
                }
            )
        except Exception as e:
            logger.debug(f"Failed to save extension prompt for debugging: {e}")

        # Run agent with structured output
        logger.info("Calling LLM API to extend timeline...")
        result = await agent.run(prompt, output_type=ToolOutput(TimelineOutput))

        output_data = result.output

        narrative_length = len(output_data.narrative_prose) if output_data.narrative_prose else 0
        logger.info(
            f"Successfully extended timeline. "
            f"Extension narrative length: {narrative_length} chars",
            extra={
                "timeline_id": str(extension_request.timeline_id),
                "extension_years": extension_request.additional_years,
                "narrative_length": narrative_length,
                "has_narrative": output_data.narrative_prose is not None
            }
        )

        return output_data

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(
            f"Error extending timeline: {e}",
            exc_info=True,
            extra={
                "timeline_id": str(extension_request.timeline_id),
                "extension_years": extension_request.additional_years
            }
        )
        raise AIGenerationError(
            "Failed to extend timeline with AI agent",
            details={
                "error": str(e),
                "error_type": type(e).__name__,
                "timeline_id": str(extension_request.timeline_id)
            }
        ) from e


# Global agent instance (optional, for reuse)
_agent_instance: Agent[Any, TimelineOutput] | None = None


def get_agent() -> Agent[Any, TimelineOutput]:
    """
    Get or create the global agent instance (singleton pattern).

    Returns:
        Configured historian agent
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_historian_agent()
    return _agent_instance