"""Helper classes and utilities for MCP server testing."""

import asyncio
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from tests.mcp.proper_mcp_client import ProperMCPClient


class MCPTestServer:
    """Helper class to run MCP server in subprocess for testing."""

    def __init__(self, server_script: Optional[str] = None, debug: bool = False):
        """Initialize MCP test server helper.

        Args:
            server_script: Path to Python script that runs MCP server
            debug: Enable debug logging
        """
        self.server_script = server_script or self._create_server_script()
        self.debug = debug
        self.client: Optional[ProperMCPClient] = None

    def _create_server_script(self) -> str:
        """Create a temporary script to run the MCP server."""
        script_content = """#!/usr/bin/env python3
import sys
import asyncio
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from kubiya_workflow_sdk.mcp.server import create_server

async def main():
    server = create_server()
    await server.run_stdio()

if __name__ == "__main__":
    asyncio.run(main())
"""

        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            f.flush()
            return f.name

    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[ProperMCPClient, None]:
        """Get an MCP client connected to the test server."""
        client = ProperMCPClient(self.server_script)
        yield client

    async def call_tool(
        self, tool_name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call an MCP tool and return the result."""
        async with self.get_client() as client:
            return await client.call_tool(tool_name, arguments or {})

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the MCP server."""
        async with self.get_client() as client:
            return await client.list_tools()

    @property
    def is_running(self) -> bool:
        """Check if the server can respond to requests."""
        try:
            # Try a simple connection test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                task = loop.create_task(self._test_connection())
                return loop.run_until_complete(task)
            finally:
                loop.close()
        except Exception:
            return False

    async def _test_connection(self) -> bool:
        """Test if server is responsive."""
        try:
            async with self.get_client() as client:
                # Try to list tools as a connection test
                await client.list_tools()
                return True
        except Exception:
            return False

    @property
    def pid(self) -> Optional[int]:
        """Get the process ID - not applicable for stdio client."""
        return None


@asynccontextmanager
async def mcp_test_server(
    server_script: Optional[str] = None, debug: bool = False
) -> AsyncGenerator[MCPTestServer, None]:
    """Context manager for MCP test server lifecycle."""
    server = MCPTestServer(server_script=server_script, debug=debug)

    try:
        yield server
    finally:
        # Cleanup if needed
        if hasattr(server, "server_script") and server.server_script:
            try:
                Path(server.server_script).unlink(missing_ok=True)
            except Exception:
                pass


async def create_test_workflow_context() -> Dict[str, Any]:
    """Create test workflow context for MCP tool testing."""
    return {
        "workflow_name": "test_workflow",
        "runner_id": "test_runner",
        "api_key": "test_api_key",
        "base_url": "https://api.kubiya.ai/api/v1",
        "secrets": {"TEST_SECRET": "test_value"},
    }


def generate_test_dsl() -> str:
    """Generate a simple test DSL workflow."""
    return """
name: test_workflow
description: Simple test workflow
steps:
  - name: echo_step
    type: shell
    shell: echo "Hello, World!"
"""


def generate_complex_test_dsl() -> str:
    """Generate a complex test DSL workflow for advanced testing."""
    return """
name: complex_test_workflow
description: Complex test workflow with multiple steps
parameters:
  - name: message
    description: Message to echo
    type: string
    default: "Hello from complex workflow"
    
steps:
  - name: prepare
    type: shell
    shell: echo "Preparing workflow..."
    
  - name: process_message
    type: python
    code: |
      import os
      message = os.environ.get('message', 'default message')
      print(f"Processing: {message}")
      
  - name: finalize
    type: shell
    shell: echo "Workflow completed successfully"
    depends_on:
      - prepare
      - process_message
"""
