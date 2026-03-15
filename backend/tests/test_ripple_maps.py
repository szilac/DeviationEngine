"""
Tests for Ripple Map models, DB, and service helpers.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CausalDomain,
    CausalEdge,
    CausalNode,
    ConfidenceLevel,
    EdgeStrength,
    EffectDuration,
    CausalRelationship,
    TimeDelay,
    RippleMapOutput,
    RippleMapResponse,
)
from app.db_models import RippleMapDB, GenerationDB
from app.services.ripple_map_service import (
    _build_generation_content,
    _compute_dominant_domain,
    _compute_max_depth,
)


# ============================================================================
# Helpers
# ============================================================================


def make_node(
    node_id: str,
    domain: CausalDomain = CausalDomain.POLITICAL,
    magnitude: int = 3,
    is_deviation_point: bool = False,
    source_generation_id: str = "gen-001",
    time_offset_years: float = 0.0,
) -> CausalNode:
    return CausalNode(
        id=node_id,
        label="Test node label",
        description="A two-sentence description. This is the second sentence.",
        domain=domain,
        sub_domain="test sub-domain",
        magnitude=magnitude,
        confidence=ConfidenceLevel.HIGH,
        time_offset_years=time_offset_years,
        duration=EffectDuration.LONG_TERM,
        affected_regions=["Europe"],
        key_figures=[],
        is_deviation_point=is_deviation_point,
        source_generation_id=source_generation_id,
    )


def make_edge(source: str, target: str) -> CausalEdge:
    return CausalEdge(
        source_node_id=source,
        target_node_id=target,
        relationship=CausalRelationship.CAUSES,
        strength=EdgeStrength.DIRECT,
        description="Source directly causes target",
        time_delay=TimeDelay.YEARS,
    )


# ============================================================================
# Test 1: Valid model construction
# ============================================================================


def test_ripple_map_models_valid():
    """CausalNode and CausalEdge accept valid data and expose correct fields."""
    node = make_node("node_001", domain=CausalDomain.ECONOMIC, magnitude=5)
    assert node.id == "node_001"
    assert node.domain == CausalDomain.ECONOMIC
    assert node.magnitude == 5
    assert node.confidence == ConfidenceLevel.HIGH
    assert node.affected_regions == ["Europe"]

    edge = make_edge("node_001", "node_002")
    assert edge.source_node_id == "node_001"
    assert edge.relationship == CausalRelationship.CAUSES
    assert edge.strength == EdgeStrength.DIRECT

    output = RippleMapOutput(nodes=[node], edges=[edge])
    assert len(output.nodes) == 1
    assert len(output.edges) == 1


# ============================================================================
# Test 2: Invalid magnitude raises ValidationError
# ============================================================================


def test_ripple_map_models_invalid_magnitude():
    """magnitude must be between 1 and 5; 6 should raise ValidationError."""
    with pytest.raises(PydanticValidationError):
        CausalNode(
            id="bad",
            label="Bad node",
            description="A. B.",
            domain=CausalDomain.MILITARY,
            sub_domain="test",
            magnitude=6,  # Invalid
            confidence=ConfidenceLevel.MEDIUM,
            time_offset_years=1.0,
            duration=EffectDuration.SHORT_TERM,
            source_generation_id="gen-001",
        )


def test_ripple_map_models_invalid_magnitude_zero():
    """magnitude=0 should also fail."""
    with pytest.raises(PydanticValidationError):
        CausalNode(
            id="bad",
            label="Bad node",
            description="A. B.",
            domain=CausalDomain.SOCIAL,
            sub_domain="test",
            magnitude=0,  # Invalid
            confidence=ConfidenceLevel.HIGH,
            time_offset_years=2.0,
            duration=EffectDuration.PERMANENT,
            source_generation_id="gen-001",
        )


# ============================================================================
# Test 3: DB model creation
# ============================================================================


@pytest.mark.asyncio
async def test_ripple_map_db_creation(db_session: AsyncSession, timeline_with_generation):
    """RippleMapDB can be created and retrieved from an in-memory DB."""
    timeline = timeline_with_generation
    timeline_id = str(timeline.id)

    node = make_node("n1", is_deviation_point=True)
    edge = make_edge("n1", "n2")

    ripple_map = RippleMapDB(
        id=str(uuid4()),
        timeline_id=timeline_id,
        nodes=[node.model_dump()],
        edges=[edge.model_dump()],
        included_generation_ids=["gen-001"],
        total_nodes=1,
        dominant_domain="political",
        max_ripple_depth=1,
        model_provider="google",
        model_name="gemini-2.5-flash",
    )
    db_session.add(ripple_map)
    await db_session.flush()

    from sqlalchemy import select
    result = await db_session.execute(
        select(RippleMapDB).where(RippleMapDB.timeline_id == timeline_id)
    )
    fetched = result.scalar_one_or_none()

    assert fetched is not None
    assert fetched.total_nodes == 1
    assert fetched.dominant_domain == "political"
    assert len(fetched.nodes) == 1
    assert fetched.nodes[0]["id"] == "n1"
    assert fetched.max_ripple_depth == 1


# ============================================================================
# Test 4: BFS max depth helper
# ============================================================================


def test_compute_max_depth_simple_chain():
    """_compute_max_depth returns correct depth for a simple linear chain."""
    nodes = [
        make_node("root", is_deviation_point=True),
        make_node("n1"),
        make_node("n2"),
        make_node("n3"),
    ]
    edges = [
        make_edge("root", "n1"),
        make_edge("n1", "n2"),
        make_edge("n2", "n3"),
    ]
    depth = _compute_max_depth(nodes, edges)
    assert depth == 3


def test_compute_max_depth_no_deviation_point():
    """Returns 0 if no deviation-point node exists."""
    nodes = [make_node("n1"), make_node("n2")]
    edges = [make_edge("n1", "n2")]
    assert _compute_max_depth(nodes, edges) == 0


def test_compute_max_depth_branching():
    """Picks the longer branch in a branching graph."""
    nodes = [
        make_node("root", is_deviation_point=True),
        make_node("a"),
        make_node("b"),
        make_node("c"),  # longer branch: root → a → c
    ]
    edges = [
        make_edge("root", "a"),
        make_edge("root", "b"),
        make_edge("a", "c"),
    ]
    depth = _compute_max_depth(nodes, edges)
    assert depth == 2


# ============================================================================
# Test 5: Dominant domain helper
# ============================================================================


def test_compute_dominant_domain():
    """Returns the domain with the most high-magnitude (4+) nodes."""
    nodes = [
        make_node("p1", domain=CausalDomain.POLITICAL, magnitude=4),
        make_node("p2", domain=CausalDomain.POLITICAL, magnitude=5),
        make_node("e1", domain=CausalDomain.ECONOMIC, magnitude=4),
        make_node("s1", domain=CausalDomain.SOCIAL, magnitude=2),  # low — not counted
    ]
    result = _compute_dominant_domain(nodes)
    assert result == "political"


def test_compute_dominant_domain_empty():
    """Returns None for empty node list."""
    assert _compute_dominant_domain([]) is None


# ============================================================================
# Test 6: _build_generation_content
# ============================================================================


def test_build_generation_content(timeline_with_generation):
    """All 8 sections present in the generation appear in the output string."""
    generation = timeline_with_generation.generations[0]
    content = _build_generation_content(generation)

    assert "## Executive Summary" in content
    assert "## Political Changes" in content
    assert "## Economic Impacts" in content
    assert "## Social Developments" in content
    assert "## Technological Shifts" in content
    assert "## Key Figures" in content
    assert "## Long-term Implications" in content
    # Conflicts section name
    assert "## Conflicts and Wars" in content
