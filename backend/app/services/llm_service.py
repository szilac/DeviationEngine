"""
LLM Service with Provider Factory Pattern.

This module provides centralized management of LLM provider configuration
and dynamic model instantiation for Pydantic-AI agents.
"""

import os
import logging
from typing import Dict, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.db_models import LLMConfigDB, AgentLLMConfigDB
from app.models import (
    LLMProvider, LLMConfigRequest, LLMConfigResponse, AvailableModelsResponse,
    AgentType, AgentLLMConfigRequest, AgentLLMConfigResponse, AllLLMConfigsResponse
    )
from app.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Available models per provider
AVAILABLE_MODELS: Dict[str, List[str]] = {
    "google": [
        "gemini-2.5-flash",
        "gemini-flash-lite-latest",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
    ],
    "openrouter": [
        "openai/gpt-4o-mini",
        "openai/gpt-5-nano",
        "openai/gpt-4o",
        "deepseek/deepseek-chat-v3.1",
        "deepseek/deepseek-v3.2",
        "z-ai/glm-4.5",
        "z-ai/glm-4.6",
        "z-ai/glm-4.7-flash",
        "z-ai/glm-5",
        "x-ai/grok-4-fast",
        "x-ai/grok-4.1-fast",
        "moonshotai/kimi-k2-thinking",
        "aion-labs/aion-2.0",
        "moonshotai/kimi-k2.5",
        "anthropic/claude-sonnet-4.6",
        "anthropic/claude-opus-4.6",
        "openrouter/healer-alpha",
        "openrouter/hunter-alpha",
    ],
    "ollama": [
        "llama3.2:3b",
        "llama3.2:1b",
    ],
    "anthropic": [
        "claude-sonet-4",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-sonnet-4-6",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-5.4",
        "gpt-5",
    ],
    "cliproxy": [
        "claude-sonnet-4-20250514",
        "claude-sonnet-4-6",
        "claude-opus-4-20250514",
        "claude-opus-4-6",
        "claude-haiku-4-5-20251001",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-5.4",
        "gpt-5",
    ],
}


async def get_current_llm_config(db: AsyncSession) -> LLMConfigDB:
    """
    Get the current LLM configuration from database.

    Args:
        db: Database session

    Returns:
        LLMConfigDB: Current configuration

    Raises:
        ConfigurationError: If configuration not found
    """
    try:
        result = await db.execute(select(LLMConfigDB).where(LLMConfigDB.id == 1))
        config = result.scalar_one_or_none()

        if config is None:
            logger.error("LLM configuration not found in database")
            raise ConfigurationError(
                "LLM configuration not initialized. Please restart the application.",
                details={"config_id": 1}
            )

        logger.debug(f"Retrieved LLM config: provider={config.provider}, model={config.model_name}")
        return config

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving LLM config: {e}", exc_info=True)
        raise ConfigurationError(
            "Failed to retrieve LLM configuration",
            details={"error": str(e)}
        )


async def update_llm_config(
    db: AsyncSession,
    config_request: LLMConfigRequest
) -> LLMConfigResponse:
    """
    Update the LLM configuration in database.

    Args:
        db: Database session
        config_request: New configuration values

    Returns:
        LLMConfigResponse: Updated configuration

    Raises:
        ConfigurationError: If update fails
    """
    try:
        # Validate model name is in available models
        provider_key = config_request.provider.value
        if config_request.model_name not in AVAILABLE_MODELS[provider_key]:
            raise ConfigurationError(
                f"Model '{config_request.model_name}' not available for provider '{provider_key}'",
                details={
                    "provider": provider_key,
                    "model": config_request.model_name,
                    "available_models": AVAILABLE_MODELS[provider_key]
                }
            )

        # Update configuration
        stmt = (
            update(LLMConfigDB)
            .where(LLMConfigDB.id == 1)
            .values(
                provider=config_request.provider.value,
                model_name=config_request.model_name,
                api_key_google=config_request.api_key_google,
                api_key_openrouter=config_request.api_key_openrouter,
                ollama_base_url=config_request.ollama_base_url,
                api_key_anthropic=config_request.api_key_anthropic,
                api_key_openai=config_request.api_key_openai,
                updated_at=datetime.now(timezone.utc)
            )
        )

        await db.execute(stmt)
        await db.commit()

        # Fetch updated config
        updated_config = await get_current_llm_config(db)

        logger.info(
            f"Updated LLM config: provider={updated_config.provider}, "
            f"model={updated_config.model_name}"
        )

        return LLMConfigResponse(
            provider=LLMProvider(updated_config.provider),
            model_name=updated_config.model_name,
            api_key_google_set=updated_config.api_key_google is not None,
            api_key_openrouter_set=updated_config.api_key_openrouter is not None,
            ollama_base_url=updated_config.ollama_base_url,
            api_key_anthropic_set=updated_config.api_key_anthropic is not None,
            api_key_openai_set=updated_config.api_key_openai is not None,
            updated_at=updated_config.updated_at
        )

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Error updating LLM config: {e}", exc_info=True)
        await db.rollback()
        raise ConfigurationError(
            "Failed to update LLM configuration",
            details={"error": str(e)}
        )


async def create_pydantic_ai_model(db: AsyncSession) -> Model:
    """
    Factory method to create a Pydantic-AI model instance based on current configuration.

    Args:
        db: Database session

    Returns:
        Model: Configured Pydantic-AI model (GeminiModel, OpenAIChatModel, or AnthropicModel)

    Raises:
        ConfigurationError: If configuration is invalid or API keys are missing
    """
    config = await get_current_llm_config(db)

    try:
        if config.provider == "google":
            # Google Gemini configuration
            api_key = config.api_key_google or os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise ConfigurationError(
                    "Google Gemini API key not configured. Set GEMINI_API_KEY environment variable "
                    "or configure in settings.",
                    details={"provider": "google"}
                )

            # Set API key in environment if it's from DB config
            if config.api_key_google:
                os.environ["GEMINI_API_KEY"] = config.api_key_google

            logger.info(f"Creating Google Gemini model: {config.model_name}")
            # GoogleModel reads API key from GEMINI_API_KEY environment variable
            return GoogleModel(model_name=config.model_name)

        elif config.provider == "openrouter":
            # OpenRouter configuration (via OpenAI-compatible interface)
            api_key = config.api_key_openrouter or os.getenv("OPENROUTER_API_KEY")

            if not api_key:
                raise ConfigurationError(
                    "OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable "
                    "or configure in settings.",
                    details={"provider": "openrouter"}
                )

            # Set API key in environment for OpenRouter provider
            os.environ["OPENROUTER_API_KEY"] = api_key

            logger.info(f"Creating OpenRouter model: {config.model_name}")
            return OpenAIChatModel(
                model_name=config.model_name,
                provider="openrouter"
            )

        elif config.provider == "ollama":
            # Ollama configuration (local LLM server)
            base_url = config.ollama_base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"

            logger.info(f"Creating Ollama model: {config.model_name} at {base_url}")
            # Ollama uses OpenAI-compatible API
            return OpenAIChatModel(
                model_name=config.model_name,
                base_url=base_url,
                api_key="ollama"  # Ollama doesn't require a real API key
            )

        elif config.provider == "anthropic":
            api_key = config.api_key_anthropic or os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                raise ConfigurationError(
                    "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable "
                    "or configure in settings.",
                    details={"provider": "anthropic"}
                )

            logger.info(f"Creating Anthropic model: {config.model_name}")
            return AnthropicModel(
                model_name=config.model_name,
                provider=AnthropicProvider(api_key=api_key),
            )

        elif config.provider == "openai":
            api_key = config.api_key_openai or os.getenv("OPENAI_API_KEY")

            if not api_key:
                raise ConfigurationError(
                    "OpenAI API key not configured. Set OPENAI_API_KEY environment variable "
                    "or configure in settings.",
                    details={"provider": "openai"}
                )

            logger.info(f"Creating OpenAI model: {config.model_name}")
            return OpenAIChatModel(
                model_name=config.model_name,
                provider=OpenAIProvider(api_key=api_key),
            )

        elif config.provider == "cliproxy":
            # CLIProxyAPI — OpenAI-compatible local proxy for Claude/OpenAI subscriptions
            base_url = config.ollama_base_url or os.getenv("CLIPROXY_BASE_URL") or "http://localhost:8317/v1"

            logger.info(f"Creating CLIProxy model: {config.model_name} at {base_url}")
            return OpenAIChatModel(
                model_name=config.model_name,
                provider=OpenAIProvider(base_url=base_url, api_key="not-needed"),
            )

        else:
            raise ConfigurationError(
                f"Unknown LLM provider: {config.provider}",
                details={"provider": config.provider}
            )

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Error creating Pydantic-AI model: {e}", exc_info=True)
        raise ConfigurationError(
            "Failed to create LLM model instance",
            details={
                "provider": config.provider,
                "model": config.model_name,
                "error": str(e)
            }
        )


def get_available_models() -> AvailableModelsResponse:
    """
    Get list of available models for each provider.

    Returns:
        AvailableModelsResponse: Available models per provider
    """
    return AvailableModelsResponse(
        google=AVAILABLE_MODELS["google"],
        openrouter=AVAILABLE_MODELS["openrouter"],
        ollama=AVAILABLE_MODELS["ollama"],
        anthropic=AVAILABLE_MODELS["anthropic"],
        openai=AVAILABLE_MODELS["openai"],
        cliproxy=AVAILABLE_MODELS["cliproxy"],
    )


async def get_llm_config_response(db: AsyncSession) -> LLMConfigResponse:
    """
    Get current LLM configuration as API response model.

    Args:
        db: Database session

    Returns:
        LLMConfigResponse: Current configuration for API response
    """
    config = await get_current_llm_config(db)

    return LLMConfigResponse(
        provider=LLMProvider(config.provider),
        model_name=config.model_name,
        api_key_google_set=config.api_key_google is not None or os.getenv("GEMINI_API_KEY") is not None,
        api_key_openrouter_set=config.api_key_openrouter is not None or os.getenv("OPENROUTER_API_KEY") is not None,
        ollama_base_url=config.ollama_base_url or os.getenv("OLLAMA_BASE_URL"),
        api_key_anthropic_set=config.api_key_anthropic is not None or os.getenv("ANTHROPIC_API_KEY") is not None,
        api_key_openai_set=config.api_key_openai is not None or os.getenv("OPENAI_API_KEY") is not None,
        updated_at=config.updated_at
    )


# ============================================================================
# Per-Agent LLM Configuration (NEW)
# ============================================================================


async def get_agent_llm_config(
    db: AsyncSession,
    agent_type: "AgentType"
) -> "AgentLLMConfigDB | None":
    """
    Get LLM configuration for a specific agent type.

    Args:
        db: Database session
        agent_type: Type of agent

    Returns:
        AgentLLMConfigDB if configured and enabled, None if should use global config
    """
    from app.db_models import AgentLLMConfigDB
    from app.models import AgentType

    try:
        result = await db.execute(
            select(AgentLLMConfigDB).where(
                AgentLLMConfigDB.agent_type == agent_type.value,
                AgentLLMConfigDB.enabled == 1
            )
        )
        config = result.scalar_one_or_none()

        if config:
            logger.debug(
                f"Found agent-specific config for {agent_type.value}: "
                f"{config.provider}/{config.model_name}"
            )
        else:
            logger.debug(f"No agent-specific config for {agent_type.value}, will use global")

        return config

    except Exception as e:
        logger.error(f"Error retrieving agent LLM config: {e}", exc_info=True)
        return None


async def set_agent_llm_config(
    db: AsyncSession,
    config_request: "AgentLLMConfigRequest"
) -> "AgentLLMConfigResponse":
    """
    Create or update LLM configuration for a specific agent.

    Args:
        db: Database session
        config_request: Agent LLM configuration

    Returns:
        AgentLLMConfigResponse with created/updated config

    Raises:
        ConfigurationError: If validation fails
    """
    from app.db_models import AgentLLMConfigDB
    from app.models import AgentLLMConfigRequest, AgentLLMConfigResponse, AgentType

    try:
        # Validate model name is available for provider
        provider_key = config_request.provider.value
        if config_request.model_name not in AVAILABLE_MODELS[provider_key]:
            raise ConfigurationError(
                f"Model '{config_request.model_name}' not available for provider '{provider_key}'",
                details={
                    "provider": provider_key,
                    "model": config_request.model_name,
                    "available_models": AVAILABLE_MODELS[provider_key]
                }
            )

        # Check if config already exists
        result = await db.execute(
            select(AgentLLMConfigDB).where(
                AgentLLMConfigDB.agent_type == config_request.agent_type.value
            )
        )
        existing_config = result.scalar_one_or_none()

        if existing_config:
            # Update existing config
            existing_config.provider = config_request.provider.value
            existing_config.model_name = config_request.model_name
            existing_config.api_key_google = config_request.api_key_google
            existing_config.api_key_openrouter = config_request.api_key_openrouter
            existing_config.ollama_base_url = config_request.ollama_base_url
            existing_config.api_key_anthropic = config_request.api_key_anthropic
            existing_config.api_key_openai = config_request.api_key_openai
            existing_config.max_tokens = config_request.max_tokens
            # Convert float temperature to string for storage
            existing_config.temperature = str(config_request.temperature) if config_request.temperature is not None else None
            existing_config.enabled = 1 if config_request.enabled else 0
            existing_config.updated_at = datetime.now(timezone.utc)

            logger.info(
                f"Updated agent config for {config_request.agent_type.value}: "
                f"{config_request.provider.value}/{config_request.model_name}"
            )
        else:
            # Create new config
            new_config = AgentLLMConfigDB(
                agent_type=config_request.agent_type.value,
                provider=config_request.provider.value,
                model_name=config_request.model_name,
                api_key_google=config_request.api_key_google,
                api_key_openrouter=config_request.api_key_openrouter,
                ollama_base_url=config_request.ollama_base_url,
                api_key_anthropic=config_request.api_key_anthropic,
                api_key_openai=config_request.api_key_openai,
                max_tokens=config_request.max_tokens,
                temperature=str(config_request.temperature) if config_request.temperature is not None else None,
                enabled=1 if config_request.enabled else 0
            )
            db.add(new_config)

            logger.info(
                f"Created agent config for {config_request.agent_type.value}: "
                f"{config_request.provider.value}/{config_request.model_name}"
            )

        await db.commit()

        # Fetch and return updated config
        result = await db.execute(
            select(AgentLLMConfigDB).where(
                AgentLLMConfigDB.agent_type == config_request.agent_type.value
            )
        )
        updated_config = result.scalar_one()

        # Parse temperature back to float
        temperature_float = float(updated_config.temperature) if updated_config.temperature else None

        return AgentLLMConfigResponse(
            id=updated_config.id,
            agent_type=AgentType(updated_config.agent_type),
            provider=LLMProvider(updated_config.provider),
            model_name=updated_config.model_name,
            api_key_google_set=updated_config.api_key_google is not None,
            api_key_openrouter_set=updated_config.api_key_openrouter is not None,
            ollama_base_url=updated_config.ollama_base_url,
            api_key_anthropic_set=updated_config.api_key_anthropic is not None,
            api_key_openai_set=updated_config.api_key_openai is not None,
            max_tokens=updated_config.max_tokens,
            temperature=temperature_float,
            enabled=bool(updated_config.enabled),
            created_at=updated_config.created_at,
            updated_at=updated_config.updated_at
        )

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Error setting agent LLM config: {e}", exc_info=True)
        await db.rollback()
        raise ConfigurationError(
            "Failed to set agent LLM configuration",
            details={"error": str(e)}
        )


async def delete_agent_llm_config(
    db: AsyncSession,
    agent_type: "AgentType"
) -> bool:
    """
    Delete per-agent LLM configuration (agent will use global config).

    Args:
        db: Database session
        agent_type: Type of agent

    Returns:
        True if deleted, False if not found
    """
    from app.db_models import AgentLLMConfigDB
    from sqlalchemy import delete

    try:
        result = await db.execute(
            delete(AgentLLMConfigDB).where(
                AgentLLMConfigDB.agent_type == agent_type.value
            )
        )

        deleted = result.rowcount > 0
        if deleted:
            await db.commit()
            logger.info(f"Deleted agent config for {agent_type.value}, will use global config")
        else:
            logger.warning(f"No agent config found for {agent_type.value}")

        return deleted

    except Exception as e:
        logger.error(f"Error deleting agent LLM config: {e}", exc_info=True)
        await db.rollback()
        return False


async def get_all_llm_configs(db: AsyncSession) -> "AllLLMConfigsResponse":
    """
    Get all LLM configurations (global + per-agent).

    Args:
        db: Database session

    Returns:
        AllLLMConfigsResponse with global and agent configs
    """
    from app.db_models import AgentLLMConfigDB
    from app.models import AllLLMConfigsResponse, AgentType, AgentLLMConfigResponse

    # Get global config
    global_response = await get_llm_config_response(db)

    # Get all agent configs
    result = await db.execute(select(AgentLLMConfigDB))
    agent_configs_db = result.scalars().all()

    agent_configs = {}
    for config in agent_configs_db:
        if config.enabled:
            # Parse temperature back to float
            temperature_float = float(config.temperature) if config.temperature else None

            agent_configs[AgentType(config.agent_type)] = AgentLLMConfigResponse(
                id=config.id,
                agent_type=AgentType(config.agent_type),
                provider=LLMProvider(config.provider),
                model_name=config.model_name,
                api_key_google_set=config.api_key_google is not None,
                api_key_openrouter_set=config.api_key_openrouter is not None,
                ollama_base_url=config.ollama_base_url,
                api_key_anthropic_set=config.api_key_anthropic is not None,
                api_key_openai_set=config.api_key_openai is not None,
                max_tokens=config.max_tokens,
                temperature=temperature_float,
                enabled=bool(config.enabled),
                created_at=config.created_at,
                updated_at=config.updated_at
            )

    # Determine which agents use custom vs global
    all_agents = list(AgentType)
    agents_with_overrides = list(agent_configs.keys())
    agents_using_global = [a for a in all_agents if a not in agents_with_overrides]

    return AllLLMConfigsResponse(
        global_config=global_response,
        agent_configs=agent_configs,
        agents_with_overrides=agents_with_overrides,
        agents_using_global=agents_using_global
    )


async def create_pydantic_ai_model_for_agent(
    db: AsyncSession,
    agent_type: "AgentType"
) -> Model:
    """
    Factory method to create Pydantic-AI model for a specific agent.

    This function implements the configuration hierarchy:
    1. Check for agent-specific config (if exists and enabled)
    2. Fall back to global config (if no agent-specific config)

    Args:
        db: Database session
        agent_type: Type of agent requesting the model

    Returns:
        Model: Configured Pydantic-AI model instance

    Raises:
        ConfigurationError: If configuration is invalid or API keys missing
    """
    from app.models import AgentType

    # Try to get agent-specific config first
    agent_config = await get_agent_llm_config(db, agent_type)

    if agent_config:
        # Use agent-specific configuration
        logger.info(
            f"Creating model for {agent_type.value} using agent-specific config: "
            f"{agent_config.provider}/{agent_config.model_name}"
        )

        config_to_use = agent_config
        # Fallback to global config for missing API keys
        global_config = await get_current_llm_config(db)

    else:
        # Use global configuration
        logger.info(
            f"Creating model for {agent_type.value} using global config"
        )
        config_to_use = await get_current_llm_config(db)
        global_config = config_to_use

    # Create model based on provider
    try:
        if config_to_use.provider == "google":
            # Google Gemini
            api_key = (
                config_to_use.api_key_google or
                global_config.api_key_google or
                os.getenv("GEMINI_API_KEY")
            )

            if not api_key:
                raise ConfigurationError(
                    f"Google Gemini API key not configured for agent '{agent_type.value}'",
                    details={"provider": "google", "agent_type": agent_type.value}
                )

            os.environ["GEMINI_API_KEY"] = api_key
            logger.info(f"Creating Google model for {agent_type.value}: {config_to_use.model_name}")
            return GoogleModel(model_name=config_to_use.model_name)

        elif config_to_use.provider == "openrouter":
            # OpenRouter
            api_key = (
                config_to_use.api_key_openrouter or
                global_config.api_key_openrouter or
                os.getenv("OPENROUTER_API_KEY")
            )

            if not api_key:
                raise ConfigurationError(
                    f"OpenRouter API key not configured for agent '{agent_type.value}'",
                    details={"provider": "openrouter", "agent_type": agent_type.value}
                )

            os.environ["OPENROUTER_API_KEY"] = api_key
            logger.info(f"Creating OpenRouter model for {agent_type.value}: {config_to_use.model_name}")
            return OpenAIChatModel(
                model_name=config_to_use.model_name,
                provider="openrouter"
            )

        elif config_to_use.provider == "ollama":
            # Ollama
            base_url = (
                config_to_use.ollama_base_url or
                global_config.ollama_base_url or
                os.getenv("OLLAMA_BASE_URL") or
                "http://localhost:11434/v1"
            )

            logger.info(f"Creating Ollama model for {agent_type.value}: {config_to_use.model_name}")
            return OpenAIChatModel(
                model_name=config_to_use.model_name,
                base_url=base_url,
                api_key="ollama"
            )

        elif config_to_use.provider == "anthropic":
            api_key = (
                config_to_use.api_key_anthropic or
                global_config.api_key_anthropic or
                os.getenv("ANTHROPIC_API_KEY")
            )

            if not api_key:
                raise ConfigurationError(
                    f"Anthropic API key not configured for agent '{agent_type.value}'",
                    details={"provider": "anthropic", "agent_type": agent_type.value}
                )

            logger.info(f"Creating Anthropic model for {agent_type.value}: {config_to_use.model_name}")
            return AnthropicModel(
                model_name=config_to_use.model_name,
                provider=AnthropicProvider(api_key=api_key),
            )

        elif config_to_use.provider == "openai":
            api_key = (
                config_to_use.api_key_openai or
                global_config.api_key_openai or
                os.getenv("OPENAI_API_KEY")
            )

            if not api_key:
                raise ConfigurationError(
                    f"OpenAI API key not configured for agent '{agent_type.value}'",
                    details={"provider": "openai", "agent_type": agent_type.value}
                )

            logger.info(f"Creating OpenAI model for {agent_type.value}: {config_to_use.model_name}")
            return OpenAIChatModel(
                model_name=config_to_use.model_name,
                provider=OpenAIProvider(api_key=api_key),
            )

        elif config_to_use.provider == "cliproxy":
            # CLIProxyAPI — OpenAI-compatible local proxy for Claude/OpenAI subscriptions
            base_url = (
                config_to_use.ollama_base_url or
                global_config.ollama_base_url or
                os.getenv("CLIPROXY_BASE_URL") or
                "http://localhost:8317/v1"
            )

            logger.info(f"Creating CLIProxy model for {agent_type.value}: {config_to_use.model_name} at {base_url}")
            return OpenAIChatModel(
                model_name=config_to_use.model_name,
                provider=OpenAIProvider(base_url=base_url, api_key="not-needed"),
            )

        else:
            raise ConfigurationError(
                f"Unknown provider for agent '{agent_type.value}': {config_to_use.provider}",
                details={"provider": config_to_use.provider}
            )

    except ConfigurationError:
        raise
    except Exception as e:
        logger.error(f"Error creating model for agent '{agent_type.value}': {e}", exc_info=True)
        raise ConfigurationError(
            f"Failed to create LLM model for agent '{agent_type.value}'",
            details={
                "provider": config_to_use.provider,
                "model": config_to_use.model_name,
                "error": str(e)
            }
        )
