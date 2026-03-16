"""Tests for new Anthropic and OpenAI LLM provider integration."""

import pytest
import os
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


def test_llm_provider_has_anthropic():
    from app.models import LLMProvider
    assert LLMProvider.ANTHROPIC == "anthropic"


def test_llm_provider_has_openai():
    from app.models import LLMProvider
    assert LLMProvider.OPENAI == "openai"


def test_llm_config_request_accepts_anthropic_key():
    from app.models import LLMConfigRequest, LLMProvider
    req = LLMConfigRequest(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5",
        api_key_anthropic="sk-ant-test",
    )
    assert req.api_key_anthropic == "sk-ant-test"


def test_llm_config_request_sanitizes_empty_anthropic_key():
    from app.models import LLMConfigRequest, LLMProvider
    req = LLMConfigRequest(
        provider=LLMProvider.GOOGLE,
        model_name="gemini-2.5-flash",
        api_key_anthropic="",
    )
    assert req.api_key_anthropic is None


def test_llm_config_request_sanitizes_empty_openai_key():
    from app.models import LLMConfigRequest, LLMProvider
    req = LLMConfigRequest(
        provider=LLMProvider.GOOGLE,
        model_name="gemini-2.5-flash",
        api_key_openai="",
    )
    assert req.api_key_openai is None


def test_available_models_response_has_anthropic_and_openai():
    from app.models import AvailableModelsResponse
    resp = AvailableModelsResponse(
        google=["gemini-2.5-flash"],
        openrouter=["openai/gpt-4o"],
        ollama=["llama3.2:3b"],
        anthropic=["claude-sonnet-4-5"],
        openai=["gpt-4o"],
    )
    assert "claude-sonnet-4-5" in resp.anthropic
    assert "gpt-4o" in resp.openai


@pytest.mark.asyncio
async def test_llm_config_db_has_anthropic_and_openai_columns(db_session: AsyncSession):
    from app.db_models import LLMConfigDB
    from datetime import datetime, timezone

    config = LLMConfigDB(
        id=1,
        provider="anthropic",
        model_name="claude-sonnet-4-5",
        api_key_anthropic="sk-ant-test",
        api_key_openai=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)

    assert config.api_key_anthropic == "sk-ant-test"
    assert config.api_key_openai is None


@pytest.mark.asyncio
async def test_agent_llm_config_db_has_anthropic_and_openai_columns(db_session: AsyncSession):
    from app.db_models import AgentLLMConfigDB

    config = AgentLLMConfigDB(
        agent_type="historian",
        provider="openai",
        model_name="gpt-4o",
        api_key_anthropic=None,
        api_key_openai="sk-test",
        enabled=1,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)

    assert config.api_key_openai == "sk-test"
    assert config.api_key_anthropic is None
