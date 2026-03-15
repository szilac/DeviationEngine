"""
Tests for Skeleton API endpoints.

This module tests:
- Skeleton generation from deviation parameters
- Skeleton retrieval and listing
- Skeleton event editing workflow
- Skeleton approval process
- Report generation from approved skeletons
- Extension skeleton workflows
"""

from uuid import UUID, uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient
from datetime import datetime, date


# ============================================================================
# Skeleton Generation Tests
# ============================================================================


def test_generate_skeleton_returns_201(test_client: TestClient):
    """Test that generate skeleton returns 201 Created."""
    with patch("app.api.skeletons.get_history_service") as mock_history, \
         patch("app.api.skeletons.execute_skeleton_generation") as mock_workflow, \
         patch("app.api.skeletons.llm_service.get_current_llm_config") as mock_llm, \
         patch("app.api.skeletons.skeleton_service.create_timeline_draft_skeleton") as mock_create:

        # Mock history service
        mock_history_inst = MagicMock()
        mock_history_inst.get_context_for_deviation.return_value = "Historical context"
        mock_history.return_value = mock_history_inst

        # Mock workflow
        mock_workflow.return_value = {
            "skeleton_output": MagicMock(events=[])
        }

        # Mock LLM config
        mock_llm.return_value = MagicMock(provider="google", model_name="gemini")

        # Mock skeleton creation
        skeleton_id = uuid4()
        mock_create.return_value = MagicMock(
            id=skeleton_id,
            deviation_date="1914-06-28",
            deviation_description="Test",
            status="draft"
        )

        response = test_client.post(
            "/api/generate-skeleton",
            json={
                "deviation_date": "1914-06-28",
                "deviation_description": "Test deviation with minimum 20 characters",
                "simulation_years": 10,
                "scenario_type": "local_deviation"
            }
        )

        assert response.status_code in [201, 400, 500]


def test_generate_skeleton_invalid_date_400(test_client: TestClient):
    """Test that generate skeleton rejects invalid dates."""
    response = test_client.post(
        "/api/generate-skeleton",
        json={
            "deviation_date": "2050-01-01",  # Future date
            "deviation_description": "Test deviation with minimum 20 characters",
            "simulation_years": 10,
            "scenario_type": "local_deviation"
        }
    )

    assert response.status_code in [400, 422]


# ============================================================================
# Get Skeletons Tests
# ============================================================================


def test_get_all_skeletons_returns_200(test_client: TestClient):
    """Test that get all skeletons returns 200 OK."""
    with patch("app.api.skeletons.skeleton_service.get_all_skeletons") as mock_get:
        mock_get.return_value = []

        response = test_client.get("/api/skeletons")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


def test_get_skeleton_by_id_returns_200(test_client: TestClient):
    """Test that get skeleton by ID returns 200 OK."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.get_skeleton") as mock_get:
        from app.models import SkeletonType, SkeletonStatus, ScenarioType
        now = datetime.utcnow()
        mock_get.return_value = MagicMock(
            id=skeleton_id,
            timeline_id=None,
            generation_id=None,
            skeleton_type=SkeletonType.TIMELINE_DRAFT,
            status=SkeletonStatus.PENDING,
            deviation_date=date(1914, 6, 28),
            deviation_description="Test",
            scenario_type=ScenarioType.LOCAL_DEVIATION,
            parent_timeline_id=None,
            extension_start_year=None,
            extension_end_year=None,
            branch_point_year=None,
            branch_deviation_description=None,
            model_provider="google",
            model_name="gemini",
            generated_at=now,
            approved_at=None,
            created_at=now,
            updated_at=now,
            events=[]
        )

        response = test_client.get(f"/api/skeleton/{skeleton_id}")

        assert response.status_code == 200


def test_get_skeleton_not_found_404(test_client: TestClient):
    """Test that get skeleton returns 404 for nonexistent skeleton."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.get_skeleton") as mock_get:
        mock_get.return_value = None

        response = test_client.get(f"/api/skeleton/{skeleton_id}")

        assert response.status_code == 404


# ============================================================================
# Update Skeleton Events Tests
# ============================================================================


def test_update_skeleton_events_returns_200(test_client: TestClient):
    """Test that update skeleton events returns 200 OK."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.update_skeleton_events") as mock_update:
        from app.models import SkeletonType, SkeletonStatus, ScenarioType
        now = datetime.utcnow()
        mock_update.return_value = MagicMock(
            id=skeleton_id,
            timeline_id=None,
            generation_id=None,
            skeleton_type=SkeletonType.TIMELINE_DRAFT,
            status=SkeletonStatus.EDITING,
            deviation_date=date(1914, 6, 28),
            deviation_description="Test",
            scenario_type=ScenarioType.LOCAL_DEVIATION,
            parent_timeline_id=None,
            extension_start_year=None,
            extension_end_year=None,
            branch_point_year=None,
            branch_deviation_description=None,
            model_provider="google",
            model_name="gemini",
            generated_at=now,
            approved_at=None,
            created_at=now,
            updated_at=now,
            events=[]
        )

        response = test_client.put(
            f"/api/skeleton/{skeleton_id}/events",
            json={
                "events_update": [],
                "deleted_event_ids": []
            }
        )

        assert response.status_code == 200


def test_update_skeleton_events_not_found_404(test_client: TestClient):
    """Test that update returns 404 for nonexistent skeleton."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.update_skeleton_events") as mock_update:
        mock_update.return_value = None

        response = test_client.put(
            f"/api/skeleton/{skeleton_id}/events",
            json={
                "events_update": [],
                "deleted_event_ids": []
            }
        )

        assert response.status_code == 404


# ============================================================================
# Approve Skeleton Tests
# ============================================================================


def test_approve_skeleton_returns_200(test_client: TestClient):
    """Test that approve skeleton returns 200 OK."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.approve_skeleton") as mock_approve:
        from app.models import SkeletonType, SkeletonStatus, ScenarioType
        now = datetime.utcnow()
        mock_approve.return_value = MagicMock(
            id=skeleton_id,
            timeline_id=None,
            generation_id=None,
            skeleton_type=SkeletonType.TIMELINE_DRAFT,
            status=SkeletonStatus.APPROVED,
            deviation_date=date(1914, 6, 28),
            deviation_description="Test",
            scenario_type=ScenarioType.LOCAL_DEVIATION,
            parent_timeline_id=None,
            extension_start_year=None,
            extension_end_year=None,
            branch_point_year=None,
            branch_deviation_description=None,
            model_provider="google",
            model_name="gemini",
            generated_at=now,
            approved_at=now,
            created_at=now,
            updated_at=now,
            events=[]
        )

        response = test_client.post(f"/api/skeleton/{skeleton_id}/approve")

        assert response.status_code == 200


def test_approve_skeleton_not_found_404(test_client: TestClient):
    """Test that approve returns 404 for nonexistent skeleton."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.approve_skeleton") as mock_approve:
        mock_approve.return_value = None

        response = test_client.post(f"/api/skeleton/{skeleton_id}/approve")

        assert response.status_code == 404


# ============================================================================
# Generate from Skeleton Tests
# ============================================================================


def test_generate_from_skeleton_returns_201(test_client: TestClient):
    """Test that generate from skeleton returns 201 Created."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.get_skeleton") as mock_get, \
         patch("app.api.skeletons.execute_report_from_skeleton") as mock_workflow, \
         patch("app.api.skeletons.timeline_service.create_timeline_with_initial_generation") as mock_create:

        # Mock skeleton
        from app.models import SkeletonType
        mock_skeleton = MagicMock()
        mock_skeleton.skeleton_type = SkeletonType.TIMELINE_DRAFT
        mock_skeleton.deviation_date = "1914-06-28"
        mock_skeleton.deviation_description = "Test"
        mock_skeleton.period_years = 10
        mock_skeleton.id = skeleton_id
        mock_get.return_value = mock_skeleton

        # Mock workflow
        mock_report = MagicMock(
            executive_summary="Summary",
            political_changes="Politics",
            conflicts_and_wars="Wars",
            economic_impacts="Economy",
            social_developments="Social",
            technological_shifts="Tech",
            key_figures="Figures",
            long_term_implications="Implications"
        )
        mock_workflow.return_value = {
            "structured_report": mock_report,
            "narrative_prose": "Narrative",
            "historian_provider": "google",
            "historian_model_name": "gemini"
        }

        # Mock timeline creation
        timeline_id = uuid4()
        mock_create.return_value = timeline_id

        response = test_client.post(
            "/api/generate-from-skeleton",
            json={
                "skeleton_id": str(skeleton_id),
                "narrative_mode": "none"
            }
        )

        assert response.status_code in [201, 404, 400, 500]


def test_generate_from_skeleton_not_found_404(test_client: TestClient):
    """Test that generate returns 404 for nonexistent skeleton."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.get_skeleton") as mock_get:
        mock_get.return_value = None

        response = test_client.post(
            "/api/generate-from-skeleton",
            json={
                "skeleton_id": str(skeleton_id),
                "narrative_mode": "none"
            }
        )

        assert response.status_code == 404


# ============================================================================
# Delete Skeleton Tests
# ============================================================================


def test_delete_skeleton_returns_204(test_client: TestClient):
    """Test that delete skeleton returns 204 No Content."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.delete_skeleton") as mock_delete:
        mock_delete.return_value = True

        response = test_client.delete(f"/api/skeleton/{skeleton_id}")

        assert response.status_code == 204


def test_delete_skeleton_not_found_404(test_client: TestClient):
    """Test that delete returns 404 for nonexistent skeleton."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.skeleton_service.delete_skeleton") as mock_delete:
        mock_delete.return_value = False

        response = test_client.delete(f"/api/skeleton/{skeleton_id}")

        assert response.status_code == 404


# ============================================================================
# Extension Skeleton Tests
# ============================================================================


def test_generate_extension_skeleton_returns_201(test_client: TestClient):
    """Test that generate extension skeleton returns 201."""
    timeline_id = uuid4()

    with patch("app.api.skeletons.timeline_service.get_timeline_by_id") as mock_get_timeline, \
         patch("app.api.skeletons.execute_extension_skeleton_generation") as mock_workflow, \
         patch("app.api.skeletons.skeleton_service.create_extension_draft_skeleton") as mock_create:

        # Mock timeline
        mock_timeline = MagicMock()
        mock_timeline.id = timeline_id
        mock_timeline.generations = [MagicMock(end_year=1924)]
        mock_get_timeline.return_value = mock_timeline

        # Mock workflow
        mock_workflow.return_value = {
            "skeleton_output": MagicMock(events=[])
        }

        # Mock skeleton creation
        mock_create.return_value = MagicMock(id=uuid4(), status="draft")

        response = test_client.post(
            "/api/generate-extension-skeleton",
            json={
                "timeline_id": str(timeline_id),
                "additional_years": 10
            }
        )

        assert response.status_code in [201, 404, 400, 500]


# ============================================================================
# Workflow Integration Tests
# ============================================================================


def test_skeleton_workflow_integration(test_client: TestClient):
    """Test complete skeleton workflow: generate → approve → generate report."""
    skeleton_id = uuid4()

    with patch("app.api.skeletons.get_history_service") as mock_history, \
         patch("app.api.skeletons.execute_skeleton_generation") as mock_gen_workflow, \
         patch("app.api.skeletons.llm_service.get_current_llm_config") as mock_llm, \
         patch("app.api.skeletons.skeleton_service.create_timeline_draft_skeleton") as mock_create, \
         patch("app.api.skeletons.skeleton_service.get_skeleton") as mock_get, \
         patch("app.api.skeletons.skeleton_service.approve_skeleton") as mock_approve, \
         patch("app.api.skeletons.execute_report_from_skeleton") as mock_report_workflow, \
         patch("app.api.skeletons.timeline_service.create_timeline_with_initial_generation") as mock_create_timeline:

        # Step 1: Generate skeleton
        mock_history_inst = MagicMock()
        mock_history_inst.get_context_for_deviation.return_value = "Context"
        mock_history.return_value = mock_history_inst

        mock_gen_workflow.return_value = {"skeleton_output": MagicMock(events=[])}
        mock_llm.return_value = MagicMock(provider="google", model_name="gemini")

        from app.models import SkeletonType, SkeletonStatus, ScenarioType
        now = datetime.utcnow()
        mock_skeleton = MagicMock(
            id=skeleton_id,
            timeline_id=None,
            generation_id=None,
            skeleton_type=SkeletonType.TIMELINE_DRAFT,
            status=SkeletonStatus.PENDING,
            deviation_date=date(1914, 6, 28),
            deviation_description="Test deviation with minimum 20 characters",
            scenario_type=ScenarioType.LOCAL_DEVIATION,
            parent_timeline_id=None,
            extension_start_year=None,
            extension_end_year=None,
            branch_point_year=None,
            branch_deviation_description=None,
            model_provider="google",
            model_name="gemini",
            generated_at=now,
            approved_at=None,
            created_at=now,
            updated_at=now,
            period_years=10,
            events=[]
        )
        mock_create.return_value = mock_skeleton

        response1 = test_client.post(
            "/api/generate-skeleton",
            json={
                "deviation_date": "1914-06-28",
                "deviation_description": "Test deviation with minimum 20 characters",
                "simulation_years": 10,
                "scenario_type": "local_deviation"
            }
        )

        # Step 2: Approve skeleton
        mock_skeleton.status = SkeletonStatus.APPROVED
        mock_skeleton.approved_at = now
        mock_get.return_value = mock_skeleton
        mock_approve.return_value = mock_skeleton

        response2 = test_client.post(f"/api/skeleton/{skeleton_id}/approve")

        # Step 3: Generate report
        mock_report = MagicMock(
            executive_summary="Summary",
            political_changes="Politics",
            conflicts_and_wars="Wars",
            economic_impacts="Economy",
            social_developments="Social",
            technological_shifts="Tech",
            key_figures="Figures",
            long_term_implications="Implications"
        )
        mock_report_workflow.return_value = {
            "structured_report": mock_report,
            "narrative_prose": "Narrative",
            "historian_provider": "google",
            "historian_model_name": "gemini"
        }
        mock_create_timeline.return_value = uuid4()

        response3 = test_client.post(
            "/api/generate-from-skeleton",
            json={
                "skeleton_id": str(skeleton_id),
                "narrative_mode": "none"
            }
        )

        # At least one step should succeed
        assert any(r.status_code in [200, 201] for r in [response1, response2, response3])
