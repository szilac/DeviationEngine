from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import timelines, skeletons
from app.db_models import GenerationDB
from app.models import StructuredReport
from tests.test_world_state import state
from tests.test_world_state_workflows import output, fake_history, fake_agents


@pytest.fixture
def no_external_services(monkeypatch):
    from app.services import vector_store_service, history_service
    history = SimpleNamespace(get_context_for_deviation=AsyncMock(return_value='History'), get_context_for_extension_rag=AsyncMock(return_value=('History', {})), get_context_for_skeleton_rag=AsyncMock(return_value=('History', {})))
    monkeypatch.setattr(timelines, 'get_history_service', lambda: history)
    monkeypatch.setattr(history_service, 'get_history_service', lambda: history)
    monkeypatch.setattr(vector_store_service, 'get_vector_store_service', lambda: SimpleNamespace(enabled=False))


@pytest.mark.asyncio
@pytest.mark.parametrize('path,status', [('direct', 201), ('direct_extension', 200), ('skeleton', 201), ('skeleton_extension', 201)])
@pytest.mark.parametrize('populated', [True, False])
async def test_http_snapshot_paths(async_test_client, db_session, async_engine, timeline_with_generation, skeleton_with_events, monkeypatch, no_external_services, path, status, populated):
    extension = 'extension' in path
    skeleton_with_events.simulation_years = 10
    if path == 'skeleton_extension':
        skeleton_with_events.skeleton_type = 'extension_draft'
        skeleton_with_events.parent_timeline_id = timeline_with_generation.id
        skeleton_with_events.extension_start_year = 10
        skeleton_with_events.extension_end_year = 20
    await db_session.commit()
    expected = state(1934 if extension else 1924).model_dump(mode='json') if populated else None
    report = StructuredReport(start_year=10 if extension else 0, end_year=20 if extension else 10, period_years=10, report_order=2 if extension else 1, **output().model_dump(exclude={'timeline_name', 'narrative_prose'}))
    fake = AsyncMock(return_value=dict(structured_report=report, narrative_prose=None, workflow_metadata={}, historian_provider='test', historian_model_name='test', world_state_snapshot=expected))
    endpoints = {
        'direct': (timelines, 'execute_timeline_generation', '/api/generate-timeline', dict(deviation_date='1914-06-28', deviation_description='A different history unfolds', simulation_years=10, scenario_type='local_deviation')),
        'direct_extension': (timelines, 'execute_timeline_extension', '/api/extend-timeline', dict(timeline_id=timeline_with_generation.id, additional_years=10)),
        'skeleton': (skeletons, 'execute_report_from_skeleton', '/api/generate-from-skeleton', dict(skeleton_id=skeleton_with_events.id)),
        'skeleton_extension': (skeletons, 'execute_extension_from_skeleton', '/api/extend-from-skeleton', dict(timeline_id=timeline_with_generation.id, skeleton_id=skeleton_with_events.id)),
    }
    module, name, url, body = endpoints[path]
    monkeypatch.setattr(module, name, fake)
    response = await async_test_client.post(url, json={**body, 'narrative_mode': 'none', 'use_rag': False})
    assert response.status_code == status, response.text
    latest = response.json()['generations'][-1]
    assert latest['world_state_snapshot'] == expected
    assert latest['key_figures'] == report.key_figures
    await db_session.commit()
    async with AsyncSession(async_engine) as fresh:
        saved = await fresh.get(GenerationDB, latest['id'])
        assert saved.world_state_snapshot == expected
        assert saved.key_figures == report.key_figures


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['direct', 'skeleton'])
@pytest.mark.parametrize('failure', ['error', 'timeout'])
async def test_real_extension_failure_still_saves(async_test_client, db_session, async_engine, timeline_with_generation, skeleton_with_events, monkeypatch, fake_agents, no_external_services, path, failure):
    import asyncio
    from app.agents import world_state_extractor_agent as extractor
    async def failing(*args, **kwargs):
        if failure == 'timeout':
            await asyncio.Event().wait()
        raise RuntimeError('Extraction failed')
    monkeypatch.setattr(extractor, 'extract_world_state', failing)
    monkeypatch.setattr(extractor, 'EXTRACTION_TIMEOUT_SECONDS', .01)
    skeleton_with_events.skeleton_type = 'extension_draft'
    skeleton_with_events.parent_timeline_id = timeline_with_generation.id
    skeleton_with_events.extension_start_year = 10
    skeleton_with_events.extension_end_year = 20
    await db_session.commit()
    body = dict(timeline_id=timeline_with_generation.id, narrative_mode='none', use_rag=False)
    if path == 'direct':
        url, status = '/api/extend-timeline', 200
        body['additional_years'] = 10
    else:
        url, status = '/api/extend-from-skeleton', 201
        body['skeleton_id'] = skeleton_with_events.id
    response = await async_test_client.post(url, json=body)
    assert response.status_code == status, response.text
    latest = response.json()['generations'][-1]
    assert latest['generation_order'] == 2
    assert latest['world_state_snapshot'] is None
    assert latest['key_figures'] == 'Report key_figures'
    await db_session.commit()
    async with AsyncSession(async_engine) as fresh:
        saved = await fresh.get(GenerationDB, latest['id'])
        assert saved.world_state_snapshot is None
        assert saved.key_figures == 'Report key_figures'


@pytest.mark.asyncio
async def test_http_export_import(async_test_client, db_session, timeline_with_generation):
    import json
    expected = state(1924).model_dump(mode='json')
    timeline_with_generation.generations[0].world_state_snapshot = expected
    await db_session.commit()
    response = await async_test_client.get(f'/api/timeline/{timeline_with_generation.id}/export')
    assert response.status_code == 200
    data = response.json()
    imported = await async_test_client.post('/api/timeline/import', files={'file': ('state.devtl', json.dumps(data), 'application/json')})
    assert imported.status_code == 201, imported.text
    assert imported.json()['generations'][0]['world_state_snapshot'] == expected
    data['timeline']['generations'][0]['world_state_snapshot'] = dict(expected, as_of_year=999)
    invalid = await async_test_client.post('/api/timeline/import', files={'file': ('bad.devtl', json.dumps(data), 'application/json')})
    assert invalid.status_code == 422, invalid.text
