"""
Pydantic-AI agent for generating audio scripts from timeline content.

This module implements the script writer agent that transforms structured
reports and narratives into audio-optimized scripts suitable for TTS generation.
"""

import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model

from app.exceptions import AIGenerationError
from app.prompt_templates import render_prompt

logger = logging.getLogger(__name__)


# ===== OUTPUT MODELS =====


class ScriptOutput(BaseModel):
    """Generated audio script output."""

    script_content: str = Field(
        ...,
        description="Complete audio script in markdown format with speaker markers"
    )
    estimated_duration_seconds: int = Field(
        ...,
        description="Estimated audio duration in seconds based on word count (150 words/min)"
    )
    word_count: int = Field(
        ...,
        description="Total word count in the script"
    )
    suggested_title: str = Field(
        ...,
        description="Suggested title for this audio script (5-12 words)"
    )
    pacing_notes: Optional[str] = Field(
        None,
        description="Notes on pacing, pauses, and emphasis for TTS generation"
    )


# ===== AGENT CREATION =====


def create_script_writer_agent(
    preset: Dict[str, Any],
    model: Model
) -> Agent[Any, ScriptOutput]:
    """
    Create and configure the script writer agent.

    The agent is configured based on the preset's style parameters and
    uses the appropriate system prompt template.

    Args:
        preset: Preset configuration dict with style_instructions and voice_count
        model: Pydantic-AI model instance

    Returns:
        Configured Agent instance for script generation

    Example:
        >>> preset = {
        ...     'name': 'Documentary Narration',
        ...     'script_type': 'documentary',
        ...     'tone': 'authoritative',
        ...     'pacing': 'medium',
        ...     'voice_count': 1,
        ...     'style_instructions': '...',
        ...     'prompt_template_name': 'script_writer/documentary.jinja2'
        ... }
        >>> agent = create_script_writer_agent(preset, model)
    """
    # Render system prompt from template based on preset
    template_name = preset.get('prompt_template_name', 'script_writer/generic.jinja2')

    system_prompt = render_prompt(
        template_name,
        preset_name=preset['name'],
        script_type=preset['script_type'],
        tone=preset['tone'],
        pacing=preset['pacing'],
        voice_count=preset['voice_count'],
        voice_roles=preset.get('voice_roles', {}),
        style_instructions=preset['style_instructions']
    )

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            'max_tokens': 8192,  # Allow for longer scripts
            'temperature': 0.7,  # Balanced creativity
        }
    )

    logger.info(
        f"Script writer agent created: preset='{preset['name']}', "
        f"type={preset['script_type']}, voices={preset['voice_count']}"
    )
    return agent


# ===== PROMPT CONSTRUCTION =====


def construct_script_prompt(
    generations_content: List[Dict[str, Any]],
    preset: Dict[str, Any],
    custom_instructions: Optional[str] = None
) -> str:
    """
    Construct the user prompt for script generation.

    Combines content from multiple generations and formats it with preset
    parameters and optional custom instructions.

    Args:
        generations_content: List of generation dicts with structured_report and narrative_prose
        preset: Preset configuration
        custom_instructions: Optional user customizations

    Returns:
        Formatted prompt string for the agent

    Example:
        >>> generations = [
        ...     {
        ...         'start_year': 0,
        ...         'end_year': 10,
        ...         'executive_summary': '...',
        ...         'political_changes': '...',
        ...         # ... other fields
        ...     }
        ... ]
        >>> prompt = construct_script_prompt(generations, preset, "Focus on economics")
    """
    # Combine content from multiple generations
    combined_content = _combine_generations_content(generations_content)

    return render_prompt(
        "script_writer/user_generation.jinja2",
        generations=generations_content,
        combined_structured_report=combined_content['structured'],
        combined_narrative=combined_content['narrative'],
        preset_name=preset['name'],
        script_type=preset['script_type'],
        voice_count=preset['voice_count'],
        voice_roles=preset.get('voice_roles', {}),
        tone=preset['tone'],
        pacing=preset['pacing'],
        custom_instructions=custom_instructions,
        target_duration_range=(300, 600)  # 5-10 minutes typical
    )


def _combine_generations_content(generations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine content from multiple generations into cohesive input.

    Merges all structured report sections and narratives from multiple
    time periods into a single combined structure.

    Args:
        generations: List of generation dicts

    Returns:
        dict with 'structured' and 'narrative' keys
    """
    # Merge structured reports
    structured = {
        'executive_summary': '\n\n'.join(g.get('executive_summary', '') for g in generations),
        'political_changes': '\n\n'.join(g.get('political_changes', '') for g in generations),
        'conflicts_and_wars': '\n\n'.join(g.get('conflicts_and_wars', '') for g in generations),
        'economic_impacts': '\n\n'.join(g.get('economic_impacts', '') for g in generations),
        'social_developments': '\n\n'.join(g.get('social_developments', '') for g in generations),
        'technological_shifts': '\n\n'.join(g.get('technological_shifts', '') for g in generations),
        'key_figures': '\n\n'.join(g.get('key_figures', '') for g in generations),
        'long_term_implications': '\n\n'.join(g.get('long_term_implications', '') for g in generations),
    }

    # Combine narratives if present
    narrative = '\n\n'.join(
        g.get('narrative_prose', '') for g in generations if g.get('narrative_prose')
    )

    return {'structured': structured, 'narrative': narrative}


# ===== GENERATION =====


async def generate_script(
    generations_content: List[Dict[str, Any]],
    preset: Dict[str, Any],
    custom_instructions: Optional[str],
    model: Model
) -> ScriptOutput:
    """
    Generate an audio script from generation content.

    This is the main entry point for script generation. It creates the agent,
    constructs the prompt, and runs the generation.

    Args:
        generations_content: List of generation data
        preset: Preset configuration
        custom_instructions: Optional user customizations
        model: Pydantic-AI model instance

    Returns:
        Generated script output with content, word count, duration, etc.

    Raises:
        AIGenerationError: If script generation fails

    Example:
        >>> from pydantic_ai.models.google import GoogleModel
        >>> model = GoogleModel(model_name="gemini-2.5-flash")
        >>> result = await generate_script(
        ...     generations_content=[gen1_dict, gen2_dict],
        ...     preset=preset_dict,
        ...     custom_instructions="Focus on economic impacts",
        ...     model=model
        ... )
        >>> print(f"Generated {result.word_count} word script")
    """
    logger.info(
        f"Generating script: preset='{preset['name']}', "
        f"generations={len(generations_content)}"
    )

    try:
        # Create agent with preset configuration
        agent = create_script_writer_agent(preset=preset, model=model)

        # Construct prompt with generation content
        prompt = construct_script_prompt(
            generations_content=generations_content,
            preset=preset,
            custom_instructions=custom_instructions
        )

        logger.debug(
            f"Prompt constructed: {len(prompt)} chars, "
            f"{len(generations_content)} generations"
        )

        # Generate script using agent
        logger.info("Calling LLM API to generate script...")
        result = await agent.run(prompt, output_type=ScriptOutput)
        output = result.output

        logger.info(
            f"Script generated successfully: {output.word_count} words, "
            f"~{output.estimated_duration_seconds}s duration",
            extra={
                "preset": preset['name'],
                "word_count": output.word_count,
                "duration": output.estimated_duration_seconds,
                "generation_count": len(generations_content)
            }
        )

        return output

    except Exception as e:
        logger.error(
            f"Error generating script: {e}",
            exc_info=True,
            extra={
                "preset": preset['name'],
                "generation_count": len(generations_content)
            }
        )
        raise AIGenerationError(
            "Failed to generate audio script with AI agent",
            details={
                "error": str(e),
                "error_type": type(e).__name__,
                "preset": preset['name']
            }
        ) from e


# ===== UTILITY FUNCTIONS =====


def estimate_duration_from_word_count(word_count: int, pacing: str = 'medium') -> int:
    """
    Estimate audio duration in seconds from word count.

    Args:
        word_count: Number of words in script
        pacing: 'fast' (180 wpm), 'medium' (150 wpm), 'slow' (120 wpm)

    Returns:
        Estimated duration in seconds

    Example:
        >>> estimate_duration_from_word_count(750, 'medium')
        300  # 5 minutes
    """
    wpm_rates = {
        'fast': 180,
        'medium': 150,
        'slow': 120,
        'varied': 150  # Use medium as default
    }

    wpm = wpm_rates.get(pacing, 150)
    duration_minutes = word_count / wpm
    return int(duration_minutes * 60)


def validate_script_structure(script_content: str, expected_voice_count: int) -> bool:
    """
    Validate that script has correct structure for voice count.

    Args:
        script_content: Markdown script content
        expected_voice_count: 1 or 2

    Returns:
        True if structure is valid

    Example:
        >>> script = "**NARRATOR**: Hello world"
        >>> validate_script_structure(script, 1)
        True
    """
    import re

    # Count unique speaker markers
    speakers = set(re.findall(r'\*\*([A-Z]+)\*\*:', script_content))

    if expected_voice_count == 1:
        return len(speakers) == 1
    elif expected_voice_count == 2:
        return len(speakers) == 2
    else:
        return False


def extract_speaker_lines(script_content: str) -> List[Dict[str, str]]:
    """
    Extract individual speaker lines from script.

    Useful for processing 2-voice scripts for TTS generation.

    Args:
        script_content: Markdown script with speaker markers

    Returns:
        List of dicts with 'speaker' and 'text' keys

    Example:
        >>> script = "**HOST**: Hello\\n\\n**EXPERT**: Hi there"
        >>> lines = extract_speaker_lines(script)
        >>> lines[0]
        {'speaker': 'HOST', 'text': 'Hello'}
    """
    import re

    pattern = r'\*\*([A-Z]+)\*\*:\s*([^\*]+)'
    matches = re.findall(pattern, script_content)

    return [
        {
            'speaker': speaker,
            'text': text.strip()
        }
        for speaker, text in matches
    ]


def count_words(text: str) -> int:
    """
    Count words in text, excluding markdown markers.

    Args:
        text: Markdown text with speaker markers

    Returns:
        Word count

    Example:
        >>> count_words("**NARRATOR**: Hello world")
        2
    """
    import re

    # Remove speaker markers like **NARRATOR**:
    text_clean = re.sub(r'\*\*[A-Z]+\*\*:', '', text)

    # Remove other markdown
    text_clean = re.sub(r'\[PAUSE\]', '', text_clean)
    text_clean = re.sub(r'[*_`]', '', text_clean)

    # Split and count
    words = text_clean.split()
    return len([w for w in words if w.strip()])
