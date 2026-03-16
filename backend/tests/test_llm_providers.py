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
