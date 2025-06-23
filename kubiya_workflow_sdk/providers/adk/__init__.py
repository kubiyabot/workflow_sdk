"""
Google ADK Provider for Kubiya Workflow SDK.

This provider uses Google's Agent Development Kit with Together AI models
to generate intelligent workflows using the SDK's Python API.
"""

# Import and check ADK availability
try:
    from google.adk import agents
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

# Only import if ADK is available
if ADK_AVAILABLE:
    from .provider import ADKProvider
    from .config import ADKConfig, ModelProvider
    from .agents import (
        create_workflow_generator_agent,
        create_compiler_agent,
        create_refinement_agent,
        create_orchestrator_agent
    )
    from .tools import KubiyaContextTools
    from .streaming import StreamHandler, SSEFormatter, VercelAIFormatter
    
    __all__ = [
        "ADKProvider",
        "ADKConfig",
        "ModelProvider",
        "KubiyaContextTools",
        "StreamHandler",
        "SSEFormatter",
        "VercelAIFormatter",
        "create_orchestrator_agent",
        "ADK_AVAILABLE"
    ]
else:
    # Provide dummy class for type hints
    class ADKProvider:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Google ADK is required for this provider. "
                "Install with: pip install kubiya-workflow-sdk[adk]"
            )
    
    __all__ = ["ADKProvider", "ADK_AVAILABLE"] 