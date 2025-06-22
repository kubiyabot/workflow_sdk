"""Refinement agent for fixing workflow errors."""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from .base import (
    ADK_AVAILABLE, LlmAgent, LlmRequest, LlmResponse, CallbackContext,
    types, _get_model_for_agent, _get_default_generate_config,
    get_docker_registry_context, get_dsl_context
)
from ..config import ADKConfig

logger = logging.getLogger(__name__)


class RefinementAgent(LlmAgent):
    """Agent for refining workflows based on errors."""
    
    def __init__(self, config: ADKConfig):
        self._config = config
        
        super().__init__(
            name="WorkflowRefiner",
            model=_get_model_for_agent(config, "refinement"),
            instruction=self._get_instruction(),
            description="Refines workflows to fix errors",
            generate_content_config=_get_default_generate_config(),
            before_model_callback=self._before_model_callback
        )
    
    def _get_instruction(self) -> str:
        # Get contexts
        docker_context = get_docker_registry_context()
        dsl_context = get_dsl_context()
        
        return f"""You are an expert at fixing Kubiya workflow code errors.

{dsl_context}

{docker_context}

Your task is to:
1. Get the original workflow Python code from session state under the key 'workflow_code'
2. Get the compilation errors from session state under the key 'compilation_errors'  
3. Analyze the errors and understand what went wrong
4. Fix the code to resolve all issues
5. Ensure the workflow follows Kubiya SDK best practices

Common issues and fixes:
- Import errors: Always use 'from kubiya_workflow_sdk import Workflow'
- Syntax errors: Check Python syntax, indentation, quotes
- Missing runner: Get actual runner from platform context
- Invalid Docker images: Use images from trusted registries
- Missing step methods: Use chainable DSL (wf.step() not add_step())
- Incorrect tool definitions: Follow the tool_def() format exactly

Best practices:
- Use the chainable DSL syntax
- Always specify a runner from the platform
- Use descriptive names for workflows and steps
- Add description fields to provide context
- Use tool_def() for Docker-based steps
- Include proper error handling (set -e)
- Use trusted Docker images only

I'll analyze the errors and fix the workflow code step by step.

First, let me identify the issues:
[Describe the errors you're fixing]

Now, here's the corrected workflow code:

<refined_workflow_code>
from kubiya_workflow_sdk import Workflow

# Fixed workflow code here
wf = (Workflow("name")
      .description("Description")
      .runner("actual-runner-name")
      .step("step1", "command"))
</refined_workflow_code>

Changes made:
1. [List each change and why it was needed]
2. [Explain the fix]

The refined code now:
✅ Addresses all reported errors
✅ Can be executed without errors
✅ Produces a valid workflow object
✅ Follows SDK conventions and best practices
✅ Uses actual resources from the platform context
"""
    
    async def _before_model_callback(
        self,
        llm_request: LlmRequest,
        callback_context: CallbackContext
    ) -> Optional[LlmResponse]:
        """Load previous artifacts for context."""
        if hasattr(callback_context, 'load_artifact'):
            try:
                # Load the previous workflow code
                code_artifact = await callback_context.load_artifact("generated_workflow.py")
                if code_artifact and code_artifact.inline_data:
                    logger.info("Loaded previous workflow code for refinement")
                
                # Load compilation errors
                result_artifact = await callback_context.load_artifact("compilation_result.json")
                if result_artifact and result_artifact.inline_data:
                    result = json.loads(result_artifact.inline_data.data.decode())
                    if result.get("errors"):
                        logger.info(f"Loaded {len(result['errors'])} errors for refinement")
                        
            except Exception as e:
                logger.warning(f"Failed to load artifacts for refinement: {e}")
        
        return None
    
    async def refine_workflow(
        self,
        workflow_code: str,
        errors: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine a workflow to fix errors.
        
        Args:
            workflow_code: Original workflow code
            errors: List of error messages
            context: Platform context
            
        Returns:
            Refinement result with fixed code
        """
        # This would be called by the orchestrator
        # For now, just return a structure
        return {
            "success": False,
            "refined_code": workflow_code,
            "changes_made": [],
            "remaining_errors": errors
        }


class RefinementLoop:
    """Handles iterative refinement until success or max iterations."""
    
    def __init__(
        self,
        refiner: RefinementAgent,
        compiler: 'CompilerAgent',
        max_iterations: int = 3
    ):
        self.refiner = refiner
        self.compiler = compiler
        self.max_iterations = max_iterations
    
    async def refine_until_success(
        self,
        initial_code: str,
        initial_errors: List[str],
        context: Dict[str, Any],
        session: Any
    ) -> Dict[str, Any]:
        """
        Refine workflow iteratively until it compiles successfully.
        
        Args:
            initial_code: Initial workflow code
            initial_errors: Initial compilation errors
            context: Platform context
            session: ADK session
            
        Returns:
            Final result with workflow or errors
        """
        current_code = initial_code
        current_errors = initial_errors
        
        for iteration in range(self.max_iterations):
            logger.info(f"Refinement iteration {iteration + 1}/{self.max_iterations}")
            
            # Update session state
            session.state["workflow_code"] = current_code
            session.state["compilation_errors"] = current_errors
            
            # Run refiner
            refinement_result = await self.refiner.refine_workflow(
                current_code,
                current_errors,
                context
            )
            
            if not refinement_result["success"]:
                return {
                    "success": False,
                    "final_code": current_code,
                    "final_errors": current_errors,
                    "iterations": iteration + 1,
                    "reason": "Failed to refine workflow"
                }
            
            current_code = refinement_result["refined_code"]
            
            # Try to compile again
            session.state["workflow_code"] = current_code
            compilation_result = await self._compile_workflow(session)
            
            if compilation_result["status"] == "success":
                return {
                    "success": True,
                    "final_code": current_code,
                    "workflow": compilation_result["workflow"],
                    "iterations": iteration + 1
                }
            
            current_errors = compilation_result.get("errors", [])
            
            # Check if we're making progress
            if current_errors == initial_errors:
                logger.warning("No progress made in refinement")
                break
        
        return {
            "success": False,
            "final_code": current_code,
            "final_errors": current_errors,
            "iterations": self.max_iterations,
            "reason": "Max iterations reached"
        }
    
    async def _compile_workflow(self, session: Any) -> Dict[str, Any]:
        """Compile workflow using the compiler agent."""
        # Create a mock context for the compiler
        class MockContext:
            def __init__(self, session, agent=None):
                self.session = session
                self.invocation_id = "compile"
                self.user_content = None
                self.end_invocation = False  # ADK expects this attribute
                self.agent = agent or self  # ADK expects agent reference
                self.branch = None  # Optional ADK attribute
                self.artifact_service = None  # Optional ADK attribute
                self.session_service = None  # Optional ADK attribute
                self.memory_service = None  # Optional ADK attribute
                self.credential_service = None  # Optional ADK attribute
                self.live_request_queue = None  # Optional ADK attribute
                self.active_streaming_tools = None  # Optional ADK attribute
                self.transcription_cache = None  # Optional ADK attribute
                self.run_config = None  # Optional ADK attribute
            
            def model_copy(self, **kwargs):
                """Mock model_copy method that ADK expects."""
                new_ctx = MockContext(self.session, agent=kwargs.get('agent', self.agent))
                for key, value in kwargs.items():
                    setattr(new_ctx, key, value)
                return new_ctx
        
        ctx = MockContext(session, agent=self.compiler)
        
        # Run compiler and extract result
        compilation_result = None
        async for event in self.compiler.run_async(ctx):
            if event.is_final_response() and event.content:
                response_text = event.content.parts[0].text
                import re
                result_match = re.search(
                    r'<compilation_result>\s*(.*?)\s*</compilation_result>',
                    response_text,
                    re.DOTALL
                )
                if result_match:
                    try:
                        compilation_result = json.loads(result_match.group(1))
                    except json.JSONDecodeError:
                        pass
        
        return compilation_result or {
            "status": "error",
            "errors": ["Failed to compile workflow"],
            "workflow": None
        }


def create_refinement_agent(config: ADKConfig) -> RefinementAgent:
    """Create a refinement agent."""
    return RefinementAgent(config)


def create_refinement_loop(
    refiner: RefinementAgent,
    compiler: 'CompilerAgent',
    max_iterations: int = 3
) -> RefinementLoop:
    """Create a refinement loop."""
    return RefinementLoop(refiner, compiler, max_iterations) 