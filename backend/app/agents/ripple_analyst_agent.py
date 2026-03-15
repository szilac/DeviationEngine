"""
Pydantic-AI agent for extracting causal graphs from timeline reports.

This module analyses structured timeline generation reports and produces
a directed causal graph (nodes + edges) suitable for the Ripple Map
force-directed visualization.
"""

import os
import json
import logging
from typing import Any, List, Optional

from pydantic_ai import Agent
from pydantic_ai.models import Model

from app.models import RippleMapOutput, CausalNode, CausalEdge
from app.exceptions import ConfigurationError, AIGenerationError
from app.prompt_templates import render_prompt

logger = logging.getLogger(__name__)


def create_ripple_analyst_agent(
    model: Optional[Model] = None,
) -> Agent[Any, RippleMapOutput]:
    """
    Create the ripple analyst agent.

    Args:
        model: Optional Pydantic-AI model instance. If None, uses default Gemini.

    Returns:
        Configured Agent for causal graph extraction.

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
        logger.warning("Using legacy default model for ripple analyst.")

    system_prompt = render_prompt("ripple_analyst/system.jinja2")

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        model_settings={
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        retries=3,
    )

    logger.info(f"Ripple analyst agent created with model: {type(model).__name__}")
    return agent


async def generate_ripple_map(
    generation_content: str,
    deviation_date: str,
    deviation_description: str,
    scenario_type: str,
    generation_id: str,
    model: Optional[Model] = None,
) -> RippleMapOutput:
    """
    Generate a causal graph from a single generation's report.

    Args:
        generation_content: Combined text of the 8 report sections.
        deviation_date: The timeline's deviation date.
        deviation_description: What changed at the deviation point.
        scenario_type: Type of deviation scenario.
        generation_id: UUID of the generation being analysed.
        model: Optional Pydantic-AI model instance.

    Returns:
        RippleMapOutput with nodes and edges extracted from the report.

    Raises:
        AIGenerationError: If causal extraction fails.
    """
    logger.info(f"Generating ripple map from generation {generation_id}")

    try:
        agent = create_ripple_analyst_agent(model=model)

        prompt = render_prompt(
            "ripple_analyst/user_generate.jinja2",
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            generation_id=generation_id,
            generation_content=generation_content,
        )

        logger.debug(f"Ripple analyst prompt length: {len(prompt)} chars")

        result = await agent.run(prompt, output_type=RippleMapOutput)
        output = result.output

        logger.info(
            f"Generated ripple map for generation {generation_id}: "
            f"{len(output.nodes)} nodes, {len(output.edges)} edges"
        )

        return output

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Error generating ripple map for generation {generation_id}: {e}", exc_info=True)
        raise AIGenerationError(
            f"Failed to generate ripple map for generation {generation_id}",
            details={"error": str(e), "error_type": type(e).__name__},
        ) from e


async def add_generations_to_ripple_map(
    existing_nodes: List[CausalNode],
    existing_edges: List[CausalEdge],
    new_generation_content: str,
    deviation_date: str,
    deviation_description: str,
    scenario_type: str,
    new_generation_id: str,
    model: Optional[Model] = None,
) -> RippleMapOutput:
    """
    Extract new nodes and edges for an additional generation.

    The returned output contains ONLY new nodes/edges. The service layer
    is responsible for merging them with the existing graph.

    Args:
        existing_nodes: Current nodes in the ripple map.
        existing_edges: Current edges in the ripple map.
        new_generation_content: Combined text of the new generation's report.
        deviation_date: The timeline's deviation date.
        deviation_description: What changed at the deviation point.
        scenario_type: Type of deviation scenario.
        new_generation_id: UUID of the new generation.
        model: Optional Pydantic-AI model instance.

    Returns:
        RippleMapOutput with only the NEW nodes and edges.

    Raises:
        AIGenerationError: If extraction fails.
    """
    logger.info(
        f"Adding generation {new_generation_id} to ripple map "
        f"(existing: {len(existing_nodes)} nodes, {len(existing_edges)} edges)"
    )

    try:
        agent = create_ripple_analyst_agent(model=model)

        # Serialize existing graph for the prompt
        existing_nodes_json = [n.model_dump() for n in existing_nodes]
        existing_edges_json = [e.model_dump() for e in existing_edges]

        prompt = render_prompt(
            "ripple_analyst/user_add_generations.jinja2",
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            new_generation_id=new_generation_id,
            new_generation_content=new_generation_content,
            existing_nodes=existing_nodes_json,
            existing_edges=existing_edges_json,
        )

        logger.debug(f"Add-generation prompt length: {len(prompt)} chars")

        result = await agent.run(prompt, output_type=RippleMapOutput)
        output = result.output

        logger.info(
            f"Extracted {len(output.nodes)} new nodes and {len(output.edges)} new edges "
            f"for generation {new_generation_id}"
        )

        return output

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(
            f"Error adding generation {new_generation_id} to ripple map: {e}", exc_info=True
        )
        raise AIGenerationError(
            f"Failed to add generation {new_generation_id} to ripple map",
            details={"error": str(e), "error_type": type(e).__name__},
        ) from e
