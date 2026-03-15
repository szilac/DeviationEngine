"""
Settings API endpoints.

This module handles:
- LLM provider configuration (global and per-agent)
- Available LLM models listing
- API key management for different providers
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os

from app.database import get_db
from app.models import (
    LLMConfigResponse,
    LLMConfigRequest,
    AvailableModelsResponse,
    AllLLMConfigsResponse,
    AgentLLMConfigRequest,
    AgentLLMConfigResponse,
    AgentType,
    LLMProvider,
    DebugSettings,
    DebugSettingsUpdate,
)
from app.services import llm_service
from app.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Create router with /api prefix
router = APIRouter(prefix="/api", tags=["settings"])


@router.get(
    "/llm-config",
    response_model=LLMConfigResponse,
    summary="Get current LLM configuration",
    description="Retrieve the current LLM provider and model configuration",
)
async def get_llm_configuration(db: AsyncSession = Depends(get_db)) -> LLMConfigResponse:
    """
    Get the current LLM provider configuration.

    Returns:
        LLMConfigResponse: Current provider, model, and API key status

    Raises:
        HTTPException: If configuration cannot be retrieved
    """
    try:
        config = await llm_service.get_llm_config_response(db)
        logger.info(
            f"Retrieved LLM config: provider={config.provider}, model={config.model_name}"
        )
        return config
    except ConfigurationError as e:
        logger.error(f"Failed to get LLM config: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error getting LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve LLM configuration",
        )


@router.put(
    "/llm-config",
    response_model=LLMConfigResponse,
    summary="Update LLM configuration",
    description="Update the LLM provider, model, and API keys",
)
async def update_llm_configuration(
    config_request: LLMConfigRequest, db: AsyncSession = Depends(get_db)
) -> LLMConfigResponse:
    """
    Update the LLM provider configuration.

    Args:
        config_request: New configuration (provider, model, API keys)
        db: Database session

    Returns:
        LLMConfigResponse: Updated configuration

    Raises:
        HTTPException: If configuration update fails or validation fails
    """
    try:
        config = await llm_service.update_llm_config(db, config_request)
        logger.info(f"Updated LLM config: provider={config.provider}, model={config.model_name}")
        return config
    except ConfigurationError as e:
        logger.error(f"Failed to update LLM config: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error updating LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update LLM configuration",
        )


@router.get(
    "/llm-models",
    response_model=AvailableModelsResponse,
    summary="Get available LLM models",
    description="Retrieve list of available models for each provider",
)
async def get_available_models() -> AvailableModelsResponse:
    """
    Get lists of available models for each LLM provider.

    Returns:
        AvailableModelsResponse: Available models per provider

    Raises:
        HTTPException: If model list cannot be retrieved
    """
    try:
        models = llm_service.get_available_models()
        logger.debug(
            f"Retrieved available models: {len(models.google)} Google, {len(models.openrouter)} OpenRouter"
        )
        return models
    except Exception as e:
        logger.error(f"Unexpected error getting available models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available models",
        )


# ============================================================================
# Per-Agent LLM Configuration Endpoints
# ============================================================================


@router.get(
    "/llm/agents",
    response_model=AllLLMConfigsResponse,
    summary="Get all LLM configurations",
    description="Retrieve global LLM config and per-agent overrides",
)
async def get_all_llm_configurations(db: AsyncSession = Depends(get_db)):
    """
    Get global and per-agent LLM configurations.

    Returns:
        AllLLMConfigsResponse: Global config and agent-specific overrides

    Raises:
        HTTPException: If configurations cannot be retrieved
    """
    try:
        configs = await llm_service.get_all_llm_configs(db)
        logger.info(
            f"Retrieved LLM configurations: global + {len(configs.agents_with_overrides)} agent overrides"
        )
        return configs
    except ConfigurationError as e:
        logger.error(f"Failed to get LLM configurations: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error getting LLM configurations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve LLM configurations",
        )


@router.post(
    "/llm/agents/{agent_type}",
    response_model=AgentLLMConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set agent-specific LLM config",
    description="Create or update LLM configuration for a specific agent",
)
async def set_agent_llm_configuration(
    agent_type: str, config_request: AgentLLMConfigRequest, db: AsyncSession = Depends(get_db)
):
    """
    Configure a specific agent to use a particular LLM model.

    This creates an override for the specified agent. If no override exists,
    the agent uses the global LLM configuration.

    Args:
        agent_type: Type of agent (historian, storyteller, skeleton, skeleton_historian)
        config_request: Agent LLM configuration

    Returns:
        AgentLLMConfigResponse: Created/updated configuration

    Raises:
        HTTPException: 400 if validation fails, 404 if agent type invalid
    """
    try:
        # Validate agent_type
        try:
            agent_type_enum = AgentType(agent_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent type: {agent_type}. Must be one of: historian, storyteller, skeleton, skeleton_historian, illustrator, translator",
            )

        # Ensure agent_type in path matches request body
        if agent_type_enum != config_request.agent_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent type in path must match request body",
            )

        config = await llm_service.set_agent_llm_config(db, config_request)
        logger.info(
            f"Set agent config for {agent_type}: {config.provider.value}/{config.model_name}"
        )
        return config

    except ConfigurationError as e:
        logger.error(f"Failed to set agent LLM config: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error setting agent LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set agent LLM configuration",
        )


@router.delete(
    "/llm/agents/{agent_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent-specific LLM config",
    description="Remove override for agent (will use global config)",
)
async def delete_agent_llm_configuration(agent_type: str, db: AsyncSession = Depends(get_db)):
    """
    Delete agent-specific LLM configuration.

    After deletion, the agent will use the global LLM configuration.

    Args:
        agent_type: Type of agent (historian, storyteller, skeleton, skeleton_historian)

    Raises:
        HTTPException: 400 if agent type invalid, 404 if config not found
    """
    try:
        # Validate agent_type
        try:
            agent_type_enum = AgentType(agent_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent type: {agent_type}. Must be one of: historian, storyteller, skeleton, skeleton_historian, illustrator",
            )

        deleted = await llm_service.delete_agent_llm_config(db, agent_type_enum)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No configuration found for agent '{agent_type}'",
            )

        logger.info(f"Deleted agent config for {agent_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting agent LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent LLM configuration",
        )


@router.get(
    "/llm/agents/{agent_type}",
    summary="Get agent-specific LLM config",
    description="Get configuration for a specific agent (or indicate it uses global)",
)
async def get_agent_llm_configuration(agent_type: str, db: AsyncSession = Depends(get_db)):
    """
    Get LLM configuration for a specific agent.

    Returns the agent-specific config if it exists, otherwise returns
    a message indicating the agent uses the global config.

    Args:
        agent_type: Type of agent (historian, storyteller, skeleton, skeleton_historian)

    Returns:
        AgentLLMConfigResponse or dict with usage info

    Raises:
        HTTPException: 400 if agent type invalid
    """
    try:
        # Validate agent_type
        try:
            agent_type_enum = AgentType(agent_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent type: {agent_type}. Must be one of: historian, storyteller, skeleton, skeleton_historian, illustrator",
            )

        agent_config = await llm_service.get_agent_llm_config(db, agent_type_enum)

        if not agent_config:
            return {
                "message": f"Agent '{agent_type}' uses global LLM configuration",
                "using_global": True,
            }

        # Parse temperature back to float
        temperature_float = (
            float(agent_config.temperature) if agent_config.temperature else None
        )

        return AgentLLMConfigResponse(
            id=agent_config.id,
            agent_type=agent_type_enum,
            provider=LLMProvider(agent_config.provider),
            model_name=agent_config.model_name,
            api_key_google_set=agent_config.api_key_google is not None,
            api_key_openrouter_set=agent_config.api_key_openrouter is not None,
            ollama_base_url=agent_config.ollama_base_url,
            max_tokens=agent_config.max_tokens,
            temperature=temperature_float,
            enabled=bool(agent_config.enabled),
            created_at=agent_config.created_at,
            updated_at=agent_config.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting agent LLM config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent LLM configuration",
        )


# ============================================================================
# Debug Settings Endpoints
# ============================================================================


@router.get(
    "/debug-settings",
    response_model=DebugSettings,
    summary="Get debug settings",
    description="Retrieve current debug settings for RAG and agent prompts",
)
async def get_debug_settings() -> DebugSettings:
    """
    Get current debug settings.

    Returns:
        DebugSettings: Current debug mode flags

    Raises:
        HTTPException: If settings cannot be retrieved
    """
    try:
        rag_debug = os.getenv("RAG_DEBUG_MODE", "false").lower() == "true"
        agent_prompts_debug = os.getenv("DEBUG_AGENT_PROMPTS", "false").lower() == "true"
        vector_store_enabled = os.getenv("VECTOR_STORE_ENABLED", "true").lower() == "true"
        context_retrieval_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()

        settings = DebugSettings(
            rag_debug_mode=rag_debug,
            debug_agent_prompts=agent_prompts_debug,
            vector_store_enabled=vector_store_enabled,
            context_retrieval_mode=context_retrieval_mode,
        )

        logger.debug(f"Retrieved debug settings: {settings}")
        return settings

    except Exception as e:
        logger.error(f"Unexpected error getting debug settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve debug settings",
        )


@router.put(
    "/debug-settings",
    response_model=DebugSettings,
    summary="Update debug settings",
    description="Update debug settings (requires restart for some changes to take effect)",
)
async def update_debug_settings(settings_update: DebugSettingsUpdate) -> DebugSettings:
    """
    Update debug settings.

    Note: Changes to these settings update environment variables but may require
    a server restart for some components to pick up the changes.

    Args:
        settings_update: New debug settings

    Returns:
        DebugSettings: Updated debug settings

    Raises:
        HTTPException: If settings update fails
    """
    try:
        # Update environment variables if values provided
        if settings_update.rag_debug_mode is not None:
            os.environ["RAG_DEBUG_MODE"] = "true" if settings_update.rag_debug_mode else "false"
            logger.info(f"Updated RAG_DEBUG_MODE to {settings_update.rag_debug_mode}")

        if settings_update.debug_agent_prompts is not None:
            os.environ["DEBUG_AGENT_PROMPTS"] = (
                "true" if settings_update.debug_agent_prompts else "false"
            )
            logger.info(f"Updated DEBUG_AGENT_PROMPTS to {settings_update.debug_agent_prompts}")

        if settings_update.vector_store_enabled is not None:
            os.environ["VECTOR_STORE_ENABLED"] = (
                "true" if settings_update.vector_store_enabled else "false"
            )
            logger.info(f"Updated VECTOR_STORE_ENABLED to {settings_update.vector_store_enabled}")

        if settings_update.context_retrieval_mode is not None:
            # Validate the value
            if settings_update.context_retrieval_mode not in ["rag", "legacy"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="context_retrieval_mode must be 'rag' or 'legacy'"
                )
            os.environ["CONTEXT_RETRIEVAL_MODE"] = settings_update.context_retrieval_mode
            logger.info(f"Updated CONTEXT_RETRIEVAL_MODE to {settings_update.context_retrieval_mode}")

        # Return current settings
        return DebugSettings(
            rag_debug_mode=os.getenv("RAG_DEBUG_MODE", "false").lower() == "true",
            debug_agent_prompts=os.getenv("DEBUG_AGENT_PROMPTS", "false").lower() == "true",
            vector_store_enabled=os.getenv("VECTOR_STORE_ENABLED", "true").lower() == "true",
            context_retrieval_mode=os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower(),
        )

    except Exception as e:
        logger.error(f"Unexpected error updating debug settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update debug settings",
        )


# ============================================================================
# Data Purge Endpoints
# ============================================================================


@router.post(
    "/purge-data",
    summary="Purge all user data",
    description="⚠️ DANGER: Permanently delete all timelines, skeleton drafts, generations, and media. Preserves configuration and ground truth.",
)
async def purge_all_data(
    preserve_ground_truth: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    ⚠️ DANGER: Purge all user-generated data from the system.

    This removes:
    - All timelines and their generations (cascades to all related data)
    - All skeleton drafts (workflow drafts)
    - All audio scripts and audio files
    - Vector store data (except ground truth if preserve_ground_truth=True)
    - Generated audio files from filesystem
    - Generated image files from filesystem
    - Agent prompt logs

    This preserves:
    - Configuration settings (LLM, translation, presets)
    - Ground truth historical data (if preserve_ground_truth=True)

    Args:
        preserve_ground_truth: If True, preserve ground truth data (default: True)
        db: Database session

    Returns:
        Dictionary with purge statistics

    Raises:
        HTTPException: If purge operation fails
    """
    try:
        from app.services.purge_service import get_purge_service

        logger.warning("=" * 80)
        logger.warning("⚠️  DATA PURGE REQUESTED VIA API")
        logger.warning(f"   Preserve ground truth: {preserve_ground_truth}")
        logger.warning("=" * 80)

        purge_service = get_purge_service()
        stats = await purge_service.purge_all_data(
            db=db,
            preserve_ground_truth=preserve_ground_truth
        )

        return {
            "success": True,
            "message": "Data purge completed successfully",
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Unexpected error during data purge: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge data: {str(e)}",
        )
