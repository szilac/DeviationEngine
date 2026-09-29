import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app import database
from app.db_models import GenerationDB
from app.models import Generation, ScenarioType, TimelineOutput, WorldStateSnapshot
from app.services import timeline_service
from tests.test_timeline_service import _make_timeline


@pytest.mark.asyncio
@pytest.mark.parametrize('fresh', [False, True])
async def test_idempotent_migration(tmp_path, fresh):
    engine = create_async_engine(f'sqlite+aiosqlite:///{tmp_path}/migration.db')
    async with engine.begin() as conn:
        if fresh:
            await conn.run_sync(database.Base.metadata.create_all)
        else:
            await conn.exec_driver_sql('CREATE TABLE generations (id TEXT PRIMARY KEY)')
            await conn.exec_driver_sql("INSERT INTO generations (id) VALUES ('sentinel')")
        await database._ensure_world_state_column(conn)
        await database._ensure_world_state_column(conn)
        columns = (await conn.exec_driver_sql('PRAGMA table_info(generations)')).fetchall()
        assert [r[1] for r in columns].count('world_state_snapshot') == 1
        if not fresh:
            assert (await conn.exec_driver_sql('SELECT id, world_state_snapshot FROM generations')).one() == ('sentinel', None)
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('with_snapshot', [True, False])
async def test_storage_roundtrip(db_session, async_engine, with_snapshot):
    timeline = _make_timeline('1914-06-28', 'A different history', ScenarioType.LOCAL_DEVIATION)
    output = TimelineOutput(**{k: 'Unchanged report' for k in ['executive_summary', 'political_changes', 'conflicts_and_wars', 'economic_impacts', 'social_developments', 'technological_shifts', 'key_figures', 'long_term_implications']})
    initial = WorldStateSnapshot(as_of_year=1924, summary='First').model_dump(mode='json') if with_snapshot else None
    await timeline_service.create_timeline_with_initial_generation(db_session, timeline, output, historian_provider='test', historian_model_name='test', world_state_snapshot=initial)
    extension = dict(initial, as_of_year=1934) if initial else None
    await timeline_service.extend_timeline_with_new_generation(db_session, timeline.id, output, 10, historian_provider='test', historian_model_name='test', world_state_snapshot=extension)
    await db_session.commit()
    async with AsyncSession(async_engine) as fresh:
        rows = (await fresh.execute(select(GenerationDB).order_by(GenerationDB.generation_order))).scalars().all()
        assert [r.world_state_snapshot for r in rows] == [initial, extension]
        parsed = Generation.model_validate(rows[0])
        assert parsed.model_dump(mode='json')['world_state_snapshot'] == initial


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['snapshots', 'missing', 'null'])
async def test_devtl_roundtrip(db_session, async_engine, timeline_with_generation, kind):
    from copy import deepcopy
    from app.services import export_service, import_service
    from tests.test_world_state import state, entity
    from tests.test_world_state_workflows import output
    from app.models import WorldRelation
    from app.agents.world_state_extractor_agent import reconcile_snapshot
    first = reconcile_snapshot(state(1924, [entity(), entity('UK', 'nation')], [WorldRelation(source='Alice', relation='leads', target='UK', active=False)]), None).model_dump(mode='json')
    timeline_with_generation.generations[0].world_state_snapshot = first
    second = dict(first, as_of_year=1934)
    await timeline_service.extend_timeline_with_new_generation(db_session, timeline_with_generation.id, output(), 10, historian_provider='test', historian_model_name='test', world_state_snapshot=second)
    await db_session.commit()
    data = await export_service.export_timeline_to_json(db_session, timeline_with_generation.id)
    generations = data['timeline']['generations']
    assert [g.get('world_state_snapshot') for g in generations] == [first, second]
    if kind != 'snapshots':
        for g in generations:
            if kind == 'missing':
                g.pop('world_state_snapshot')
            else:
                g['world_state_snapshot'] = None
    before = deepcopy(data)
    imported = await import_service.import_timeline_from_json(db_session, data)
    assert data == before
    assert str(imported) != timeline_with_generation.id
    async with AsyncSession(async_engine) as fresh:
        rows = (await fresh.execute(select(GenerationDB).where(GenerationDB.timeline_id == str(imported)).order_by(GenerationDB.generation_order))).scalars().all()
        assert [r.world_state_snapshot for r in rows] == ([first, second] if kind == 'snapshots' else [None, None])
        assert rows[0].id != generations[0]['id']


@pytest.mark.asyncio
@pytest.mark.parametrize('bad', ['year', 'conflict', 'dangling', 'blank'])
async def test_malformed_import_no_partial_timeline(db_session, timeline_with_generation, bad):
    from app.services import export_service, import_service
    from app.db_models import TimelineDB
    from sqlalchemy import func
    from tests.test_world_state import state, entity
    data = await export_service.export_timeline_to_json(db_session, timeline_with_generation.id)
    raw = state(1924, [entity()]).model_dump(mode='json')
    if bad == 'year':
        raw['as_of_year'] = 999
    elif bad == 'conflict':
        raw['entities'].append(dict(raw['entities'][0], status='alive'))
    elif bad == 'dangling':
        raw['relations'] = [dict(source='Alice', relation='leads', target='Missing')]
    else:
        raw['entities'][0]['name'] = '   '
    data['timeline']['generations'][0]['world_state_snapshot'] = raw
    before = await db_session.scalar(select(func.count()).select_from(TimelineDB))
    with pytest.raises(import_service.InvalidFileFormatError):
        await import_service.import_timeline_from_json(db_session, data)
    assert await db_session.scalar(select(func.count()).select_from(TimelineDB)) == before
