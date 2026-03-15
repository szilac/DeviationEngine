"""
Tests for health and info API endpoints.

Tests the root endpoint (/) and health check endpoint (/api/health).
"""

import pytest
from fastapi.testclient import TestClient


def test_get_root_returns_200(test_client: TestClient):
    """Test that root endpoint returns 200 OK."""
    response = test_client.get("/")
    assert response.status_code == 200


def test_get_health_returns_200(test_client: TestClient):
    """Test that health check endpoint returns 200 OK."""
    response = test_client.get("/api/health")
    assert response.status_code == 200


def test_get_health_has_correct_structure(test_client: TestClient):
    """Test that health check endpoint returns correct structure."""
    response = test_client.get("/api/health")
    data = response.json()

    # Check required keys (HealthResponse model)
    assert "status" in data
    assert "version" in data

    # Check values
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


def test_get_health_status_is_healthy(test_client: TestClient):
    """Test that health status is 'healthy' when API is operational."""
    response = test_client.get("/api/health")
    data = response.json()

    assert data["status"] == "healthy"


def test_get_health_version_matches_api_version(test_client: TestClient):
    """Test that health version is 1.0.0."""
    response = test_client.get("/api/health")
    data = response.json()
    assert data["version"] == "1.0.0"


def test_get_health_response_is_json_content_type(test_client: TestClient):
    """Test that health check endpoint returns JSON content type."""
    response = test_client.get("/api/health")
    assert "application/json" in response.headers["content-type"]


def test_get_health_response_is_json(test_client: TestClient):
    """Test that health check endpoint returns JSON content type."""
    response = test_client.get("/api/health")
    assert "application/json" in response.headers["content-type"]
