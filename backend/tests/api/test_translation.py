"""
Tests for translation API endpoints.

Tests:
- POST /api/generations/{generation_id}/translate - Translate generation report
- POST /api/generations/{generation_id}/narrative/translate - Translate narrative
- GET /api/translation/usage - Get translation usage statistics
- GET /api/translation/config - Get translation configuration
- PUT /api/translation/config - Update translation configuration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4


# ============================================================================
# POST /api/generations/{generation_id}/translate Tests
# ============================================================================


@pytest.mark.asyncio
async def test_translate_generation_returns_200(
    test_client: TestClient, timeline_with_generation
):
    """Test that translate generation endpoint returns 200 OK."""
    generation_id = timeline_with_generation.generations[0].id

    request_data = {"target_language": "hu", "method": "llm"}

    # Mock translation service
    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_generation.return_value = {
            "executive_summary": "Hungarian translation",
            "political_changes": "Hungarian political",
            "economic_impacts": "Hungarian economic",
            "social_developments": "Hungarian social",
            "technological_shifts": "Hungarian tech",
            "conflicts_and_wars": "Hungarian conflicts",
            "key_figures": "Hungarian figures",
            "long_term_implications": "Hungarian implications",
        }
        mock_service.return_value = mock_instance

        response = test_client.post(
            f"/api/generations/{generation_id}/translate", json=request_data
        )

        # Allow both 200 and 201 status codes
        assert response.status_code in [200, 201]


@pytest.mark.asyncio
async def test_translate_generation_response_structure(
    test_client: TestClient, timeline_with_generation
):
    """Test that translate generation response has correct structure."""
    generation_id = timeline_with_generation.generations[0].id

    request_data = {"target_language": "hu", "method": "llm"}

    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_generation.return_value = {
            "executive_summary": "Test",
            "political_changes": "Test",
            "economic_impacts": "Test",
            "social_developments": "Test",
            "technological_shifts": "Test",
            "conflicts_and_wars": "Test",
            "key_figures": "Test",
            "long_term_implications": "Test",
        }
        mock_service.return_value = mock_instance

        response = test_client.post(
            f"/api/generations/{generation_id}/translate", json=request_data
        )

        data = response.json()

        # Check required keys
        assert "generation_id" in data
        assert "target_language" in data
        assert "translations" in data
        assert "character_count" in data
        assert "cached" in data


def test_translate_generation_not_found_404(test_client: TestClient):
    """Test that translating nonexistent generation returns 404 or 503."""
    nonexistent_id = str(uuid4())
    request_data = {"target_language": "hu", "method": "llm"}

    response = test_client.post(
        f"/api/generations/{nonexistent_id}/translate", json=request_data
    )

    # Can return 503 if translation service not configured, or 404 if not found
    assert response.status_code in [404, 503]


# ============================================================================
# POST /api/generations/{generation_id}/narrative/translate Tests
# ============================================================================


@pytest.mark.asyncio
async def test_translate_narrative_returns_200(
    test_client: TestClient, timeline_with_generation
):
    """Test that translate narrative endpoint returns 200 OK."""
    generation_id = timeline_with_generation.generations[0].id

    request_data = {"target_language": "hu", "method": "llm"}

    # Mock translation service
    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_narrative.return_value = "Hungarian narrative translation"
        mock_service.return_value = mock_instance

        response = test_client.post(
            f"/api/generations/{generation_id}/narrative/translate", json=request_data
        )

        # Allow both 200 and 201 status codes
        assert response.status_code in [200, 201]


@pytest.mark.asyncio
async def test_translate_narrative_response_structure(
    test_client: TestClient, timeline_with_generation
):
    """Test that translate narrative response has correct structure."""
    generation_id = timeline_with_generation.generations[0].id

    request_data = {"target_language": "hu", "method": "llm"}

    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_narrative.return_value = "Test narrative"
        mock_service.return_value = mock_instance

        response = test_client.post(
            f"/api/generations/{generation_id}/narrative/translate", json=request_data
        )

        data = response.json()

        # Check required keys
        assert "generation_id" in data
        assert "target_language" in data
        assert "narrative_prose" in data
        assert "character_count" in data
        assert "cached" in data


def test_translate_narrative_not_found_404(test_client: TestClient):
    """Test that translating narrative of nonexistent generation returns 404 or 503."""
    nonexistent_id = str(uuid4())
    request_data = {"target_language": "hu", "method": "llm"}

    response = test_client.post(
        f"/api/generations/{nonexistent_id}/narrative/translate", json=request_data
    )

    # Can return 503 if translation service not configured, or 404 if not found
    assert response.status_code in [404, 503]


# ============================================================================
# GET /api/translation/usage Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_translation_usage_returns_200(test_client: TestClient):
    """Test that translation usage endpoint returns 200 OK."""
    # Mock translation service
    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_usage_stats.return_value = {
            "year_month": "2025-01",
            "characters_used": 10000,
            "characters_limit": 500000,
            "percentage_used": 2.0,
            "api_calls": 5,
        }
        mock_service.return_value = mock_instance

        response = test_client.get("/api/translation/usage")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_translation_usage_response_structure(test_client: TestClient):
    """Test that translation usage response has correct structure."""
    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_usage_stats.return_value = {
            "year_month": "2025-01",
            "characters_used": 10000,
            "characters_limit": 500000,
            "percentage_used": 2.0,
            "api_calls": 5,
        }
        mock_service.return_value = mock_instance

        response = test_client.get("/api/translation/usage")
        data = response.json()

        # Check required keys
        assert "year_month" in data
        assert "characters_used" in data
        assert "characters_limit" in data
        assert "percentage_used" in data
        assert "api_calls" in data


@pytest.mark.asyncio
async def test_get_translation_usage_with_month_parameter(test_client: TestClient):
    """Test translation usage with specific month parameter."""
    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.get_usage_stats.return_value = {
            "year_month": "2024-12",
            "characters_used": 5000,
            "characters_limit": 500000,
            "percentage_used": 1.0,
            "api_calls": 3,
        }
        mock_service.return_value = mock_instance

        response = test_client.get("/api/translation/usage?month=2024-12")
        assert response.status_code == 200
        data = response.json()
        assert data["year_month"] == "2024-12"


# ============================================================================
# GET /api/translation/config Tests
# ============================================================================


def test_get_translation_config_returns_200(test_client: TestClient):
    """Test that translation config endpoint returns 200 OK."""
    response = test_client.get("/api/translation/config")
    assert response.status_code == 200


def test_get_translation_config_response_structure(test_client: TestClient):
    """Test that translation config response has correct structure."""
    response = test_client.get("/api/translation/config")
    data = response.json()

    # Check required keys
    assert "enabled" in data
    assert "api_tier" in data
    assert "api_key_set" in data
    assert "updated_at" in data


def test_get_translation_config_default_values(test_client: TestClient):
    """Test that translation config returns sensible defaults."""
    response = test_client.get("/api/translation/config")
    data = response.json()

    # Check data types
    assert isinstance(data["enabled"], bool)
    assert isinstance(data["api_key_set"], bool)
    assert data["api_tier"] in ["free", "pro"]


# ============================================================================
# PUT /api/translation/config Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_translation_config_returns_200(test_client: TestClient):
    """Test that update translation config endpoint returns 200 OK."""
    request_data = {"api_key": "test-api-key:fx", "api_tier": "free", "enabled": True}

    response = test_client.put("/api/translation/config", json=request_data)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_translation_config_response_structure(test_client: TestClient):
    """Test that update translation config response has correct structure."""
    request_data = {"api_key": "test-key:fx", "api_tier": "free", "enabled": True}

    response = test_client.put("/api/translation/config", json=request_data)
    data = response.json()

    # Check required keys
    assert "enabled" in data
    assert "api_tier" in data
    assert "api_key_set" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_update_translation_config_enables_service(test_client: TestClient):
    """Test that updating config can enable translation service."""
    request_data = {"api_key": "valid-key:fx", "api_tier": "free", "enabled": True}

    response = test_client.put("/api/translation/config", json=request_data)
    data = response.json()

    assert data["enabled"] == True
    assert data["api_key_set"] == True


@pytest.mark.asyncio
async def test_update_translation_config_validates_tier(test_client: TestClient):
    """Test that invalid API tier is rejected."""
    request_data = {"api_key": "test-key:fx", "api_tier": "invalid", "enabled": True}

    response = test_client.put("/api/translation/config", json=request_data)
    # Should return validation error (422)
    assert response.status_code in [400, 422]


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_translate_generation_invalid_language_422(
    test_client: TestClient, timeline_with_generation
):
    """Test that invalid language code returns 422."""
    generation_id = timeline_with_generation.generations[0].id

    request_data = {"target_language": "invalid_language", "method": "llm"}

    response = test_client.post(
        f"/api/generations/{generation_id}/translate", json=request_data
    )

    # Should return validation error
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_translation_service_error_handling(
    test_client: TestClient, timeline_with_generation
):
    """Test that translation service errors are handled gracefully."""
    generation_id = timeline_with_generation.generations[0].id

    request_data = {"target_language": "hu", "method": "llm"}

    with patch("app.services.translation_service.get_translation_service") as mock_service:
        mock_instance = AsyncMock()
        mock_instance.translate_generation.side_effect = Exception("Service error")
        mock_service.return_value = mock_instance

        response = test_client.post(
            f"/api/generations/{generation_id}/translate", json=request_data
        )

        assert response.status_code == 500


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_translation_config_crud_workflow(test_client: TestClient):
    """Test complete config update and retrieval workflow."""
    # Get initial config
    get_response = test_client.get("/api/translation/config")
    assert get_response.status_code == 200

    # Update config
    update_data = {"api_key": "new-key:fx", "api_tier": "free", "enabled": True}
    put_response = test_client.put("/api/translation/config", json=update_data)
    assert put_response.status_code == 200

    # Verify update
    verify_response = test_client.get("/api/translation/config")
    verify_data = verify_response.json()
    assert verify_data["enabled"] == True
    assert verify_data["api_key_set"] == True
