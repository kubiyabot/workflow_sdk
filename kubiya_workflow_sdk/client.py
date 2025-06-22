"""Kubiya API client for workflow operations."""

import json
import time
import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Generator, Union, AsyncGenerator
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .core.exceptions import (
    APIError as KubiyaAPIError,
    WorkflowExecutionError,
    ConnectionError as KubiyaConnectionError,
    WorkflowTimeoutError as KubiyaTimeoutError,
    AuthenticationError as KubiyaAuthenticationError,
    WorkflowError as WorkflowNotFoundError
)
from .core.types import WorkflowStatus

logger = logging.getLogger(__name__)


class StreamingKubiyaClient:
    """Async streaming client for real-time workflow execution with the Kubiya API."""
    
    def __init__(
        self,
        api_token: str,
        base_url: str = "https://api.kubiya.ai",
        runner: str = "core-testing-2",
        timeout: int = 300,
        max_retries: int = 3
    ):
        """Initialize the streaming Kubiya client.
        
        Args:
            api_token: Kubiya API token (note: using api_token for compatibility)
            base_url: Base URL for the Kubiya API
            runner: Kubiya runner instance name
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        self.runner = runner
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Default headers - Use UserKey format for API key authentication
        self.headers = {
            "Authorization": f"UserKey {api_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
    
    async def execute_workflow_stream(
        self,
        workflow: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a workflow with async streaming.
        
        Args:
            workflow: Workflow definition dictionary
            params: Workflow parameters
            
        Yields:
            Event dictionaries from the streaming response
            
        Raises:
            WorkflowExecutionError: If execution fails
            KubiyaAPIError: For API errors
        """
        # Prepare request body
        request_body = {
            **workflow
        }
        
        if params:
            request_body['parameters'] = params
        
        url = urljoin(self.base_url, f"/api/v1/workflow?runner={self.runner}&command=execute_workflow")
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        
        try:
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.headers
            ) as session:
                async with session.post(
                    url,
                    json=request_body
                ) as response:
                    
                    # Check for authentication errors
                    if response.status == 401:
                        raise KubiyaAuthenticationError("Invalid API token or unauthorized access")
                    
                    # Check for other errors
                    if response.status >= 400:
                        error_text = await response.text()
                        raise KubiyaAPIError(
                            f"API request failed: HTTP {response.status}",
                            status_code=response.status,
                            response_data={"error": error_text}
                        )
                    
                    # Process the streaming response
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            
                            if data.strip() == '[DONE]':
                                return
                            
                            try:
                                event_data = json.loads(data)
                                yield event_data
                                
                                # Check for end events
                                if event_data.get('end') or event_data.get('finishReason'):
                                    return
                                    
                            except json.JSONDecodeError:
                                # Yield raw data if it's not JSON
                                yield {"type": "raw_data", "data": data}
                        
                        elif line.startswith('event: '):
                            event_type = line[7:].strip()
                            if event_type in ['end', 'error']:
                                yield {"type": "event", "event_type": event_type}
                                if event_type == 'end':
                                    return
                                    
        except aiohttp.ClientError as e:
            raise KubiyaConnectionError(f"Failed to connect to Kubiya API: {str(e)}")
        except asyncio.TimeoutError:
            raise KubiyaTimeoutError(f"Request timed out after {self.timeout} seconds")
        except Exception as e:
            if not isinstance(e, (KubiyaAPIError, KubiyaAuthenticationError, KubiyaConnectionError)):
                raise WorkflowExecutionError(f"Streaming execution failed: {str(e)}")
            raise


class KubiyaClient:
    """Client for interacting with the Kubiya API."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.kubiya.ai",
        runner: str = "core-testing-2",
        timeout: int = 300,
        max_retries: int = 3
    ):
        """Initialize the Kubiya client.
        
        Args:
            api_key: Kubiya API key
            base_url: Base URL for the Kubiya API
            runner: Kubiya runner instance name
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.runner = runner
        self.timeout = timeout
        
        # Create session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers - Use UserKey format for API key authentication
        self.session.headers.update({
            "Authorization": f"UserKey {api_key}",
            "Content-Type": "application/json"
        })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[requests.Response, Generator[str, None, None]]:
        """Make an HTTP request to the Kubiya API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            stream: Whether to stream the response
            **kwargs: Additional request arguments
            
        Returns:
            Response object or generator for streaming responses
            
        Raises:
            KubiyaAPIError: For API errors
            KubiyaConnectionError: For connection errors
            KubiyaTimeoutError: For timeout errors
            KubiyaAuthenticationError: For authentication errors
        """
        url = urljoin(self.base_url, endpoint)
        
        # Update headers for streaming if needed
        headers = kwargs.pop('headers', {})
        if stream:
            headers['Accept'] = 'text/event-stream'
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                timeout=self.timeout,
                stream=stream,
                headers=headers,
                **kwargs
            )
            
            # Check for authentication errors
            if response.status_code == 401:
                raise KubiyaAuthenticationError("Invalid API key or unauthorized access")
            
            # For non-streaming responses, check status
            if not stream:
                try:
                    response.raise_for_status()
                except requests.HTTPError as e:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        pass
                    raise KubiyaAPIError(
                        f"API request failed: {str(e)}",
                        status_code=response.status_code,
                        response_data=error_data
                    )
        
            if stream:
                return self._handle_stream(response)
            return response
            
        except requests.exceptions.Timeout:
            raise KubiyaTimeoutError(f"Request to {url} timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError as e:
            raise KubiyaConnectionError(f"Failed to connect to Kubiya API: {str(e)}")
        except requests.exceptions.RequestException as e:
            if not isinstance(e, (KubiyaAPIError, KubiyaAuthenticationError)):
                raise KubiyaAPIError(f"Request failed: {str(e)}")
            raise

    def _handle_stream(self, response: requests.Response) -> Generator[str, None, None]:
        """Handle Server-Sent Events (SSE) stream with proper heartbeat handling.
        
        Args:
            response: Streaming response object
            
        Yields:
            Event data strings
            
        Raises:
            WorkflowExecutionError: For execution errors in the stream
        """
        try:
            workflow_ended = False
            last_heartbeat = time.time()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() == '[DONE]':
                            workflow_ended = True
                            return
                        
                        # Check for end events
                        try:
                            event_data = json.loads(data)
                            if event_data.get('end') or event_data.get('finishReason'):
                                workflow_ended = True
                            elif event_data.get('type') == 'heartbeat':
                                last_heartbeat = time.time()
                                # Continue processing heartbeats to keep connection alive
                        except json.JSONDecodeError:
                            pass
                        
                        yield data
                        
                        # If workflow ended, stop processing
                        if workflow_ended:
                            return
                            
                elif line.startswith('retry:'):
                    # Handle SSE retry directive
                    yield line
                elif line.startswith('event:'):
                    # Handle SSE event type
                    event_type = line[6:].strip()
                    if event_type in ['end', 'error']:
                        yield line
                        # Don't immediately close on error events - wait for explicit end
                    else:
                        yield line
                        
        except Exception as e:
            raise WorkflowExecutionError(f"Error processing stream: {str(e)}")
        finally:
            response.close()
    
    def execute_workflow(
        self,
        workflow_definition: Union[Dict[str, Any], str],
        parameters: Optional[Dict[str, Any]] = None,
        stream: bool = True
    ) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """Execute a workflow.
        
        Args:
            workflow_definition: Workflow definition (dict or JSON string)
            parameters: Workflow parameters
            stream: Whether to stream the response
            
        Returns:
            For streaming: Generator yielding event data
            For non-streaming: Final response data
            
        Raises:
            WorkflowExecutionError: If execution fails
            KubiyaAPIError: For API errors
        """
        # Convert string to dict if needed
        if isinstance(workflow_definition, str):
            try:
                workflow_definition = json.loads(workflow_definition)
            except json.JSONDecodeError as e:
                raise WorkflowExecutionError(f"Invalid workflow JSON: {str(e)}")
        
        # Ensure workflow_definition is properly formatted
        if not isinstance(workflow_definition, dict):
            raise WorkflowExecutionError("Workflow definition must be a dictionary")
        
        # Add parameters if provided
        if parameters:
            workflow_definition['parameters'] = parameters
        
        # Prepare request body - workflow fields at top level
        request_body = {
            **workflow_definition  # Spread workflow fields at top level
        }
        
        logger.info("Executing workflow...")
        logger.debug(f"Request body: {json.dumps(request_body, indent=2)}")
        
        # Execute the workflow
        response = self._make_request(
            method="POST",
            endpoint=f"/api/v1/workflow?runner={self.runner}&command=execute_workflow",
            data=request_body,
            stream=stream
        )
        
        if stream:
            return response
        else:
            # For non-streaming, collect all data
            result = []
            for event in response:
                result.append(event)
            return {"events": result}

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the status of a workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Workflow status information
            
        Raises:
            WorkflowNotFoundError: If workflow not found
            KubiyaAPIError: For API errors
        """
        try:
            response = self._make_request(
                method="GET",
                endpoint=f"/api/v1/workflows/{workflow_id}/status"
            )
            return response.json()
        except KubiyaAPIError as e:
            if e.status_code == 404:
                raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
            raise

    def cancel_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Cancel a running workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Cancellation result
            
        Raises:
            WorkflowNotFoundError: If workflow not found
            KubiyaAPIError: For API errors
        """
        try:
            response = self._make_request(
                method="POST",
                endpoint=f"/api/v1/workflows/{workflow_id}/cancel"
            )
            return response.json()
        except KubiyaAPIError as e:
            if e.status_code == 404:
                raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
            raise

    def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List workflows.
        
        Args:
            status: Filter by workflow status
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of workflows
            
        Raises:
            KubiyaAPIError: For API errors
        """
        params = {
            "limit": limit,
            "offset": offset
        }
            
        response = self._make_request(
            method="GET",
            endpoint="/api/v1/workflows",
            params=params
        )
        return response.json()


# Convenience function for simple workflow execution
def execute_workflow(
    workflow_definition: Union[Dict[str, Any], str],
    api_key: str,
    parameters: Optional[Dict[str, Any]] = None,
    base_url: str = "https://api.kubiya.ai",
    runner: str = "core-testing-2",
    stream: bool = True
) -> Union[Dict[str, Any], Generator[str, None, None]]:
    """Execute a workflow using the Kubiya API.
    
    This is a convenience function that creates a client and executes the workflow.
    
    Args:
        workflow_definition: Workflow definition (dict or JSON string)
        api_key: Kubiya API key
        parameters: Workflow parameters
        base_url: Base URL for the Kubiya API
        runner: Kubiya runner instance name
        stream: Whether to stream the response
        
    Returns:
        For streaming: Generator yielding event data
        For non-streaming: Final response data
        
    Example:
        >>> from kubiya_workflow_sdk import execute_workflow
        >>> 
        >>> workflow = {
        ...     "name": "hello_world",
        ...     "steps": [{
        ...         "name": "greet",
        ...         "type": "shell",
        ...         "command": "echo 'Hello, World!'"
        ...     }]
        ... }
        >>> 
        >>> # Stream execution
        >>> for event in execute_workflow(workflow, api_key="your-key", runner="core-testing-2"):
        ...     print(event)
        >>> 
        >>> # Get all results at once
        >>> result = execute_workflow(workflow, api_key="your-key", runner="core-testing-2", stream=False)
        >>> print(result)
    """
    client = KubiyaClient(api_key=api_key, base_url=base_url, runner=runner)
    return client.execute_workflow(
        workflow_definition=workflow_definition,
        parameters=parameters,
        stream=stream
    ) 