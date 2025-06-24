"""
MCP Client implementation for testing Kubiya MCP servers.

Compatible with FastMCP pattern for easy testing and integration.
"""

import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, Optional, Union, List
from pathlib import Path


class Client:
    """
    FastMCP-compatible client for Kubiya MCP servers.

    Can connect to:
    - A server object directly (for testing)
    - A Python file that runs an MCP server
    - A running MCP server via stdio/HTTP
    """

    def __init__(self, target: Union[str, object], transport: str = "direct"):
        """
        Initialize MCP client.

        Args:
            target: Server object, Python file path, or server URL
            transport: "direct", "stdio", or "http"
        """
        self.target = target
        self.transport = transport
        self.server = None
        self.process = None
        self._in_context = False

    async def __aenter__(self):
        """Enter async context."""
        self._in_context = True

        if self.transport == "direct" and hasattr(self.target, "call_tool"):
            # Direct server object
            self.server = self.target
        elif self.transport == "stdio" and isinstance(self.target, str):
            # Launch subprocess
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                self.target,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        self._in_context = False

        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self._in_context:
            raise RuntimeError("Client must be used within async context (async with client:)")

        arguments = arguments or {}

        if self.transport == "direct" and self.server:
            # Direct call to server object
            return await self.server.call_tool(tool_name, arguments)

        elif self.transport == "stdio" and self.process:
            # Send command via stdio
            command = {"method": "call_tool", "params": {"name": tool_name, "arguments": arguments}}

            # Write command
            self.process.stdin.write(json.dumps(command).encode() + b"\n")
            await self.process.stdin.drain()

            # Read response
            response_line = await self.process.stdout.readline()
            response = json.loads(response_line.decode())

            return response.get("result")

        else:
            raise ValueError(f"Unsupported transport: {self.transport}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server."""
        if self.transport == "direct" and self.server:
            return self.server.list_tools()
        else:
            # Would implement stdio/HTTP protocol
            return []

    async def define_workflow(self, name: str, code: str, description: str = "") -> Dict[str, Any]:
        """
        Define a workflow from Python code.

        Convenience method that calls the define_workflow tool.
        """
        return await self.call_tool(
            "define_workflow", {"name": name, "code": code, "description": description}
        )

    async def execute_workflow(
        self, name: str, params: Optional[Dict[str, Any]] = None, stream: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a workflow.

        Convenience method that calls the execute_workflow tool.
        """
        return await self.call_tool(
            "execute_workflow", {"name": name, "params": params or {}, "stream": stream}
        )

    async def query_graphql(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query.

        Convenience method that calls the graphql_query tool.
        """
        return await self.call_tool("graphql_query", {"query": query, "variables": variables or {}})


# Convenience function for quick testing
async def test_server(server_or_path: Union[str, object], test_code: str = None):
    """
    Quick test function for MCP servers.

    Example:
        await test_server(mcp_server, '''
            @workflow(name="test")
            def test_workflow():
                return step("hello").shell("echo Hello World")
        ''')
    """
    transport = "direct" if hasattr(server_or_path, "call_tool") else "stdio"
    client = Client(server_or_path, transport=transport)

    async with client:
        # List tools
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        if test_code:
            # Define workflow
            result = await client.define_workflow("test", test_code)
            print(f"\nWorkflow defined: {result}")

            if result.get("success"):
                # Execute it
                exec_result = await client.execute_workflow("test")
                print(f"Execution result: {exec_result}")

        # Try GraphQL if available
        try:
            gql_result = await client.query_graphql("{ workflows { name steps { name } } }")
            print(f"\nGraphQL query result: {gql_result}")
        except:
            print("\nGraphQL not available")


__all__ = ["Client", "test_server"]
