"""
Base provider class for Kubiya Workflow SDK.

All providers must extend this base class and implement
the required methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncGenerator


class BaseProvider(ABC):
    """
    Abstract base class for workflow providers.
    
    Providers extend the Kubiya SDK with capabilities to generate,
    validate, refine, and execute workflows using various approaches
    (AI agents, templates, etc.)
    """
    
    def __init__(self, client: Any, **kwargs):
        """
        Initialize the provider.
        
        Args:
            client: Kubiya SDK client instance
            **kwargs: Provider-specific configuration
        """
        self.client = client
        self.config = kwargs
    
    @abstractmethod
    def generate_workflow(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Generate a workflow based on the task description.
        
        Args:
            task: Task description or requirements
            context: Additional context for generation
            **kwargs: Provider-specific options
            
        Returns:
            Generated workflow (dict or streaming response)
        """
        pass
    
    @abstractmethod
    def validate_workflow(
        self,
        workflow_code: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Validate a workflow definition.
        
        Args:
            workflow_code: Workflow code or definition to validate
            context: Additional validation context
            **kwargs: Provider-specific options
            
        Returns:
            Validation result with errors and warnings
        """
        pass
    
    @abstractmethod
    def refine_workflow(
        self,
        workflow_code: str,
        errors: List[str],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Refine a workflow based on errors or feedback.
        
        Args:
            workflow_code: Current workflow code
            errors: List of errors to fix
            context: Additional context
            **kwargs: Provider-specific options
            
        Returns:
            Refined workflow
        """
        pass
    
    async def execute_workflow(
        self,
        workflow: Union[str, Dict[str, Any]],
        parameters: Optional[Dict[str, Any]] = None,
        stream: bool = True,
        stream_format: str = "sse",
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Execute a workflow with optional streaming.
        
        Args:
            workflow: Workflow dict or name/ID
            parameters: Workflow execution parameters
            stream: Enable streaming response
            stream_format: Streaming format ("sse" or "vercel")
            **kwargs: Provider-specific options
            
        Returns:
            Execution result or streaming response
        """
        raise NotImplementedError("Workflow execution not implemented for this provider") 