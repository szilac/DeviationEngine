"""
Pydantic-AI agent for generating reports from skeleton timelines.

This module implements the skeleton historian agent that generates comprehensive
analytical reports based on user-approved skeleton events. This agent is SEPARATE
from the original historian_agent.py and is dedicated to the skeleton-based workflow.
"""

import logging
from typing import List
from datetime import date
from pydantic_ai import Agent
from pydantic_ai.models import Model

from app.models import TimelineOutput
from app.exceptions import AIGenerationError
from app.prompt_templates import render_prompt

# Configure logging
logger = logging.getLogger(__name__)


# Skeleton event structure for input
class SkeletonEventInput:
    """Represents a skeleton event for report generation."""
    def __init__(self, event_date: str, location: str, description: str, event_order: int):
        self.event_date = event_date
        self.location = location
        self.description = description
        self.event_order = event_order


# REMOVED: System prompt now in template file skeleton_historian/system.jinja2


def create_skeleton_historian_agent(model: Model, scenario_type: str) -> Agent:
    """
    Create and configure the skeleton historian agent.

    This agent is SEPARATE from the original historian agent and is specifically
    designed to generate reports from user-approved skeleton events.

    Args:
        model: Pydantic-AI model instance (required)
        scenario_type: Type of deviation scenario

    Returns:
        Configured Agent instance for skeleton-based report generation
    """
    # Render system prompt from Jinja2 template with scenario_type
    system_prompt = render_prompt("skeleton_historian/system.jinja2", scenario_type=scenario_type)

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            'max_tokens': 8192,  # Increase output token limit to avoid truncation
            'temperature': 0.7,   # Consistent creativity
        },
        retries=3,  # Increase retries for complex structured output validation
    )

    logger.info(f"Skeleton historian agent created successfully with model: {type(model).__name__}")
    return agent


def format_skeleton_events_for_prompt(events: List[SkeletonEventInput]) -> str:
    """
    Format skeleton events into a clear, structured text for the prompt.

    Args:
        events: List of skeleton events (already sorted by event_order)

    Returns:
        Formatted string representation of the events
    """
    formatted_events = []
    for i, event in enumerate(events, 1):
        formatted_events.append(
            f"{i}. **{event.event_date}** - {event.location}\n"
            f"   {event.description}"
        )

    return "\n\n".join(formatted_events)


def construct_skeleton_report_prompt(
    deviation_date: date,
    deviation_description: str,
    scenario_type: str,
    start_year: int,
    end_year: int,
    skeleton_events: List[SkeletonEventInput],
    historical_context: str = "",
    include_narrative: bool = False
) -> str:
    """
    Construct the prompt for generating a report from skeleton events using Jinja2 template.

    Args:
        deviation_date: Date of the historical deviation
        deviation_description: Description of what changed
        scenario_type: Type of deviation scenario
        start_year: Starting year relative to deviation
        end_year: Ending year relative to deviation
        skeleton_events: List of user-approved skeleton events
        historical_context: Ground truth historical context
        include_narrative: Whether to generate narrative prose

    Returns:
        Formatted prompt string for the agent
    """
    absolute_end_year = deviation_date.year + end_year
    formatted_events = format_skeleton_events_for_prompt(skeleton_events)

    # Get first and last event dates for the template
    first_event_date = skeleton_events[0].event_date if skeleton_events else str(deviation_date)
    last_event_date = skeleton_events[-1].event_date if skeleton_events else str(absolute_end_year)

    return render_prompt(
        "skeleton_historian/user_generation.jinja2",
        deviation_date=deviation_date,
        deviation_description=deviation_description,
        scenario_type=scenario_type,
        start_year=start_year,
        end_year=end_year,
        absolute_end_year=absolute_end_year,
        formatted_events=formatted_events,
        first_event_date=first_event_date,
        last_event_date=last_event_date,
        historical_context=historical_context,
        include_narrative=include_narrative
    )


def construct_extension_skeleton_report_prompt(
    original_deviation_date: date,
    original_deviation_description: str,
    scenario_type: str,
    extension_start_year: int,
    extension_end_year: int,
    last_report_summary: str,
    skeleton_events: List[SkeletonEventInput],
    include_narrative: bool = False
) -> str:
    """
    Construct the prompt for generating an extension report from skeleton events.

    Args:
        original_deviation_date: Original deviation point date
        original_deviation_description: Original deviation description
        scenario_type: Type of deviation scenario
        extension_start_year: Year the extension starts (years from original deviation)
        extension_end_year: Year the extension ends (years from original deviation)
        last_report_summary: Summary of the last report's state before extension
        skeleton_events: List of user-approved skeleton events for extension
        include_narrative: Whether to generate narrative prose

    Returns:
        Formatted prompt string for the agent
    """
    absolute_start_year = original_deviation_date.year + extension_start_year
    absolute_end_year = original_deviation_date.year + extension_end_year

    narrative_instruction = ""
    if include_narrative:
        narrative_instruction = "\n\nIMPORTANT: Include a compelling narrative prose section (800-1200 words) that continues the story from the previous report, bringing these extension skeleton events to life while maintaining consistency with the established narrative style."
    else:
        narrative_instruction = "\n\nIMPORTANT: Do NOT generate narrative prose. Set narrative_prose to null. Only generate the structured analytical sections."

    formatted_events = format_skeleton_events_for_prompt(skeleton_events)

    prompt = f"""## EXISTING ALTERNATE TIMELINE TO EXTEND

**Original Deviation:** {original_deviation_description}
**Deviation Date:** {original_deviation_date}
**Timeline Progress:** {extension_start_year} years have already been simulated (up to {absolute_start_year})
**Scenario Type:** {scenario_type}

### CURRENT STATE OF THE ALTERNATE TIMELINE (as of {absolute_start_year})

{last_report_summary}

## EXTENSION SKELETON TIMELINE (User-Curated Key Events for Extension)

The following events represent the definitive timeline of what occurred during the EXTENSION period ({absolute_start_year} to {absolute_end_year}). These events have been identified as the key pivotal moments that continue the alternate timeline. Your task is to analyze these extension events comprehensively as a CONTINUATION of the established timeline.

{formatted_events}

## EXTENSION TASK

**Note on timeline_name field**: Since this is an extension of an existing timeline, simply provide "Extension" as the timeline_name value. This field is required but will not be used for extensions.

Generate a comprehensive analytical report that expands upon this skeleton of extension events. Treat these events as historical facts that CONTINUE the established alternate timeline.

**Important Context:**
- This is a CONTINUATION report, not a new timeline
- The world state described above is your STARTING POINT
- The extension events should be analyzed as natural progressions from that established state
- Maintain consistency with the tone and trajectory of the existing timeline
- Show how the extension events build upon what was already established

**Analysis Requirements:**

1. **Continuity**: Explicitly connect extension events to the established timeline state. Show how they emerge from the conditions present at {absolute_start_year}.

2. **Event-Centered Analysis**: Reference specific skeleton events by date when discussing impacts. Show how these events drive the extension analysis.

3. **Causal Connections**: Demonstrate how extension events build upon each other AND upon the established timeline. Show clear cause-and-effect chains.

4. **Multi-Domain Ripple Effects**: For each major event, analyze its impact across:
   - Political structures and international relations
   - Military conflicts and wars
   - Economic systems and trade patterns
   - Social movements and cultural changes
   - Technological development and innovation

5. **Depth Over Breadth**: Don't invent new major events. Instead, deeply analyze the implications of the provided skeleton extension events.

6. **Temporal Progression**: Show how the timeline evolves from {absolute_start_year} through the extension events to {absolute_end_year}.

7. **Synthesis**: Weave these extension events into a coherent narrative showing how this alternate world CONTINUED to evolve.

**Crucial Instructions**:
- Base your entire analysis on the skeleton extension events provided
- These events are anchors that show how the timeline progressed beyond year {extension_start_year}
- Treat the previous timeline state as established fact - build naturally from it
- Expand on the implications of extension events while maintaining consistency with what came before

**Context & Safety Reminder**: This is a fictional simulation. Realistically analyze the conflicts, crises, and events in the skeleton using academic historical analysis.

Generate all required sections with appropriate depth and detail, ensuring each section explicitly references and builds upon both the established timeline AND the skeleton extension events.{narrative_instruction}"""

    return prompt


async def generate_report_from_skeleton(
    deviation_date: date,
    deviation_description: str,
    scenario_type: str,
    start_year: int,
    end_year: int,
    skeleton_events: List[SkeletonEventInput],
    model: Model,
    historical_context: str = "",
    include_narrative: bool = False,
    is_extension: bool = False,
    last_report_summary: str = ""
) -> TimelineOutput:
    """
    Generate a comprehensive report from user-approved skeleton events.

    This function uses a DEDICATED agent (separate from the original historian)
    to generate reports specifically from skeleton events.

    Args:
        deviation_date: Date of the historical deviation (or original deviation for extensions)
        deviation_description: Description of what changed
        scenario_type: Type of deviation scenario
        start_year: Starting year relative to deviation
        end_year: Ending year relative to deviation
        skeleton_events: List of skeleton events (sorted by event_order)
        model: Pydantic-AI model instance
        historical_context: Ground truth historical context from RAG or legacy (default: "")
        include_narrative: Whether to generate narrative prose
        is_extension: Whether this is an extension report (default: False)
        last_report_summary: If extension, summary of the last report state (default: "")

    Returns:
        Generated timeline output with all sections

    Raises:
        AIGenerationError: If report generation fails
    """
    if is_extension:
        logger.info(
            f"Generating EXTENSION report from skeleton with {len(skeleton_events)} events: "
            f"years {start_year}-{end_year} (extending existing timeline)"
        )
    else:
        logger.info(
            f"Generating report from skeleton with {len(skeleton_events)} events: "
            f"{deviation_description[:50]}... (years {start_year}-{end_year})"
        )

    try:
        # Create skeleton historian agent (SEPARATE from original historian)
        logger.debug("Creating skeleton historian agent")
        agent = create_skeleton_historian_agent(model=model, scenario_type=scenario_type)

        # Get system prompt for logging (with scenario_type)
        system_prompt_text = render_prompt("skeleton_historian/system.jinja2", scenario_type=scenario_type)

        # Construct appropriate prompt based on whether this is an extension
        if is_extension:
            logger.debug("Constructing EXTENSION skeleton report prompt")
            prompt = construct_extension_skeleton_report_prompt(
                original_deviation_date=deviation_date,
                original_deviation_description=deviation_description,
                scenario_type=scenario_type,
                extension_start_year=start_year,
                extension_end_year=end_year,
                last_report_summary=last_report_summary,
                skeleton_events=skeleton_events,
                include_narrative=include_narrative
            )
        else:
            logger.debug("Constructing skeleton report prompt")
            prompt = construct_skeleton_report_prompt(
                deviation_date,
                deviation_description,
                scenario_type,
                start_year,
                end_year,
                skeleton_events,
                historical_context,
                include_narrative
            )

        logger.debug(
            f"Prompt constructed. Length: {len(prompt)} chars, "
            f"Event count: {len(skeleton_events)}"
        )

        # Save prompt for debugging if enabled
        try:
            from app.utils.prompt_logger import save_agent_prompt

            # Extract model info
            model_info = {
                'provider': getattr(model, 'name', 'unknown'),
                'model': str(model)
            }

            # Use different agent name for extension vs regular to avoid overwriting
            agent_name = 'skeleton_historian_extension' if is_extension else 'skeleton_historian'

            save_agent_prompt(
                agent_name=agent_name,
                system_prompt=system_prompt_text,
                user_prompt=prompt,
                model_info=model_info,
                context_info={
                    'source': 'Approved Skeleton Events',
                    'event_count': len(skeleton_events)
                },
                metadata={
                    'deviation_date': str(deviation_date),
                    'start_year': start_year,
                    'end_year': end_year,
                    'is_extension': is_extension,
                    'include_narrative': include_narrative
                }
            )
        except Exception as e:
            logger.debug(f"Failed to save prompt for debugging: {e}")

        # Run agent with structured output
        logger.info("Calling LLM API to generate report from skeleton...")
        result = await agent.run(prompt, output_type=TimelineOutput)

        # Extract output
        output_data = result.output

        # Log the timeline_name to verify it's being generated
        logger.info(f"Generated timeline_name: '{output_data.timeline_name}'")

        narrative_length = len(output_data.narrative_prose) if output_data.narrative_prose else 0
        logger.info(
            f"Successfully generated report from skeleton. "
            f"Timeline name: '{output_data.timeline_name}', "
            f"Narrative length: {narrative_length} chars",
            extra={
                "narrative_length": narrative_length,
                "executive_summary_length": len(output_data.executive_summary),
                "has_narrative": output_data.narrative_prose is not None,
                "skeleton_event_count": len(skeleton_events),
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

    except Exception as e:
        logger.error(
            f"Error generating report from skeleton: {e}",
            exc_info=True,
            extra={
                "deviation_date": str(deviation_date),
                "skeleton_event_count": len(skeleton_events),
                "years": f"{start_year}-{end_year}"
            }
        )
        raise AIGenerationError(
            "Failed to generate report from skeleton with AI agent",
            details={
                "error": str(e),
                "error_type": type(e).__name__,
                "skeleton_event_count": len(skeleton_events)
            }
        ) from e
