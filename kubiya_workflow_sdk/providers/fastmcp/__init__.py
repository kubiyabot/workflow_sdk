"""
FastMCP Provider for Kubiya Workflow SDK.

This provider integrates with FastMCP servers to provide MCP tools,
prompts, and resources for workflow generation and execution.
"""

# Always make these available
from .config import FastMCPConfig

# Check if we can import the provider
try:
    from .provider import FastMCPProvider
    FASTMCP_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"FastMCP provider import failed: {e}")
    FASTMCP_AVAILABLE = False
    FastMCPProvider = None

__all__ = ["FastMCPConfig", "FastMCPProvider", "FASTMCP_AVAILABLE"]

# Export convenience functions
def create_fastmcp_provider(client=None, config=None):
    """Create a FastMCP provider instance."""
    if not FASTMCP_AVAILABLE:
        raise ImportError("FastMCP provider is not available. Check dependencies.")
    
    if config is None:
        config = FastMCPConfig()
    
    return FastMCPProvider(client=client, config=config) 