"""
Ripple Map Service.

Orchestrates the Ripple Analyst agent to build and grow causal web
visualizations for timelines. One ripple map per timeline; grows
incrementally as new generations are added.
"""

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db_models import GenerationDB, RippleMapDB, TimelineDB
from app.exceptions import NotFoundError, ValidationError, AIGenerationError
from app.models import AgentType, CausalEdge, CausalNode, RippleMapOutput

logger = logging.getLogger(__name__)

# The 8 structured report sections in display order
REPORT_SECTIONS = [
    ("Executive Summary", "executive_summary"),
    ("Political Changes", "political_changes"),
    ("Conflicts and Wars", "conflicts_and_wars"),
    ("Economic Impacts", "economic_impacts"),
    ("Social Developments", "social_developments"),
    ("Technological Shifts", "technological_shifts"),
    ("Key Figures", "key_figures"),
    ("Long-term Implications", "long_term_implications"),
]


# ============================================================================
# Helpers
# ============================================================================


def _build_generation_content(generation: GenerationDB) -> str:
    """
    Concatenate all 8 structured report sections into a single string.

    Args:
        generation: GenerationDB record with report fields.

    Returns:
        Formatted string of all non-empty report sections.
    """
    sections = []
    for label, field_name in REPORT_SECTIONS:
        content = getattr(generation, field_name, "")
        if content:
            sections.append(f"## {label}\n{content}")
    return "\n\n".join(sections)


def _compute_dominant_domain(nodes: List[CausalNode]) -> Optional[str]:
    """
    Find the domain with the most high-magnitude (4+) nodes.

    Args:
        nodes: List of causal nodes.

    Returns:
        Domain name with most high-magnitude nodes, or None if empty.
    """
    if not nodes:
        return None

    domain_counts: Dict[str, int] = {}
    for node in nodes:
        if node.magnitude >= 4:
            domain_counts[node.domain.value] = domain_counts.get(node.domain.value, 0) + 1

    if not domain_counts:
        # Fallback: most common domain overall
        for node in nodes:
            domain_counts[node.domain.value] = domain_counts.get(node.domain.value, 0) + 1

    return max(domain_counts, key=domain_counts.__getitem__)


def _compute_max_depth(nodes: List[CausalNode], edges: List[CausalEdge]) -> int:
    """
    Find the longest causal chain using BFS from the deviation point.

    Args:
        nodes: All causal nodes.
        edges: All causal edges.

    Returns:
        Integer depth of the longest causal chain.
    """
    if not nodes or not edges:
        return 0

    # Find deviation point node
    deviation_node = next((n for n in nodes if n.is_deviation_point), None)
    if not deviation_node:
        return 0

    # Build adjacency list
    adjacency: Dict[str, List[str]] = {n.id: [] for n in nodes}
    for edge in edges:
        if edge.source_node_id in adjacency:
            adjacency[edge.source_node_id].append(edge.target_node_id)

    # BFS to find max depth
    queue: deque = deque([(deviation_node.id, 0)])
    visited = {deviation_node.id}
    max_depth = 0

    while queue:
        node_id, depth = queue.popleft()
        max_depth = max(max_depth, depth)

        for neighbour_id in adjacency.get(node_id, []):
            if neighbour_id not in visited:
                visited.add(neighbour_id)
                queue.append((neighbour_id, depth + 1))

    return max_depth


def _extract_model_info(model) -> tuple[Optional[str], Optional[str]]:
    """
    Extract provider and model name strings from a Pydantic-AI model instance.

    Args:
        model: Pydantic-AI model instance.

    Returns:
        Tuple of (provider_str, model_name_str).
    """
    if model is None:
        return "google", "gemini-2.5-flash"

    model_repr = repr(model)

    if "Google" in type(model).__name__ or "Gemini" in type(model).__name__:
        provider = "google"
    elif "OpenAI" in type(model).__name__:
        # Could be openrouter or ollama
        provider = getattr(model, "provider", "openrouter") or "openrouter"
        if isinstance(provider, str) and "openrouter" not in provider.lower():
            provider = "ollama"
    else:
        provider = "unknown"

    model_name = getattr(model, "model_name", None) or str(model_repr)

    return provider, model_name


def _merge_ripple_outputs(
    first: RippleMapOutput,
    rest: List[RippleMapOutput],
) -> tuple[List[CausalNode], List[CausalEdge]]:
    """
    Merge multiple RippleMapOutput objects into a single flat node/edge list.

    Args:
        first: The initial output (from the first generation).
        rest: Additional outputs to merge in.

    Returns:
        Tuple of (merged_nodes, merged_edges).
    """
    all_nodes = list(first.nodes)
    all_edges = list(first.edges)
    seen_node_ids = {n.id for n in all_nodes}

    for output in rest:
        for node in output.nodes:
            if node.id not in seen_node_ids:
                all_nodes.append(node)
                seen_node_ids.add(node.id)

        # Edges: deduplicate by (source, target, relationship) tuple
        seen_edges = {
            (e.source_node_id, e.target_node_id, e.relationship.value)
            for e in all_edges
        }
        for edge in output.edges:
            key = (edge.source_node_id, edge.target_node_id, edge.relationship.value)
            if key not in seen_edges:
                all_edges.append(edge)
                seen_edges.add(key)

    return all_nodes, all_edges


# ============================================================================
# Public Service Functions
# ============================================================================


async def generate_ripple_map(
    db: AsyncSession,
    timeline_id: str,
    generation_ids: List[str],
) -> RippleMapDB:
    """
    Generate a ripple map for a timeline from the specified generations.

    Calls the Ripple Analyst agent once per generation (first generation uses
    the initial generate prompt; subsequent ones use the add-generations prompt
    for better cross-generation causal connections), then stores the merged
    result.

    Args:
        db: Database session.
        timeline_id: UUID of the parent timeline.
        generation_ids: List of generation UUIDs to include.

    Returns:
        Saved RippleMapDB record.

    Raises:
        NotFoundError: If timeline or any generation not found.
        ValidationError: If a ripple map already exists for this timeline.
        AIGenerationError: If agent extraction fails.
    """
    # Validate timeline exists
    result = await db.execute(select(TimelineDB).where(TimelineDB.id == timeline_id))
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise NotFoundError(f"Timeline {timeline_id} not found")

    # Check no existing ripple map
    existing = await db.execute(
        select(RippleMapDB).where(RippleMapDB.timeline_id == timeline_id)
    )
    if existing.scalar_one_or_none():
        raise ValidationError(
            "A ripple map already exists for this timeline. "
            "Use add-generations to extend it, or delete it first."
        )

    # Load and validate generations
    generations = await _load_and_validate_generations(db, timeline_id, generation_ids)

    # Get per-agent model
    model = None
    try:
        from app.services.llm_service import create_pydantic_ai_model_for_agent
        model = await create_pydantic_ai_model_for_agent(db, AgentType.RIPPLE_ANALYST)
    except Exception:
        logger.debug("No agent LLM config available for ripple_analyst, using default")

    deviation_date = str(timeline.root_deviation_date)
    deviation_description = timeline.root_deviation_description
    scenario_type = timeline.scenario_type

    from app.agents.ripple_analyst_agent import (
        add_generations_to_ripple_map as agent_add,
        generate_ripple_map as agent_generate,
    )

    # Process first generation
    first_gen = generations[0]
    first_content = _build_generation_content(first_gen)

    first_output = await agent_generate(
        generation_content=first_content,
        deviation_date=deviation_date,
        deviation_description=deviation_description,
        scenario_type=scenario_type,
        generation_id=str(first_gen.id),
        model=model,
    )

    accumulated_nodes = list(first_output.nodes)
    accumulated_edges = list(first_output.edges)

    # Chain subsequent generations through add_generations for cross-gen edges
    for gen in generations[1:]:
        add_output = await agent_add(
            existing_nodes=accumulated_nodes,
            existing_edges=accumulated_edges,
            new_generation_content=_build_generation_content(gen),
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            new_generation_id=str(gen.id),
            model=model,
        )

        seen_ids = {n.id for n in accumulated_nodes}
        for node in add_output.nodes:
            if node.id not in seen_ids:
                accumulated_nodes.append(node)
                seen_ids.add(node.id)

        seen_edges = {
            (e.source_node_id, e.target_node_id, e.relationship.value)
            for e in accumulated_edges
        }
        for edge in add_output.edges:
            key = (edge.source_node_id, edge.target_node_id, edge.relationship.value)
            if key not in seen_edges:
                accumulated_edges.append(edge)
                seen_edges.add(key)

    # Compute summary fields
    total_nodes = len(accumulated_nodes)
    dominant_domain = _compute_dominant_domain(accumulated_nodes)
    max_depth = _compute_max_depth(accumulated_nodes, accumulated_edges)
    model_provider, model_name = _extract_model_info(model)

    # Persist
    ripple_map = RippleMapDB(
        id=str(uuid4()),
        timeline_id=timeline_id,
        nodes=[n.model_dump() for n in accumulated_nodes],
        edges=[e.model_dump() for e in accumulated_edges],
        included_generation_ids=[str(g.id) for g in generations],
        total_nodes=total_nodes,
        dominant_domain=dominant_domain,
        max_ripple_depth=max_depth,
        model_provider=model_provider,
        model_name=model_name,
    )
    db.add(ripple_map)
    await db.commit()
    await db.refresh(ripple_map)

    logger.info(
        f"Created ripple map {ripple_map.id} for timeline {timeline_id}: "
        f"{total_nodes} nodes, {len(accumulated_edges)} edges, depth={max_depth}"
    )

    return ripple_map


async def add_generations(
    db: AsyncSession,
    timeline_id: str,
    generation_ids: List[str],
) -> RippleMapDB:
    """
    Add new generations to an existing ripple map.

    Args:
        db: Database session.
        timeline_id: UUID of the parent timeline.
        generation_ids: New generation UUIDs to incorporate.

    Returns:
        Updated RippleMapDB record.

    Raises:
        NotFoundError: If timeline or ripple map not found.
        ValidationError: If all requested generations are already included.
        AIGenerationError: If agent extraction fails.
    """
    # Load timeline
    result = await db.execute(select(TimelineDB).where(TimelineDB.id == timeline_id))
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise NotFoundError(f"Timeline {timeline_id} not found")

    # Load existing ripple map
    result = await db.execute(
        select(RippleMapDB).where(RippleMapDB.timeline_id == timeline_id)
    )
    ripple_map = result.scalar_one_or_none()
    if not ripple_map:
        raise NotFoundError(f"No ripple map found for timeline {timeline_id}")

    # Filter out already-included generations
    already_included = set(ripple_map.included_generation_ids or [])
    new_ids = [gid for gid in generation_ids if gid not in already_included]
    if not new_ids:
        raise ValidationError(
            "All requested generations are already included in the ripple map."
        )

    generations = await _load_and_validate_generations(db, timeline_id, new_ids)

    # Reconstruct existing nodes/edges from DB JSON
    existing_nodes = [CausalNode(**n) for n in (ripple_map.nodes or [])]
    existing_edges = [CausalEdge(**e) for e in (ripple_map.edges or [])]

    # Get per-agent model
    model = None
    try:
        from app.services.llm_service import create_pydantic_ai_model_for_agent
        model = await create_pydantic_ai_model_for_agent(db, AgentType.RIPPLE_ANALYST)
    except Exception:
        logger.debug("No agent LLM config for ripple_analyst, using default")

    from app.agents.ripple_analyst_agent import add_generations_to_ripple_map as agent_add

    deviation_date = str(timeline.root_deviation_date)
    deviation_description = timeline.root_deviation_description
    scenario_type = timeline.scenario_type

    accumulated_nodes = list(existing_nodes)
    accumulated_edges = list(existing_edges)

    for gen in generations:
        add_output = await agent_add(
            existing_nodes=accumulated_nodes,
            existing_edges=accumulated_edges,
            new_generation_content=_build_generation_content(gen),
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            new_generation_id=str(gen.id),
            model=model,
        )

        seen_ids = {n.id for n in accumulated_nodes}
        for node in add_output.nodes:
            if node.id not in seen_ids:
                accumulated_nodes.append(node)
                seen_ids.add(node.id)

        seen_edges = {
            (e.source_node_id, e.target_node_id, e.relationship.value)
            for e in accumulated_edges
        }
        for edge in add_output.edges:
            key = (edge.source_node_id, edge.target_node_id, edge.relationship.value)
            if key not in seen_edges:
                accumulated_edges.append(edge)
                seen_edges.add(key)

    # Update record
    model_provider, model_name = _extract_model_info(model)

    ripple_map.nodes = [n.model_dump() for n in accumulated_nodes]
    ripple_map.edges = [e.model_dump() for e in accumulated_edges]
    ripple_map.included_generation_ids = list(already_included) + [str(g.id) for g in generations]
    ripple_map.total_nodes = len(accumulated_nodes)
    ripple_map.dominant_domain = _compute_dominant_domain(accumulated_nodes)
    ripple_map.max_ripple_depth = _compute_max_depth(accumulated_nodes, accumulated_edges)
    ripple_map.model_provider = model_provider
    ripple_map.model_name = model_name
    ripple_map.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(ripple_map)

    logger.info(
        f"Updated ripple map {ripple_map.id}: "
        f"now {ripple_map.total_nodes} nodes, depth={ripple_map.max_ripple_depth}"
    )

    return ripple_map


async def get_ripple_map(
    db: AsyncSession,
    timeline_id: str,
) -> Optional[RippleMapDB]:
    """
    Retrieve the ripple map for a timeline, or None if none exists.

    Args:
        db: Database session.
        timeline_id: UUID of the parent timeline.

    Returns:
        RippleMapDB record or None.
    """
    result = await db.execute(
        select(RippleMapDB).where(RippleMapDB.timeline_id == timeline_id)
    )
    return result.scalar_one_or_none()


async def delete_ripple_map(
    db: AsyncSession,
    timeline_id: str,
) -> bool:
    """
    Delete the ripple map for a timeline.

    Args:
        db: Database session.
        timeline_id: UUID of the parent timeline.

    Returns:
        True if deleted, False if no map was found.
    """
    ripple_map = await get_ripple_map(db, timeline_id)
    if not ripple_map:
        return False

    await db.delete(ripple_map)
    await db.commit()

    logger.info(f"Deleted ripple map for timeline {timeline_id}")
    return True


# ============================================================================
# Private Helpers
# ============================================================================


async def _load_and_validate_generations(
    db: AsyncSession,
    timeline_id: str,
    generation_ids: List[str],
) -> List[GenerationDB]:
    """
    Load generations by ID and verify they belong to the given timeline.

    Args:
        db: Database session.
        timeline_id: Expected parent timeline UUID.
        generation_ids: Generation UUIDs to load.

    Returns:
        List of GenerationDB records in the requested order.

    Raises:
        NotFoundError: If any generation not found or belongs to another timeline.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(GenerationDB).where(
            GenerationDB.id.in_(generation_ids),
            GenerationDB.timeline_id == timeline_id,
        )
    )
    generations = list(result.scalars().all())

    found_ids = {str(g.id) for g in generations}
    missing = [gid for gid in generation_ids if gid not in found_ids]
    if missing:
        raise NotFoundError(
            f"Generations not found or not part of timeline {timeline_id}: {missing}"
        )

    # Return in requested order
    id_to_gen = {str(g.id): g for g in generations}
    return [id_to_gen[gid] for gid in generation_ids]
