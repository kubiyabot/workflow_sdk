"""
ADK Provider for Kubiya Workflow SDK.

This provider uses AI agents to generate Kubiya workflows.
"""

# Always make these available
from .config import ADKConfig

# Check if we can import the provider
try:
    from .provider import ADKProvider
    ADK_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"ADK provider import failed: {e}")
    ADK_AVAILABLE = False
    ADKProvider = None

__all__ = ["ADKConfig", "ADKProvider", "ADK_AVAILABLE"]

# Export convenience functions
def create_adk_provider(client=None, config=None):
    """Create an ADK provider instance."""
    if not ADK_AVAILABLE:
        raise ImportError("ADK provider is not available. Check dependencies.")
    
    if config is None:
        config = ADKConfig()
    
    return ADKProvider(client=client, config=config) 