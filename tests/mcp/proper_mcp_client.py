"""Proper MCP client using the official MCP library."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ProperMCPClient:
    """MCP client using the official MCP library."""

    def __init__(self, server_script: str):
        """Initialize client with path to server script."""
        self.server_script = server_script
        self.server_params = StdioServerParameters(command=sys.executable, args=[server_script])

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        """Connect to the MCP server and return a session."""
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                init_result = await session.initialize()
                yield session

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        async with self.connect() as session:
            result = await session.list_tools()
            return [tool.model_dump() for tool in result.tools]

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool and return the result."""
        async with self.connect() as session:
            result = await session.call_tool(name, arguments or {})
            return [content.model_dump() for content in result.content]

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts."""
        async with self.connect() as session:
            result = await session.list_prompts()
            return [prompt.model_dump() for prompt in result.prompts]

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a prompt."""
        async with self.connect() as session:
            result = await session.get_prompt(name, arguments or {})
            return result.model_dump()

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources."""
        async with self.connect() as session:
            result = await session.list_resources()
            return [resource.model_dump() for resource in result.resources]

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource."""
        async with self.connect() as session:
            result = await session.read_resource(uri)
            return result.model_dump()
