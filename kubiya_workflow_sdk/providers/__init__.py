"""
Kubiya Workflow SDK Providers.

This module provides extensible providers for workflow generation
using various AI frameworks and approaches.
"""

from typing import Dict, Type, Any, Optional
import logging

from .base import BaseProvider

logger = logging.getLogger(__name__)

# Provider registry
_providers: Dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]) -> None:
    """
    Register a workflow provider.
    
    Args:
        name: Provider name (e.g., "adk", "langchain", etc.)
        provider_class: Provider class that extends BaseProvider
    """
    if not issubclass(provider_class, BaseProvider):
        raise ValueError(f"Provider {provider_class} must extend BaseProvider")
    
    _providers[name] = provider_class
    logger.info(f"Registered provider: {name}")


def get_provider(name: str, client: Any, **kwargs) -> BaseProvider:
    """
    Get a provider instance by name.
    
    Args:
        name: Provider name
        client: Kubiya SDK client
        **kwargs: Provider-specific configuration
        
    Returns:
        Provider instance
        
    Raises:
        ValueError: If provider not found
    """
    if name not in _providers:
        raise ValueError(
            f"Provider '{name}' not found. Available providers: {list(_providers.keys())}"
        )
    
    provider_class = _providers[name]
    return provider_class(client=client, **kwargs)


def list_providers() -> list[str]:
    """Get list of available provider names."""
    return list(_providers.keys())


# Auto-register built-in providers
try:
    from .adk import ADKProvider, ADK_AVAILABLE
    if ADK_AVAILABLE:
        register_provider("adk", ADKProvider)
    else:
        logger.debug("ADK provider not registered - Google ADK not available")
except ImportError as e:
    logger.debug(f"ADK provider not available: {e}")

# Re-export for convenience
__all__ = [
    "BaseProvider",
    "register_provider", 
    "get_provider",
    "list_providers",
]

# Export ADK provider if available
try:
    from .adk import ADKProvider
    __all__.append("ADKProvider")
except ImportError:
    pass 