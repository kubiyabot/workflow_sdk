"""Kubiya MCP Server - Legacy compatibility wrapper.

This module provides backward compatibility. 
Use kubiya_workflow_sdk.mcp.server package directly for new code.
"""

import warnings
from .server import (
    KubiyaMCPServer,
    create_server
)

warnings.warn(
    "Importing from kubiya_workflow_sdk.mcp.server is deprecated. "
    "Use kubiya_workflow_sdk.mcp.server package directly.",
    DeprecationWarning,
    stacklevel=2
)

# Legacy exports
__all__ = [
    "KubiyaMCPServer",
    "create_server"
]
