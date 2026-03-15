"""
Pydantic-AI agent for generating image prompts for alternate history timelines.

This module implements the illustrator agent that analyzes timeline reports and
generates detailed image prompts suitable for AI image generation. The prompts are
designed to capture the visual essence of key moments in the alternate timeline.
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model

from app.exceptions import AIGenerationError
from app.prompt_templates import render_prompt

# Configure logging
logger = logging.getLogger(__name__)


# Output models for illustrator agent
class ImagePromptOutput(BaseModel):
    """Single image prompt for the timeline."""
    prompt_text: str = Field(
        ...,
        description="Detailed image generation prompt (50-200 words) with visual details, style, composition"
    )
    event_year: Optional[int] = Field(
        None,
        description="RELATIVE year from deviation point. 0 = deviation year, 5 = 5 years after deviation, -2 = 2 years before deviation. ALWAYS use relative years, NEVER absolute years."
    )
    title: str = Field(
        ...,
        description="Short descriptive title for the image (5-10 words)"
    )
    description: Optional[str] = Field(
        None,
        description="Brief context about what this image represents (1-2 sentences)"
    )
    style_notes: Optional[str] = Field(
        None,
        description="Style guidance (e.g., 'photorealistic 1920s documentary', 'propaganda poster', 'newspaper photo')"
    )


class IllustratorAgentOutput(BaseModel):
    """Complete image prompt collection from the agent."""
    prompts: List[ImagePromptOutput] = Field(
        ...,
        description="List of image prompts in chronological order"
    )
    overall_visual_theme: str = Field(
        ...,
        description="Overall visual theme/aesthetic for this timeline (2-3 sentences)"
    )


# REMOVED: System prompt now in template file illustrator/system.jinja2

def create_illustrator_agent(model: Model) -> Agent:
    """
    Create and configure the illustrator agent.

    Args:
        model: Pydantic-AI model instance (required)

    Returns:
        Configured Agent instance for image prompt generation
    """
    # Render system prompt from Jinja2 template
    system_prompt = render_prompt("illustrator/system.jinja2")

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
    )

    logger.info(f"Illustrator agent created successfully with model: {type(model).__name__}")
    return agent


def construct_illustrator_prompt(
    deviation_date: str,
    deviation_description: str,
    simulation_years: int,
    structured_report: dict,
    narrative_prose: Optional[str],
    num_images: int,
    focus_areas: Optional[List[str]] = None,
    report_start_year: int = 0
) -> str:
    """
    Construct the user prompt for image prompt generation.

    Args:
        deviation_date: Date of the historical deviation (formatted string)
        deviation_description: Description of what changed
        simulation_years: Number of years simulated
        structured_report: Structured report data (dict with sections)
        narrative_prose: Optional narrative text
        num_images: Number of images to generate prompts for
        focus_areas: Optional list of focus areas (political, economic, social, etc.)
        report_start_year: Year when this report period starts (0 for first report)

    Returns:
        Formatted prompt string for the agent
    """
    # Extract year from date string
    deviation_year = int(deviation_date.split('-')[0])
    end_year = deviation_year + simulation_years

    # For non-first generations, calculate the actual start year for this generation
    actual_start_year = deviation_year + report_start_year

    # Build focus areas section
    focus_section = ""
    if focus_areas:
        focus_section = f"""
## FOCUS AREAS

The user has requested special emphasis on these domains:
{chr(10).join(f'- {area.capitalize()}' for area in focus_areas)}

While you should still show variety, try to include more images related to these areas.
"""

    # Build narrative section if available
    narrative_section = ""
    if narrative_prose:
        narrative_section = f"""
## NARRATIVE PROSE

{narrative_prose[:3000]}{'...' if len(narrative_prose) > 3000 else ''}

{"="*80}
"""

    # Build coverage instruction - conditionally include deviation point for first report only
    deviation_point_instruction = ""
    if report_start_year == 0:
        deviation_point_instruction = "   - Include the deviation point or its immediate aftermath\n"

    prompt = f"""## ALTERNATE TIMELINE TO ILLUSTRATE

**Deviation Point:** {deviation_date}
**What Changed:** {deviation_description}
**Time Period:** {actual_start_year} to {end_year} ({end_year - actual_start_year} years)
{f"**Note:** This focuses on a specific time period within the broader alternate timeline" if report_start_year > 0 else ""}

## STRUCTURED REPORT

### Executive Summary
{structured_report.get('executive_summary', 'N/A')}

### Political Changes
{structured_report.get('political_changes', 'N/A')}

### Conflicts and Wars
{structured_report.get('conflicts_and_wars', 'N/A')}

### Economic Impacts
{structured_report.get('economic_impacts', 'N/A')}

### Social Developments
{structured_report.get('social_developments', 'N/A')}

### Technological Shifts
{structured_report.get('technological_shifts', 'N/A')}

### Key Figures
{structured_report.get('key_figures', 'N/A')}

### Long-term Implications
{structured_report.get('long_term_implications', 'N/A')}

{"="*80}
{narrative_section}{focus_section}

## TASK

Generate {num_images} detailed image prompts that visually capture the essence of this alternate timeline.

**Requirements:**

1. **Coverage**: Select moments that span the timeline from {actual_start_year} to {end_year}
{deviation_point_instruction}   - Show key turning points mentioned in the report
   - Represent different phases of this generation's evolution

2. **Variety**: Include diverse types of images:
   - Major historical events (summits, battles, protests, celebrations)
   - Everyday life and society (people, streets, workplaces)
   - Technology and infrastructure (vehicles, buildings, inventions)
   - Cultural artifacts (posters, newspapers, monuments)
   - Key figures in action (leaders, innovators, revolutionaries)
   - Landscapes and cityscapes showing change over time

3. **Visual Detail**: Each prompt must be specific and vivid:
   - Describe people: clothing, expressions, poses, actions
   - Describe settings: architecture, weather, time of day, atmosphere
   - Describe composition: camera angle, framing, what's in foreground/background
   - Specify style: photography style, artistic approach, era-appropriate aesthetics

4. **Historical Authenticity**: Match visual styles to the period:
   - {actual_start_year}s-{end_year}s aesthetic and technology
   - Period-appropriate photography or artistic styles
   - Clothing, architecture, vehicles from the right era
   - Consider how technology and style evolve through this time period

5. **Emotional Resonance**: Show the human impact:
   - Joy, fear, determination, hope, conflict
   - Individual stories within the larger historical sweep
   - Moments that make this alternate world feel real

6. **Chronological Order**: Arrange prompts from earliest to latest year

**Remember:** These prompts will be used with AI image generators. Be specific, visual, and concrete. Focus on what can be SEEN and CAPTURED in a single image. Avoid abstract concepts - ground everything in visual reality.

**CRITICAL: Use RELATIVE years for event_year field!**
- event_year=0 means the deviation year ({deviation_year})
- event_year=5 means 5 years after deviation ({deviation_year + 5})
- event_year=10 means 10 years after deviation ({deviation_year + 10})
- DO NOT use absolute years like {deviation_year}, {deviation_year + 5}, etc. in the event_year field!
- ONLY use relative years: 0, 1, 2, 3, 4, 5, etc.

Generate {num_images} image prompts now, ensuring they collectively tell the visual story of this alternate timeline."""

    return prompt


async def generate_image_prompts(
    deviation_date: str,
    deviation_description: str,
    simulation_years: int,
    structured_report: dict,
    narrative_prose: Optional[str],
    num_images: int,
    model: Model,
    focus_areas: Optional[List[str]] = None,
    report_start_year: int = 0
) -> IllustratorAgentOutput:
    """
    Generate image prompts for a timeline using the AI agent.

    Args:
        deviation_date: Date of the historical deviation (formatted string)
        deviation_description: Description of what changed
        simulation_years: Number of years simulated
        structured_report: Structured report data
        narrative_prose: Optional narrative prose
        num_images: Number of images to generate prompts for (3-20)
        model: Pydantic-AI model instance
        focus_areas: Optional list of focus areas
        report_start_year: Year when this report period starts (0 for first report)

    Returns:
        Generated image prompts with overall visual theme

    Raises:
        AIGenerationError: If prompt generation fails
    """
    logger.info(
        f"Generating {num_images} image prompts for timeline: "
        f"{deviation_description[:50]}... ({simulation_years} years)"
    )

    try:
        # Create illustrator agent
        logger.debug("Creating illustrator agent")
        agent = create_illustrator_agent(model=model)

        # Construct prompt
        logger.debug("Constructing illustrator prompt")
        prompt = construct_illustrator_prompt(
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            simulation_years=simulation_years,
            structured_report=structured_report,
            narrative_prose=narrative_prose,
            num_images=num_images,
            focus_areas=focus_areas,
            report_start_year=report_start_year
        )

        logger.debug(
            f"Prompt constructed. Length: {len(prompt)} chars, "
            f"Requesting {num_images} images"
        )

        # Run agent with structured output
        logger.info("Calling LLM API to generate image prompts...")
        result = await agent.run(prompt, output_type=IllustratorAgentOutput)

        # Extract output
        output_data = result.output

        logger.info(
            f"Successfully generated {len(output_data.prompts)} image prompts",
            extra={
                "prompt_count": len(output_data.prompts),
                "requested_count": num_images,
                "deviation_description": deviation_description[:50]
            }
        )

        # Validate prompt count
        if len(output_data.prompts) < num_images - 2:
            logger.warning(
                f"Generated {len(output_data.prompts)} prompts, "
                f"requested {num_images}. Significant shortfall."
            )
        elif len(output_data.prompts) > num_images + 5:
            logger.warning(
                f"Generated {len(output_data.prompts)} prompts, "
                f"requested {num_images}. Trimming excess."
            )
            output_data.prompts = output_data.prompts[:num_images + 2]

        # Prompts are already in chronological order from the agent
        # prompt_order will be assigned when creating the skeleton in the service layer

        return output_data

    except Exception as e:
        logger.error(
            f"Error generating image prompts: {e}",
            exc_info=True,
            extra={
                "deviation_description": deviation_description[:50],
                "num_images": num_images
            }
        )
        raise AIGenerationError(
            "Failed to generate image prompts with AI agent",
            details={
                "error": str(e),
                "error_type": type(e).__name__
            }
        ) from e
