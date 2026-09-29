from datetime import date
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.agents import workflows, historian_agent, skeleton_agent, skeleton_historian_agent
from app.agents.orchestrator import WorkflowContext
from app.models import TimelineExtensionRequest, ScenarioType, TimelineOutput
from tests.test_timeline_service import _make_timeline
from tests.test_world_state import state, entity
from app.models import WorldRelation


def timeline_with_state():
    timeline = _make_timeline('1914-06-28', 'A different history unfolds', ScenarioType.LOCAL_DEVIATION)
    timeline.generations[0].world_state_snapshot = state(1924, [entity(), entity('UK', 'nation')], [WorldRelation(source='Alice', relation='allied with', target='UK', active=False)])
    return timeline


def output():
    return TimelineOutput(**{k: 'Report ' + k for k in ['executive_summary', 'political_changes', 'conflicts_and_wars', 'economic_impacts', 'social_developments', 'technological_shifts', 'key_figures', 'long_term_implications']})


def skeleton(start=10):
    return SimpleNamespace(id=uuid4(), deviation_date=date(1914, 6, 28), deviation_description='A different history unfolds', start_year=start, end_year=start+10, period_years=10, events=[SimpleNamespace(event_date=date(1925, 1, 1), location='London', description='Alice explicitly returns to life', event_order=2), SimpleNamespace(event_date=date(1924, 7, 1), location='London', description='First approved event', event_order=1)])


@pytest.fixture
def fake_history(monkeypatch):
    from app.services import history_service
    service = SimpleNamespace(get_context_for_skeleton_rag=AsyncMock(return_value=('Historical context', {})), get_context_for_deviation=AsyncMock(return_value='Historical context'))
    monkeypatch.setattr(history_service, 'get_history_service', lambda: service)
    return service


@pytest.mark.asyncio
async def test_all_extension_prompts(monkeypatch, fake_history):
    timeline = timeline_with_state()
    request = TimelineExtensionRequest(timeline_id=timeline.id, additional_years=10)
    prompts = []
    async def direct(timeline, request, history, model=None, previous_world_state=''):
        prompts.append(historian_agent.construct_extension_prompt(timeline, request, history, previous_world_state=previous_world_state))
        return output()
    async def planning(**kw):
        prompts.append(skeleton_agent.construct_extension_skeleton_prompt(kw['deviation_date'], kw['deviation_description'], kw['scenario_type'], kw['extension_start_year'], kw['simulation_years'], kw['last_report_context'], kw['historical_context']))
        return SimpleNamespace(events=[])
    async def report(**kw):
        prompts.append(skeleton_historian_agent.construct_extension_skeleton_report_prompt(kw['deviation_date'], kw['deviation_description'], kw['scenario_type'], kw['start_year'], kw['end_year'], kw['last_report_summary'], kw['skeleton_events']))
        return output()
    monkeypatch.setattr(historian_agent, 'extend_timeline', direct)
    monkeypatch.setattr(skeleton_agent, 'generate_skeleton', planning)
    monkeypatch.setattr(skeleton_historian_agent, 'generate_report_from_skeleton', report)
    await workflows.execute_timeline_extension(request, timeline, 'Legacy prose')
    ctx = WorkflowContext(state={'timeline': timeline, 'extension_request': request, 'skeleton': skeleton(), 'historical_context': 'Legacy prose', 'last_report_context': 'Legacy prose'})
    await workflows._generate_extension_skeleton_events(ctx)
    await workflows._generate_extension_report_from_skeleton(ctx)
    assert len(prompts) == 3
    for prompt in prompts:
        assert all(value in prompt for value in ['Alice', 'deceased', 'inactive', '1924'])
    assert prompts[-1].index('First approved event') < prompts[-1].index('Alice explicitly returns to life')


@pytest.fixture
def fake_agents(monkeypatch, fake_history):
    from app.services import llm_service
    monkeypatch.setattr(llm_service, 'get_agent_llm_config', AsyncMock(return_value=None))
    monkeypatch.setattr(llm_service, 'get_current_llm_config', AsyncMock(return_value=SimpleNamespace(provider='test', model_name='test')))
    monkeypatch.setattr(llm_service, 'create_pydantic_ai_model_for_agent', AsyncMock(return_value=object()))
    monkeypatch.setattr(historian_agent, 'generate_timeline', AsyncMock(return_value=output()))
    monkeypatch.setattr(historian_agent, 'extend_timeline', AsyncMock(return_value=output()))
    monkeypatch.setattr(skeleton_historian_agent, 'generate_report_from_skeleton', AsyncMock(return_value=output()))
    monkeypatch.setattr(workflows.storyteller_agent, 'generate_narrative', AsyncMock(return_value='Advanced narrative'))


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['direct', 'direct_extension', 'skeleton', 'skeleton_extension'])
@pytest.mark.parametrize('advanced', [False, True])
async def test_four_workflows_extract_once(monkeypatch, fake_agents, path, advanced):
    from app.models import TimelineCreationRequest, NarrativeMode
    timeline = timeline_with_state()
    mode = NarrativeMode.ADVANCED_OMNISCIENT if advanced else NarrativeMode.NONE
    request = TimelineCreationRequest(deviation_date=date(1914, 6, 28), deviation_description='A different history unfolds', simulation_years=10, scenario_type=ScenarioType.LOCAL_DEVIATION, narrative_mode=mode)
    extension = TimelineExtensionRequest(timeline_id=timeline.id, additional_years=10, narrative_mode=mode)
    expected = state(1934 if 'extension' in path else 1924).model_dump(mode='json')
    helper = AsyncMock(return_value=expected)
    monkeypatch.setattr(workflows, 'try_extract_world_state', helper, raising=False)
    db = object()
    if path == 'direct':
        result = await workflows.execute_timeline_generation(request, 'History', db)
    elif path == 'direct_extension':
        result = await workflows.execute_timeline_extension(extension, timeline, 'History', db)
    elif path == 'skeleton':
        result = await workflows.execute_report_from_skeleton(skeleton(0), request, db)
    else:
        result = await workflows.execute_extension_from_skeleton(timeline, skeleton(), extension, db)
    helper.assert_awaited_once()
    args = helper.call_args.kwargs
    assert args['root_year'] == 1914
    assert args['structured_report'].end_year == (20 if 'extension' in path else 10)
    assert args['structured_report'].key_figures == 'Report key_figures'
    assert args['db_session'] is db
    assert (args['prior'] is not None) == ('extension' in path)
    assert result['world_state_snapshot'] == expected
    if advanced:
        assert result['narrative_prose'] == 'Advanced narrative'


@pytest.mark.asyncio
@pytest.mark.parametrize('paths', [('direct', 'direct', 'direct'), ('skeleton', 'skeleton', 'skeleton'), ('direct', 'skeleton', 'direct')])
@pytest.mark.parametrize('interrupted', [False, True])
async def test_three_generation_continuity(db_session, async_engine, monkeypatch, fake_agents, paths, interrupted):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
    from pydantic_ai.models.test import TestModel
    from app.models import TimelineCreationRequest, Timeline, AgentType, NarrativeMode
    from app.services import timeline_service, llm_service
    from app.agents import world_state_extractor_agent as extractor
    updates = [state(1924, [entity(), entity('UK', 'nation')], [WorldRelation(source='Alice', relation='allied with', target='UK')]), state(1934, relations=[WorldRelation(source='Alice', relation='allied with', target='UK', active=False)]), state(1944)]
    position = [0]
    prompts = []
    async def factory(db, agent_type):
        return TestModel(custom_output_args=updates[position[0]].model_dump(mode='json')) if agent_type == AgentType.WORLD_STATE_EXTRACTOR else object()
    monkeypatch.setattr(llm_service, 'create_pydantic_ai_model_for_agent', factory)
    original_extract = extractor.extract_world_state
    async def extract(*args, **kw):
        if interrupted and position[0] == 1:
            await asyncio.Event().wait()
        return await original_extract(*args, **kw)
    monkeypatch.setattr(extractor, 'extract_world_state', extract)
    monkeypatch.setattr(extractor, 'EXTRACTION_TIMEOUT_SECONDS', .05 if interrupted else 45)
    async def direct(timeline, request, history, model=None, previous_world_state=''):
        prompts.append(historian_agent.construct_extension_prompt(timeline, request, history, previous_world_state))
        return output()
    async def report(**kw):
        if kw.get('is_extension'):
            prompts.append(skeleton_historian_agent.construct_extension_skeleton_report_prompt(kw['deviation_date'], kw['deviation_description'], kw['scenario_type'], kw['start_year'], kw['end_year'], kw['last_report_summary'], kw['skeleton_events']))
        return output()
    monkeypatch.setattr(historian_agent, 'extend_timeline', direct)
    monkeypatch.setattr(skeleton_historian_agent, 'generate_report_from_skeleton', report)
    timeline = None
    saved_snapshots = []
    for index, path in enumerate(paths):
        position[0] = index
        if index == 0:
            request = TimelineCreationRequest(deviation_date=date(1914, 6, 28), deviation_description='A different history unfolds', simulation_years=10, scenario_type=ScenarioType.LOCAL_DEVIATION, narrative_mode=NarrativeMode.NONE)
            result = await workflows.execute_timeline_generation(request, 'History', db_session) if path == 'direct' else await workflows.execute_report_from_skeleton(skeleton(0), request, db_session)
            timeline = _make_timeline('1914-06-28', request.deviation_description, request.scenario_type)
            await timeline_service.create_timeline_with_initial_generation(db_session, timeline, output(), historian_provider='test', historian_model_name='test', world_state_snapshot=result['world_state_snapshot'])
        else:
            request = TimelineExtensionRequest(timeline_id=timeline.id, additional_years=10, narrative_mode=NarrativeMode.NONE)
            result = await workflows.execute_timeline_extension(request, timeline, 'Legacy prose', db_session) if path == 'direct' else await workflows.execute_extension_from_skeleton(timeline, skeleton(index*10), request, db_session)
            await timeline_service.extend_timeline_with_new_generation(db_session, timeline.id, output(), 10, historian_provider='test', historian_model_name='test', world_state_snapshot=result['world_state_snapshot'])
        await db_session.commit()
        async with AsyncSession(async_engine) as fresh:
            timeline = Timeline.model_validate(await timeline_service.get_timeline_by_id(fresh, timeline.id))
        saved_snapshots.append(timeline.generations[-1].world_state_snapshot)
    assert saved_snapshots[0].entities
    if interrupted:
        assert saved_snapshots[1] is None
        assert 'STRUCTURED WORLD STATE' not in prompts[-1]
        assert saved_snapshots[2].entities == []
        assert saved_snapshots[2].as_of_year == 1944
    else:
        assert all(x in prompts[-1] for x in ['Alice', 'deceased', 'inactive', '1934'])
        assert any(e.name == 'Alice' and e.status == 'deceased' for e in saved_snapshots[1].entities)
        assert saved_snapshots[1].relations[0].active is False
        assert saved_snapshots[2].relations[0].active is False
