"""
ADK Provider for Kubiya Workflow Generation.

This provider integrates Google's ADK (Agent Development Kit) to generate
intelligent workflows for the Kubiya platform using the SDK's Python API.
"""

import logging
import json
import yaml
import asyncio
import sys
import os
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
import uuid

# Fix AsyncIterator import for Python 3.9
if sys.version_info >= (3, 9):
    from collections.abc import AsyncIterator
else:
    from typing import AsyncIterator

# Handle nested event loops
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass  # nest_asyncio is optional but recommended

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
    from google.adk.artifacts.gcs_artifact_service import GcsArtifactService
    from google.adk.events.event import Event
    from google.adk.events.event_actions import EventActions
    from google.genai import types
    from google.adk.models.llm_response import LlmResponse
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    # Mock types for when ADK is not installed
    class Runner:
        pass
    class Event:
        pass
    class EventActions:
        pass
    class InMemorySessionService:
        pass
    class InMemoryArtifactService:
        pass
    class GcsArtifactService:
        pass
    class LlmResponse:
        pass
    class types:
        class Content:
            pass
        class Part:
            pass

from ...core.exceptions import ProviderError
from ..base import BaseProvider
from .config import ADKConfig, ModelProvider
from .agents import ADK_AVAILABLE as AGENTS_AVAILABLE, create_orchestrator_agent
from .tools import KubiyaContextTools
from .streaming import StreamHandler, SSEFormatter, VercelAIFormatter

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an async coroutine, handling nested event loops."""
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # We're in an event loop, create a task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No event loop, use asyncio.run
        return asyncio.run(coro)


class ADKProvider(BaseProvider):
    """
    ADK Provider implementation for intelligent workflow generation.
    
    Features:
    - Uses Together AI models by default (configurable)
    - Generates workflows using Kubiya SDK Python API
    - Executes workflows with streaming support
    - Supports SSE and Vercel AI SDK streaming formats
    - Uses ADK artifacts for workflow storage
    - Proper event-based streaming
    - Includes error refinement loop
    - Validates workflows using SDK before returning
    """
    
    def __init__(
        self,
        client: Any,
        config: Optional[ADKConfig] = None,
        artifact_service: Optional[Any] = None,
        session_service: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize ADK Provider.
        
        Args:
            client: Kubiya SDK client
            config: ADK configuration (defaults to Together AI)
            artifact_service: ADK artifact service (defaults to InMemory)
            session_service: ADK session service (defaults to InMemory)
            **kwargs: Additional provider options
        """
        if not ADK_AVAILABLE or not AGENTS_AVAILABLE:
            raise ImportError(
                "Google ADK is required for this provider. "
                "Install with: pip install kubiya-workflow-sdk[adk]"
            )
        
        super().__init__(client, **kwargs)
        
        # Initialize configuration
        self.config = config or ADKConfig()
        self.config.validate()
        
        # Set up environment for Together AI
        self.config.setup_environment()
        
        # Register all models in ADK's registry with LiteLLM
        self._configure_litellm_models()
        
        # Initialize Kubiya client and tools
        self.client = client
        # Pass API key and org_name from client to context tools
        self.context_tools = KubiyaContextTools(
            api_key=getattr(client, 'api_key', None),
            base_url=getattr(client, 'base_url', 'https://api.kubiya.ai'),
            org_name=getattr(client, 'org_name', None)
        )
        
        # Initialize ADK services
        self.artifact_service = artifact_service or InMemoryArtifactService()
        self.session_service = session_service or InMemorySessionService()
        
        # Initialize orchestrator agent
        self._orchestrator = None
        self._runner = None
        
        # Handle both string and enum types for model_provider
        provider_value = (
            self.config.model_provider.value 
            if hasattr(self.config.model_provider, 'value') 
            else self.config.model_provider
        )
        logger.info(f"Initialized ADK Provider with {provider_value} models")
    
    @property
    def orchestrator(self):
        """Lazy load orchestrator agent."""
        if self._orchestrator is None:
            self._orchestrator = create_orchestrator_agent(
                config=self.config,
                context_tools=self.context_tools,
                kubiya_client=self.client,
                artifact_service=self.artifact_service,
                max_iterations=self.config.max_loop_iterations
            )
        return self._orchestrator
    
    @property
    def runner(self):
        """Lazy load ADK runner."""
        if self._runner is None:
            self._runner = Runner(
                agent=self.orchestrator,
                app_name="kubiya_workflow_generator",
                session_service=self.session_service,
                artifact_service=self.artifact_service
            )
        return self._runner
    
    def generate_workflow(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        stream_format: str = "sse",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Generate a workflow for the given task.
        
        Args:
            task: Task description or requirements
            context: Additional context (optional)
            stream: Enable streaming response
            stream_format: Streaming format ("sse" or "vercel")
            session_id: Session ID for conversation continuity
            user_id: User ID for artifact namespacing
            **kwargs: Additional generation options
        
        Returns:
            Generated workflow as JSON or streaming response
        """
        try:
            # Set defaults
            user_id = user_id or "default_user"
            session_id = session_id or str(uuid.uuid4())
            
            # Create user message
            user_message = types.Content(
                role="user",
                parts=[types.Part(text=task)]
            )
            
            if stream:
                # Return async generator for streaming
                return self._stream_workflow_generation(
                    user_message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    stream_format=stream_format,
                    context=context
                )
            else:
                # Run synchronously and extract workflow
                workflow = run_async(
                    self._generate_workflow_sync(
                        user_message=user_message,
                        user_id=user_id,
                        session_id=session_id,
                        context=context
                    )
                )
                return workflow
                
        except Exception as e:
            logger.error(f"ADK workflow generation failed: {e}")
            raise ProviderError(f"Workflow generation failed: {str(e)}")
    
    async def _generate_workflow_sync(
        self,
        user_message: types.Content,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate workflow synchronously."""
        workflow_dict = None
        
        # Always create a new session for each workflow generation
        logger.info(f"Creating new session: app={self.runner.app_name}, user={user_id}, session={session_id}")
        session = await self.session_service.create_session(
            app_name="kubiya_workflow_generator",
            user_id=user_id,
            session_id=session_id,
            state=context or {}
        )
        logger.info(f"Created session: {session_id} - session object: {session}")
        
        # Log runner state
        logger.info(f"Runner app_name: {self.runner.app_name}")
        logger.info(f"Session service type: {type(self.session_service)}")
        
        # Run the ADK runner
        logger.info(f"Running ADK runner with user_id={user_id}, session_id={session_id}")
        event_count = 0
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            event_count += 1
            logger.debug(f"Received event {event_count}: {type(event)}, turn_complete={getattr(event, 'turn_complete', False)}")
            
            # Check if event has content with workflow data
            if event.content and event.content.parts and event.content.parts[0].text:
                response_text = event.content.parts[0].text
                
                # Look for workflow JSON in response
                import re
                workflow_match = re.search(
                    r'<workflow>\s*(.*?)\s*</workflow>',
                    response_text,
                    re.DOTALL
                )
                if workflow_match:
                    try:
                        workflow_dict = json.loads(workflow_match.group(1))
                        logger.info("Successfully extracted workflow from response")
                        break  # Stop processing once we have the workflow
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse workflow JSON: {e}")
        
        logger.info(f"Total events received: {event_count}")
        
        # Also check for workflow in artifacts (if save_artifact worked)
        if hasattr(event, 'actions') and event.actions and hasattr(event.actions, 'artifact_delta'):
            logger.info(f"Artifacts saved: {event.actions.artifact_delta}")
        
        if not workflow_dict:
            raise ProviderError("Failed to generate workflow")
        
        # Validate using SDK
        validation_result = self._validate_with_sdk(workflow_dict)
        if not validation_result["valid"]:
            raise ProviderError(
                f"Generated workflow is invalid: {', '.join(validation_result['errors'])}"
            )
        
        return workflow_dict
    
    async def _stream_workflow_generation(
        self,
        user_message: types.Content,
        user_id: str,
        session_id: str,
        stream_format: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream workflow generation events."""
        formatter = (
            VercelAIFormatter() if stream_format == "vercel"
            else SSEFormatter()
        )
        
        try:
            # Always create a new session for each workflow generation
            logger.info(f"Creating new session for streaming: {session_id}")
            session = await self.session_service.create_session(
                app_name="kubiya_workflow_generator",
                user_id=user_id,
                session_id=session_id,
                state=context or {}
            )
            logger.info(f"Created session for streaming: {session_id}")
            
            # Run the ADK runner and stream events
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message
            ):
                # Format event based on its type
                formatted_event = self._format_adk_event(event, formatter)
                if formatted_event:
                    yield formatted_event
            
            # Send completion event
            completion_event = formatter.format_completion()
            if completion_event:
                yield completion_event
                
        except Exception as e:
            error_event = formatter.format_error(str(e))
            yield error_event
    
    def _format_adk_event(
        self,
        event: Event,
        formatter: Union[SSEFormatter, VercelAIFormatter]
    ) -> Optional[str]:
        """Format ADK event for streaming."""
        # Handle text content
        if event.content and event.content.parts:
            if event.get_function_calls():
                # Format tool calls
                calls = event.get_function_calls()
                formatted_events = []
                for call in calls:
                    formatted = formatter.format_tool_call(call.name, call.args)
                    if formatted:
                        formatted_events.append(formatted)
                return ''.join(formatted_events)
            
            elif event.get_function_responses():
                # Format tool results
                responses = event.get_function_responses()
                formatted_events = []
                for response in responses:
                    formatted = formatter.format_tool_result(response.name, response.response)
                    if formatted:
                        formatted_events.append(formatted)
                return ''.join(formatted_events)
            
            elif event.content.parts[0].text:
                # Format text content
                return formatter.format_text(event.content.parts[0].text)
        
        # Handle artifacts saved
        if event.actions and event.actions.artifact_delta:
            if hasattr(formatter, 'format_metadata'):
                return formatter.format_metadata({
                    "artifacts_saved": event.actions.artifact_delta
                })
        
        # Handle errors
        if hasattr(event, 'error_code') and event.error_code:
            return formatter.format_error(f"{event.error_code}: {event.error_message}")
        
        return None
    
    async def execute_workflow(
        self,
        workflow: Union[str, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        stream: bool = True,
        stream_format: str = "sse",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Execute a workflow with optional streaming.
        
        Args:
            workflow: Workflow dict, name/ID, or Python code
            parameters: Workflow execution parameters
            stream: Enable streaming response
            stream_format: Streaming format ("sse" or "vercel")
            user_id: User ID for artifact storage
            session_id: Session ID for continuity
            **kwargs: Additional execution options
        
        Returns:
            Execution result or streaming response
        """
        try:
            # Set defaults
            user_id = user_id or "default_user"
            session_id = session_id or str(uuid.uuid4())
            
            # Save workflow as artifact for execution
            workflow_artifact = await self._save_workflow_artifact(
                workflow=workflow,
                user_id=user_id,
                session_id=session_id
            )
            
            # Generate execution code using SDK
            execution_code = self._generate_execution_code(workflow, parameters)
            
            # Save execution code as artifact
            code_artifact = types.Part.from_bytes(
                data=execution_code.encode(),
                mime_type="text/x-python"
            )
            
            # Get session context
            try:
                session = await self.session_service.get_session(
                    app_name="kubiya_workflow_generator",
                    user_id=user_id,
                    session_id=session_id
                )
            except Exception:
                # Session doesn't exist, create it
                session = await self.session_service.create_session(
                    app_name="kubiya_workflow_generator",
                    user_id=user_id,
                    session_id=session_id,
                    state={}
                )
                logger.info(f"Created new session for workflow execution: {session_id}")
            
            exec_version = session.context.save_artifact(
                filename="execution_code.py",
                artifact=code_artifact
            )
            
            logger.info(f"Saved execution code as artifact version {exec_version}")
            
            if stream:
                return self._stream_sdk_execution(
                    execution_code=execution_code,
                    stream_format=stream_format,
                    user_id=user_id,
                    session_id=session_id,
                    **kwargs
                )
            else:
                # Execute workflow using SDK
                result = await self._execute_sdk_workflow(execution_code)
                
                # Save result as artifact
                result_artifact = types.Part.from_bytes(
                    data=json.dumps(result, indent=2).encode(),
                    mime_type="application/json"
                )
                result_version = session.context.save_artifact(
                    filename="execution_result.json",
                    artifact=result_artifact
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise ProviderError(f"Workflow execution failed: {str(e)}")
    
    async def _save_workflow_artifact(
        self,
        workflow: Union[str, Dict[str, Any]],
        user_id: str,
        session_id: str
    ) -> int:
        """Save workflow as artifact and return version."""
        # Ensure session exists
        try:
            session = await self.session_service.get_session(
                app_name="kubiya_workflow_generator",
                user_id=user_id,
                session_id=session_id
            )
        except Exception:
            # Session doesn't exist, create it
            session = await self.session_service.create_session(
                app_name="kubiya_workflow_generator",
                user_id=user_id,
                session_id=session_id,
                state={}
            )
            logger.info(f"Created new session for artifact storage: {session_id}")
        
        if isinstance(workflow, dict):
            # It's already a workflow dict
            artifact = types.Part.from_bytes(
                data=json.dumps(workflow, indent=2).encode(),
                mime_type="application/json"
            )
            filename = "workflow_to_execute.json"
        else:
            # It's Python code or workflow name
            artifact = types.Part.from_bytes(
                data=workflow.encode() if isinstance(workflow, str) else str(workflow).encode(),
                mime_type="text/plain"
            )
            filename = "workflow_to_execute.txt"
        
        version = session.context.save_artifact(
            filename=filename,
            artifact=artifact
        )
        
        logger.info(f"Saved workflow as artifact '{filename}' version {version}")
        return version
    
    def _generate_execution_code(
        self,
        workflow: Union[str, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Python code to execute workflow using SDK."""
        params_str = ""
        if parameters:
            params_str = f", parameters={json.dumps(parameters)}"
        
        if isinstance(workflow, str):
            # If it's already Python code, append execution
            if "from kubiya_workflow_sdk" in workflow:
                return f"""
{workflow}

# Execute the workflow
import asyncio

async def execute():
    result = await workflow.execute({params_str})
    return result

execution_result = asyncio.run(execute())
"""
            else:
                # It's a workflow name/ID
                return f"""
from kubiya_workflow_sdk import KubiyaClient
import asyncio

# Initialize client
client = KubiyaClient()

# Execute workflow by name
async def execute():
    result = await client.execute_workflow("{workflow}"{params_str})
    return result

execution_result = asyncio.run(execute())
"""
        else:
            # It's a workflow dict - generate code to create and execute it
            workflow_json = json.dumps(workflow, indent=2)
            return f"""
from kubiya_workflow_sdk.dsl import Workflow, Step, parallel, sequence
from kubiya_workflow_sdk.dsl.executors import PythonExecutor, BashExecutor
import json
import asyncio

# Recreate workflow from dict
workflow_dict = {workflow_json}

# Create workflow object
workflow = Workflow(workflow_dict['name'])
workflow.description = workflow_dict.get('description', '')

# Add steps from dict
for step_dict in workflow_dict.get('steps', []):
    step = Step(
        name=step_dict['name'],
        executor=globals()[step_dict['executor']['type']](
            script=step_dict['executor']['script']
        )
    )
    if 'depends_on' in step_dict:
        step.depends_on = step_dict['depends_on']
    workflow.add_step(step)

# Execute the workflow
async def execute():
    result = await workflow.execute({params_str})
    return result

execution_result = asyncio.run(execute())
"""
    
    async def _stream_sdk_execution(
        self,
        execution_code: str,
        stream_format: str,
        user_id: str,
        session_id: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream workflow execution events from SDK."""
        formatter = (
            VercelAIFormatter() if stream_format == "vercel"
            else SSEFormatter()
        )
        
        try:
            # Create execution request for ADK
            exec_message = types.Content(
                role="user",
                parts=[types.Part(text=f"Execute this workflow code and stream the results:\n\n```python\n{execution_code}\n```")]
            )
            
            # Use a specialized execution agent or the orchestrator
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=exec_message
            ):
                # Format execution events
                if event.content and event.content.parts and event.content.parts[0].text:
                    text = event.content.parts[0].text
                    
                    # Look for execution markers
                    if "Starting execution" in text or "Executing" in text:
                        yield formatter.format_text("🚀 Workflow execution started\n")
                    elif "Step" in text and ("started" in text or "completed" in text):
                        yield formatter.format_text(text + "\n")
                    elif "Error" in text or "Failed" in text:
                        yield formatter.format_error(text)
                    else:
                        yield formatter.format_text(text)
                
                # Check for execution results in artifacts
                if event.actions and event.actions.artifact_delta:
                    if "execution_result.json" in event.actions.artifact_delta:
                        yield formatter.format_text("✅ Workflow execution completed\n")
            
            # Send completion
            yield formatter.format_completion()
            
        except Exception as e:
            yield formatter.format_error(str(e))
    
    async def _execute_sdk_workflow(self, execution_code: str) -> Dict[str, Any]:
        """Execute workflow synchronously using SDK."""
        try:
            # Create a namespace for execution
            namespace = {
                'KubiyaClient': self.client.__class__,
                'client': self.client
            }
            
            # Execute the code
            exec(execution_code, namespace)
            
            # Get the result
            if 'execution_result' in namespace:
                return namespace['execution_result']
            else:
                # If no execution_result, try to find and execute the workflow
                for key, value in namespace.items():
                    if hasattr(value, 'execute'):
                        result = await value.execute()
                        return result
                
                raise ProviderError("No executable workflow found in generated code")
                
        except Exception as e:
            logger.error(f"SDK execution failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def validate_workflow(
        self,
        workflow_code: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Validate a workflow Python code or dict.
        
        Args:
            workflow_code: Python code that creates a workflow or workflow dict/JSON
            context: Additional validation context
            **kwargs: Additional validation options
        
        Returns:
            Validation result with errors and warnings
        """
        try:
            # Check if it's already a dict/JSON
            workflow_dict = None
            if isinstance(workflow_code, dict):
                workflow_dict = workflow_code
            elif isinstance(workflow_code, str):
                # Try to parse as JSON first
                try:
                    workflow_dict = json.loads(workflow_code)
                except json.JSONDecodeError:
                    # Not JSON, assume it's Python code
                    workflow_dict = self._execute_workflow_code(workflow_code)
            
            if not workflow_dict:
                return {
                    "valid": False,
                    "errors": ["No workflow found"],
                    "warnings": []
                }
            
            # Validate using SDK
            return self._validate_with_sdk(workflow_dict)
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
    
    def refine_workflow(
        self,
        workflow_code: str,
        errors: List[str],
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Refine a workflow based on errors.
        
        Args:
            workflow_code: Current workflow Python code
            errors: List of errors to fix
            context: Additional context
            user_id: User ID for artifact storage
            session_id: Session ID for continuity
            **kwargs: Additional refinement options
        
        Returns:
            Refined workflow as JSON
        """
        try:
            # Set defaults
            user_id = user_id or "default_user"
            session_id = session_id or str(uuid.uuid4())
            
            # Create refinement request
            refine_message = types.Content(
                role="user",
                parts=[types.Part(text=f"""
Fix this workflow code that has errors:

```python
{workflow_code}
```

Errors to fix:
{json.dumps(errors, indent=2)}

Please provide the corrected workflow code.
""")]
            )
            
            # Run refinement through ADK
            refined_workflow = run_async(
                self._generate_workflow_sync(
                    user_message=refine_message,
                    user_id=user_id,
                    session_id=session_id,
                    context=context
                )
            )
            
            return refined_workflow
            
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            raise ProviderError(f"Workflow refinement failed: {str(e)}")
    
    def _execute_workflow_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Execute workflow Python code and return the workflow dict."""
        try:
            namespace = {}
            exec(code, namespace)
            
            # Look for workflow object
            for var_name in ['workflow', 'wf', 'workflow_dict']:
                if var_name in namespace:
                    obj = namespace[var_name]
                    if hasattr(obj, 'to_dict'):
                        return obj.to_dict()
                    elif isinstance(obj, dict):
                        return obj
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to execute workflow code: {e}")
            return None
    
    def _validate_with_sdk(self, workflow_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow using SDK."""
        try:
            from kubiya_workflow_sdk.dsl import Workflow
            
            # Create workflow object
            wf = Workflow(workflow_dict.get("name", "unnamed"))
            wf.data = workflow_dict
            
            # Validate
            return wf.validate()
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"SDK validation error: {str(e)}"],
                "warnings": []
            }

    def compose(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        mode: str = "plan",
        stream: bool = True,
        stream_format: str = "sse",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Compose a workflow solution end-to-end.
        
        The provider handles everything internally - the loop orchestrator
        will generate the workflow and optionally execute it based on mode.
        
        Args:
            task: Task description or user requirement
            context: Platform context (resources, constraints)
            parameters: Execution parameters (only used in 'act' mode)
            mode: 'plan' to generate workflow, 'act' to generate and execute
            stream: Enable streaming response
            stream_format: Streaming format ("sse" or "vercel")
            session_id: Session ID for continuity
            user_id: User ID for artifact storage
            **kwargs: Additional options
        
        Returns:
            Workflow dict or streaming response
        """
        # Set defaults
        user_id = user_id or "default_user"
        session_id = session_id or str(uuid.uuid4())
        
        # Update config based on mode
        if hasattr(self.config, 'execute_workflows'):
            self.config.execute_workflows = (mode == "act")
        
        # Create compose message with mode context
        compose_message = types.Content(
            role="user",
            parts=[types.Part(text=task)]
        )
        
        # Update session context with mode and parameters
        session_context = context or {}
        session_context['compose_mode'] = mode
        session_context['compose_parameters'] = parameters
        
        if stream:
            # Return the async generator directly
            return self._stream_compose(
                user_message=compose_message,
                user_id=user_id,
                session_id=session_id,
                stream_format=stream_format,
                context=session_context
            )
        else:
            # Non-streaming: run the full orchestration using run_async
            return run_async(self._compose_sync(
                user_message=compose_message,
                user_id=user_id,
                session_id=session_id,
                context=session_context
            ))
    
    async def _stream_compose(
        self,
        user_message: types.Content,
        user_id: str,
        session_id: str,
        stream_format: str,
        context: Optional[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Stream compose operation - let the orchestrator handle everything."""
        formatter = (
            VercelAIFormatter() if stream_format == "vercel"
            else SSEFormatter()
        )
        
        try:
            # Create or update session
            try:
                session = await self.session_service.get_session(
                    app_name="kubiya_workflow_generator",
                    user_id=user_id,
                    session_id=session_id
                )
                # Update context
                session.context.state.update(context)
            except:
                session = await self.session_service.create_session(
                    app_name="kubiya_workflow_generator",
                    user_id=user_id,
                    session_id=session_id,
                    state=context
                )
            
            # Stream through the orchestrator - it handles everything
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message
            ):
                # Format and yield event
                formatted_event = self._format_adk_event(event, formatter)
                if formatted_event:
                    yield formatted_event
            
            # Send completion
            yield formatter.format_completion()
            
        except Exception as e:
            yield formatter.format_error(str(e))
    
    async def _compose_sync(
        self,
        user_message: types.Content,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Non-streaming compose - run the full orchestration."""
        # Create or update session
        try:
            session = await self.session_service.get_session(
                app_name="kubiya_workflow_generator",
                user_id=user_id,
                session_id=session_id
            )
            session.context.state.update(context)
        except:
            session = await self.session_service.create_session(
                app_name="kubiya_workflow_generator",
                user_id=user_id,
                session_id=session_id,
                state=context
            )
        
        # Run the orchestration
        result = {"workflow": None, "execution_result": None}
        
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            # Extract workflow from response
            if event.content and event.content.parts and event.content.parts[0].text:
                response_text = event.content.parts[0].text
                
                # Look for workflow JSON
                import re
                workflow_match = re.search(
                    r'<workflow>\s*(.*?)\s*</workflow>',
                    response_text,
                    re.DOTALL
                )
                if workflow_match:
                    try:
                        result["workflow"] = json.loads(workflow_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # Look for execution result
                exec_match = re.search(
                    r'<execution_result>\s*(.*?)\s*</execution_result>',
                    response_text,
                    re.DOTALL
                )
                if exec_match:
                    try:
                        result["execution_result"] = json.loads(exec_match.group(1))
                    except json.JSONDecodeError:
                        result["execution_result"] = exec_match.group(1)
        
        return result

    def _configure_litellm_models(self):
        """Configure LiteLLM for all model providers."""
        try:
            import litellm
            
            # Handle both string and enum types for model_provider
            provider_value = (
                self.config.model_provider.value 
                if hasattr(self.config.model_provider, 'value') 
                else self.config.model_provider
            )
            logger.info(f"Configuring LiteLLM for {provider_value} models...")
            
            # Configure based on model provider
            if self.config.model_provider == ModelProvider.TOGETHER_AI:
                # Ensure Together AI API key is set for LiteLLM
                api_key = os.getenv("TOGETHER_API_KEY")
                if api_key:
                    os.environ["TOGETHERAI_API_KEY"] = api_key
                    logger.info("✅ Together AI API key configured for LiteLLM")
                else:
                    logger.warning("⚠️  TOGETHER_API_KEY not found - Together AI models may not work")
            
            elif self.config.model_provider == ModelProvider.GOOGLE_AI:
                # Ensure Google API key is set
                api_key = os.getenv("GOOGLE_API_KEY")
                if api_key:
                    logger.info("✅ Google AI API key found for LiteLLM")
                else:
                    logger.warning("⚠️  GOOGLE_API_KEY not found - Google AI models may not work")
            
            elif self.config.model_provider == ModelProvider.VERTEX_AI:
                # Ensure Vertex AI credentials are set
                if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                    logger.info("✅ Vertex AI credentials configured for LiteLLM")
                else:
                    logger.warning("⚠️  GOOGLE_APPLICATION_CREDENTIALS not found - Vertex AI models may not work")
            
            # Enable verbose logging for debugging (set to True if needed)
            litellm.set_verbose = False
            
            # Log configured models
            logger.info(f"✅ LiteLLM configured for {provider_value} models")
            logger.debug(f"Models configured: {', '.join([self.config.get_model_for_role(role) for role in ['orchestrator', 'context_loader', 'workflow_generator', 'compiler', 'refinement', 'fast']])}")
                    
        except ImportError as e:
            provider_value = (
                self.config.model_provider.value 
                if hasattr(self.config.model_provider, 'value') 
                else self.config.model_provider
            )
            logger.warning(f"Could not import litellm - {provider_value} models not available: {e}") 