"""
Tests for character profile consistency logic.
"""
import pytest
from types import SimpleNamespace
from app.services.character_service import _find_nearest_profile
from app.prompt_templates import render_prompt


def make_profile(cutoff_year: int):
    """Create a minimal duck-typed profile object for testing."""
    return SimpleNamespace(cutoff_year=cutoff_year)


# ============================================================================
# _find_nearest_profile
# ============================================================================


def test_returns_none_when_no_profiles():
    assert _find_nearest_profile([], target_year=1940) is None


def test_returns_none_when_only_profile_is_excluded():
    profiles = [make_profile(1940)]
    assert _find_nearest_profile(profiles, target_year=1940, exclude_year=1940) is None


def test_returns_single_non_excluded_profile():
    profiles = [make_profile(1930)]
    result = _find_nearest_profile(profiles, target_year=1940, exclude_year=1940)
    assert result.cutoff_year == 1930


def test_returns_nearest_by_distance():
    profiles = [make_profile(1910), make_profile(1935), make_profile(1960)]
    result = _find_nearest_profile(profiles, target_year=1940, exclude_year=1940)
    assert result.cutoff_year == 1935


def test_excludes_exact_year_match():
    profiles = [make_profile(1940), make_profile(1935)]
    result = _find_nearest_profile(profiles, target_year=1940, exclude_year=1940)
    assert result.cutoff_year == 1935


def test_no_exclude_year_returns_nearest_including_exact_match():
    profiles = [make_profile(1940), make_profile(1910)]
    result = _find_nearest_profile(profiles, target_year=1940)
    assert result.cutoff_year == 1940


# ============================================================================
# Prompt template rendering
# ============================================================================


def test_prompt_renders_without_existing_biography():
    prompt = render_prompt(
        "character_profiler/user_generate.jinja2",
        character_name="Winston Churchill",
        character_title="Prime Minister",
        character_era="1920-1940",
        timeline_content="Timeline goes here.",
        deviation_date="1914-08-01",
        deviation_description="WWI never starts",
        scenario_type="local_deviation",
        existing_biography=None,
    )
    assert "Winston Churchill" in prompt
    assert "Existing Profile Reference" not in prompt


def test_prompt_renders_with_existing_biography():
    bio = "Born in 1874 at Blenheim Palace, Churchill showed early aptitude..."
    prompt = render_prompt(
        "character_profiler/user_generate.jinja2",
        character_name="Winston Churchill",
        character_title="Prime Minister",
        character_era="1920-1940",
        timeline_content="Timeline goes here.",
        deviation_date="1914-08-01",
        deviation_description="WWI never starts",
        scenario_type="local_deviation",
        existing_biography=bio,
    )
    assert "Existing Profile Reference" in prompt
    assert bio in prompt
    assert "canonical" in prompt
