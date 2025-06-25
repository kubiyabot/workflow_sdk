"""
MCP (Model Context Protocol) integration for Kubiya Workflows.

This module provides tools for creating MCP servers that expose Kubiya workflow
functionality to any MCP-compatible client or agent framework.
"""

from .server import KubiyaMCPServer, create_server

# Legacy aliases for backward compatibility
KubiyaMCP = KubiyaMCPServer
create_mcp_server = create_server

__all__ = ["KubiyaMCPServer", "create_server", "KubiyaMCP", "create_mcp_server"]
