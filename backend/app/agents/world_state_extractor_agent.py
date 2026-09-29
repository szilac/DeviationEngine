"""Validated accumulated world facts and optional report extraction."""
import logging
import re
from datetime import date
from typing import Optional

from app.models import WorldStateSnapshot

logger = logging.getLogger(__name__)
ALIASES = {
    'uk': 'united kingdom', 'britain': 'united kingdom',
    'great britain': 'united kingdom', 'ussr': 'soviet union',
    'soviets': 'soviet union', 'usa': 'united states',
    'us': 'united states', 'america': 'united states',
}


def canonical_key(name: str) -> str:
    key = ' '.join(re.sub(r"[.,'\"]", '', name).lower().split())
    return key[4:] if key.startswith('the ') else key


def _nonblank(value: str) -> None:
    if not canonical_key(value):
        raise ValueError('World-state strings must not be blank')


def _identity(entity):
    return entity.type.value, canonical_key(entity.name)


def _resolve(name, entities, entity_type=None):
    key = canonical_key(name)
    candidates = [e for e in entities if entity_type is None or e.type == entity_type]
    exact = [e for e in candidates if canonical_key(e.name) == key]
    matches = exact or [e for e in candidates if ALIASES.get(canonical_key(e.name), canonical_key(e.name)) == ALIASES.get(key, key)]
    if len(matches) > 1:
        raise ValueError(f'Ambiguous world-state name: {name}')
    return matches[0] if matches else None


def reconcile_snapshot(updates: WorldStateSnapshot, prior: Optional[WorldStateSnapshot]) -> WorldStateSnapshot:
    _nonblank(updates.summary)
    if prior and updates.as_of_year < prior.as_of_year:
        raise ValueError('World-state cutoff cannot go backwards')
    entities = {}
    relations = {}
    # Validate prior data too, without mutating the earlier snapshot/ORM JSON.
    if prior:
        checked = reconcile_snapshot(prior, None)
        entities = {_identity(e): e for e in checked.entities}
        relations = {(canonical_key(r.source), canonical_key(r.relation), canonical_key(r.target)): r for r in checked.relations}
    # Exact identities across the entire set take precedence over alias matches.
    roster = list(entities.values())
    for e in updates.entities:
        _nonblank(e.name)
        _nonblank(e.status)
        if e.note is not None:
            _nonblank(e.note)
        if _identity(e) not in {_identity(x) for x in roster}:
            roster.append(e)
    seen = {}
    for e in updates.entities:
        existing = _resolve(e.name, list(entities.values()), e.type)
        # Do not collapse two exact names explicitly present in this update set.
        exact_prior = entities.get(_identity(e))
        if exact_prior:
            existing = exact_prior
        elif existing and any(_identity(x) == _identity(existing) for x in updates.entities):
            existing = None
        updated = e.model_copy(deep=True)
        if existing:
            updated.name = existing.name
        identity = _identity(updated)
        if identity in seen and seen[identity] != updated:
            raise ValueError(f'Conflicting entity updates: {e.name}')
        seen[identity] = updated
    entities.update(seen)
    seen_relations = {}
    for r in updates.relations:
        for text in (r.source, r.relation, r.target):
            _nonblank(text)
        source = _resolve(r.source, entities.values())
        target = _resolve(r.target, entities.values())
        if source is None or target is None:
            raise ValueError('Dangling world-state relationship')
        updated = r.model_copy(update={'source': source.name, 'target': target.name}, deep=True)
        identity = (canonical_key(source.name), canonical_key(r.relation), canonical_key(target.name))
        if identity in seen_relations and seen_relations[identity].active != r.active:
            raise ValueError('Conflicting relationship updates')
        if identity in relations:
            updated.relation = relations[identity].relation
        seen_relations[identity] = updated
    relations.update(seen_relations)
    # ponytail: retain accumulated facts without pruning; measure prompt growth before adding archival/compaction.
    return WorldStateSnapshot(
        as_of_year=updates.as_of_year, summary=updates.summary,
        entities=sorted(entities.values(), key=lambda e: (e.type.value, e.name)),
        relations=sorted(relations.values(), key=lambda r: (r.source, r.relation, r.target)),
    )


def previous_snapshot(timeline) -> Optional[WorldStateSnapshot]:
    latest = max(timeline.generations, key=lambda g: g.generation_order, default=None)
    try:
        if latest is None or getattr(latest, 'world_state_snapshot', None) is None:
            logger.info('Structured carry-over unavailable for latest generation')
            return None
        snapshot = WorldStateSnapshot.model_validate(latest.world_state_snapshot)
        root = timeline.root_deviation_date
        root = date.fromisoformat(root) if isinstance(root, str) else root
        if snapshot.as_of_year != root.year + latest.end_year:
            raise ValueError('Stored snapshot cutoff does not match generation')
        return reconcile_snapshot(snapshot, None)
    except (ValueError, TypeError):
        logger.warning('Invalid latest world-state snapshot; structured carry-over unavailable', exc_info=True)
        return None


EXTRACTION_TIMEOUT_SECONDS = 180.0
REPORT_SECTIONS = (
    'executive_summary', 'political_changes', 'conflicts_and_wars',
    'economic_impacts', 'social_developments', 'technological_shifts',
    'key_figures', 'long_term_implications',
)


async def extract_world_state(report_sections: dict, scenario_type: str, start_year: int,
                              end_year: int, prior: Optional[WorldStateSnapshot], model) -> WorldStateSnapshot:
    from pydantic_ai import Agent, ModelRetry
    from app.prompt_templates import render_prompt

    system_prompt = render_prompt('world_state_extractor/system.jinja2')
    user_prompt = render_prompt(
        'world_state_extractor/user.jinja2', report_sections=report_sections,
        scenario_type=scenario_type, start_year=start_year, end_year=end_year,
        prior=prior.model_dump(mode='json') if prior else None,
    )
    agent = Agent(model=model, system_prompt=system_prompt, output_type=WorldStateSnapshot, retries=2)

    # Validate inside the run so the model gets the error back and can correct its output.
    @agent.output_validator
    def validate(updates: WorldStateSnapshot) -> WorldStateSnapshot:
        try:
            if updates.as_of_year != end_year:
                raise ValueError(f'as_of_year must be {end_year}')
            return reconcile_snapshot(updates, prior)
        except ValueError as e:
            raise ModelRetry(f'Invalid world-state snapshot: {e}') from e

    result = await agent.run(user_prompt)
    return result.output


async def try_extract_world_state(structured_report, scenario_type: str, root_year: int,
                                  prior: Optional[WorldStateSnapshot], db_session) -> Optional[dict]:
    import asyncio
    from app.models import AgentType
    from app.services import llm_service

    if db_session is None:
        return None

    async def run_extraction():
        model = await llm_service.create_pydantic_ai_model_for_agent(db_session, AgentType.WORLD_STATE_EXTRACTOR)
        snapshot = await extract_world_state(
            {key: getattr(structured_report, key) for key in REPORT_SECTIONS},
            scenario_type, root_year + structured_report.start_year,
            root_year + structured_report.end_year, prior, model,
        )
        return snapshot.model_dump(mode='json')

    try:
        return await asyncio.wait_for(run_extraction(), timeout=EXTRACTION_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning('World-state extraction timed out; continuing without snapshot')
        return None
    except Exception:
        logger.warning('World-state extraction failed; continuing without snapshot', exc_info=True)
        return None


def render_world_state_constraints(snapshot: Optional[WorldStateSnapshot]) -> str:
    from app.prompt_templates import render_prompt
    if snapshot is None:
        return ''
    return render_prompt('_world_state_constraints.jinja2', snapshot=reconcile_snapshot(snapshot, None))
