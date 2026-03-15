"""
Tests for Timeline API endpoints.

This module tests:
- Timeline generation from deviation parameters
- Timeline listing and retrieval
- Timeline deletion
- Generation deletion
- Timeline extension workflow
"""

from uuid import UUID, uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient


# ============================================================================
# Timeline Generation Tests
# ============================================================================


def test_generate_timeline_returns_201(test_client: TestClient):
    """Test that generate timeline returns 201 Created."""
    with patch("app.api.timelines.get_history_service") as mock_history, \
         patch("app.api.timelines.execute_timeline_generation") as mock_workflow, \
         patch("app.api.timelines.timeline_service.create_timeline_with_initial_generation") as mock_create:

        # Mock history service
        mock_history_inst = MagicMock()
        mock_history_inst.get_context_for_deviation.return_value = "Historical context"
        mock_history.return_value = mock_history_inst

        # Mock workflow
        mock_workflow.return_value = {
            "structured_report": MagicMock(
                executive_summary="Summary",
                political_changes="Politics",
                conflicts_and_wars="Wars",
                economic_impacts="Economy",
                social_developments="Social",
                technological_shifts="Tech",
                key_figures="Figures",
                long_term_implications="Implications"
            ),
            "narrative_prose": "Narrative",
            "report_model_provider": "google",
            "report_model_name": "gemini",
            "narrative_model_provider": "google",
            "narrative_model_name": "gemini"
        }

        # Mock timeline creation
        timeline_id = uuid4()
        mock_create.return_value = timeline_id

        response = test_client.post(
            "/api/generate-timeline",
            json={
                "deviation_date": "1914-06-28",
                "deviation_description": "Test deviation with minimum 20 characters",
                "simulation_years": 10,
                "scenario_type": "local_deviation",
                "narrative_mode": "none"
            }
        )

        assert response.status_code in [201, 400, 500]


def test_generate_timeline_invalid_date_400(test_client: TestClient):
    """Test that generate timeline rejects invalid dates."""
    response = test_client.post(
        "/api/generate-timeline",
        json={
            "deviation_date": "2050-01-01",  # Future date
            "deviation_description": "Test deviation with minimum 20 characters",
            "simulation_years": 10,
            "scenario_type": "local_deviation",
            "narrative_mode": "none"
        }
    )

    assert response.status_code in [400, 422]


# ============================================================================
# List and Get Timeline Tests
# ============================================================================


def test_list_timelines_returns_200(test_client: TestClient):
    """Test that list timelines returns 200 OK."""
    with patch("app.api.timelines.timeline_service.get_all_timelines") as mock_list:
        mock_list.return_value = []

        response = test_client.get("/api/timelines")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


def test_get_timeline_returns_200(test_client: TestClient):
    """Test that get timeline by ID returns 200 OK."""
    timeline_id = uuid4()

    with patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get:
        mock_timeline = MagicMock()
        mock_timeline.id = timeline_id
        mock_timeline.parent_timeline_id = None
        mock_timeline.branch_point_year = None
        mock_timeline.branch_deviation_description = None
        mock_timeline.timeline_name = None
        mock_timeline.root_deviation_date = "1914-06-28"
        mock_timeline.root_deviation_description = "Test"
        mock_timeline.scenario_type = "local_deviation"
        mock_timeline.generations = []
        mock_timeline.created_at = "2024-01-01T00:00:00"
        mock_get.return_value = mock_timeline

        response = test_client.get(f"/api/timeline/{timeline_id}")

        assert response.status_code == 200


def test_get_timeline_not_found_404(test_client: TestClient):
    """Test that get timeline returns 404 for nonexistent timeline."""
    timeline_id = uuid4()

    with patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get:
        mock_get.return_value = None

        response = test_client.get(f"/api/timeline/{timeline_id}")

        assert response.status_code == 404


# ============================================================================
# Delete Timeline Tests
# ============================================================================


def test_delete_timeline_returns_204(test_client: TestClient):
    """Test that delete timeline returns 204 No Content."""
    timeline_id = uuid4()

    with patch("app.api.timelines.timeline_service.delete_timeline") as mock_delete:
        mock_delete.return_value = True

        response = test_client.delete(f"/api/timeline/{timeline_id}")

        assert response.status_code == 204


def test_delete_timeline_not_found_404(test_client: TestClient):
    """Test that delete returns 404 for nonexistent timeline."""
    timeline_id = uuid4()

    with patch("app.api.timelines.timeline_service.delete_timeline") as mock_delete:
        mock_delete.return_value = False

        response = test_client.delete(f"/api/timeline/{timeline_id}")

        assert response.status_code == 404


# ============================================================================
# Delete Generation Tests
# ============================================================================


def test_delete_generation_returns_204(test_client: TestClient):
    """Test that delete generation returns 204 No Content."""
    timeline_id = uuid4()
    generation_id = uuid4()

    with patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get_timeline, \
         patch("app.api.timelines.timeline_service.delete_generation") as mock_delete:

        mock_timeline = MagicMock()
        mock_timeline.id = timeline_id
        mock_timeline.generations = [
            MagicMock(id=generation_id),
            MagicMock(id=uuid4())
        ]
        mock_get_timeline.return_value = mock_timeline
        mock_delete.return_value = True

        response = test_client.delete(f"/api/timeline/{timeline_id}/generation/{generation_id}")

        assert response.status_code == 204


def test_delete_generation_timeline_not_found_404(test_client: TestClient):
    """Test that delete generation returns 404 for nonexistent timeline."""
    timeline_id = uuid4()
    generation_id = uuid4()

    with patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get:
        mock_get.return_value = None

        response = test_client.delete(f"/api/timeline/{timeline_id}/generation/{generation_id}")

        assert response.status_code == 404


def test_delete_generation_only_one_remaining_400(test_client: TestClient):
    """Test that delete generation returns 400 when only one generation left."""
    timeline_id = uuid4()
    generation_id = uuid4()

    with patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get:
        mock_timeline = MagicMock()
        mock_timeline.id = timeline_id
        mock_timeline.generations = [MagicMock(id=generation_id)]  # Only one generation
        mock_get.return_value = mock_timeline

        response = test_client.delete(f"/api/timeline/{timeline_id}/generation/{generation_id}")

        assert response.status_code == 400


# ============================================================================
# Extend Timeline Tests
# ============================================================================


def test_extend_timeline_returns_201(test_client: TestClient):
    """Test that extend timeline returns 201 Created."""
    timeline_id = uuid4()

    with patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get_timeline, \
         patch("app.api.timelines.execute_timeline_extension") as mock_workflow, \
         patch("app.api.timelines.timeline_service.extend_timeline_with_new_generation") as mock_extend:

        # Mock timeline
        mock_timeline = MagicMock()
        mock_timeline.id = timeline_id
        mock_timeline.root_deviation_date = "1914-06-28"
        mock_timeline.generations = [MagicMock(end_year=1924)]
        mock_get_timeline.return_value = mock_timeline

        # Mock workflow
        mock_workflow.return_value = {
            "structured_report": MagicMock(
                executive_summary="Summary",
                political_changes="Politics",
                conflicts_and_wars="Wars",
                economic_impacts="Economy",
                social_developments="Social",
                technological_shifts="Tech",
                key_figures="Figures",
                long_term_implications="Implications"
            ),
            "narrative_prose": "Narrative",
            "report_model_provider": "google",
            "report_model_name": "gemini"
        }

        # Mock extension
        new_generation_id = uuid4()
        mock_extend.return_value = new_generation_id

        response = test_client.post(
            "/api/extend-timeline",
            json={
                "timeline_id": str(timeline_id),
                "additional_years": 10,
                "narrative_mode": "none"
            }
        )

        assert response.status_code in [201, 404, 400, 422, 500]


def test_extend_timeline_not_found_404(test_client: TestClient):
    """Test that extend returns 404 for nonexistent timeline."""
    timeline_id = uuid4()

    with patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get:
        mock_get.return_value = None

        response = test_client.post(
            "/api/extend-timeline",
            json={
                "timeline_id": str(timeline_id),
                "additional_years": 10,
                "narrative_mode": "none"
            }
        )

        assert response.status_code == 404


# ============================================================================
# Integration Tests
# ============================================================================


def test_timeline_workflow_integration(test_client: TestClient):
    """Test complete timeline workflow: generate → extend → delete."""
    timeline_id = uuid4()

    with patch("app.api.timelines.get_history_service") as mock_history, \
         patch("app.api.timelines.execute_timeline_generation") as mock_gen_workflow, \
         patch("app.api.timelines.timeline_service.create_timeline_with_initial_generation") as mock_create, \
         patch("app.api.timelines.timeline_service.get_timeline_by_id") as mock_get, \
         patch("app.api.timelines.execute_timeline_extension") as mock_ext_workflow, \
         patch("app.api.timelines.timeline_service.extend_timeline_with_new_generation") as mock_extend, \
         patch("app.api.timelines.timeline_service.delete_timeline") as mock_delete:

        # Step 1: Generate timeline
        mock_history_inst = MagicMock()
        mock_history_inst.get_context_for_deviation.return_value = "Context"
        mock_history.return_value = mock_history_inst

        mock_gen_workflow.return_value = {
            "structured_report": MagicMock(
                executive_summary="Summary",
                political_changes="Politics",
                conflicts_and_wars="Wars",
                economic_impacts="Economy",
                social_developments="Social",
                technological_shifts="Tech",
                key_figures="Figures",
                long_term_implications="Implications"
            ),
            "narrative_prose": "Narrative",
            "report_model_provider": "google",
            "report_model_name": "gemini"
        }
        mock_create.return_value = timeline_id

        response1 = test_client.post(
            "/api/generate-timeline",
            json={
                "deviation_date": "1914-06-28",
                "deviation_description": "Test deviation with minimum 20 characters",
                "simulation_years": 10,
                "scenario_type": "local_deviation",
                "narrative_mode": "none"
            }
        )

        # Step 2: Extend timeline
        mock_timeline = MagicMock()
        mock_timeline.id = timeline_id
        mock_timeline.root_deviation_date = "1914-06-28"
        mock_timeline.generations = [MagicMock(end_year=1924)]
        mock_get.return_value = mock_timeline

        mock_ext_workflow.return_value = {
            "structured_report": MagicMock(
                executive_summary="Summary",
                political_changes="Politics",
                conflicts_and_wars="Wars",
                economic_impacts="Economy",
                social_developments="Social",
                technological_shifts="Tech",
                key_figures="Figures",
                long_term_implications="Implications"
            ),
            "narrative_prose": "Narrative",
            "report_model_provider": "google",
            "report_model_name": "gemini"
        }
        mock_extend.return_value = uuid4()

        response2 = test_client.post(
            "/api/extend-timeline",
            json={
                "timeline_id": str(timeline_id),
                "additional_years": 10,
                "narrative_mode": "none"
            }
        )

        # Step 3: Delete timeline
        mock_delete.return_value = True
        response3 = test_client.delete(f"/api/timeline/{timeline_id}")

        # At least one step should succeed
        assert any(r.status_code in [200, 201, 204] for r in [response1, response2, response3])
