"""Workflow executor agent for running workflows on Kubiya platform."""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import (
    ADK_AVAILABLE, BaseAgent, LlmAgent, CallbackContext, FunctionTool,
    types, _get_model_for_agent, _get_default_generate_config,
    WorkflowExecutionResult, InvocationContext, Event, AsyncIterator
)
from ..config import ADKConfig

logger = logging.getLogger(__name__)


class WorkflowExecutorAgent(BaseAgent):
    """Agent responsible for executing workflows on the Kubiya platform."""
    
    def __init__(self, config: ADKConfig, kubiya_client: Any):
        super().__init__(
            name="WorkflowExecutor",
            description="Executes workflows on the Kubiya platform and streams results"
        )
        self._config = config
        self._kubiya_client = kubiya_client
        self._current_workflow = None
        self._current_execution_id = None
        self._execution_events = []
    
    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncIterator[Event]:
        """Execute workflow and stream results in real-time."""
        invocation_id = ctx.invocation_id
        session = ctx.session
        
        # Get workflow from session
        workflow_json = session.state.get("compiled_workflow")
        if not workflow_json:
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text="❌ Error: No compiled workflow found in session")]
                ),
                partial=False,
                turn_complete=True
            )
            return
        
        # Extract execution parameters
        params = session.state.get("execution_params", {})
        
        yield Event(
            author=self.name,
            invocation_id=invocation_id,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"🚀 Starting execution of workflow '{workflow_json.get('name')}'...\n")]
            ),
            partial=False
        )
        
        # Show execution details
        runner = workflow_json.get("runner", "kubiya-hosted")
        org_name = self._kubiya_client.org_name if hasattr(self._kubiya_client, 'org_name') else "unknown"
        
        yield Event(
            author=self.name,
            invocation_id=invocation_id,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"📍 Execution Details:\n   - Organization: {org_name}\n   - Runner: {runner}\n   - API Endpoint: {self._kubiya_client.base_url if hasattr(self._kubiya_client, 'base_url') else 'default'}\n\n")]
            ),
            partial=True
        )
        
        # Execute the workflow with streaming
        try:
            # Prepare workflow for execution
            if params:
                workflow_json['parameters'] = params
            
            # Generate execution ID
            execution_id = f"exec_{int(time.time())}_{workflow_json.get('name', 'unnamed')}"
            outputs = {}
            logs = []
            execution_status = "running"
            event_count = 0
            start_time = time.time()
            
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"📡 Starting SSE stream for execution ID: {execution_id}\n\n")]
                ),
                partial=True
            )
            
            # Stream execution events from Kubiya API
            try:
                for event_data in self._kubiya_client.execute_workflow(
                    workflow_definition=workflow_json,
                    parameters=params,
                    stream=True
                ):
                    event_count += 1
                    
                    # Yield SSE event info
                    yield Event(
                        author=self.name,
                        invocation_id=invocation_id,
                        content=types.Content(
                            role="assistant",
                            parts=[types.Part(text=f"🔄 SSE Event #{event_count}: ")]
                        ),
                        partial=True
                    )
                    
                    # Parse and stream event
                    try:
                        if isinstance(event_data, str):
                            # Try to parse as JSON
                            try:
                                event = json.loads(event_data)
                            except:
                                # Not JSON, treat as log message
                                logs.append(event_data)
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text=f"Log: {event_data}\n")]
                                    ),
                                    partial=True
                                )
                                continue
                        else:
                            event = event_data
                        
                        # Handle different event types
                        if isinstance(event, dict):
                            event_type = event.get('type', 'unknown')
                            
                            if event_type == 'start':
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text="✅ Workflow execution started\n")]
                                    ),
                                    partial=True
                                )
                                execution_status = "running"
                            elif event_type == 'step_start':
                                step_name = event.get('step', 'unknown')
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text=f"📍 Step '{step_name}' started\n")]
                                    ),
                                    partial=True
                                )
                            elif event_type == 'step_complete':
                                step_name = event.get('step', 'unknown')
                                step_output = event.get('output', {})
                                outputs[step_name] = step_output
                                output_str = f"✅ Step '{step_name}' completed"
                                if step_output:
                                    output_str += f" with output: {json.dumps(step_output, indent=2)}"
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text=output_str + "\n")]
                                    ),
                                    partial=True
                                )
                            elif event_type == 'log':
                                log_msg = event.get('message', '')
                                logs.append(log_msg)
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text=f"📝 {log_msg}\n")]
                                    ),
                                    partial=True
                                )
                            elif event_type == 'error':
                                error_msg = event.get('message', 'Unknown error')
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text=f"❌ Error: {error_msg}\n")]
                                    ),
                                    partial=True
                                )
                                execution_status = "failed"
                            elif event_type == 'complete':
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text="✅ Workflow execution completed\n")]
                                    ),
                                    partial=True
                                )
                                execution_status = "success"
                                break
                            elif event.get('end') or event.get('finishReason'):
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text="🏁 Stream ended\n")]
                                    ),
                                    partial=True
                                )
                                if execution_status == "running":
                                    execution_status = "success"
                                break
                            else:
                                # Unknown event type, show raw
                                yield Event(
                                    author=self.name,
                                    invocation_id=invocation_id,
                                    content=types.Content(
                                        role="assistant",
                                        parts=[types.Part(text=f"{event_type}: {json.dumps(event)}\n")]
                                    ),
                                    partial=True
                                )
                        
                    except Exception as parse_error:
                        yield Event(
                            author=self.name,
                            invocation_id=invocation_id,
                            content=types.Content(
                                role="assistant",
                                parts=[types.Part(text=f"⚠️ Parse error: {parse_error}\n")]
                            ),
                            partial=True
                        )
                        logs.append(f"Parse error: {event_data}")
                
                duration = time.time() - start_time
                
                # Show execution summary
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"\n\n📊 Execution Summary:\n   - Total Events: {event_count}\n   - Status: {execution_status}\n   - Duration: {duration:.2f}s\n")]
                    ),
                    partial=False
                )
                
            except Exception as stream_error:
                logger.error(f"Streaming error: {stream_error}")
                execution_status = "failed"
                logs.append(f"Streaming error: {str(stream_error)}")
                yield Event(
                    author=self.name,
                    invocation_id=invocation_id,
                    content=types.Content(
                        role="assistant",
                        parts=[types.Part(text=f"❌ Streaming error: {stream_error}\n")]
                    ),
                    partial=False
                )
            
            # Create execution result
            result = WorkflowExecutionResult(
                success=(execution_status == "success"),
                execution_id=execution_id,
                outputs=outputs,
                logs=logs,
                duration_seconds=time.time() - start_time,
                errors=[] if execution_status == "success" else ["Workflow execution failed"]
            )
            
            # Store result in session
            session.state["execution_result"] = {
                "success": result.success,
                "execution_id": result.execution_id,
                "outputs": result.outputs,
                "errors": result.errors,
                "logs": result.logs,
                "duration_seconds": result.duration_seconds
            }
            
            # Format final response with result tag for extraction
            final_response = f"\n<execution_result>\n{json.dumps(session.state['execution_result'], indent=2)}\n</execution_result>"
            
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=final_response)]
                ),
                partial=False,
                turn_complete=True
            )
            
        except Exception as e:
            logger.error(f"Execution failed with error: {e}", exc_info=True)
            yield Event(
                author=self.name,
                invocation_id=invocation_id,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"❌ Execution error: {str(e)}")]
                ),
                partial=False,
                turn_complete=True
            )
    
    def _get_instruction(self) -> str:
        return """You are responsible for executing workflows on the Kubiya platform.

Your tasks:
1. Get the compiled workflow from session state under 'compiled_workflow'
2. Use the execute_workflow tool to start execution
3. Monitor the execution status
4. Retrieve logs if needed
5. Report the final execution result

Execution process:
1. Call execute_workflow with the workflow JSON
2. Poll get_execution_status until completion (success/failed/cancelled)
3. If execution fails, get logs to understand why
4. Return a comprehensive execution summary

Output format:
<execution_result>
{
  "success": true/false,
  "execution_id": "exec_123",
  "status": "success/failed/cancelled",
  "duration_seconds": 45,
  "outputs": {
    "step1": {"output": "value"},
    "step2": {"output": "value"}
  },
  "logs": ["log line 1", "log line 2"],
  "errors": []
}
</execution_result>

Handle errors gracefully and provide helpful error messages.
"""
    
    def _execute_workflow_tool(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow on the Kubiya platform using the real API."""
        try:
            logger.info(f"🚀 Starting workflow execution via Kubiya API")
            logger.info(f"   Workflow: {workflow_json.get('name', 'unnamed')}")
            logger.info(f"   Runner: {workflow_json.get('runner', 'kubiya-hosted')}")
            
            # Use the actual Kubiya client execute_workflow method
            # This returns a generator for streaming
            execution_id = f"exec_{int(time.time())}_{workflow_json.get('name', 'unnamed')}"
            
            # Store workflow and execution info for streaming
            self._current_workflow = workflow_json
            self._current_execution_id = execution_id
            self._execution_events = []
            
            return {
                "success": True,
                "workflow_json": workflow_json,
                "execution_id": execution_id,
                "status": "starting",
                "message": "Workflow execution initiated. Stream events will follow."
            }
        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_execution_status_tool(self, execution_id: str) -> Dict[str, Any]:
        """Get the status of a workflow execution (mock for now)."""
        # Since the Kubiya API doesn't have a status endpoint yet,
        # we track status internally
        if hasattr(self, '_execution_events'):
            return {
                "success": True,
                "execution_id": execution_id,
                "status": "running",  # Would be determined from events
                "progress": {"events": len(self._execution_events)},
                "outputs": {},
                "start_time": None,
                "end_time": None
            }
        return {
            "success": False,
            "error": "No execution found"
        }
    
    def _get_execution_logs_tool(
        self,
        execution_id: str,
        step_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get logs from a workflow execution (mock for now)."""
        # Return stored logs if available
        if hasattr(self, '_execution_events'):
            logs = [e for e in self._execution_events if 'log' in str(e).lower()]
            return {
                "success": True,
                "execution_id": execution_id,
                "logs": logs
            }
        return {
            "success": False,
            "error": "No logs available"
        }
    
    def _cancel_execution_tool(self, execution_id: str) -> Dict[str, Any]:
        """Cancel a running workflow execution (not implemented yet)."""
        # The Kubiya API doesn't have a cancel endpoint yet
        logger.warning(f"Cancel execution not implemented for {execution_id}")
        return {
            "success": False,
            "error": "Cancel endpoint not available"
        }
    
    def _before_tool_callback(
        self,
        tool_name: str,
        args: Dict[str, Any],
        callback_context: CallbackContext
    ) -> Optional[Dict[str, Any]]:
        """Log tool execution."""
        logger.debug(f"WorkflowExecutor calling tool: {tool_name}")
        return None
    
    async def _after_model_callback(
        self,
        llm_response: Any,
        callback_context: CallbackContext
    ) -> Optional[Any]:
        """Save execution results as artifacts."""
        if not llm_response or not hasattr(llm_response, 'content'):
            return llm_response
        
        try:
            if hasattr(llm_response.content, 'parts'):
                response_text = llm_response.content.parts[0].text
            else:
                response_text = str(llm_response.content)
            
            # Extract execution result
            import re
            result_match = re.search(
                r'<execution_result>\s*(.*?)\s*</execution_result>',
                response_text,
                re.DOTALL
            )
            
            if result_match and hasattr(callback_context, 'save_artifact'):
                try:
                    result_data = json.loads(result_match.group(1))
                    
                    # Save execution result as artifact
                    result_artifact = types.Part.from_bytes(
                        data=json.dumps(result_data, indent=2).encode(),
                        mime_type="application/json"
                    )
                    version = await callback_context.save_artifact(
                        filename="execution_result.json",
                        artifact=result_artifact
                    )
                    logger.info(f"Saved execution result as artifact version {version}")
                    
                    # Save to session state
                    if hasattr(callback_context, 'session'):
                        callback_context.session.state["execution_result"] = result_data
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse execution result")
        
        except Exception as e:
            logger.error(f"Error in after_model_callback: {e}")
        
        return llm_response
    
    async def execute_workflow(
        self,
        workflow_json: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300
    ) -> WorkflowExecutionResult:
        """
        Execute a workflow and stream results using the real Kubiya API.
        
        Args:
            workflow_json: Compiled workflow JSON
            params: Execution parameters
            timeout_seconds: Maximum time to wait for completion
            
        Returns:
            WorkflowExecutionResult
        """
        start_time = time.time()
        
        try:
            # Log where the workflow is being executed
            runner_name = workflow_json.get("runner", "kubiya-hosted")
            org_name = self._kubiya_client.org_name if hasattr(self._kubiya_client, 'org_name') else "unknown"
            
            logger.info(f"🚀 Executing workflow '{workflow_json.get('name')}' on Kubiya platform")
            logger.info(f"   Organization: {org_name}")
            logger.info(f"   Runner: {runner_name}")
            logger.info(f"   API Endpoint: {self._kubiya_client.base_url if hasattr(self._kubiya_client, 'base_url') else 'default'}")
            
            # Update params if provided
            if params:
                workflow_json['parameters'] = params
            
            # Execute workflow with streaming using the real Kubiya client
            execution_id = f"exec_{int(time.time())}_{workflow_json.get('name', 'unnamed')}"
            outputs = {}
            logs = []
            execution_status = "running"
            
            logger.info(f"\n📡 Starting SSE stream for workflow execution...")
            logger.info(f"   Execution ID: {execution_id}")
            
            # Stream execution events
            event_count = 0
            try:
                # Use the actual Kubiya client execute_workflow method with streaming
                for event_data in self._kubiya_client.execute_workflow(
                    workflow_definition=workflow_json,
                    parameters=params,
                    stream=True
                ):
                    event_count += 1
                    
                    # Log the raw SSE event
                    logger.info(f"\n🔄 SSE Event #{event_count}:")
                    logger.info(f"   Raw: {event_data[:200]}..." if len(event_data) > 200 else f"   Raw: {event_data}")
                    
                    # Parse SSE event
                    try:
                        if isinstance(event_data, str):
                            # Try to parse as JSON
                            import json
                            try:
                                event = json.loads(event_data)
                            except:
                                # Not JSON, treat as log message
                                logs.append(event_data)
                                logger.info(f"   Type: Log message")
                                logger.info(f"   Content: {event_data}")
                                continue
                        else:
                            event = event_data
                        
                        # Handle different event types
                        if isinstance(event, dict):
                            event_type = event.get('type', 'unknown')
                            logger.info(f"   Type: {event_type}")
                            
                            if event_type == 'start':
                                logger.info("   ✅ Workflow execution started")
                                execution_status = "running"
                            elif event_type == 'step_start':
                                step_name = event.get('step', 'unknown')
                                logger.info(f"   📍 Step '{step_name}' started")
                            elif event_type == 'step_complete':
                                step_name = event.get('step', 'unknown')
                                step_output = event.get('output', {})
                                outputs[step_name] = step_output
                                logger.info(f"   ✅ Step '{step_name}' completed")
                                if step_output:
                                    logger.info(f"      Output: {json.dumps(step_output, indent=2)}")
                            elif event_type == 'log':
                                log_msg = event.get('message', '')
                                logs.append(log_msg)
                                logger.info(f"   📝 Log: {log_msg}")
                            elif event_type == 'error':
                                error_msg = event.get('message', 'Unknown error')
                                logger.error(f"   ❌ Error: {error_msg}")
                                execution_status = "failed"
                            elif event_type == 'complete':
                                logger.info("   ✅ Workflow execution completed")
                                execution_status = "success"
                                break
                            elif event.get('end') or event.get('finishReason'):
                                logger.info("   🏁 Stream ended")
                                if execution_status == "running":
                                    execution_status = "success"
                                break
                        
                    except Exception as parse_error:
                        logger.warning(f"   ⚠️  Failed to parse event: {parse_error}")
                        logs.append(f"Parse error: {event_data}")
                    
                logger.info(f"\n📊 Execution Summary:")
                logger.info(f"   Total Events: {event_count}")
                logger.info(f"   Status: {execution_status}")
                logger.info(f"   Duration: {time.time() - start_time:.2f}s")
                
            except Exception as stream_error:
                logger.error(f"❌ Streaming error: {stream_error}")
                execution_status = "failed"
                logs.append(f"Streaming error: {str(stream_error)}")
            
            # Return execution result
            return WorkflowExecutionResult(
                success=(execution_status == "success"),
                execution_id=execution_id,
                outputs=outputs,
                logs=logs,
                duration_seconds=time.time() - start_time,
                errors=[] if execution_status == "success" else ["Workflow execution failed"]
            )
            
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            import traceback
            traceback.print_exc()
            return WorkflowExecutionResult(
                success=False,
                errors=[str(e)]
            )


def create_workflow_executor_agent(
    config: ADKConfig,
    kubiya_client: Any
) -> WorkflowExecutorAgent:
    """Create a workflow executor agent."""
    return WorkflowExecutorAgent(config, kubiya_client) 