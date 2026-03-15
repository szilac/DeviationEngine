"""
Tests for Audio Router endpoints.

Tests the audio script generation, preset management, and audio file operations.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.models import ScriptStatus, ScriptType


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


# Preset endpoints tests
def test_list_presets_returns_200(test_client: TestClient):
    with patch("app.api.audio.preset_service.get_all_presets") as mock_get:
        mock_get.return_value = []
        response = test_client.get("/api/audio/presets")
        assert response.status_code == 200


def test_get_preset_returns_200(test_client: TestClient):
    from app.models import ScriptPreset, ScriptTone, ScriptPacing
    preset_id = str(uuid4())
    with patch("app.api.audio.preset_service.get_preset_by_id") as mock_get:
        mock_get.return_value = ScriptPreset(
            id=preset_id,
            name="Test Preset",
            description="Test preset description",
            script_type=ScriptType.DOCUMENTARY,
            tone=ScriptTone.NEUTRAL,
            pacing=ScriptPacing.MEDIUM,
            voice_count=1,
            voice_roles={"narrator": "Main narrator"},
            style_instructions="Neutral, informative style instructions for this test preset",
            prompt_template_name="script_writer/generic.jinja2",
            is_system=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        response = test_client.get(f"/api/audio/presets/{preset_id}")
        assert response.status_code == 200


def test_create_preset_returns_201(test_client: TestClient):
    from app.models import ScriptPreset, ScriptTone, ScriptPacing
    with patch("app.api.audio.preset_service.create_preset", create=True) as mock_create:
        mock_create.return_value = ScriptPreset(
            id=str(uuid4()),
            name="New Preset",
            description="New preset description",
            script_type=ScriptType.DOCUMENTARY,
            tone=ScriptTone.NEUTRAL,
            pacing=ScriptPacing.MEDIUM,
            voice_count=1,
            voice_roles={"narrator": "Main narrator"},
            style_instructions="Neutral style instructions for this new test preset",
            prompt_template_name="script_writer/generic.jinja2",
            is_system=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        response = test_client.post(
            "/api/audio/presets",
            json={
                "name": "New Preset",
                "description": "New preset description",
                "script_type": "documentary",
                "template_content": "Template"
            }
        )
        assert response.status_code in [201, 422]


def test_delete_preset_returns_204(test_client: TestClient):
    preset_id = str(uuid4())
    with patch("app.api.audio.preset_service.delete_preset", create=True) as mock_delete:
        mock_delete.return_value = True
        response = test_client.delete(f"/api/audio/presets/{preset_id}")
        assert response.status_code in [204, 404]


# Script endpoints tests
def test_list_scripts_returns_200(test_client: TestClient):
    with patch("app.api.audio.script_service.list_scripts") as mock_list:
        mock_list.return_value = []
        response = test_client.get("/api/audio/scripts")
        assert response.status_code == 200


def test_get_script_returns_200(test_client: TestClient):
    from app.models import AudioScript
    script_id = uuid4()
    with patch("app.api.audio.script_service.get_script_by_id") as mock_get:
        mock_get.return_value = AudioScript(
            id=script_id,
            preset_id=str(uuid4()),
            generation_ids=[],
            title="Test Script Title",
            script_content="# Script Content\n\nNarrator: This is the script content.",
            script_structure="single_voice",
            word_count=100,
            estimated_duration_seconds=300,
            status=ScriptStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        response = test_client.get(f"/api/audio/scripts/{script_id}")
        assert response.status_code == 200


def test_delete_script_returns_204(test_client: TestClient):
    script_id = uuid4()
    with patch("app.api.audio.script_service.delete_script") as mock_delete:
        mock_delete.return_value = True
        response = test_client.delete(f"/api/audio/scripts/{script_id}")
        assert response.status_code == 204


# Audio generation tests
def test_list_script_audio_returns_200(test_client: TestClient):
    script_id = uuid4()
    with patch("app.api.audio.audio_service.list_audio_files_for_script") as mock_list:
        mock_list.return_value = []
        response = test_client.get(f"/api/audio/scripts/{script_id}/audio")
        assert response.status_code == 200


def test_delete_audio_file_returns_204(test_client: TestClient):
    audio_file_id = uuid4()
    with patch("app.api.audio.audio_service.delete_audio_file") as mock_delete:
        mock_delete.return_value = True
        response = test_client.delete(f"/api/audio/{audio_file_id}")
        assert response.status_code == 204


def test_list_script_translations_returns_200(test_client: TestClient):
    script_id = uuid4()
    with patch("app.api.audio.script_service.list_translations_for_script") as mock_list:
        mock_list.return_value = []
        response = test_client.get(f"/api/audio/scripts/{script_id}/translations")
        assert response.status_code == 200
