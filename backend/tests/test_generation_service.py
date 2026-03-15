"""
Tests for generation-related operations.

Tests operations on generations within timelines:
- Generation retrieval
- Generation metadata
- Narrative modes
- Model tracking
"""

import pytest
from uuid import uuid4
from datetime import date

from app.services import timeline_service
from app.models import (
    Timeline,
    Generation,
    GenerationType,
    TimelineOutput,
    ScenarioType,
    NarrativeMode,
)


# ============================================================================
# Helper Functions
# ============================================================================


def _make_timeline(
    deviation_date,
    deviation_description,
    scenario_type,
    period_years=10,
    narrative_mode=NarrativeMode.NONE,
    narrative_custom_pov=None,
    source_skeleton_id=None,
    storyteller_provider=None,
    storyteller_model_name=None,
):
    """Helper to create a Timeline pydantic object for service tests."""
    timeline_id = uuid4()
    gen = Generation(
        timeline_id=timeline_id,
        generation_order=1,
        generation_type=GenerationType.INITIAL,
        start_year=0,
        end_year=period_years,
        period_years=period_years,
        executive_summary="placeholder",
        political_changes="placeholder",
        conflicts_and_wars="placeholder",
        economic_impacts="placeholder",
        social_developments="placeholder",
        technological_shifts="placeholder",
        key_figures="placeholder",
        long_term_implications="placeholder",
        narrative_mode=narrative_mode,
        narrative_custom_pov=narrative_custom_pov,
        source_skeleton_id=source_skeleton_id,
    )
    return Timeline(
        id=timeline_id,
        root_deviation_date=deviation_date if isinstance(deviation_date, date) else date.fromisoformat(deviation_date),
        root_deviation_description=deviation_description,
        scenario_type=scenario_type,
        generations=[gen],
    )


# ============================================================================
# Generation Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_generation_by_id(db_session, timeline_with_generation):
    """Test retrieving a specific generation."""
    generation = timeline_with_generation.generations[0]

    # Retrieve timeline and check generation
    timeline = await timeline_service.get_timeline_by_id(
        db=db_session, timeline_id=timeline_with_generation.id
    )

    found_generation = next(
        (gen for gen in timeline.generations if gen.id == generation.id), None
    )

    assert found_generation is not None
    assert found_generation.id == generation.id
    assert found_generation.generation_order == 1
    assert found_generation.generation_type == GenerationType.INITIAL.value


@pytest.mark.asyncio
async def test_get_latest_generation(db_session, timeline_with_generation):
    """Test getting the latest generation from a timeline."""
    timeline_id = timeline_with_generation.id  # Capture before expire_all()

    # Add an extension
    extension_output = TimelineOutput(
        executive_summary="Extension",
        political_changes="Politics",
        conflicts_and_wars="Conflicts",
        economic_impacts="Economy",
        social_developments="Society",
        technological_shifts="Tech",
        key_figures="Figures",
        long_term_implications="Implications",
    )

    await timeline_service.extend_timeline_with_new_generation(
        db=db_session,
        timeline_id=timeline_id,
        extension_output=extension_output,
        additional_years=10,
        narrative_mode=NarrativeMode.NONE,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    # Expire cached objects then retrieve timeline fresh
    db_session.expire_all()
    timeline = await timeline_service.get_timeline_by_id(
        db=db_session, timeline_id=timeline_id
    )

    # Latest generation should be the extension (order 2)
    latest = max(timeline.generations, key=lambda g: g.generation_order)
    assert latest.generation_order == 2
    assert latest.generation_type == GenerationType.EXTENSION.value


# ============================================================================
# Narrative Mode Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generation_with_no_narrative(db_session, sample_timeline_data):
    """Test generation with no narrative mode."""
    timeline_output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
        narrative_prose=None,
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.NONE,
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert generation.narrative_mode == NarrativeMode.NONE.value
    assert generation.narrative_prose is None


@pytest.mark.asyncio
async def test_generation_with_basic_narrative(db_session, sample_timeline_data):
    """Test generation with basic narrative mode."""
    timeline_output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
        narrative_prose="This is the basic narrative story...",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.BASIC,
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert generation.narrative_mode == NarrativeMode.BASIC.value
    assert generation.narrative_prose == "This is the basic narrative story..."
    assert generation.narrative_custom_pov is None


@pytest.mark.asyncio
async def test_generation_with_advanced_omniscient_narrative(db_session, sample_timeline_data):
    """Test generation with advanced omniscient narrative mode."""
    timeline_output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
        narrative_prose="From an omniscient perspective, the world changed...",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.ADVANCED_OMNISCIENT,
        storyteller_provider="google",
        storyteller_model_name="gemini-pro",
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
        storyteller_provider="google",
        storyteller_model_name="gemini-pro",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert generation.narrative_mode == NarrativeMode.ADVANCED_OMNISCIENT.value
    assert generation.narrative_prose is not None
    assert generation.narrative_model_provider == "google"
    assert generation.narrative_model_name == "gemini-pro"


@pytest.mark.asyncio
async def test_generation_with_advanced_custom_pov_narrative(db_session, sample_timeline_data):
    """Test generation with advanced custom POV narrative mode."""
    timeline_output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
        narrative_prose="As a Viennese journalist, I witnessed...",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.ADVANCED_CUSTOM_POV,
        narrative_custom_pov="A young Viennese journalist working for Die Presse",
        storyteller_provider="openrouter",
        storyteller_model_name="anthropic/claude-3-sonnet",
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
        storyteller_provider="openrouter",
        storyteller_model_name="anthropic/claude-3-sonnet",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert generation.narrative_mode == NarrativeMode.ADVANCED_CUSTOM_POV.value
    assert generation.narrative_prose is not None
    assert generation.narrative_custom_pov == "A young Viennese journalist working for Die Presse"
    assert generation.narrative_model_provider == "openrouter"


# ============================================================================
# Model Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generation_tracks_historian_model(db_session, sample_timeline_data):
    """Test that generation tracks which historian model was used."""
    timeline_output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.NONE,
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="openrouter",
        historian_model_name="anthropic/claude-3-opus",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert generation.report_model_provider == "openrouter"
    assert generation.report_model_name == "anthropic/claude-3-opus"


@pytest.mark.asyncio
async def test_generation_tracks_separate_narrative_model(db_session, sample_timeline_data):
    """Test that generation can track separate models for report and narrative."""
    timeline_output = TimelineOutput(
        executive_summary="Test",
        political_changes="Test",
        conflicts_and_wars="Test",
        economic_impacts="Test",
        social_developments="Test",
        technological_shifts="Test",
        key_figures="Test",
        long_term_implications="Test",
        narrative_prose="Narrative text",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.ADVANCED_OMNISCIENT,
        storyteller_provider="openrouter",
        storyteller_model_name="anthropic/claude-3-sonnet",
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
        storyteller_provider="openrouter",
        storyteller_model_name="anthropic/claude-3-sonnet",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    # Report should track historian
    assert generation.report_model_provider == "google"
    assert generation.report_model_name == "gemini-pro"
    # Narrative should track storyteller
    assert generation.narrative_model_provider == "openrouter"
    assert generation.narrative_model_name == "anthropic/claude-3-sonnet"


# ============================================================================
# Generation Period Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generation_period_calculation(db_session, timeline_with_generation):
    """Test that generation period fields are correctly set."""
    generation = timeline_with_generation.generations[0]

    assert generation.start_year == 0
    assert generation.end_year == 10
    assert generation.period_years == 10


@pytest.mark.asyncio
async def test_extension_generation_period(db_session, timeline_with_generation):
    """Test that extension generation periods are sequential."""
    # First generation: 0-10
    first_gen = timeline_with_generation.generations[0]
    assert first_gen.start_year == 0
    assert first_gen.end_year == 10

    # Add extension: should be 10-25
    extension_output = TimelineOutput(
        executive_summary="Extension",
        political_changes="Politics",
        conflicts_and_wars="Conflicts",
        economic_impacts="Economy",
        social_developments="Society",
        technological_shifts="Tech",
        key_figures="Figures",
        long_term_implications="Implications",
    )

    extension_gen = await timeline_service.extend_timeline_with_new_generation(
        db=db_session,
        timeline_id=timeline_with_generation.id,
        extension_output=extension_output,
        additional_years=15,
        narrative_mode=NarrativeMode.NONE,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    assert extension_gen.start_year == 10
    assert extension_gen.end_year == 25
    assert extension_gen.period_years == 15


# ============================================================================
# Source Skeleton Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generation_tracks_source_skeleton(db_session, skeleton_with_events):
    """Test that generation tracks which skeleton was used."""
    from uuid import UUID

    timeline_output = TimelineOutput(
        executive_summary="From skeleton",
        political_changes="Politics",
        conflicts_and_wars="Conflicts",
        economic_impacts="Economy",
        social_developments="Society",
        technological_shifts="Tech",
        key_figures="Figures",
        long_term_implications="Implications",
    )

    timeline_obj = _make_timeline(
        deviation_date=skeleton_with_events.deviation_date,
        deviation_description=skeleton_with_events.deviation_description,
        scenario_type=ScenarioType(skeleton_with_events.scenario_type),
        period_years=10,
        narrative_mode=NarrativeMode.NONE,
        source_skeleton_id=UUID(skeleton_with_events.id),
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert str(generation.source_skeleton_id) == skeleton_with_events.id


@pytest.mark.asyncio
async def test_generation_without_skeleton(db_session, sample_timeline_data):
    """Test generation created without skeleton has no source_skeleton_id."""
    timeline_output = TimelineOutput(
        executive_summary="Direct generation",
        political_changes="Politics",
        conflicts_and_wars="Conflicts",
        economic_impacts="Economy",
        social_developments="Society",
        technological_shifts="Tech",
        key_figures="Figures",
        long_term_implications="Implications",
    )

    timeline_obj = _make_timeline(
        deviation_date="1914-06-28",
        deviation_description=sample_timeline_data["root_deviation_description"],
        scenario_type=ScenarioType.LOCAL_DEVIATION,
        period_years=10,
        narrative_mode=NarrativeMode.NONE,
    )

    created = await timeline_service.create_timeline_with_initial_generation(
        db=db_session,
        timeline=timeline_obj,
        initial_generation_output=timeline_output,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )
    timeline = await timeline_service.get_timeline_by_id(db=db_session, timeline_id=created.id)

    generation = timeline.generations[0]
    assert generation.source_skeleton_id is None
