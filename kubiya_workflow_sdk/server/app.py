"""
Kubiya Workflow SDK Server

Professional REST API server with:
- SSE streaming for real-time workflow execution
- OpenAPI 3.0 specification
- Async execution support
- Keep-alive connections
- Comprehensive error handling
- Request validation
- Authentication support
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio
import json
import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import aiofiles
from sse_starlette.sse import EventSourceResponse

from ..core.types import WorkflowStatus, ExecutionResult
from ..client_v2 import StreamingKubiyaClient
from ..dsl_v2 import FlowWorkflow
from ..validation import validate_workflow as validate_workflow_func
from .models import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowStatusResponse,
    WorkflowValidationRequest,
    WorkflowValidationResponse,
    PythonExecutionRequest,
    ServerHealthResponse,
    ServerConfigResponse
)
from .execution_manager import ExecutionManager
from .sse_handler import SSEHandler
from .auth import auth, auth_required

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowServer:
    """Professional workflow execution server with SSE streaming."""
    
    def __init__(
        self,
        title: str = "Kubiya Workflow SDK Server",
        version: str = "2.0.0",
        description: str = "Enterprise-grade workflow execution server with SSE streaming",
        api_prefix: str = "/api/v2",
        enable_cors: bool = True,
        cors_origins: List[str] = ["*"],
        max_concurrent_executions: int = 100,
        execution_timeout: int = 3600,
        keep_alive_interval: int = 30
    ):
        self.title = title
        self.version = version
        self.description = description
        self.api_prefix = api_prefix
        self.max_concurrent_executions = max_concurrent_executions
        self.execution_timeout = execution_timeout
        self.keep_alive_interval = keep_alive_interval
        
        # Initialize components
        self.execution_manager = ExecutionManager(
            max_concurrent=max_concurrent_executions,
            default_timeout=execution_timeout
        )
        self.sse_handler = SSEHandler(keep_alive_interval=keep_alive_interval)
        
        # Create FastAPI app
        self.app = self._create_app(enable_cors, cors_origins)
    
    def _create_app(self, enable_cors: bool, cors_origins: List[str]) -> FastAPI:
        """Create and configure FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Manage application lifecycle."""
            # Startup
            logger.info(f"Starting {self.title} v{self.version}")
            await self.execution_manager.start()
            yield
            # Shutdown
            logger.info("Shutting down server")
            await self.execution_manager.stop()
        
        app = FastAPI(
            title=self.title,
            version=self.version,
            description=self.description,
            docs_url=f"{self.api_prefix}/docs",
            redoc_url=f"{self.api_prefix}/redoc",
            openapi_url=f"{self.api_prefix}/openapi.json",
            lifespan=lifespan
        )
        
        # Configure CORS
        if enable_cors:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI) -> None:
        """Register all API routes."""
        
        @app.get(f"{self.api_prefix}/health", response_model=ServerHealthResponse)
        async def health_check():
            """Check server health status."""
            return ServerHealthResponse(
                status="healthy",
                timestamp=datetime.utcnow(),
                version=self.version,
                active_executions=self.execution_manager.active_count,
                max_executions=self.max_concurrent_executions
            )
        
        @app.get(f"{self.api_prefix}/config", response_model=ServerConfigResponse)
        async def get_config(api_token: Optional[str] = Depends(auth)):
            """Get server configuration."""
            return ServerConfigResponse(
                version=self.version,
                api_prefix=self.api_prefix,
                max_concurrent_executions=self.max_concurrent_executions,
                execution_timeout=self.execution_timeout,
                keep_alive_interval=self.keep_alive_interval,
                features={
                    "sse_streaming": True,
                    "async_execution": True,
                    "python_execution": True,
                    "workflow_validation": True,
                    "authentication": api_token is not None
                }
            )
        
        @app.post(
            f"{self.api_prefix}/workflows/execute",
            response_model=WorkflowExecutionResponse,
            summary="Execute a workflow",
            description="Execute a workflow with optional SSE streaming for real-time updates"
        )
        async def execute_workflow(
            request: WorkflowExecutionRequest,
            background_tasks: BackgroundTasks,
            stream: bool = True,
            api_token: Optional[str] = Depends(auth)
        ):
            """Execute a workflow with optional streaming."""
            try:
                
                # Generate execution ID
                execution_id = str(uuid.uuid4())
                
                # Start execution
                if stream:
                    # Return SSE stream
                    return EventSourceResponse(
                        self._stream_workflow_execution(
                            execution_id,
                            request.workflow,
                            request.parameters,
                            api_token
                        ),
                        headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                            "X-Execution-ID": execution_id
                        }
                    )
                else:
                    # Execute in background
                    background_tasks.add_task(
                        self._execute_workflow_background,
                        execution_id,
                        request.workflow,
                        request.parameters,
                        api_token
                    )
                    
                    return WorkflowExecutionResponse(
                        execution_id=execution_id,
                        status=WorkflowStatus.PENDING,
                        message="Workflow execution started",
                        stream_url=f"{self.api_prefix}/workflows/executions/{execution_id}/stream"
                    )
                    
            except Exception as e:
                logger.error(f"Workflow execution failed: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @app.get(
            f"{self.api_prefix}/workflows/executions/{{execution_id}}",
            response_model=WorkflowStatusResponse
        )
        async def get_execution_status(execution_id: str):
            """Get workflow execution status."""
            result = await self.execution_manager.get_execution(execution_id)
            if not result:
                raise HTTPException(status_code=404, detail="Execution not found")
            
            return WorkflowStatusResponse(
                execution_id=execution_id,
                status=result.status,
                start_time=result.start_time,
                end_time=result.end_time,
                duration_seconds=result.duration_seconds,
                outputs=result.outputs,
                errors=result.errors,
                step_count=len(result.step_results),
                completed_steps=sum(1 for r in result.step_results.values() if r.is_finished)
            )
        
        @app.get(f"{self.api_prefix}/workflows/executions/{{execution_id}}/stream")
        async def stream_execution(execution_id: str):
            """Stream workflow execution events via SSE."""
            result = await self.execution_manager.get_execution(execution_id)
            if not result:
                raise HTTPException(status_code=404, detail="Execution not found")
            
            return EventSourceResponse(
                self._replay_execution_events(execution_id),
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        
        @app.post(
            f"{self.api_prefix}/workflows/validate",
            response_model=WorkflowValidationResponse
        )
        async def validate_workflow(request: WorkflowValidationRequest):
            """Validate a workflow definition."""
            try:
                # Validate workflow directly
                validation_result = validate_workflow_func(request.workflow)
                
                return WorkflowValidationResponse(
                    valid=validation_result.valid,
                    errors=validation_result.errors,
                    warnings=validation_result.warnings if hasattr(validation_result, 'warnings') else [],
                    info=validation_result.info if hasattr(validation_result, 'info') else []
                )
                
            except Exception as e:
                return WorkflowValidationResponse(
                    valid=False,
                    errors=[str(e)],
                    warnings=[],
                    info=[]
                )
        
        @app.post(
            f"{self.api_prefix}/python/execute",
            summary="Execute Python code",
            description="Execute Python code and stream results via SSE"
        )
        async def execute_python(
            request: PythonExecutionRequest,
            stream: bool = True
        ):
            """Execute Python code with optional streaming."""
            try:
                execution_id = str(uuid.uuid4())
                
                if stream:
                    return EventSourceResponse(
                        self._stream_python_execution(
                            execution_id,
                            request.code,
                            request.context
                        ),
                        headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                            "X-Execution-ID": execution_id
                        }
                    )
                else:
                    # Execute synchronously
                    result = await self._execute_python_code(
                        request.code,
                        request.context
                    )
                    return JSONResponse(content=result)
                    
            except Exception as e:
                logger.error(f"Python execution failed: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @app.delete(f"{self.api_prefix}/workflows/executions/{{execution_id}}")
        async def cancel_execution(execution_id: str):
            """Cancel a running workflow execution."""
            success = await self.execution_manager.cancel_execution(execution_id)
            if not success:
                raise HTTPException(status_code=404, detail="Execution not found")
            
            return {"message": "Execution cancelled", "execution_id": execution_id}
        
        @app.get(f"{self.api_prefix}/workflows/executions")
        async def list_executions(
            status: Optional[WorkflowStatus] = None,
            limit: int = 100,
            offset: int = 0
        ):
            """List workflow executions."""
            executions = await self.execution_manager.list_executions(
                status=status,
                limit=limit,
                offset=offset
            )
            
            return {
                "executions": [e.to_dict() for e in executions],
                "total": len(executions),
                "limit": limit,
                "offset": offset
            }
    
    async def _stream_workflow_execution(
        self,
        execution_id: str,
        workflow_dict: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        api_token: Optional[str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream workflow execution events."""
        try:
            # Create client
            client = StreamingKubiyaClient(api_token=api_token)
            
            # Start execution
            async for event in client.execute_workflow_stream(
                workflow=workflow_dict,
                params=parameters
            ):
                # Transform and yield events
                yield {
                    "event": event.get("type", "update"),
                    "data": json.dumps({
                        "execution_id": execution_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        **event
                    })
                }
                
                # Keep alive
                if event.get("type") == "keep-alive":
                    continue
                    
                # Store event
                await self.execution_manager.add_event(execution_id, event)
                
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "execution_id": execution_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
    
    async def _stream_python_execution(
        self,
        execution_id: str,
        code: str,
        context: Optional[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream Python code execution."""
        try:
            # Create execution context
            exec_context = context or {}
            exec_globals = {"__name__": "__main__"}
            exec_globals.update(exec_context)
            
            # Capture output
            import io
            import sys
            
            output_buffer = io.StringIO()
            error_buffer = io.StringIO()
            
            # Redirect stdout/stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            sys.stdout = output_buffer
            sys.stderr = error_buffer
            
            try:
                # Execute code
                exec(code, exec_globals)
                
                # Yield output
                output = output_buffer.getvalue()
                if output:
                    yield {
                        "event": "output",
                        "data": json.dumps({
                            "execution_id": execution_id,
                            "type": "stdout",
                            "content": output,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    }
                
                # Yield success
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "execution_id": execution_id,
                        "status": "success",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
                
            except Exception as e:
                # Yield error
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "execution_id": execution_id,
                        "error": str(e),
                        "traceback": error_buffer.getvalue(),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
                
            finally:
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
        except Exception as e:
            logger.error(f"Python execution error: {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "execution_id": execution_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
    
    async def _execute_python_code(
        self,
        code: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute Python code synchronously."""
        exec_context = context or {}
        exec_globals = {"__name__": "__main__"}
        exec_globals.update(exec_context)
        
        try:
            exec(code, exec_globals)
            return {
                "status": "success",
                "outputs": {k: v for k, v in exec_globals.items() if not k.startswith("__")}
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _execute_workflow_background(
        self,
        execution_id: str,
        workflow_dict: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
        api_token: Optional[str]
    ) -> None:
        """Execute workflow in background."""
        try:
            client = StreamingKubiyaClient(api_token=api_token)
            result = await client.execute_workflow_async(
                workflow=workflow_dict,
                params=parameters
            )
            
            await self.execution_manager.store_result(execution_id, result)
            
        except Exception as e:
            logger.error(f"Background execution failed: {str(e)}")
            # Store error result
            error_result = ExecutionResult(
                execution_id=execution_id,
                workflow_name=workflow_dict.get("name", "unknown"),
                status=WorkflowStatus.FAILED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                errors=[str(e)]
            )
            await self.execution_manager.store_result(execution_id, error_result)
    
    async def _replay_execution_events(
        self,
        execution_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Replay execution events for reconnection."""
        events = await self.execution_manager.get_events(execution_id)
        
        for event in events:
            yield {
                "event": event.get("type", "replay"),
                "data": json.dumps(event)
            }
        
        # Continue with keep-alive
        while True:
            await asyncio.sleep(self.keep_alive_interval)
            yield {
                "event": "keep-alive",
                "data": json.dumps({
                    "execution_id": execution_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """Run the server."""
        import uvicorn
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            **kwargs
        )


# Create default server instance
def create_server(**kwargs) -> WorkflowServer:
    """Create a workflow server instance."""
    return WorkflowServer(**kwargs)


# Export for direct usage
__all__ = [
    "WorkflowServer",
    "create_server"
] 