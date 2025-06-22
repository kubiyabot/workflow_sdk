"""ADK agents for workflow generation, compilation, execution, and validation."""

from .base import (
    ADK_AVAILABLE,
    get_docker_registry_context,
    get_dsl_context,
    MissingContext,
    WorkflowGenerationResult,
    WorkflowExecutionResult,
    ValidationResult
)

from .context_loader import (
    ContextLoaderAgent,
    create_context_loader_agent
)

from .workflow_generator import (
    WorkflowGeneratorAgent,
    create_workflow_generator_agent
)

from .compiler import (
    CompilerAgent,
    create_compiler_agent
)

from .refiner import (
    RefinementAgent,
    RefinementLoop,
    create_refinement_agent,
    create_refinement_loop
)

from .executor import (
    WorkflowExecutorAgent,
    create_workflow_executor_agent
)

from .validator import (
    WorkflowValidatorAgent,
    create_workflow_validator_agent
)

from .loop_orchestrator import (
    LoopOrchestratorAgent,
    create_loop_orchestrator_agent
)

# For backward compatibility, also expose the main orchestrator as OrchestratorAgent
OrchestratorAgent = LoopOrchestratorAgent
create_orchestrator_agent = create_loop_orchestrator_agent

__all__ = [
    # Base utilities
    "ADK_AVAILABLE",
    "get_docker_registry_context",
    "get_dsl_context",
    "MissingContext",
    "WorkflowGenerationResult",
    "WorkflowExecutionResult",
    "ValidationResult",
    
    # Agents
    "ContextLoaderAgent",
    "WorkflowGeneratorAgent",
    "CompilerAgent",
    "RefinementAgent",
    "RefinementLoop",
    "WorkflowExecutorAgent",
    "WorkflowValidatorAgent",
    "LoopOrchestratorAgent",
    "OrchestratorAgent",  # Backward compatibility
    
    # Factory functions
    "create_context_loader_agent",
    "create_workflow_generator_agent",
    "create_compiler_agent",
    "create_refinement_agent",
    "create_refinement_loop",
    "create_workflow_executor_agent",
    "create_workflow_validator_agent",
    "create_loop_orchestrator_agent",
    "create_orchestrator_agent",  # Backward compatibility
] 