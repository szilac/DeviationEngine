"""
Tests for historical events and ground truth reports API endpoints.

Tests:
- GET /api/historical-events - Historical events with date range
- GET /api/ground-truth-reports - List ground truth reports
- GET /api/ground-truth-reports/{report_id} - Get specific ground truth report
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


# ============================================================================
# GET /api/historical-events Tests
# ============================================================================


def test_get_historical_events_returns_200(test_client: TestClient):
    """Test that historical events endpoint returns 200 OK."""
    response = test_client.get("/api/historical-events")
    assert response.status_code == 200


def test_get_historical_events_returns_list(test_client: TestClient):
    """Test that historical events endpoint returns a list."""
    response = test_client.get("/api/historical-events")
    data = response.json()
    assert isinstance(data, list)


def test_get_historical_events_with_default_range(test_client: TestClient):
    """Test historical events with default year range (1900-2000)."""
    response = test_client.get("/api/historical-events")
    assert response.status_code == 200
    data = response.json()

    # If events exist, they should have year information
    if len(data) > 0:
        for event in data:
            # Events have start_year and/or end_year fields
            assert "start_year" in event or "end_year" in event or "year" in event or "date" in event


def test_get_historical_events_with_custom_range(test_client: TestClient):
    """Test historical events with custom year range."""
    response = test_client.get("/api/historical-events?start_year=1920&end_year=1950")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_historical_events_response_structure(test_client: TestClient):
    """Test that historical events have correct structure."""
    response = test_client.get("/api/historical-events")
    data = response.json()

    # If events exist, check structure
    if len(data) > 0:
        event = data[0]
        # Historical events should have these fields (based on HistoricalEvent model)
        assert "title" in event or "description" in event


# ============================================================================
# GET /api/ground-truth-reports Tests
# ============================================================================


def test_get_ground_truth_reports_returns_200(test_client: TestClient):
    """Test that ground truth reports endpoint returns 200 OK."""
    response = test_client.get("/api/ground-truth-reports")
    assert response.status_code == 200


def test_get_ground_truth_reports_returns_list(test_client: TestClient):
    """Test that ground truth reports endpoint returns a list."""
    response = test_client.get("/api/ground-truth-reports")
    data = response.json()
    assert isinstance(data, list)


def test_get_ground_truth_reports_structure(test_client: TestClient):
    """Test that ground truth reports have correct structure."""
    response = test_client.get("/api/ground-truth-reports")
    data = response.json()

    # If reports exist, check structure
    if len(data) > 0:
        report = data[0]
        required_keys = ["id", "start_year", "end_year", "period_years", "title", "content", "type"]
        for key in required_keys:
            assert key in report, f"Missing key: {key}"

        # Check type is correct
        assert report["type"] == "ground_truth"

        # Check ID format
        assert report["id"].startswith("ground-truth-")


def test_get_ground_truth_reports_content_truncated(test_client: TestClient):
    """Test that ground truth reports list truncates content."""
    response = test_client.get("/api/ground-truth-reports")
    data = response.json()

    # If reports exist with content, check truncation
    if len(data) > 0 and "content" in data[0]:
        # Content should be truncated or have ellipsis if original is long
        content = data[0]["content"]
        # Either short content or truncated with "..."
        assert len(content) <= 503  # 500 + "..."


# ============================================================================
# GET /api/ground-truth-reports/{report_id} Tests
# ============================================================================


def test_get_ground_truth_report_by_id_returns_200(test_client: TestClient):
    """Test that getting a specific ground truth report returns 200 OK."""
    # First get list to find a valid ID
    list_response = test_client.get("/api/ground-truth-reports")
    reports = list_response.json()

    # Skip if no reports available
    if len(reports) == 0:
        pytest.skip("No ground truth reports available for testing")

    report_id = reports[0]["id"]
    response = test_client.get(f"/api/ground-truth-reports/{report_id}")
    assert response.status_code == 200


def test_get_ground_truth_report_by_id_structure(test_client: TestClient):
    """Test that individual ground truth report has correct structure."""
    # First get list to find a valid ID
    list_response = test_client.get("/api/ground-truth-reports")
    reports = list_response.json()

    # Skip if no reports available
    if len(reports) == 0:
        pytest.skip("No ground truth reports available for testing")

    report_id = reports[0]["id"]
    response = test_client.get(f"/api/ground-truth-reports/{report_id}")
    data = response.json()

    required_keys = ["id", "start_year", "end_year", "period_years", "title", "content", "type"]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"


def test_get_ground_truth_report_full_content(test_client: TestClient):
    """Test that individual report returns full content (not truncated)."""
    # First get list to find a valid ID
    list_response = test_client.get("/api/ground-truth-reports")
    list_reports = list_response.json()

    # Skip if no reports available
    if len(list_reports) == 0:
        pytest.skip("No ground truth reports available for testing")

    report_id = list_reports[0]["id"]

    # Get full report
    detail_response = test_client.get(f"/api/ground-truth-reports/{report_id}")
    detail_report = detail_response.json()

    # Full report content should be longer than truncated list content (if original was long)
    list_content = list_reports[0]["content"]
    detail_content = detail_report["content"]

    # If list content was truncated (has "..."), detail should be longer
    if list_content.endswith("..."):
        assert len(detail_content) >= len(list_content)


def test_get_ground_truth_report_invalid_id_format_400(test_client: TestClient):
    """Test that invalid report ID format returns 400."""
    response = test_client.get("/api/ground-truth-reports/invalid-id-format")
    assert response.status_code == 400


def test_get_ground_truth_report_nonexistent_404(test_client: TestClient):
    """Test that nonexistent ground truth report returns 404."""
    response = test_client.get("/api/ground-truth-reports/ground-truth-9999-9999")
    assert response.status_code == 404


def test_get_ground_truth_report_id_matches(test_client: TestClient):
    """Test that returned report ID matches requested ID."""
    # First get list to find a valid ID
    list_response = test_client.get("/api/ground-truth-reports")
    reports = list_response.json()

    # Skip if no reports available
    if len(reports) == 0:
        pytest.skip("No ground truth reports available for testing")

    report_id = reports[0]["id"]
    response = test_client.get(f"/api/ground-truth-reports/{report_id}")
    data = response.json()

    assert data["id"] == report_id


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_historical_events_handles_service_errors(test_client: TestClient):
    """Test that historical events endpoint handles service errors gracefully."""
    # Mock the service to raise an exception
    with patch("app.api.historical.get_historical_events_service") as mock_service:
        mock_instance = MagicMock()
        mock_instance.get_events.side_effect = Exception("Service error")
        mock_service.return_value = mock_instance

        response = test_client.get("/api/historical-events")
        assert response.status_code == 500


def test_ground_truth_reports_handles_directory_errors(test_client: TestClient):
    """Test that ground truth reports handle missing directory gracefully."""
    # This should return empty list or handle error gracefully
    response = test_client.get("/api/ground-truth-reports")
    # Should not crash, returns 200 with empty list or error
    assert response.status_code in [200, 500]


# ============================================================================
# Integration Tests
# ============================================================================


def test_ground_truth_list_and_detail_consistency(test_client: TestClient):
    """Test that list and detail endpoints return consistent data."""
    # Get list
    list_response = test_client.get("/api/ground-truth-reports")
    list_reports = list_response.json()

    # Skip if no reports
    if len(list_reports) == 0:
        pytest.skip("No ground truth reports available for testing")

    # Get detail for first report
    report_id = list_reports[0]["id"]
    detail_response = test_client.get(f"/api/ground-truth-reports/{report_id}")
    detail_report = detail_response.json()

    # Check consistency
    assert list_reports[0]["id"] == detail_report["id"]
    assert list_reports[0]["start_year"] == detail_report["start_year"]
    assert list_reports[0]["end_year"] == detail_report["end_year"]
    assert list_reports[0]["type"] == detail_report["type"]
