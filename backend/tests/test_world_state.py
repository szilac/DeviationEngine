from types import SimpleNamespace

import pytest

from app.models import WorldEntity, WorldRelation, WorldStateSnapshot
from app.agents.world_state_extractor_agent import canonical_key, reconcile_snapshot, previous_snapshot


def state(year=1920, entities=(), relations=()):
    return WorldStateSnapshot(as_of_year=year, summary='Period overview', entities=list(entities), relations=list(relations))


def entity(name='Alice', type='person', status='deceased'):
    return WorldEntity(name=name, type=type, status=status)


def test_retention_nonmutation_and_endings():
    prior = state(entities=[entity(), entity('UK', 'nation')], relations=[WorldRelation(source='Alice', relation='leads', target='UK')])
    saved = prior.model_dump()
    updates = state(1930, relations=[WorldRelation(source='Alice', relation='leads', target='Britain', active=False)])
    merged = reconcile_snapshot(updates, prior)
    assert {e.name: e.status for e in merged.entities} == {e.name: e.status for e in prior.entities}
    assert not merged.relations[0].active
    assert prior.model_dump() == saved
    assert updates.entities == []
    assert not reconcile_snapshot(state(1940), merged).relations[0].active


def test_alias_only_endpoint_and_exact_priority():
    prior = state(entities=[entity('United Kingdom', 'nation'), entity()])
    merged = reconcile_snapshot(state(1930, relations=[WorldRelation(source='Alice', relation='visits', target='UK')]), prior)
    assert merged.relations[0].target == 'United Kingdom'
    separate = state(entities=[entity('UK', 'nation'), entity('Britain', 'nation')])
    assert len(reconcile_snapshot(separate, None).entities) == 2


@pytest.mark.parametrize('updates', [
    lambda: state(entities=[entity(), entity(status='alive')]),
    lambda: state(entities=[entity(), entity('Alice', 'nation')], relations=[WorldRelation(source='Alice', relation='knows', target='Alice')]),
    lambda: state(relations=[WorldRelation(source='Missing', relation='knows', target='Missing')]),
    lambda: state(entities=[entity()], relations=[WorldRelation(source='Alice', relation='knows', target='Alice', active=x) for x in [True, False]]),
    lambda: state(entities=[entity('  ')]),
    lambda: state(entities=[entity(status='  ')]),
    lambda: WorldStateSnapshot(as_of_year=1920, summary='  '),
])
def test_invalid_updates(updates):
    with pytest.raises(ValueError):
        reconcile_snapshot(updates(), None)


def test_identical_duplicates_types_and_normalization():
    assert canonical_key(' The  U.S.A. ') == 'usa'
    merged = reconcile_snapshot(state(entities=[entity(), entity(), entity('Alice', 'nation')]), None)
    assert len(merged.entities) == 2
    with pytest.raises(ValueError):
        reconcile_snapshot(state(1910), state())


def test_previous_uses_latest_only():
    older = SimpleNamespace(generation_order=1, end_year=20, world_state_snapshot=state().model_dump())
    latest = SimpleNamespace(generation_order=2, end_year=30, world_state_snapshot=state(1930).model_dump())
    timeline = SimpleNamespace(root_deviation_date='1900-01-01', generations=[latest, older])
    assert previous_snapshot(timeline).as_of_year == 1930
    latest.world_state_snapshot = None
    assert previous_snapshot(timeline) is None
    latest.world_state_snapshot = state().model_dump()
    assert previous_snapshot(timeline) is None


@pytest.mark.asyncio
async def test_extraction_messages_and_validation():
    from pydantic_ai import UnexpectedModelBehavior, capture_run_messages
    from pydantic_ai.models.test import TestModel
    from app.agents.world_state_extractor_agent import extract_world_state
    prior = state(entities=[entity()], relations=[WorldRelation(source='Alice', relation='leads', target='Alice', active=False)])
    sections = {name: 'Evidence ' + name for name in ['executive_summary', 'political_changes', 'conflicts_and_wars', 'economic_impacts', 'social_developments', 'technological_shifts', 'key_figures', 'long_term_implications']}
    with capture_run_messages() as messages:
        result = await extract_world_state(sections, 'local_deviation', 1920, 1930, prior, TestModel(custom_output_args=state(1930).model_dump(mode='json')))
    prompt = str(messages)
    assert all(value in prompt for value in sections.values())
    assert all(value in prompt for value in ['1920', '1930', 'deceased', 'false'])
    assert result.entities[0].name == 'Alice'
    for bad in [state(1940), state(1930, entities=[entity(), entity(status='alive')])]:
        with pytest.raises(UnexpectedModelBehavior):
            await extract_world_state(sections, 'local_deviation', 1920, 1930, prior, TestModel(custom_output_args=bad.model_dump(mode='json')))


@pytest.mark.asyncio
async def test_extraction_retries_invalid_snapshot():
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel
    from app.agents.world_state_extractor_agent import extract_world_state
    dangling = state(1930, entities=[entity()], relations=[WorldRelation(source='Alice', relation='leads', target='Nobody')])
    outputs = [dangling, state(1930, entities=[entity()])]
    feedback = []

    def respond(messages, info):
        feedback.append(str(messages[-1]))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, outputs.pop(0).model_dump(mode='json'))])

    result = await extract_world_state({}, 'local_deviation', 1920, 1930, None, FunctionModel(respond))
    assert result.entities[0].name == 'Alice'
    assert 'Dangling' in feedback[1]


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['timeout', 'model_timeout', 'error', 'cancel', 'invalid', 'no_db'])
async def test_optional_extraction_boundary(monkeypatch, caplog, failure):
    import asyncio
    from app.agents import world_state_extractor_agent as extractor
    from app.services import llm_service
    cancelled = []
    async def fail(*args, **kwargs):
        if failure in ['timeout', 'model_timeout']:
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)
        if failure == 'cancel':
            raise asyncio.CancelledError()
        if failure == 'invalid':
            raise ValueError('invalid data')
        raise RuntimeError('provider unavailable')
    async def model(*args):
        return object()
    monkeypatch.setattr(llm_service, 'create_pydantic_ai_model_for_agent', fail if failure == 'model_timeout' else model)
    monkeypatch.setattr(extractor, 'extract_world_state', fail)
    monkeypatch.setattr(extractor, 'EXTRACTION_TIMEOUT_SECONDS', .01)
    report = SimpleNamespace(start_year=20, end_year=30, **{k: 'section' for k in extractor.REPORT_SECTIONS})
    if failure == 'cancel':
        with pytest.raises(asyncio.CancelledError):
            await extractor.try_extract_world_state(report, 'local_deviation', 1900, None, object())
    else:
        assert await extractor.try_extract_world_state(report, 'local_deviation', 1900, None, None if failure == 'no_db' else object()) is None
    if 'timeout' in failure:
        assert cancelled and 'timed out' in caplog.text


def test_constraint_rendering_and_legacy():
    from app.agents.world_state_extractor_agent import render_world_state_constraints
    assert render_world_state_constraints(None) == ''
    snapshot = state(entities=[entity()])
    assert 'deceased' in render_world_state_constraints(snapshot)
