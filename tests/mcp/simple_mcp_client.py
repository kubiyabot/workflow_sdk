"""Simple MCP client for testing that implements proper JSON-RPC protocol."""

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional
import uuid


class SimpleMCPClient:
    """Simple MCP client that implements JSON-RPC 2.0 protocol."""
    
    def __init__(self, server_script: str):
        """Initialize client with path to server script."""
        self.server_script = server_script
        self.process: Optional[subprocess.Popen] = None
        self.initialized = False
        
    async def __aenter__(self):
        """Start the server process."""
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            self.server_script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Initialize the MCP session
        await self._initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            
    async def _send_request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        if not self.process:
            raise RuntimeError("Client not started")
            
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params is not None:
            request["params"] = params
            
        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from server")
            
        try:
            response = json.loads(response_line.decode().strip())
        except json.JSONDecodeError as e:
            stderr_data = await self.process.stderr.read()
            raise RuntimeError(f"Invalid JSON response: {e}. Stderr: {stderr_data.decode()}")
            
        # Check for errors
        if "error" in response:
            error = response["error"]
            raise RuntimeError(f"MCP Error {error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}")
            
        return response.get("result", {})
        
    async def _initialize(self):
        """Initialize the MCP session."""
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        
        self.initialized = True
        return result
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        if not self.initialized:
            raise RuntimeError("Client not initialized")
            
        result = await self._send_request("tools/list")
        return result.get("tools", [])
        
    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool."""
        if not self.initialized:
            raise RuntimeError("Client not initialized")
            
        params = {
            "name": name,
            "arguments": arguments or {}
        }
        
        result = await self._send_request("tools/call", params)
        return result