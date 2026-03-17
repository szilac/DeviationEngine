"""
Predefined workflow definitions for common agent orchestration patterns.

This module provides ready-to-use workflow builders for standard
multi-agent patterns in the Deviation Engine application.
"""

import logging
from typing import Optional

from app.agents.orchestrator import orchestrator, WorkflowContext
from app.agents import historian_agent, storyteller_agent, skeleton_agent, skeleton_historian_agent
from app.models import (
    TimelineCreationRequest,
    TimelineExtensionRequest,
    NarrativeMode,
    StructuredReport,
    ScenarioType,
)
from app.exceptions import AIGenerationError

# Configure logging
logger = logging.getLogger(__name__)


async def _generate_structured_report(context: WorkflowContext) -> StructuredReport:
    """
    Workflow step: Generate structured historical analysis.

    Args:
        context: Workflow context containing deviation_request and historical_context

    Returns:
        StructuredReport with analytical sections
    """
    request = context.get("deviation_request")
    historical_context = context.get("historical_context")
    # Use historian-specific model if available, fallback to general model
    model = context.get("historian_model") or context.get("model")

    logger.info(
        f"Generating structured report for deviation: {request.deviation_description[:50]}..."
    )

    # Call historian agent with the model
    timeline_output = await historian_agent.generate_timeline(
        request,
        historical_context,
        model=model
    )

    # Extract structured report
    structured_report = StructuredReport(
        start_year=0,
        end_year=request.simulation_years,
        period_years=request.simulation_years,
        report_order=1,
        executive_summary=timeline_output.executive_summary,
        political_changes=timeline_output.political_changes,
        conflicts_and_wars=timeline_output.conflicts_and_wars,
        economic_impacts=timeline_output.economic_impacts,
        social_developments=timeline_output.social_developments,
        technological_shifts=timeline_output.technological_shifts,
        key_figures=timeline_output.key_figures,
        long_term_implications=timeline_output.long_term_implications,
    )

    # Store in context for next steps
    context.set("structured_report", structured_report)
    context.set("basic_narrative", timeline_output.narrative_prose)
    context.set("timeline_name", timeline_output.timeline_name)  # Store timeline name for later use

    logger.info("Structured report generated successfully")
    return structured_report


async def _generate_advanced_narrative(context: WorkflowContext) -> Optional[str]:
    """
    Workflow step: Generate advanced narrative prose using storyteller agent.

    This step only executes if narrative_mode is ADVANCED_OMNISCIENT or ADVANCED_CUSTOM_POV.

    Args:
        context: Workflow context containing structured_report and deviation_request

    Returns:
        Generated narrative prose or None if basic/no narrative mode
    """
    request = context.get("deviation_request")
    structured_report = context.get("structured_report")
    # Use storyteller-specific model if available, fallback to general model
    model = context.get("storyteller_model") or context.get("model")

    # For extensions, use the extension_request's narrative_mode if available
    extension_request = context.get("extension_request")
    narrative_mode = extension_request.narrative_mode if extension_request else request.narrative_mode

    # Skip if not advanced mode
    if narrative_mode not in [
        NarrativeMode.ADVANCED_OMNISCIENT,
        NarrativeMode.ADVANCED_CUSTOM_POV
    ]:
        logger.info(f"Skipping advanced narrative (mode: {narrative_mode.value})")
        return None

    logger.info(f"Generating advanced narrative (mode: {narrative_mode.value})")

    # Get custom POV if provided (prefer extension_request if available)
    if narrative_mode == NarrativeMode.ADVANCED_CUSTOM_POV:
        custom_pov = extension_request.narrative_custom_pov if extension_request else request.narrative_custom_pov
    else:
        custom_pov = None

    # Call storyteller agent with the model
    narrative = await storyteller_agent.generate_narrative(
        structured_report,
        request,
        custom_pov,
        model=model
    )

    context.set("advanced_narrative", narrative)
    logger.info(f"Advanced narrative generated successfully ({len(narrative)} chars)")

    return narrative


def _select_final_narrative(context: WorkflowContext) -> Optional[str]:
    """
    Workflow step: Select the appropriate narrative based on mode.

    Args:
        context: Workflow context

    Returns:
        Final narrative prose to use, or None
    """
    request = context.get("deviation_request")
    # For extensions, use the extension_request's narrative_mode if available
    extension_request = context.get("extension_request")
    narrative_mode = extension_request.narrative_mode if extension_request else request.narrative_mode

    if narrative_mode == NarrativeMode.NONE:
        return None
    elif narrative_mode == NarrativeMode.BASIC:
        return context.get("basic_narrative")
    elif narrative_mode in [NarrativeMode.ADVANCED_OMNISCIENT, NarrativeMode.ADVANCED_CUSTOM_POV]:
        # Use advanced if available, fallback to basic
        return context.get("advanced_narrative") or context.get("basic_narrative")

    logger.warning(f"Unknown narrative mode: {narrative_mode}, defaulting to basic")
    return context.get("basic_narrative")


def create_timeline_generation_workflow(
    deviation_request: TimelineCreationRequest,
    historical_context: str,
) -> WorkflowContext:
    """
    Create a workflow for generating a new timeline with multi-agent coordination.

    This workflow orchestrates the following steps:
    1. Generate structured historical analysis (historian_agent)
    2. Conditionally generate advanced narrative (storyteller_agent)
    3. Select final narrative based on mode

    Args:
        deviation_request: The deviation request from the user
        historical_context: Ground truth historical context

    Returns:
        A configured workflow ready for execution
    """
    workflow = orchestrator.create_workflow(
        name="timeline_generation",
        description="Generate alternate history timeline with optional advanced narrative"
    )

    # Step 1: Generate structured report (always executed)
    workflow.add_step(
        name="generate_structured_report",
        func=_generate_structured_report,
        timeout=360.0,  # 6 minutes max (Anthropic needs more time for large structured outputs)
        retry_count=1,  # Retry once on failure
    )

    # Step 2: Generate advanced narrative (conditional)
    workflow.add_step(
        name="generate_advanced_narrative",
        func=_generate_advanced_narrative,
        condition=lambda ctx: ctx.get("deviation_request").narrative_mode in [
            NarrativeMode.ADVANCED_OMNISCIENT,
            NarrativeMode.ADVANCED_CUSTOM_POV
        ],
        timeout=360.0,  # 6 minutes max (Anthropic needs more time for large structured outputs)
        retry_count=1,
    )

    return workflow


async def _extend_timeline_structured(context: WorkflowContext) -> StructuredReport:
    """
    Workflow step: Generate structured report for timeline extension.

    Args:
        context: Workflow context

    Returns:
        StructuredReport for the extension period
    """
    extension_request = context.get("extension_request")
    timeline = context.get("timeline")
    historical_context = context.get("historical_context")
    # Use historian-specific model if available, fallback to general model
    model = context.get("historian_model") or context.get("model")

    # Debug logging
    logger.debug(f"extension_request type: {type(extension_request)}, value: {extension_request}")

    if not hasattr(extension_request, 'additional_years'):
        logger.error(f"extension_request is not a TimelineExtensionRequest! Type: {type(extension_request)}, Value: {extension_request}")
        raise TypeError(f"extension_request must be TimelineExtensionRequest, got {type(extension_request)}")

    logger.info(f"Extending timeline {timeline.id} by {extension_request.additional_years} years")

    # Calculate extension period details
    current_max_year = timeline.total_years_simulated
    new_start_year = current_max_year
    new_end_year = current_max_year + extension_request.additional_years

    # Get next generation order (number of existing generations + 1)
    next_order = len(timeline.generations) + 1

    # Call extend_timeline from historian agent with the model
    timeline_output = await historian_agent.extend_timeline(
        timeline,
        extension_request,
        historical_context,
        model=model
    )

    # Extract structured report with proper period fields
    structured_report = StructuredReport(
        start_year=new_start_year,
        end_year=new_end_year,
        period_years=extension_request.additional_years,
        report_order=next_order,
        executive_summary=timeline_output.executive_summary,
        political_changes=timeline_output.political_changes,
        conflicts_and_wars=timeline_output.conflicts_and_wars,
        economic_impacts=timeline_output.economic_impacts,
        social_developments=timeline_output.social_developments,
        technological_shifts=timeline_output.technological_shifts,
        key_figures=timeline_output.key_figures,
        long_term_implications=timeline_output.long_term_implications,
    )

    context.set("structured_report", structured_report)
    context.set("basic_narrative", timeline_output.narrative_prose)

    logger.info("Extension structured report generated successfully")
    return structured_report


def create_timeline_extension_workflow(
    extension_request: TimelineExtensionRequest,
    timeline,  # Timeline model
    historical_context: str,
) -> WorkflowContext:
    """
    Create a workflow for extending an existing timeline.

    This workflow follows the same pattern as timeline generation:
    1. Generate structured report for extension period (historian_agent)
    2. Conditionally generate advanced narrative (storyteller_agent)
    3. Select final narrative based on mode

    Args:
        extension_request: The extension request
        timeline: The existing timeline to extend
        historical_context: Ground truth historical context

    Returns:
        A configured workflow ready for execution
    """
    workflow = orchestrator.create_workflow(
        name="timeline_extension",
        description="Extend existing timeline with optional advanced narrative"
    )

    # Step 1: Generate extension structured report
    workflow.add_step(
        name="extend_timeline_structured",
        func=_extend_timeline_structured,
        timeout=360.0,
        retry_count=1,
    )

    # Step 2: Generate advanced narrative (conditional)
    # Note: We reuse the same function, it works with extension_request too
    workflow.add_step(
        name="generate_advanced_narrative",
        func=_generate_advanced_narrative,
        condition=lambda ctx: ctx.get("extension_request").narrative_mode in [
            NarrativeMode.ADVANCED_OMNISCIENT,
            NarrativeMode.ADVANCED_CUSTOM_POV
        ],
        timeout=360.0,
        retry_count=1,
    )

    return workflow


async def execute_timeline_generation(
    deviation_request: TimelineCreationRequest,
    historical_context: str,
    db_session=None,
) -> dict:
    """
    Execute the complete timeline generation workflow.

    Args:
        deviation_request: The deviation request
        historical_context: Historical context for grounding
        db_session: Optional database session for LLM config (if None, uses env vars)

    Returns:
        Dictionary with structured_report, narrative_prose, and model info keys
    """
    # Get per-agent LLM models from service if db_session provided
    historian_model = None
    storyteller_model = None
    historian_provider = None
    historian_model_name = None
    storyteller_provider = None
    storyteller_model_name = None

    if db_session:
        from app.services import llm_service
        from app.models import AgentType

        # Get agent-specific configs to track what models will be used
        historian_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.HISTORIAN
        )
        storyteller_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.STORYTELLER
        )

        # Get global config for fallback
        global_config = await llm_service.get_current_llm_config(db_session)

        # Determine which config will be used for historian
        historian_config = historian_agent_config if historian_agent_config else global_config
        historian_provider = historian_config.provider
        historian_model_name = historian_config.model_name

        # Determine which config will be used for storyteller
        storyteller_config = storyteller_agent_config if storyteller_agent_config else global_config
        storyteller_provider = storyteller_config.provider
        storyteller_model_name = storyteller_config.model_name

        # Create agent-specific models
        historian_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.HISTORIAN
        )
        storyteller_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.STORYTELLER
        )
        logger.info(
            f"Using per-agent LLM models: historian={historian_provider}/{historian_model_name}, "
            f"storyteller={storyteller_provider}/{storyteller_model_name}"
        )

    workflow = create_timeline_generation_workflow(deviation_request, historical_context)

    # Initialize context with agent-specific models
    initial_state = {
        "deviation_request": deviation_request,
        "historical_context": historical_context,
        "historian_model": historian_model,
        "storyteller_model": storyteller_model,
        "model": historian_model,  # Keep for backward compatibility
    }

    # Execute workflow
    result_context = await orchestrator.execute_workflow(
        workflow,
        initial_state=initial_state,
        metadata={
            "deviation_date": str(deviation_request.deviation_date),
            "simulation_years": deviation_request.simulation_years,
            "narrative_mode": deviation_request.narrative_mode.value,
        }
    )

    # Extract final results
    structured_report = result_context.get_result("generate_structured_report")
    final_narrative = _select_final_narrative(result_context)
    timeline_name = result_context.get("timeline_name")  # Get timeline name from context

    # Determine which model was actually used for the narrative
    # If narrative mode is ADVANCED and storyteller was used, return storyteller info
    # Otherwise, if there's a basic narrative, it came from the historian
    narrative_provider = None
    narrative_model_name = None
    if final_narrative:
        if deviation_request.narrative_mode in [NarrativeMode.ADVANCED_OMNISCIENT, NarrativeMode.ADVANCED_CUSTOM_POV]:
            # Advanced narrative uses storyteller
            narrative_provider = storyteller_provider
            narrative_model_name = storyteller_model_name
        else:
            # Basic narrative uses historian
            narrative_provider = historian_provider
            narrative_model_name = historian_model_name

    return {
        "structured_report": structured_report,
        "narrative_prose": final_narrative,
        "timeline_name": timeline_name,  # Include timeline name from agent
        "workflow_metadata": result_context.metadata,
        "historian_provider": historian_provider,
        "historian_model_name": historian_model_name,
        "storyteller_provider": narrative_provider,
        "storyteller_model_name": narrative_model_name,
    }


async def execute_timeline_extension(
    extension_request: TimelineExtensionRequest,
    timeline,  # Timeline model
    historical_context: str,
    db_session=None,
) -> dict:
    """
    Execute the complete timeline extension workflow.

    Args:
        extension_request: The extension request
        timeline: The existing timeline
        historical_context: Historical context for grounding
        db_session: Optional database session for LLM config (if None, uses env vars)

    Returns:
        Dictionary with structured_report, narrative_prose, and model info keys
    """
    # Get per-agent LLM models from service if db_session provided
    historian_model = None
    storyteller_model = None
    historian_provider = None
    historian_model_name = None
    storyteller_provider = None
    storyteller_model_name = None

    if db_session:
        from app.services import llm_service
        from app.models import AgentType

        # Get agent-specific configs to track what models will be used
        historian_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.HISTORIAN
        )
        storyteller_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.STORYTELLER
        )

        # Get global config for fallback
        global_config = await llm_service.get_current_llm_config(db_session)

        # Determine which config will be used for historian
        historian_config = historian_agent_config if historian_agent_config else global_config
        historian_provider = historian_config.provider
        historian_model_name = historian_config.model_name

        # Determine which config will be used for storyteller
        storyteller_config = storyteller_agent_config if storyteller_agent_config else global_config
        storyteller_provider = storyteller_config.provider
        storyteller_model_name = storyteller_config.model_name

        # Create agent-specific models
        historian_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.HISTORIAN
        )
        storyteller_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.STORYTELLER
        )
        logger.info(
            f"Using per-agent LLM models for extension: historian={historian_provider}/{historian_model_name}, "
            f"storyteller={storyteller_provider}/{storyteller_model_name}"
        )

    workflow = create_timeline_extension_workflow(
        extension_request,
        timeline,
        historical_context
    )

    # Create a deviation_request from timeline's root deviation for narrative generation
    from datetime import date as date_type
    deviation_request_for_narrative = TimelineCreationRequest(
        deviation_date=date_type.fromisoformat(timeline.root_deviation_date) if isinstance(timeline.root_deviation_date, str) else timeline.root_deviation_date,
        deviation_description=timeline.root_deviation_description,
        simulation_years=timeline.total_years_simulated,
        scenario_type=timeline.scenario_type,
        narrative_mode=extension_request.narrative_mode,
        narrative_custom_pov=extension_request.narrative_custom_pov
    )

    # Initialize context with agent-specific models
    initial_state = {
        "extension_request": extension_request,
        "timeline": timeline,
        "historical_context": historical_context,
        "historian_model": historian_model,
        "storyteller_model": storyteller_model,
        "model": historian_model,  # Keep for backward compatibility
        # For narrative generation, we use the original deviation_request from the timeline
        "deviation_request": deviation_request_for_narrative,
    }

    # Execute workflow
    result_context = await orchestrator.execute_workflow(
        workflow,
        initial_state=initial_state,
        metadata={
            "timeline_id": str(timeline.id),
            "additional_years": extension_request.additional_years,
            "narrative_mode": extension_request.narrative_mode.value,
        }
    )

    # Extract final results
    structured_report = result_context.get_result("extend_timeline_structured")
    final_narrative = _select_final_narrative(result_context)
    timeline_name = result_context.get("timeline_name")  # Get timeline name from context

    # Determine which model was actually used for the narrative
    # If narrative mode is ADVANCED and storyteller was used, return storyteller info
    # Otherwise, if there's a basic narrative, it came from the historian
    narrative_provider = None
    narrative_model_name = None
    if final_narrative:
        if extension_request.narrative_mode in [NarrativeMode.ADVANCED_OMNISCIENT, NarrativeMode.ADVANCED_CUSTOM_POV]:
            # Advanced narrative uses storyteller
            narrative_provider = storyteller_provider
            narrative_model_name = storyteller_model_name
        else:
            # Basic narrative uses historian
            narrative_provider = historian_provider
            narrative_model_name = historian_model_name

    return {
        "structured_report": structured_report,
        "narrative_prose": final_narrative,
        "timeline_name": timeline_name,  # Include timeline name from agent
        "workflow_metadata": result_context.metadata,
        "historian_provider": historian_provider,
        "historian_model_name": historian_model_name,
        "storyteller_provider": narrative_provider,
        "storyteller_model_name": narrative_model_name,
    }


# ============================================================================
# Skeleton-Based Workflow Functions
# ============================================================================


async def _generate_skeleton_events(context: WorkflowContext):
    """
    Workflow step: Generate skeleton timeline events.

    Args:
        context: Workflow context containing skeleton_request, historical_context, and model

    Returns:
        SkeletonAgentOutput with events and summary
    """
    request = context.get("skeleton_request")
    historical_context = context.get("historical_context")
    # Use skeleton-specific model if available, fallback to general model
    model = context.get("skeleton_model") or context.get("model")

    logger.info(
        f"Generating skeleton events for deviation: {request.deviation_description[:50]}..."
    )

    # Call skeleton agent
    skeleton_output = await skeleton_agent.generate_skeleton(
        deviation_date=request.deviation_date,
        deviation_description=request.deviation_description,
        scenario_type=request.scenario_type.value,
        simulation_years=request.simulation_years,
        historical_context=historical_context,
        model=model
    )

    context.set("skeleton_output", skeleton_output)
    logger.info(f"Skeleton generated with {len(skeleton_output.events)} events")

    return skeleton_output


async def _generate_report_from_skeleton_events(context: WorkflowContext) -> StructuredReport:
    """
    Workflow step: Generate structured report from skeleton events.

    Uses the SEPARATE skeleton_historian_agent to generate comprehensive
    report based on user-approved skeleton events.

    Args:
        context: Workflow context containing skeleton, deviation_request, and model

    Returns:
        StructuredReport with analytical sections
    """
    skeleton = context.get("skeleton")
    deviation_request = context.get("deviation_request")
    # Use skeleton_historian-specific model if available, fallback to general model
    model = context.get("skeleton_historian_model") or context.get("model")
    include_narrative = context.get("include_narrative", False)
    db = context.get("db")

    logger.info(
        f"Generating report from skeleton {skeleton.id} with {len(skeleton.events)} events"
    )

    # Convert skeleton events to input format for agent
    from app.agents.skeleton_historian_agent import SkeletonEventInput
    skeleton_events = [
        SkeletonEventInput(
            event_date=event.event_date.isoformat(),
            location=event.location,
            description=event.description,
            event_order=event.event_order
        )
        for event in sorted(skeleton.events, key=lambda e: e.event_order)
    ]

    # Retrieve ground truth historical context
    from app.services.history_service import get_history_service
    history_service = get_history_service()

    try:
        # Extract use_rag from deviation_request
        use_rag = deviation_request.use_rag if hasattr(deviation_request, 'use_rag') else True

        historical_context, debug_info = await history_service.get_context_for_skeleton_rag(
            deviation_description=skeleton.deviation_description,
            scenario_type=deviation_request.scenario_type.value,
            deviation_date=skeleton.deviation_date,
            skeleton_events=skeleton_events,
            use_rag=use_rag,
            db=db
        )
        logger.info(
            f"Retrieved ground truth context for skeleton: "
            f"{debug_info.get('final_chunks', 0)} chunks, "
            f"~{debug_info.get('total_tokens', 0):.0f} tokens"
        )
    except Exception as e:
        logger.warning(
            f"Failed to retrieve ground truth context for skeleton, using legacy: {e}"
        )
        # Fallback to legacy (respect user's use_rag choice)
        use_rag = deviation_request.use_rag if hasattr(deviation_request, 'use_rag') else True
        historical_context = await history_service.get_context_for_deviation(
            deviation_date=skeleton.deviation_date,
            simulation_years=skeleton.period_years,
            deviation_description=skeleton.deviation_description,
            scenario_type=deviation_request.scenario_type.value,
            use_rag=use_rag,
            db=db
        )

    # Call skeleton historian agent with historical context
    timeline_output = await skeleton_historian_agent.generate_report_from_skeleton(
        deviation_date=skeleton.deviation_date,
        deviation_description=skeleton.deviation_description,
        scenario_type=deviation_request.scenario_type.value,
        start_year=skeleton.start_year,
        end_year=skeleton.end_year,
        skeleton_events=skeleton_events,
        model=model,
        historical_context=historical_context,
        include_narrative=include_narrative
    )

    # Extract structured report
    structured_report = StructuredReport(
        start_year=skeleton.start_year,
        end_year=skeleton.end_year,
        period_years=skeleton.period_years,
        report_order=1,
        executive_summary=timeline_output.executive_summary,
        political_changes=timeline_output.political_changes,
        conflicts_and_wars=timeline_output.conflicts_and_wars,
        economic_impacts=timeline_output.economic_impacts,
        social_developments=timeline_output.social_developments,
        technological_shifts=timeline_output.technological_shifts,
        key_figures=timeline_output.key_figures,
        long_term_implications=timeline_output.long_term_implications,
    )

    context.set("structured_report", structured_report)
    context.set("basic_narrative", timeline_output.narrative_prose)

    logger.info("Structured report generated from skeleton successfully")
    return structured_report


def create_skeleton_generation_workflow(
    skeleton_request: TimelineCreationRequest,
    historical_context: str,
) -> WorkflowContext:
    """
    Create a workflow for generating a skeleton timeline.

    This workflow orchestrates:
    1. Generate skeleton events (skeleton_agent)

    Args:
        skeleton_request: The skeleton generation request from the user
        historical_context: Ground truth historical context

    Returns:
        A configured workflow ready for execution
    """
    workflow = orchestrator.create_workflow(
        name="skeleton_generation",
        description="Generate editable skeleton of key events for alternate timeline"
    )

    # Step 1: Generate skeleton events
    workflow.add_step(
        name="generate_skeleton_events",
        func=_generate_skeleton_events,
        timeout=360.0,  # 6 minutes max (Anthropic needs more time for large structured outputs)
        retry_count=1,
    )

    return workflow


def create_report_from_skeleton_workflow(
    skeleton,  # SkeletonResponse
    deviation_request: TimelineCreationRequest,
) -> WorkflowContext:
    """
    Create a workflow for generating a report from user-approved skeleton.

    This workflow follows similar pattern to timeline generation:
    1. Generate structured report from skeleton (skeleton_historian_agent)
    2. Conditionally generate advanced narrative (storyteller_agent)
    3. Select final narrative based on mode

    Args:
        skeleton: The approved skeleton with events
        deviation_request: The deviation request (for narrative mode)

    Returns:
        A configured workflow ready for execution
    """
    workflow = orchestrator.create_workflow(
        name="report_from_skeleton",
        description="Generate comprehensive report from user-approved skeleton events"
    )

    # Step 1: Generate structured report from skeleton
    workflow.add_step(
        name="generate_report_from_skeleton",
        func=_generate_report_from_skeleton_events,
        timeout=360.0,
        retry_count=1,
    )

    # Step 2: Generate advanced narrative (conditional)
    workflow.add_step(
        name="generate_advanced_narrative",
        func=_generate_advanced_narrative,
        condition=lambda ctx: ctx.get("deviation_request").narrative_mode in [
            NarrativeMode.ADVANCED_OMNISCIENT,
            NarrativeMode.ADVANCED_CUSTOM_POV
        ],
        timeout=360.0,
        retry_count=1,
    )

    return workflow


async def execute_skeleton_generation(
    skeleton_request: TimelineCreationRequest,
    historical_context: str,
    db_session=None,
) -> dict:
    """
    Execute the complete skeleton generation workflow.

    Args:
        skeleton_request: The skeleton generation request
        historical_context: Historical context for grounding
        db_session: Optional database session for LLM config (if None, uses env vars)

    Returns:
        Dictionary with skeleton_output key
    """
    # Get per-agent LLM model from service if db_session provided
    skeleton_model = None
    if db_session:
        from app.services import llm_service
        from app.models import AgentType

        skeleton_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.SKELETON
        )
        logger.info(f"Using skeleton agent LLM model: {type(skeleton_model).__name__}")

    workflow = create_skeleton_generation_workflow(skeleton_request, historical_context)

    # Initialize context with skeleton model
    initial_state = {
        "skeleton_request": skeleton_request,
        "historical_context": historical_context,
        "skeleton_model": skeleton_model,
        "model": skeleton_model,  # Keep for backward compatibility
    }

    # Execute workflow
    result_context = await orchestrator.execute_workflow(
        workflow,
        initial_state=initial_state,
        metadata={
            "deviation_date": str(skeleton_request.deviation_date),
            "simulation_years": skeleton_request.simulation_years,
            "scenario_type": skeleton_request.scenario_type.value,
        }
    )

    # Extract final results
    skeleton_output = result_context.get_result("generate_skeleton_events")

    return {
        "skeleton_output": skeleton_output,
        "workflow_metadata": result_context.metadata,
    }


async def execute_report_from_skeleton(
    skeleton,  # SkeletonResponse
    deviation_request: TimelineCreationRequest,
    db_session=None,
) -> dict:
    """
    Execute the complete report generation from skeleton workflow.

    Args:
        skeleton: The approved skeleton with events
        deviation_request: The deviation request (contains narrative mode)
        db_session: Optional database session for LLM config (if None, uses env vars)

    Returns:
        Dictionary with structured_report, narrative_prose, and model info keys
    """
    # Get per-agent LLM models from service if db_session provided
    skeleton_historian_model = None
    storyteller_model = None
    skeleton_historian_provider = None
    skeleton_historian_model_name = None
    storyteller_provider = None
    storyteller_model_name = None

    if db_session:
        from app.services import llm_service
        from app.models import AgentType

        # Get agent-specific configs to track what models will be used
        skeleton_historian_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.SKELETON_HISTORIAN
        )
        storyteller_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.STORYTELLER
        )

        # Get global config for fallback
        global_config = await llm_service.get_current_llm_config(db_session)

        # Determine which config will be used for skeleton_historian
        skeleton_historian_config = skeleton_historian_agent_config if skeleton_historian_agent_config else global_config
        skeleton_historian_provider = skeleton_historian_config.provider
        skeleton_historian_model_name = skeleton_historian_config.model_name

        # Determine which config will be used for storyteller
        storyteller_config = storyteller_agent_config if storyteller_agent_config else global_config
        storyteller_provider = storyteller_config.provider
        storyteller_model_name = storyteller_config.model_name

        # Create agent-specific models
        skeleton_historian_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.SKELETON_HISTORIAN
        )
        storyteller_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.STORYTELLER
        )
        logger.info(
            f"Using per-agent LLM models for skeleton report: "
            f"skeleton_historian={skeleton_historian_provider}/{skeleton_historian_model_name}, "
            f"storyteller={storyteller_provider}/{storyteller_model_name}"
        )

    # Determine if historian should generate narrative
    # BASIC: historian generates narrative
    # ADVANCED: historian skips narrative, storyteller generates it later
    # NONE: no narrative at all
    include_narrative = deviation_request.narrative_mode == NarrativeMode.BASIC

    workflow = create_report_from_skeleton_workflow(skeleton, deviation_request)

    # Initialize context with agent-specific models
    initial_state = {
        "skeleton": skeleton,
        "deviation_request": deviation_request,
        "skeleton_historian_model": skeleton_historian_model,
        "storyteller_model": storyteller_model,
        "model": skeleton_historian_model,  # Keep for backward compatibility
        "include_narrative": include_narrative,
        "db": db_session,  # Pass database session for ground truth retrieval
    }

    # Execute workflow
    result_context = await orchestrator.execute_workflow(
        workflow,
        initial_state=initial_state,
        metadata={
            "skeleton_id": str(skeleton.id),
            "event_count": len(skeleton.events),
            "narrative_mode": deviation_request.narrative_mode.value,
        }
    )

    # Extract final results
    structured_report = result_context.get_result("generate_report_from_skeleton")
    final_narrative = _select_final_narrative(result_context)
    timeline_name = result_context.get("timeline_name")  # Get timeline name from context

    # Determine which model was actually used for the narrative
    # If narrative mode is ADVANCED and storyteller was used, return storyteller info
    # Otherwise, if there's a basic narrative, it came from the skeleton_historian
    narrative_provider = None
    narrative_model_name = None
    if final_narrative:
        if deviation_request.narrative_mode in [NarrativeMode.ADVANCED_OMNISCIENT, NarrativeMode.ADVANCED_CUSTOM_POV]:
            # Advanced narrative uses storyteller
            narrative_provider = storyteller_provider
            narrative_model_name = storyteller_model_name
        else:
            # Basic narrative uses skeleton_historian
            narrative_provider = skeleton_historian_provider
            narrative_model_name = skeleton_historian_model_name

    return {
        "structured_report": structured_report,
        "narrative_prose": final_narrative,
        "timeline_name": timeline_name,  # Include timeline name from agent
        "workflow_metadata": result_context.metadata,
        "historian_provider": skeleton_historian_provider,
        "historian_model_name": skeleton_historian_model_name,
        "storyteller_provider": narrative_provider,
        "storyteller_model_name": narrative_model_name,
    }


# ============================================================================
# Extension Skeleton Workflow Functions
# ============================================================================


async def _generate_extension_skeleton_events(context: WorkflowContext):
    """
    Workflow step: Generate extension skeleton timeline events.

    Uses context from the last report to maintain continuity when extending.

    Args:
        context: Workflow context containing timeline, extension_request, and model

    Returns:
        SkeletonAgentOutput with events and summary
    """
    timeline = context.get("timeline")
    extension_request = context.get("extension_request")
    historical_context = context.get("historical_context")
    # Use skeleton-specific model if available, fallback to general model
    model = context.get("skeleton_model") or context.get("model")

    # Get last generation for context
    # Handle both TimelineDB (database model) and Timeline (Pydantic model)
    if hasattr(timeline, 'latest_generation'):
        # Pydantic Timeline model with @property
        last_generation = timeline.latest_generation
    elif hasattr(timeline, 'generations') and timeline.generations:
        # TimelineDB model - manually get latest by generation_order
        last_generation = max(timeline.generations, key=lambda g: g.generation_order)
    else:
        last_generation = None

    # Build context from last generation
    last_report_context = ""
    if last_generation:
        last_report_context = f"""
PREVIOUS PERIOD SUMMARY (Years {last_generation.start_year}-{last_generation.end_year}):

Executive Summary:
{last_generation.executive_summary}

Long-term Implications:
{last_generation.long_term_implications}
"""

    # Add user's additional context if provided
    if extension_request.additional_context:
        last_report_context += f"\n\nADDITIONAL CONTEXT:\n{extension_request.additional_context}"

    logger.info(
        f"Generating extension skeleton for timeline {timeline.id} "
        f"(+{extension_request.additional_years} years)"
    )

    # Calculate extension period
    current_max_year = timeline.total_years_simulated
    extension_start_year = current_max_year
    extension_end_year = current_max_year + extension_request.additional_years

    # Convert original root_deviation_date string to date object
    from datetime import datetime
    original_deviation_date = (
        datetime.strptime(timeline.root_deviation_date, "%Y-%m-%d").date()
        if isinstance(timeline.root_deviation_date, str)
        else timeline.root_deviation_date
    )

    # Call skeleton agent with extension context
    skeleton_output = await skeleton_agent.generate_skeleton(
        deviation_date=original_deviation_date,  # Pass original deviation date
        deviation_description=timeline.root_deviation_description,
        scenario_type=timeline.scenario_type.value if isinstance(timeline.scenario_type, ScenarioType) else timeline.scenario_type,
        simulation_years=extension_request.additional_years,
        historical_context=historical_context,
        model=model,
        is_extension=True,  # Mark as extension
        extension_start_year=current_max_year,  # Years already simulated
        last_report_context=last_report_context  # Pass last report state
    )

    context.set("skeleton_output", skeleton_output)
    context.set("extension_start_year", extension_start_year)
    logger.info(f"Extension skeleton generated with {len(skeleton_output.events)} events")

    return skeleton_output


async def _generate_extension_report_from_skeleton(context: WorkflowContext) -> StructuredReport:
    """
    Workflow step: Generate extension report from skeleton events.

    Uses skeleton_historian_agent to generate comprehensive report for
    the extension period based on user-approved skeleton events.

    Args:
        context: Workflow context containing skeleton, timeline, extension_request, and model

    Returns:
        StructuredReport with analytical sections for extension period
    """
    skeleton = context.get("skeleton")
    timeline = context.get("timeline")
    extension_request = context.get("extension_request")
    # Use skeleton_historian-specific model if available, fallback to general model
    model = context.get("skeleton_historian_model") or context.get("model")
    include_narrative = context.get("include_narrative", False)
    db = context.get("db")

    logger.info(
        f"Generating extension report from skeleton {skeleton.id} "
        f"with {len(skeleton.events)} events"
    )

    # Convert skeleton events to input format for agent
    from app.agents.skeleton_historian_agent import SkeletonEventInput
    skeleton_events = [
        SkeletonEventInput(
            event_date=event.event_date.isoformat(),
            location=event.location,
            description=event.description,
            event_order=event.event_order
        )
        for event in sorted(skeleton.events, key=lambda e: e.event_order)
    ]

    # Calculate generation order
    next_order = len(timeline.generations) + 1

    # Get last report context for extension
    last_report_context = context.get("last_report_context", "")

    # For extension skeletons, get deviation info from parent timeline
    from datetime import date as date_type
    if isinstance(timeline.root_deviation_date, str):
        deviation_date = date_type.fromisoformat(timeline.root_deviation_date)
    else:
        deviation_date = timeline.root_deviation_date

    # Retrieve ground truth historical context for extension period
    from app.services.history_service import get_history_service
    history_service = get_history_service()

    try:
        # Extract use_rag from extension_request
        use_rag = extension_request.use_rag if hasattr(extension_request, 'use_rag') else True

        historical_context, debug_info = await history_service.get_context_for_skeleton_rag(
            deviation_description=timeline.root_deviation_description,
            scenario_type=timeline.scenario_type.value if hasattr(timeline.scenario_type, 'value') else timeline.scenario_type,
            deviation_date=deviation_date,
            skeleton_events=skeleton_events,
            use_rag=use_rag,
            db=db
        )
        logger.info(
            f"Retrieved ground truth context for extension skeleton: "
            f"{debug_info.get('final_chunks', 0)} chunks, "
            f"~{debug_info.get('total_tokens', 0):.0f} tokens"
        )
    except Exception as e:
        logger.warning(
            f"Failed to retrieve ground truth context for extension skeleton, using legacy: {e}"
        )
        # Fallback to legacy (respect user's use_rag choice)
        use_rag = extension_request.use_rag if hasattr(extension_request, 'use_rag') else True
        historical_context = await history_service.get_context_for_deviation(
            deviation_date=deviation_date,
            simulation_years=skeleton.period_years,
            deviation_description=timeline.root_deviation_description,
            scenario_type=timeline.scenario_type.value if hasattr(timeline.scenario_type, 'value') else timeline.scenario_type,
            use_rag=use_rag,
            db=db
        )

    # Call skeleton historian agent with extension context
    timeline_output = await skeleton_historian_agent.generate_report_from_skeleton(
        deviation_date=deviation_date,  # Use timeline's root deviation date
        deviation_description=timeline.root_deviation_description,  # Use timeline's root deviation description
        scenario_type=timeline.scenario_type.value if hasattr(timeline.scenario_type, 'value') else timeline.scenario_type,
        start_year=skeleton.start_year,
        end_year=skeleton.end_year,
        skeleton_events=skeleton_events,
        model=model,
        historical_context=historical_context,
        include_narrative=include_narrative,
        is_extension=True,  # Mark as extension
        last_report_summary=last_report_context  # Pass last report state
    )

    # Extract structured report
    structured_report = StructuredReport(
        start_year=skeleton.start_year,
        end_year=skeleton.end_year,
        period_years=skeleton.period_years,
        report_order=next_order,
        executive_summary=timeline_output.executive_summary,
        political_changes=timeline_output.political_changes,
        conflicts_and_wars=timeline_output.conflicts_and_wars,
        economic_impacts=timeline_output.economic_impacts,
        social_developments=timeline_output.social_developments,
        technological_shifts=timeline_output.technological_shifts,
        key_figures=timeline_output.key_figures,
        long_term_implications=timeline_output.long_term_implications,
    )

    context.set("structured_report", structured_report)
    context.set("basic_narrative", timeline_output.narrative_prose)
    context.set("timeline_name", timeline_output.timeline_name)  # Store timeline name for later use

    logger.info("Extension report from skeleton generated successfully")
    return structured_report


async def execute_extension_skeleton_generation(
    timeline,  # Timeline model
    extension_request,  # ExtensionSkeletonRequest
    historical_context: str,
    db_session=None,
) -> dict:
    """
    Execute workflow to generate an extension skeleton.

    This creates a temporary, hidden skeleton for extending an existing timeline.
    The skeleton includes context from the last report for continuity.

    Args:
        timeline: The existing timeline to extend
        extension_request: The extension skeleton request (ExtensionSkeletonRequest)
        historical_context: Ground truth historical context
        db_session: Optional database session for LLM config

    Returns:
        Dictionary with skeleton_output and extension_start_year keys
    """
    # Get per-agent LLM model from service if db_session provided
    skeleton_model = None
    if db_session:
        from app.services import llm_service
        from app.models import AgentType

        skeleton_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.SKELETON
        )
        logger.info(f"Using skeleton agent LLM model for extension skeleton: {type(skeleton_model).__name__}")

    # Create workflow
    workflow = orchestrator.create_workflow(
        name="extension_skeleton_generation",
        description="Generate extension skeleton with context from last report"
    )

    # Add step to generate extension skeleton events
    workflow.add_step(
        name="generate_extension_skeleton_events",
        func=_generate_extension_skeleton_events,
        timeout=360.0,
        retry_count=1,
    )

    # Initialize context with skeleton model
    initial_state = {
        "timeline": timeline,
        "extension_request": extension_request,
        "historical_context": historical_context,
        "skeleton_model": skeleton_model,
        "model": skeleton_model,  # Keep for backward compatibility
    }

    # Execute workflow
    result_context = await orchestrator.execute_workflow(
        workflow,
        initial_state=initial_state,
        metadata={
            "timeline_id": str(timeline.id),
            "additional_years": extension_request.additional_years,
            "has_additional_context": bool(extension_request.additional_context),
        }
    )

    # Extract results
    skeleton_output = result_context.get_result("generate_extension_skeleton_events")
    extension_start_year = result_context.get("extension_start_year")

    return {
        "skeleton_output": skeleton_output,
        "extension_start_year": extension_start_year,
        "workflow_metadata": result_context.metadata,
    }


async def execute_extension_from_skeleton(
    timeline,  # Timeline model
    skeleton,  # SkeletonResponse (approved extension skeleton)
    extension_request,  # ExtendFromSkeletonRequest
    db_session=None,
) -> dict:
    """
    Execute workflow to extend timeline from approved extension skeleton.

    Generates a comprehensive extension report based on user-approved skeleton events.

    Args:
        timeline: The existing timeline to extend
        skeleton: The approved extension skeleton
        extension_request: The extension request (ExtendFromSkeletonRequest)
        db_session: Optional database session for LLM config

    Returns:
        Dictionary with structured_report, narrative_prose, and model info keys
    """
    # Get per-agent LLM models from service if db_session provided
    skeleton_historian_model = None
    storyteller_model = None
    skeleton_historian_provider = None
    skeleton_historian_model_name = None
    storyteller_provider = None
    storyteller_model_name = None

    if db_session:
        from app.services import llm_service
        from app.models import AgentType

        # Get agent-specific configs to track what models will be used
        skeleton_historian_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.SKELETON_HISTORIAN
        )
        storyteller_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.STORYTELLER
        )

        # Get global config for fallback
        global_config = await llm_service.get_current_llm_config(db_session)

        # Determine which config will be used for skeleton_historian
        skeleton_historian_config = skeleton_historian_agent_config if skeleton_historian_agent_config else global_config
        skeleton_historian_provider = skeleton_historian_config.provider
        skeleton_historian_model_name = skeleton_historian_config.model_name

        # Determine which config will be used for storyteller
        storyteller_config = storyteller_agent_config if storyteller_agent_config else global_config
        storyteller_provider = storyteller_config.provider
        storyteller_model_name = storyteller_config.model_name

        # Create agent-specific models
        skeleton_historian_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.SKELETON_HISTORIAN
        )
        storyteller_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.STORYTELLER
        )
        logger.info(
            f"Using per-agent LLM models for extension from skeleton: "
            f"skeleton_historian={skeleton_historian_provider}/{skeleton_historian_model_name}, "
            f"storyteller={storyteller_provider}/{storyteller_model_name}"
        )

    # Determine if historian should generate narrative for extension
    # BASIC: historian generates narrative
    # ADVANCED: historian skips narrative, storyteller generates it later
    # NONE: no narrative at all
    include_narrative = extension_request.narrative_mode == NarrativeMode.BASIC

    # Create workflow
    workflow = orchestrator.create_workflow(
        name="extension_from_skeleton",
        description="Generate extension report from approved skeleton events"
    )

    # Add step to generate extension report from skeleton
    workflow.add_step(
        name="generate_extension_report_from_skeleton",
        func=_generate_extension_report_from_skeleton,
        timeout=360.0,
        retry_count=1,
    )

    # Add advanced narrative step (conditional)
    workflow.add_step(
        name="generate_advanced_narrative",
        func=_generate_advanced_narrative,
        condition=lambda ctx: ctx.get("extension_request").narrative_mode in [
            NarrativeMode.ADVANCED_OMNISCIENT,
            NarrativeMode.ADVANCED_CUSTOM_POV
        ],
        timeout=360.0,
        retry_count=1,
    )

    # Initialize context
    # Create a deviation_request from timeline's root deviation for narrative generation
    from datetime import date as date_type
    deviation_request_for_narrative = TimelineCreationRequest(
        deviation_date=date_type.fromisoformat(timeline.root_deviation_date) if isinstance(timeline.root_deviation_date, str) else timeline.root_deviation_date,
        deviation_description=timeline.root_deviation_description,
        simulation_years=timeline.total_years_simulated,
        scenario_type=timeline.scenario_type,
        narrative_mode=extension_request.narrative_mode,
        narrative_custom_pov=extension_request.narrative_custom_pov
    )

    initial_state = {
        "skeleton": skeleton,
        "timeline": timeline,
        "extension_request": extension_request,
        "deviation_request": deviation_request_for_narrative,  # Add for narrative generation
        "skeleton_historian_model": skeleton_historian_model,
        "storyteller_model": storyteller_model,
        "model": skeleton_historian_model,  # Keep for backward compatibility
        "include_narrative": include_narrative,
        "db": db_session,  # Pass database session for ground truth retrieval
    }

    # Execute workflow
    result_context = await orchestrator.execute_workflow(
        workflow,
        initial_state=initial_state,
        metadata={
            "timeline_id": str(timeline.id),
            "skeleton_id": str(skeleton.id),
            "event_count": len(skeleton.events),
            "narrative_mode": extension_request.narrative_mode.value,
        }
    )

    # Extract final results
    structured_report = result_context.get_result("generate_extension_report_from_skeleton")
    final_narrative = _select_final_narrative(result_context)
    timeline_name = result_context.get("timeline_name")  # Get timeline name from context

    # Determine which model was actually used for the narrative
    # If narrative mode is ADVANCED and storyteller was used, return storyteller info
    # Otherwise, if there's a basic narrative, it came from the skeleton_historian
    narrative_provider = None
    narrative_model_name = None
    if final_narrative:
        if extension_request.narrative_mode in [NarrativeMode.ADVANCED_OMNISCIENT, NarrativeMode.ADVANCED_CUSTOM_POV]:
            # Advanced narrative uses storyteller
            narrative_provider = storyteller_provider
            narrative_model_name = storyteller_model_name
        else:
            # Basic narrative uses skeleton_historian
            narrative_provider = skeleton_historian_provider
            narrative_model_name = skeleton_historian_model_name

    return {
        "structured_report": structured_report,
        "narrative_prose": final_narrative,
        "timeline_name": timeline_name,  # Include timeline name from agent
        "workflow_metadata": result_context.metadata,
        "historian_provider": skeleton_historian_provider,
        "historian_model_name": skeleton_historian_model_name,
        "storyteller_provider": narrative_provider,
        "storyteller_model_name": narrative_model_name,
    }


# ============================================================================
# Image Generation Workflow Functions (NEW - Illustrator Agent)
# ============================================================================


async def _generate_image_prompts(context: WorkflowContext):
    """
    Workflow step: Generate image prompts for timeline visualization.

    Args:
        context: Workflow context containing timeline report data and illustrator model

    Returns:
        IllustratorAgentOutput with image prompts and overall visual theme
    """
    image_request = context.get("image_request")
    timeline_id = context.get("timeline_id")
    report_id = context.get("report_id")
    structured_report = context.get("structured_report")
    narrative_prose = context.get("narrative_prose")
    deviation_date = context.get("deviation_date")
    deviation_description = context.get("deviation_description")
    simulation_years = context.get("simulation_years")
    report_start_year = context.get("report_start_year", 0)

    # Use illustrator-specific model if available, fallback to general model
    model = context.get("illustrator_model") or context.get("model")

    logger.info(
        f"Generating {image_request.num_images} image prompts for timeline {timeline_id}"
    )

    # Import illustrator agent
    from app.agents import illustrator_agent

    # Call illustrator agent
    illustrator_output = await illustrator_agent.generate_image_prompts(
        deviation_date=deviation_date,
        deviation_description=deviation_description,
        simulation_years=simulation_years,
        structured_report=structured_report,
        narrative_prose=narrative_prose,
        num_images=image_request.num_images,
        model=model,
        focus_areas=image_request.focus_areas,
        report_start_year=report_start_year
    )

    context.set("illustrator_output", illustrator_output)
    logger.info(f"Generated {len(illustrator_output.prompts)} image prompts successfully")

    return illustrator_output


async def execute_image_prompt_generation(
    image_request,  # ImagePromptSkeletonCreate
    timeline_data: dict,  # Contains report, narrative, deviation info
    db_session=None,
) -> dict:
    """
    Execute workflow to generate image prompts for a timeline.

    Args:
        image_request: The image prompt generation request
        timeline_data: Dictionary with timeline/report data (structured_report, narrative_prose, etc.)
        db_session: Optional database session for LLM config

    Returns:
        Dictionary with illustrator_output key
    """
    # Get per-agent LLM model from service if db_session provided
    illustrator_model = None
    illustrator_provider = None
    illustrator_model_name = None

    if db_session:
        from app.services import llm_service
        from app.models import AgentType

        # Get agent-specific config to track what model will be used
        illustrator_agent_config = await llm_service.get_agent_llm_config(
            db_session, AgentType.ILLUSTRATOR
        )

        # Get global config for fallback
        global_config = await llm_service.get_current_llm_config(db_session)

        # Determine which config will be used
        illustrator_config = illustrator_agent_config if illustrator_agent_config else global_config
        illustrator_provider = illustrator_config.provider
        illustrator_model_name = illustrator_config.model_name

        # Create agent-specific model
        illustrator_model = await llm_service.create_pydantic_ai_model_for_agent(
            db_session, AgentType.ILLUSTRATOR
        )
        logger.info(
            f"Using illustrator agent LLM model: {illustrator_provider}/{illustrator_model_name}"
        )

    # Create workflow
    workflow = orchestrator.create_workflow(
        name="image_prompt_generation",
        description="Generate image prompts for timeline visualization"
    )

    # Add step to generate image prompts
    workflow.add_step(
        name="generate_image_prompts",
        func=_generate_image_prompts,
        timeout=360.0,
        retry_count=1,
    )

    # Initialize context
    initial_state = {
        "image_request": image_request,
        "timeline_id": timeline_data.get("timeline_id"),
        "report_id": timeline_data.get("report_id") or timeline_data.get("generation_id"),
        "structured_report": timeline_data.get("report") or timeline_data.get("generation"),
        "narrative_prose": timeline_data.get("narrative"),
        "deviation_date": timeline_data.get("deviation_date"),
        "deviation_description": timeline_data.get("deviation_description"),
        "simulation_years": timeline_data.get("simulation_years"),
        "report_start_year": timeline_data.get("report_start_year") or timeline_data.get("generation_start_year", 0),
        "illustrator_model": illustrator_model,
        "model": illustrator_model,  # Keep for backward compatibility
    }

    # Execute workflow
    result_context = await orchestrator.execute_workflow(
        workflow,
        initial_state=initial_state,
        metadata={
            "timeline_id": str(timeline_data.get("timeline_id")),
            "report_id": str(timeline_data.get("report_id")),
            "num_images": image_request.num_images,
            "has_focus_areas": bool(image_request.focus_areas),
        }
    )

    # Extract results
    illustrator_output = result_context.get_result("generate_image_prompts")

    return {
        "illustrator_output": illustrator_output,
        "workflow_metadata": result_context.metadata,
        "illustrator_provider": illustrator_provider,
        "illustrator_model_name": illustrator_model_name,
    }
