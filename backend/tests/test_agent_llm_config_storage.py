"""Agent LLM overrides must save for every provider/agent the API accepts."""

import pytest
from sqlalchemy import select

from app.database import _rebuild_agent_llm_configs_if_stale
from app.db_models import AgentLLMConfigDB
from app.models import AgentLLMConfigRequest, AgentType, LLMProvider
from app.services import llm_service


@pytest.mark.asyncio
async def test_every_provider_and_agent_can_be_saved(db_session):
    for agent in AgentType:
        for provider in LLMProvider:
            request = AgentLLMConfigRequest(
                agent_type=agent,
                provider=provider,
                model_name=llm_service.AVAILABLE_MODELS[provider.value][0],
                enabled=True,
            )
            saved = await llm_service.set_agent_llm_config(db_session, request)
            assert (saved.agent_type, saved.provider) == (agent, provider)


@pytest.mark.asyncio
async def test_stale_table_is_rebuilt_keeping_rows(async_engine):
    async with async_engine.begin() as conn:
        await conn.exec_driver_sql("DROP TABLE agent_llm_configs")
        await conn.exec_driver_sql(
            "CREATE TABLE agent_llm_configs (id INTEGER NOT NULL, agent_type VARCHAR(50) NOT NULL, "
            "provider VARCHAR(50) NOT NULL, model_name VARCHAR(100) NOT NULL, api_key_google TEXT, "
            "api_key_openrouter TEXT, api_key_anthropic TEXT, api_key_openai TEXT, ollama_base_url TEXT, "
            "max_tokens INTEGER, temperature VARCHAR(10), enabled INTEGER NOT NULL, "
            "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, PRIMARY KEY (id), "
            "CONSTRAINT valid_agent_provider CHECK (provider IN ('google', 'openai')))"
        )
        await conn.exec_driver_sql(
            "CREATE UNIQUE INDEX ix_agent_llm_configs_agent_type ON agent_llm_configs (agent_type)"
        )
        await conn.exec_driver_sql(
            "INSERT INTO agent_llm_configs VALUES (1, 'historian', 'google', 'm', NULL, NULL, NULL, "
            "NULL, NULL, NULL, NULL, 1, '2026-01-01', '2026-01-01')"
        )

        await _rebuild_agent_llm_configs_if_stale(conn)

        await conn.exec_driver_sql(
            "INSERT INTO agent_llm_configs (agent_type, provider, model_name, enabled, created_at, updated_at) "
            "VALUES ('world_state_extractor', 'cliproxy', 'm', 1, '2026-01-01', '2026-01-01')"
        )
        rows = (await conn.execute(select(AgentLLMConfigDB.agent_type))).scalars().all()
    assert sorted(rows) == ["historian", "world_state_extractor"]
