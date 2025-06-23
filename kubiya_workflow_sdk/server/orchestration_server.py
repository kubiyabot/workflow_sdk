"""
Orchestration Server for Kubiya Workflow SDK

Extends the base server with orchestration provider support:
- Multiple provider modes (ADK, MCP, etc.)
- Compose endpoint for intelligent workflow generation
- Vercel AI SDK streaming format
- Decoupled generation, execution, and composition endpoints
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
import asyncio
import json
import uuid
import logging
from datetime import datetime
from enum import Enum

from .app import WorkflowServer
from .models import BaseRequest, BaseResponse
from ..providers import get_provider, ProviderType
from ..providers.adk import ADKProvider, ADKConfig
from ..client import KubiyaClient

logger = logging.getLogger(__name__)


class ProviderMode(str, Enum):
    """Available orchestration provider modes."""
    ADK = "adk"
    MCP = "mcp"
    BASIC = "basic"


class ComposeRequest(BaseModel):
    """Request model for workflow composition."""
    task: str = Field(..., description="Task description or requirements")
    mode: ProviderMode = Field(ProviderMode.ADK, description="Provider mode to use")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Execution parameters")
    execute: bool = Field(False, description="Execute after generation")
    stream: bool = Field(True, description="Enable streaming response")
    stream_format: str = Field("vercel", description="Streaming format (vercel or sse)")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    user_id: Optional[str] = Field(None, description="User ID for personalization")


class GenerateRequest(BaseModel):
    """Request model for workflow generation."""
    task: str = Field(..., description="Task description")
    mode: ProviderMode = Field(ProviderMode.ADK, description="Provider mode")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    stream: bool = Field(True, description="Enable streaming")
    stream_format: str = Field("vercel", description="Streaming format")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")


class ExecuteRequest(BaseModel):
    """Request model for workflow execution."""
    workflow: Union[str, Dict[str, Any]] = Field(..., description="Workflow to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Execution parameters")
    mode: ProviderMode = Field(ProviderMode.ADK, description="Provider mode")
    stream: bool = Field(True, description="Enable streaming")
    stream_format: str = Field("vercel", description="Streaming format")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")


class RefineRequest(BaseModel):
    """Request model for workflow refinement."""
    workflow_code: str = Field(..., description="Workflow code to refine")
    errors: List[str] = Field(..., description="Errors to fix")
    mode: ProviderMode = Field(ProviderMode.ADK, description="Provider mode")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    stream: bool = Field(True, description="Enable streaming")
    stream_format: str = Field("vercel", description="Streaming format")


class OrchestrationServer(WorkflowServer):
    """Extended server with orchestration provider support."""
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        default_mode: ProviderMode = ProviderMode.ADK,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.providers = providers or {}
        self.default_mode = default_mode
        
        # Initialize providers
        self._init_providers()
        
        # Register additional routes
        self._register_orchestration_routes()
    
    def _init_providers(self):
        """Initialize orchestration providers."""
        # Initialize ADK provider if not provided
        if ProviderMode.ADK not in self.providers:
            try:
                # Create Kubiya client
                client = KubiyaClient()
                
                # Create ADK config
                config = ADKConfig(
                    execute_workflows=False,  # Don't execute during generation
                    max_loop_iterations=3,
                    enable_streaming=True
                )
                
                # Create ADK provider
                self.providers[ProviderMode.ADK] = ADKProvider(
                    client=client,
                    config=config
                )
                logger.info("Initialized ADK provider")
            except Exception as e:
                logger.warning(f"Failed to initialize ADK provider: {e}")
    
    def _register_orchestration_routes(self):
        """Register orchestration-specific routes."""
        
        @self.app.post(
            f"{self.api_prefix}/compose",
            summary="Compose a workflow",
            description="Intelligently compose a workflow using orchestration providers"
        )
        async def compose_workflow(request: ComposeRequest):
            """Compose a workflow using the specified provider mode."""
            try:
                provider = self.providers.get(request.mode)
                if not provider:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Provider mode '{request.mode}' not available"
                    )
                
                if request.stream:
                    # Return streaming response
                    return StreamingResponse(
                        self._stream_composition(provider, request),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                            "Access-Control-Allow-Origin": "*"
                        }
                    )
                else:
                    # Generate synchronously
                    workflow = await self._compose_workflow(provider, request)
                    return JSONResponse(content=workflow)
                    
            except Exception as e:
                logger.error(f"Composition failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post(
            f"{self.api_prefix}/generate",
            summary="Generate a workflow",
            description="Generate a workflow without execution"
        )
        async def generate_workflow(request: GenerateRequest):
            """Generate a workflow using the specified provider."""
            try:
                provider = self.providers.get(request.mode)
                if not provider:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Provider mode '{request.mode}' not available"
                    )
                
                if request.stream:
                    return StreamingResponse(
                        self._stream_generation(provider, request),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                            "Access-Control-Allow-Origin": "*"
                        }
                    )
                else:
                    workflow = provider.generate_workflow(
                        task=request.task,
                        context=request.context,
                        stream=False,
                        session_id=request.session_id,
                        user_id=request.user_id
                    )
                    return JSONResponse(content=workflow)
                    
            except Exception as e:
                logger.error(f"Generation failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post(
            f"{self.api_prefix}/execute",
            summary="Execute a workflow",
            description="Execute a pre-generated workflow"
        )
        async def execute_workflow(request: ExecuteRequest):
            """Execute a workflow using the specified provider."""
            try:
                provider = self.providers.get(request.mode)
                if not provider:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Provider mode '{request.mode}' not available"
                    )
                
                if request.stream:
                    return StreamingResponse(
                        self._stream_execution(provider, request),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                            "Access-Control-Allow-Origin": "*"
                        }
                    )
                else:
                    result = await provider.execute_workflow(
                        workflow=request.workflow,
                        parameters=request.parameters,
                        stream=False,
                        session_id=request.session_id,
                        user_id=request.user_id
                    )
                    return JSONResponse(content=result)
                    
            except Exception as e:
                logger.error(f"Execution failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post(
            f"{self.api_prefix}/refine",
            summary="Refine a workflow",
            description="Refine a workflow to fix errors"
        )
        async def refine_workflow(request: RefineRequest):
            """Refine a workflow using the specified provider."""
            try:
                provider = self.providers.get(request.mode)
                if not provider:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Provider mode '{request.mode}' not available"
                    )
                
                if hasattr(provider, 'refine_workflow'):
                    if request.stream:
                        return StreamingResponse(
                            self._stream_refinement(provider, request),
                            media_type="text/event-stream",
                            headers={
                                "Cache-Control": "no-cache",
                                "X-Accel-Buffering": "no",
                                "Access-Control-Allow-Origin": "*"
                            }
                        )
                    else:
                        result = provider.refine_workflow(
                            workflow_code=request.workflow_code,
                            errors=request.errors,
                            context=request.context,
                            stream=False
                        )
                        return JSONResponse(content=result)
                else:
                    raise HTTPException(
                        status_code=501,
                        detail=f"Provider '{request.mode}' does not support refinement"
                    )
                    
            except Exception as e:
                logger.error(f"Refinement failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get(
            f"{self.api_prefix}/providers",
            summary="List available providers",
            description="Get list of available orchestration providers"
        )
        async def list_providers():
            """List available orchestration providers."""
            providers_info = {}
            for mode, provider in self.providers.items():
                providers_info[mode] = {
                    "name": provider.__class__.__name__,
                    "available": True,
                    "features": {
                        "generation": True,
                        "execution": hasattr(provider, 'execute_workflow'),
                        "refinement": hasattr(provider, 'refine_workflow'),
                        "streaming": True
                    }
                }
            
            return {
                "providers": providers_info,
                "default": self.default_mode
            }
    
    async def _stream_composition(
        self,
        provider: Any,
        request: ComposeRequest
    ) -> AsyncGenerator[str, None]:
        """Stream workflow composition with optional execution."""
        try:
            # Check if provider has compose capability
            if hasattr(provider, 'compose'):
                # Stream directly from provider's compose method
                async for event in provider.compose(
                    task=request.task,
                    context=request.context,
                    parameters=request.parameters,
                    mode="act" if request.execute else "plan",
                    stream=True,
                    stream_format=request.stream_format,
                    session_id=request.session_id,
                    user_id=request.user_id
                ):
                    yield event
            else:
                # Fallback error for providers without compose
                error_msg = f"Provider '{request.provider}' does not support compose capability"
                if request.stream_format == "vercel":
                    error_event = {
                        "id": str(uuid.uuid4()),
                        "type": "error",
                        "error": {
                            "message": error_msg,
                            "code": "COMPOSE_NOT_SUPPORTED"
                        }
                    }
                else:
                    error_event = {
                        "event": "error",
                        "data": json.dumps({
                            "error": error_msg,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    }
                yield f"data: {json.dumps(error_event)}\n\n"
                        
        except Exception as e:
            # Format error according to stream format
            if request.stream_format == "vercel":
                error_event = {
                    "id": str(uuid.uuid4()),
                    "type": "error",
                    "error": {
                        "message": str(e),
                        "code": "COMPOSITION_ERROR"
                    }
                }
            else:
                error_event = {
                    "event": "error",
                    "data": json.dumps({
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    async def _stream_generation(
        self,
        provider: Any,
        request: GenerateRequest
    ) -> AsyncGenerator[str, None]:
        """Stream workflow generation."""
        async for event in provider.generate_workflow(
            task=request.task,
            context=request.context,
            stream=True,
            stream_format=request.stream_format,
            session_id=request.session_id,
            user_id=request.user_id
        ):
            yield event
    
    async def _stream_execution(
        self,
        provider: Any,
        request: ExecuteRequest
    ) -> AsyncGenerator[str, None]:
        """Stream workflow execution."""
        async for event in provider.execute_workflow(
            workflow=request.workflow,
            parameters=request.parameters,
            stream=True,
            stream_format=request.stream_format,
            session_id=request.session_id,
            user_id=request.user_id
        ):
            yield event
    
    async def _stream_refinement(
        self,
        provider: Any,
        request: RefineRequest
    ) -> AsyncGenerator[str, None]:
        """Stream workflow refinement."""
        async for event in provider.refine_workflow(
            workflow_code=request.workflow_code,
            errors=request.errors,
            context=request.context,
            stream=True,
            stream_format=request.stream_format
        ):
            yield event
    
    async def _compose_workflow(
        self,
        provider: Any,
        request: ComposeRequest
    ) -> Dict[str, Any]:
        """Compose workflow synchronously."""
        # Generate workflow
        workflow = provider.generate_workflow(
            task=request.task,
            context=request.context,
            stream=False,
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        result = {"workflow": workflow}
        
        # Execute if requested
        if request.execute and hasattr(provider, 'execute_workflow'):
            execution_result = await provider.execute_workflow(
                workflow=workflow,
                parameters=request.parameters,
                stream=False,
                session_id=request.session_id,
                user_id=request.user_id
            )
            result["execution"] = execution_result
        
        return result


def create_orchestration_server(**kwargs) -> OrchestrationServer:
    """Create an orchestration server instance."""
    return OrchestrationServer(**kwargs) 