"""Loop orchestrator agent that coordinates the entire workflow generation, execution, and validation process."""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import (
    ADK_AVAILABLE, BaseAgent, InvocationContext, Event, EventActions,
    types, AsyncIterator, InMemoryArtifactService,
    WorkflowGenerationResult, WorkflowExecutionResult, ValidationResult
)
from .context_loader import ContextLoaderAgent
from .workflow_generator import WorkflowGeneratorAgent
from .compiler import CompilerAgent
from .refiner import RefinementAgent, RefinementLoop
from .executor import WorkflowExecutorAgent
from .validator import WorkflowValidatorAgent
from ..config import ADKConfig
from ..tools import KubiyaContextTools

logger = logging.getLogger(__name__)


class LoopOrchestratorAgent(BaseAgent):
    """Main orchestrator that coordinates the entire workflow lifecycle."""
    
    def __init__(
        self,
        config: ADKConfig,
        context_tools: KubiyaContextTools,
        kubiya_client: Any,
        artifact_service: Optional[Any] = None,
        max_iterations: int = 3
    ):
        super().__init__(
            name="WorkflowLoopOrchestrator",
            description="Orchestrates the complete workflow generation, execution, and validation loop"
        )
        # Store as private attributes
        self._config = config
        self._context_tools = context_tools
        self._kubiya_client = kubiya_client
        self._artifact_service = artifact_service or InMemoryArtifactService()
        self._max_iterations = max_iterations
        
        # Create sub-agents
        self._context_loader = ContextLoaderAgent(config, context_tools)
        self._generator = WorkflowGeneratorAgent(config, context_tools)
        self._compiler = CompilerAgent(config)
        self._refiner = RefinementAgent(config)
        self._executor = WorkflowExecutorAgent(config, kubiya_client)
        self._validator = WorkflowValidatorAgent(config)
        
        # Create refinement loop
        self._refinement_loop = RefinementLoop(
            self._refiner,
            self._compiler,
            max_iterations=3
        )
    
    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncIterator[Event]:
        """Orchestrate the complete workflow lifecycle."""
        invocation_id = ctx.invocation_id
        session = ctx.session
        
        # Extract user requirements
        user_requirements = ctx.user_content.parts[0].text if ctx.user_content and ctx.user_content.parts else ""
        session.state["workflow_requirements"] = user_requirements
        
        # Check if we're in compose mode
        compose_mode = session.state.get("compose_mode", None)
        compose_parameters = session.state.get("compose_parameters", {})
        
        # Override execute_workflows if in compose mode
        if compose_mode == "act":
            self._config.execute_workflows = True
            
        # Emit start event based on mode
        start_message = "🚀 Starting workflow generation and validation loop..."
        if compose_mode:
            mode_desc = "generation and execution" if compose_mode == "act" else "generation"
            start_message = f"🚀 Starting workflow {mode_desc} (compose mode: {compose_mode})..."
            
        yield Event(
            author=self.name,
            invocation_id=invocation_id,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=start_message)]
            ),
            partial=False
        )
        
        overall_iterations = 0
        success = False
        final_workflow = None
        final_execution_result = None
        
        while overall_iterations < self._max_iterations and not success:
            overall_iterations += 1
            logger.info(f"Starting overall iteration {overall_iterations}/{self._max_iterations}")
            
            # Step 1: Load Platform Context
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"\n📊 Step 1/{overall_iterations}: Loading platform context...")]
                ),
                partial=False
            )
            
            # Load context directly using the tools instead of running the agent
            platform_context = {
                "available_runners": [],
                "relevant_integrations": {},
                "available_secrets": [],
                "organization": {},
                "missing_resources": [],
                "recommendations": []
            }
            
            try:
                # Get organization info
                org_info = self._context_tools.get_org_info()
                platform_context["organization"] = org_info
                
                # Get available runners
                runners = self._context_tools.get_runners()
                platform_context["available_runners"] = [r.get("name", r.get("id", "unknown")) for r in runners] if isinstance(runners, list) else []
                
                # Get integrations
                integrations = self._context_tools.get_integrations()
                if isinstance(integrations, dict):
                    platform_context["relevant_integrations"] = integrations
                elif isinstance(integrations, list):
                    # Convert list to dict format
                    platform_context["relevant_integrations"] = {
                        integration.get("name", "unknown"): {
                            "enabled": integration.get("enabled", False),
                            "config": integration.get("config", {})
                        }
                        for integration in integrations
                    }
                
                # Get secrets metadata
                secrets = self._context_tools.get_secrets_metadata()
                platform_context["available_secrets"] = [s.get("name", s.get("key", "unknown")) for s in secrets] if isinstance(secrets, list) else []
                
                # Save context to session
                session.state["platform_context"] = platform_context
                
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"✅ Platform context loaded successfully")]
                    ),
                    partial=False
                )
                
            except Exception as e:
                logger.warning(f"Failed to load some platform context: {e}")
                # Continue with partial context
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"⚠️ Partial platform context loaded")]
                    ),
                    partial=False
                )
            
            # Step 2: Generate Workflow
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"\n🔨 Step 2/{overall_iterations}: Generating workflow code...\n")]
                ),
                partial=True
            )
            
            # Stream directly from generator
            workflow_code = None
            final_response = None
            
            async for event in self._generator.run_async(ctx):
                # Pass through the agent's streaming output
                if event.content and event.content.parts:
                    yield event  # Direct passthrough of agent events
                    
                    if event.is_final_response():
                        final_response = event.content.parts[0].text if event.content.parts else ""
                        # Extract generated code from final response
                        import re
                        code_match = re.search(
                            r'<workflow_code>\s*(.*?)\s*</workflow_code>',
                            final_response,
                            re.DOTALL
                        )
                        if code_match:
                            workflow_code = code_match.group(1)
                            session.state["workflow_code"] = workflow_code
            
            if not workflow_code:
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text="❌ Failed to generate workflow code. Retrying...")]
                    ),
                    partial=False
                )
                continue
            
            # Step 3: Compile Workflow
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"\n⚙️ Step 3/{overall_iterations}: Compiling workflow...")]
                ),
                partial=False
            )
            
            compilation_result = None
            async for event in self._compiler.run_async(ctx):
                # Let compiler stream its own output
                if event.content and event.content.parts:
                    yield event
                    
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
            
            # Check if compilation was successful
            if not compilation_result or compilation_result.get("status") != "success":
                # Step 3.5: Refine if compilation failed
                errors = compilation_result.get("errors", ["Unknown compilation error"]) if compilation_result else ["Compilation failed"]
                
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"\n🔧 Compilation failed with errors. Attempting automatic refinement...\n")]
                    ),
                    partial=True
                )
                
                # Stream the errors
                for error in errors:
                    yield Event(
                        author=self.name,
                        invocation_id=invocation_id,
                        content=types.Content(
                            role="assistant",
                            parts=[types.Part(text=f"- {error}\n")]
                        ),
                        partial=True
                    )
                
                # Use refinement loop
                refinement_result = await self._refinement_loop.refine_until_success(
                    workflow_code,
                    errors,
                    platform_context,
                    session
                )
                
                if refinement_result["success"]:
                    final_workflow = refinement_result["workflow"]
                    session.state["compiled_workflow"] = final_workflow
                else:
                    yield Event(
                        author=self.name,
                        invocation_id=invocation_id,
                        content=types.Content(
                            role="assistant",
                            parts=[types.Part(text=f"❌ Refinement failed: {refinement_result['reason']}. Retrying from scratch...")]
                        ),
                        partial=False
                    )
                    continue
            else:
                final_workflow = compilation_result["workflow"]
                session.state["compiled_workflow"] = final_workflow
            
            # Step 4: Execute Workflow (optional, based on config or compose mode)
            if self._config.execute_workflows or compose_mode == "act":
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"\n🚀 Step 4/{overall_iterations}: Executing workflow on Kubiya platform...")]
                    ),
                    partial=False
                )
                
                # Show execution details
                runner = final_workflow.get("runner", "default")
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"\n📍 Execution Details:\n   - Organization: {self._kubiya_client.org_name if hasattr(self._kubiya_client, 'org_name') else 'default'}\n   - Runner: {runner}\n   - Workflow: {final_workflow.get('name', 'unnamed')}\n")]
                    ),
                    partial=False
                )
                
                # Use compose parameters if available, otherwise use workflow params
                exec_params = compose_parameters if compose_parameters else final_workflow.get("params", {})
                
                # Create a streaming execution context
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"\n📡 Streaming execution events...\n")]
                    ),
                    partial=False
                )
                
                # Stream execution events directly from the executor
                execution_result = None
                try:
                    # Instead of creating a new context, use the current context
                    # The executor will read the workflow from session state
                    exec_ctx = ctx
                    
                    # Set the workflow in session for executor
                    session.state["compiled_workflow"] = final_workflow
                    session.state["execution_params"] = exec_params
                    
                    # Stream execution events
                    async for exec_event in self._executor.run_async(exec_ctx):
                        # Pass through execution events directly
                        if exec_event.content and exec_event.content.parts:
                            yield exec_event
                            
                            # Check if this is the final event with result
                            if exec_event.is_final_response():
                                response_text = exec_event.content.parts[0].text
                                # Try to extract execution result
                                import re
                                result_match = re.search(
                                    r'<execution_result>\s*(.*?)\s*</execution_result>',
                                    response_text,
                                    re.DOTALL
                                )
                                if result_match:
                                    try:
                                        exec_result_data = json.loads(result_match.group(1))
                                        execution_result = type('ExecutionResult', (), exec_result_data)()
                                        final_execution_result = execution_result
                                    except:
                                        pass
                    
                    # If we didn't get a result from streaming, check session state
                    if not execution_result and "execution_result" in session.state:
                        exec_data = session.state["execution_result"]
                        execution_result = type('ExecutionResult', (), exec_data)()
                        final_execution_result = execution_result
                    
                    # Save execution result in session
                    if execution_result:
                        session.state["execution_result"] = {
                            "success": getattr(execution_result, 'success', False),
                            "execution_id": getattr(execution_result, 'execution_id', None),
                            "outputs": getattr(execution_result, 'outputs', {}),
                            "errors": getattr(execution_result, 'errors', []),
                            "logs": getattr(execution_result, 'logs', []),
                            "duration_seconds": getattr(execution_result, 'duration_seconds', 0)
                        }
                        
                except Exception as e:
                    logger.error(f"Execution streaming failed: {e}")
                    yield Event(
                        author=self.name,
                        invocation_id=invocation_id,
                        content=types.Content(
                            role="assistant",
                            parts=[types.Part(text=f"⚠️ Execution failed: {str(e)}")]
                        ),
                        partial=False
                    )
            
            # Step 5: Validate Workflow
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"\n✅ Step 5/{overall_iterations}: Validating workflow against requirements...")]
                ),
                partial=False
            )
            
            validation_result = None
            validation_summary = ""
            async for event in self._validator.run_async(ctx):
                # Stream validator output
                if event.content and event.content.parts:
                    yield event
                    
                if event.is_final_response() and event.content:
                    response_text = event.content.parts[0].text
                    validation_summary = response_text  # Save for final summary
                    import re
                    result_match = re.search(
                        r'<validation_result>\s*(.*?)\s*</validation_result>',
                        response_text,
                        re.DOTALL
                    )
                    if result_match:
                        try:
                            validation_result = json.loads(result_match.group(1))
                        except json.JSONDecodeError:
                            pass
            
            if validation_result and validation_result.get("meets_requirements"):
                success = True
                
                # Save final workflow as user artifact
                if hasattr(session, 'context') and hasattr(session.context, 'save_artifact'):
                    workflow_artifact = types.Part.from_bytes(
                        data=json.dumps(final_workflow, indent=2).encode(),
                        mime_type="application/json"
                    )
                    version = await session.context.save_artifact(
                        filename="user:final_workflow.json",
                        artifact=workflow_artifact
                    )
                    
                    # Also save with timestamp
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    await session.context.save_artifact(
                        filename=f"user:workflow_{timestamp}.json",
                        artifact=workflow_artifact
                    )
                
                # The validator already provided a comprehensive summary
                # Add the final workflow JSON
                
                # In compose mode, wrap the workflow in tags for extraction
                if compose_mode:
                    workflow_output = f"\n\n<workflow>\n{json.dumps(final_workflow, indent=2)}\n</workflow>"
                    
                    # If act mode and execution was successful, include execution result
                    if compose_mode == "act" and final_execution_result:
                        exec_result_data = {
                            "success": final_execution_result.success,
                            "execution_id": final_execution_result.execution_id,
                            "outputs": final_execution_result.outputs,
                            "duration_seconds": final_execution_result.duration_seconds
                        }
                        workflow_output += f"\n\n<execution_result>\n{json.dumps(exec_result_data, indent=2)}\n</execution_result>"
                else:
                    workflow_output = f"\n\n### 📄 Final Workflow JSON:\n```json\n{json.dumps(final_workflow, indent=2)}\n```"
                
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"{workflow_output}\n\n✅ The workflow has been saved as an artifact and is ready for use!")]
                    ),
                    partial=False,
                    turn_complete=True
                )
            else:
                # Validation failed, need to iterate
                missing_reqs = validation_result.get("missing_requirements", []) if validation_result else ["Unknown validation failure"]
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"\n🔄 Validation identified issues: {', '.join(missing_reqs)}. Iterating...")]
                    ),
                    partial=False
                )
                
                # Update requirements with validation feedback
                session.state["workflow_requirements"] = f"{user_requirements}\n\nAdditional requirements from validation:\n" + "\n".join(missing_reqs)
        
        if not success:
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"\n❌ Failed to generate a valid workflow after {overall_iterations} iterations. Please refine your requirements and try again.")]
                ),
                partial=False,
                turn_complete=True
            )
    



def create_loop_orchestrator_agent(
    config: ADKConfig,
    context_tools: KubiyaContextTools,
    kubiya_client: Any,
    artifact_service: Optional[Any] = None,
    max_iterations: int = 3
) -> LoopOrchestratorAgent:
    """Create a loop orchestrator agent."""
    return LoopOrchestratorAgent(
        config,
        context_tools,
        kubiya_client,
        artifact_service,
        max_iterations
    ) 