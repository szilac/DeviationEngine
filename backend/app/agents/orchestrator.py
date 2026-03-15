"""
Agent orchestrator for coordinating multi-agent workflows.

This module provides a flexible orchestration layer for managing complex
agent interactions, including sequential and parallel execution patterns,
state management, error handling, and result passing between agents.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio

from app.exceptions import AIGenerationError

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for generic workflow state (for future extensibility)
StateT = TypeVar('StateT')
ResultT = TypeVar('ResultT')


class ExecutionMode(str, Enum):
    """Agent execution modes."""
    SEQUENTIAL = "sequential"  # Execute agents one after another
    PARALLEL = "parallel"      # Execute agents concurrently
    CONDITIONAL = "conditional"  # Execute based on conditions


class StepStatus(str, Enum):
    """Workflow step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowContext:
    """
    Context object passed between workflow steps.

    Attributes:
        state: Shared state dictionary for passing data between steps
        metadata: Metadata about the workflow execution
        results: Results from completed steps
        errors: Errors encountered during execution
    """
    state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, Exception] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the workflow state."""
        self.state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the workflow state."""
        return self.state.get(key, default)

    def set_result(self, step_name: str, result: Any) -> None:
        """Store the result of a workflow step."""
        self.results[step_name] = result

    def get_result(self, step_name: str, default: Any = None) -> Any:
        """Retrieve the result of a workflow step."""
        return self.results.get(step_name, default)

    def set_error(self, step_name: str, error: Exception) -> None:
        """Store an error from a workflow step."""
        self.errors[step_name] = error

    def has_errors(self) -> bool:
        """Check if any errors were encountered."""
        return len(self.errors) > 0


@dataclass
class WorkflowStep:
    """
    Represents a single step in a workflow.

    Attributes:
        name: Unique name for this step
        func: Async function to execute for this step
        condition: Optional condition function to determine if step should run
        on_error: Optional error handler function
        timeout: Optional timeout in seconds
        retry_count: Number of retries on failure (default: 0)
    """
    name: str
    func: Callable[[WorkflowContext], Any]
    condition: Optional[Callable[[WorkflowContext], bool]] = None
    on_error: Optional[Callable[[WorkflowContext, Exception], Any]] = None
    timeout: Optional[float] = None
    retry_count: int = 0
    status: StepStatus = StepStatus.PENDING

    async def execute(self, context: WorkflowContext) -> Any:
        """
        Execute this workflow step.

        Args:
            context: The workflow context

        Returns:
            The result of the step execution

        Raises:
            Exception: If execution fails and no error handler is provided
        """
        # Check condition if provided
        if self.condition and not self.condition(context):
            logger.info(f"Step '{self.name}' skipped due to condition")
            self.status = StepStatus.SKIPPED
            return None

        self.status = StepStatus.RUNNING
        logger.info(f"Executing workflow step: {self.name}")

        attempt = 0
        last_error = None

        while attempt <= self.retry_count:
            try:
                # Execute with timeout if specified
                if self.timeout:
                    result = await asyncio.wait_for(
                        self.func(context),
                        timeout=self.timeout
                    )
                else:
                    result = await self.func(context)

                self.status = StepStatus.COMPLETED
                context.set_result(self.name, result)
                logger.info(f"Step '{self.name}' completed successfully")
                return result

            except asyncio.TimeoutError as e:
                last_error = e
                logger.error(f"Step '{self.name}' timed out after {self.timeout}s")
                if attempt < self.retry_count:
                    attempt += 1
                    logger.info(f"Retrying step '{self.name}' (attempt {attempt + 1}/{self.retry_count + 1})")
                    continue
                break

            except Exception as e:
                last_error = e
                logger.error(f"Error in step '{self.name}': {e}", exc_info=True)

                if attempt < self.retry_count:
                    attempt += 1
                    logger.info(f"Retrying step '{self.name}' (attempt {attempt + 1}/{self.retry_count + 1})")
                    continue
                break

        # Handle error
        self.status = StepStatus.FAILED
        context.set_error(self.name, last_error)

        if self.on_error:
            logger.info(f"Executing error handler for step '{self.name}'")
            return await self.on_error(context, last_error)
        else:
            raise last_error


class Workflow:
    """
    Manages a workflow of agent execution steps.

    This class provides a declarative way to define multi-agent workflows
    with support for sequential execution, parallel execution, conditional
    logic, error handling, and state management.
    """

    def __init__(self, name: str, description: Optional[str] = None):
        """
        Initialize a workflow.

        Args:
            name: Unique name for this workflow
            description: Optional description of the workflow
        """
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.execution_mode = ExecutionMode.SEQUENTIAL

    def add_step(
        self,
        name: str,
        func: Callable[[WorkflowContext], Any],
        condition: Optional[Callable[[WorkflowContext], bool]] = None,
        on_error: Optional[Callable[[WorkflowContext, Exception], Any]] = None,
        timeout: Optional[float] = None,
        retry_count: int = 0,
    ) -> "Workflow":
        """
        Add a step to the workflow.

        Args:
            name: Unique name for this step
            func: Async function to execute
            condition: Optional condition to determine if step should run
            on_error: Optional error handler
            timeout: Optional timeout in seconds
            retry_count: Number of retries on failure

        Returns:
            Self for method chaining
        """
        step = WorkflowStep(
            name=name,
            func=func,
            condition=condition,
            on_error=on_error,
            timeout=timeout,
            retry_count=retry_count,
        )
        self.steps.append(step)
        logger.debug(f"Added step '{name}' to workflow '{self.name}'")
        return self

    def set_execution_mode(self, mode: ExecutionMode) -> "Workflow":
        """
        Set the execution mode for this workflow.

        Args:
            mode: The execution mode (sequential or parallel)

        Returns:
            Self for method chaining
        """
        self.execution_mode = mode
        return self

    async def execute(
        self,
        initial_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowContext:
        """
        Execute the workflow.

        Args:
            initial_state: Optional initial state for the workflow
            metadata: Optional metadata about the workflow execution

        Returns:
            The final workflow context with results and state

        Raises:
            AIGenerationError: If workflow execution fails
        """
        logger.info(f"Starting workflow: {self.name}")
        start_time = datetime.now()

        # Initialize context
        context = WorkflowContext(
            state=initial_state or {},
            metadata={
                **(metadata or {}),
                "workflow_name": self.name,
                "start_time": start_time.isoformat(),
                "execution_mode": self.execution_mode.value,
            }
        )

        try:
            if self.execution_mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential(context)
            elif self.execution_mode == ExecutionMode.PARALLEL:
                await self._execute_parallel(context)
            else:
                raise ValueError(f"Unsupported execution mode: {self.execution_mode}")

            # Update metadata
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            context.metadata["end_time"] = end_time.isoformat()
            context.metadata["duration_seconds"] = duration
            context.metadata["completed_steps"] = [
                step.name for step in self.steps if step.status == StepStatus.COMPLETED
            ]
            context.metadata["failed_steps"] = [
                step.name for step in self.steps if step.status == StepStatus.FAILED
            ]

            logger.info(
                f"Workflow '{self.name}' completed in {duration:.2f}s. "
                f"Steps: {len(context.metadata['completed_steps'])} completed, "
                f"{len(context.metadata['failed_steps'])} failed"
            )

            return context

        except Exception as e:
            logger.error(f"Workflow '{self.name}' failed: {e}", exc_info=True)
            raise AIGenerationError(
                f"Workflow execution failed: {str(e)}",
                details={
                    "workflow_name": self.name,
                    "error_type": type(e).__name__,
                    "completed_steps": [s.name for s in self.steps if s.status == StepStatus.COMPLETED],
                }
            ) from e

    async def _execute_sequential(self, context: WorkflowContext) -> None:
        """Execute steps sequentially."""
        for step in self.steps:
            await step.execute(context)

    async def _execute_parallel(self, context: WorkflowContext) -> None:
        """Execute steps in parallel."""
        tasks = [step.execute(context) for step in self.steps]
        await asyncio.gather(*tasks, return_exceptions=True)


class AgentOrchestrator:
    """
    Orchestrates complex multi-agent workflows.

    This orchestrator provides high-level methods for common agent coordination
    patterns while allowing for custom workflow definitions.
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.workflows: Dict[str, Workflow] = {}
        logger.info("Agent orchestrator initialized")

    def create_workflow(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Workflow:
        """
        Create a new workflow.

        Args:
            name: Unique name for the workflow
            description: Optional description

        Returns:
            A new Workflow instance
        """
        workflow = Workflow(name, description)
        self.workflows[name] = workflow
        return workflow

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """
        Get a workflow by name.

        Args:
            name: Name of the workflow

        Returns:
            The workflow if found, None otherwise
        """
        return self.workflows.get(name)

    async def execute_workflow(
        self,
        workflow: Workflow,
        initial_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowContext:
        """
        Execute a workflow.

        Args:
            workflow: The workflow to execute
            initial_state: Optional initial state
            metadata: Optional metadata

        Returns:
            The workflow context with results
        """
        return await workflow.execute(initial_state, metadata)


# Singleton instance for application-wide use
orchestrator = AgentOrchestrator()
