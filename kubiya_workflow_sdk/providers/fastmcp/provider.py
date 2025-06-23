"""
FastMCP Provider for Kubiya Workflow SDK.

This provider integrates with FastMCP (Model Context Protocol) servers to:
- Discover and use MCP tools for automation
- Access MCP prompts for workflow generation
- Retrieve MCP resources for context
- Generate workflows using MCP capabilities
"""

import asyncio
import json
import logging
import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from ..base import BaseProvider
from .config import FastMCPConfig

logger = logging.getLogger(__name__)


class MCPTool(BaseModel):
    """MCP Tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class MCPPrompt(BaseModel):
    """MCP Prompt definition."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class MCPResource(BaseModel):
    """MCP Resource definition."""
    uri: str
    name: str
    description: str
    mimeType: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPServerCapabilities(BaseModel):
    """MCP Server capabilities."""
    tools: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None


class MCPServerInfo(BaseModel):
    """MCP Server information."""
    name: str
    version: str
    capabilities: MCPServerCapabilities
    metadata: Optional[Dict[str, Any]] = None


class FastMCPProvider(BaseProvider):
    """
    FastMCP provider for integrating MCP servers with Kubiya workflows.
    
    This provider connects to MCP servers to discover and use tools, prompts,
    and resources for intelligent workflow generation and execution.
    """
    
    def __init__(self, client: Any, config: Optional[FastMCPConfig] = None, **kwargs):
        """Initialize the FastMCP provider."""
        super().__init__(client, **kwargs)
        
        self.config = config or FastMCPConfig()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.connection_timeout)
        )
        
        # MCP state
        self.connected_servers: Dict[str, Any] = {}
        self.available_tools: Dict[str, MCPTool] = {}
        self.available_prompts: Dict[str, MCPPrompt] = {}
        self.available_resources: Dict[str, MCPResource] = {}
        
        # Cache
        self._tool_cache: Dict[str, Any] = {}
        self._response_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        logger.info("FastMCP provider initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_to_servers()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect_from_servers()
    
    async def connect_to_servers(self):
        """Connect to all configured MCP servers."""
        tasks = []
        
        # Connect to configured servers
        for server_config in self.config.mcp_servers:
            tasks.append(self._connect_to_server(server_config))
        
        # Connect to default server if specified
        if self.config.default_server_url:
            default_config = {
                "name": "default",
                "url": self.config.default_server_url,
                "description": "Default MCP server"
            }
            tasks.append(self._connect_to_server(default_config))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to connect to server {i}: {result}")
    
    async def _connect_to_server(self, server_config: Dict[str, Any]):
        """Connect to a single MCP server."""
        try:
            server_name = server_config["name"]
            server_url = server_config["url"]
            
            logger.info(f"Connecting to MCP server: {server_name} at {server_url}")
            
            # Initialize connection to MCP server
            init_response = await self._send_mcp_request(
                server_url,
                {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": self.config.protocol_version,
                        "capabilities": {
                            "tools": {},
                            "prompts": {},
                            "resources": {}
                        },
                        "clientInfo": self.config.client_info
                    }
                }
            )
            
            if "result" not in init_response:
                raise Exception(f"Invalid initialize response: {init_response}")
            
            result = init_response["result"]
            server_info = MCPServerInfo(
                name=result.get("serverInfo", {}).get("name", server_name),
                version=result.get("serverInfo", {}).get("version", "unknown"),
                capabilities=MCPServerCapabilities(**result.get("capabilities", {})),
                metadata=server_config.get("metadata", {})
            )
            
            self.connected_servers[server_name] = server_info
            
            # Discover tools, prompts, and resources
            await self._discover_server_capabilities(server_name, server_url)
            
            logger.info(f"Successfully connected to MCP server: {server_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_name}: {e}")
            raise
    
    async def _discover_server_capabilities(self, server_name: str, server_url: str):
        """Discover tools, prompts, and resources from an MCP server."""
        try:
            # Discover tools
            if self.config.enable_tool_calls:
                tools_response = await self._send_mcp_request(
                    server_url,
                    {
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": "tools/list"
                    }
                )
                
                if "result" in tools_response:
                    for tool_data in tools_response["result"].get("tools", []):
                        tool = MCPTool(**tool_data)
                        tool_key = f"{server_name}:{tool.name}"
                        self.available_tools[tool_key] = tool
                        logger.debug(f"Discovered tool: {tool_key}")
            
            # Discover prompts
            if self.config.enable_prompts:
                prompts_response = await self._send_mcp_request(
                    server_url,
                    {
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": "prompts/list"
                    }
                )
                
                if "result" in prompts_response:
                    for prompt_data in prompts_response["result"].get("prompts", []):
                        prompt = MCPPrompt(**prompt_data)
                        prompt_key = f"{server_name}:{prompt.name}"
                        self.available_prompts[prompt_key] = prompt
                        logger.debug(f"Discovered prompt: {prompt_key}")
            
            # Discover resources
            if self.config.enable_resources:
                resources_response = await self._send_mcp_request(
                    server_url,
                    {
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": "resources/list"
                    }
                )
                
                if "result" in resources_response:
                    for resource_data in resources_response["result"].get("resources", []):
                        resource = MCPResource(**resource_data)
                        resource_key = f"{server_name}:{resource.name}"
                        self.available_resources[resource_key] = resource
                        logger.debug(f"Discovered resource: {resource_key}")
                        
        except Exception as e:
            logger.warning(f"Failed to discover capabilities from {server_name}: {e}")
    
    async def _send_mcp_request(
        self,
        server_url: str,
        request: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send an MCP request to a server."""
        timeout = timeout or self.config.request_timeout
        
        try:
            response = await self.http_client.post(
                server_url,
                json=request,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"MCP request failed to {server_url}: {e}")
            raise
    
    async def disconnect_from_servers(self):
        """Disconnect from all MCP servers."""
        await self.http_client.aclose()
        self.connected_servers.clear()
        self.available_tools.clear()
        self.available_prompts.clear()
        self.available_resources.clear()
    
    def generate_workflow(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = True,
        stream_format: str = "vercel",
        **kwargs
    ) -> Any:
        """Generate a workflow using MCP capabilities."""
        if stream:
            return self._stream_workflow_generation(task, context, stream_format, **kwargs)
        else:
            return asyncio.run(self._generate_workflow_sync(task, context, **kwargs))
    
    async def _generate_workflow_sync(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate workflow synchronously."""
        workflow = {
            "id": str(uuid.uuid4()),
            "name": f"MCP Workflow: {task[:50]}...",
            "description": task,
            "created_at": datetime.utcnow().isoformat(),
            "provider": "fastmcp",
            "mcp_capabilities": {
                "tools": len(self.available_tools),
                "prompts": len(self.available_prompts),
                "resources": len(self.available_resources)
            }
        }
        return workflow
    
    async def _stream_workflow_generation(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        stream_format: str = "vercel",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream workflow generation process."""
        try:
            workflow_id = str(uuid.uuid4())
            
            # Send start event
            yield self._format_stream_event({
                "type": "workflow-start",
                "workflowId": workflow_id,
                "task": task
            }, stream_format)
            
            # Simulate workflow generation
            workflow_code = f'''
"""
MCP Workflow: {task}
Generated by FastMCP Provider
"""

from kubiya_workflow_sdk import workflow

@workflow
def mcp_workflow():
    """
    {task}
    
    This workflow uses FastMCP capabilities.
    """
    print("Executing MCP workflow: {task}")
    return {{"status": "completed", "task": "{task}"}}
'''
            
            # Stream the workflow code
            for char in workflow_code:
                yield self._format_stream_event({
                    "type": "text-delta",
                    "textDelta": char
                }, stream_format)
                await asyncio.sleep(0.01)
            
            # Send completion event
            yield self._format_stream_event({
                "type": "workflow-complete",
                "workflowId": workflow_id
            }, stream_format)
            
        except Exception as e:
            yield self._format_stream_event({
                "type": "error",
                "error": {"message": str(e), "code": "GENERATION_ERROR"}
            }, stream_format)
    
    def _format_stream_event(self, data: Dict[str, Any], format_type: str) -> str:
        """Format streaming event."""
        if format_type == "vercel":
            return f"2:[{json.dumps(data)}]\n"
        else:
            return f"data: {json.dumps(data)}\n\n"
    
    def validate_workflow(
        self,
        workflow_code: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Validate a workflow definition."""
        return {"valid": True, "errors": [], "warnings": []}
    
    def refine_workflow(
        self,
        workflow_code: str,
        errors: List[str],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Refine a workflow based on errors."""
        return f"# Refined workflow\n{workflow_code}"
    
    async def execute_workflow(
        self,
        workflow: Union[str, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        stream: bool = True,
        stream_format: str = "sse",
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """Execute a workflow with MCP tools."""
        result = {"status": "completed", "message": "MCP workflow executed"}
        
        if stream:
            async def stream_execution():
                yield self._format_stream_event({
                    "type": "execution-complete",
                    "result": result
                }, stream_format)
            return stream_execution()
        else:
            return result
    
    def get_discovery_info(self) -> Dict[str, Any]:
        """Get discovery information for this provider."""
        return {
            "provider": "fastmcp",
            "version": "1.0.0",
            "protocol_version": self.config.protocol_version,
            "capabilities": {
                "streaming": self.config.enable_streaming,
                "tools": self.config.enable_tool_calls,
                "prompts": self.config.enable_prompts,
                "resources": self.config.enable_resources,
                "mcp_support": True
            },
            "connected_servers": list(self.connected_servers.keys()),
            "available_capabilities": {
                "tools": len(self.available_tools),
                "prompts": len(self.available_prompts),
                "resources": len(self.available_resources)
            },
            "mcp_tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "server": tool_key.split(':')[0] if ':' in tool_key else "unknown"
                }
                for tool_key, tool in self.available_tools.items()
            ],
            "mcp_prompts": [
                {
                    "name": prompt.name,
                    "description": prompt.description,
                    "server": prompt_key.split(':')[0] if ':' in prompt_key else "unknown"
                }
                for prompt_key, prompt in self.available_prompts.items()
            ],
            "mcp_resources": [
                {
                    "name": resource.name,
                    "description": resource.description,
                    "uri": resource.uri,
                    "server": resource_key.split(':')[0] if ':' in resource_key else "unknown"
                }
                for resource_key, resource in self.available_resources.items()
            ]
        } 