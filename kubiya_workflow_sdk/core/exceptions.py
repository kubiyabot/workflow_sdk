"""Kubiya Workflow SDK exceptions."""

from typing import Optional, Dict, Any, List


class KubiyaSDKError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Workflow Errors
class WorkflowError(KubiyaSDKError):
    """Base class for workflow-related errors."""

    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails."""

    def __init__(self, message: str, errors: List[str]):
        super().__init__(message, {"errors": errors})
        self.errors = errors


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails."""

    def __init__(
        self, message: str, execution_id: Optional[str] = None, step_name: Optional[str] = None
    ):
        super().__init__(message, {"execution_id": execution_id, "step_name": step_name})
        self.execution_id = execution_id
        self.step_name = step_name


class WorkflowTimeoutError(WorkflowExecutionError):
    """Raised when workflow execution times out."""

    pass


# Client Errors
class ClientError(KubiyaSDKError):
    """Base class for client-related errors."""

    pass


class AuthenticationError(ClientError):
    """Raised when authentication fails."""

    pass


class APIError(ClientError):
    """Raised when API request fails."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None
    ):
        super().__init__(message, {"status_code": status_code, "response_body": response_body})
        self.status_code = status_code
        self.response_body = response_body


class ConnectionError(ClientError):
    """Raised when connection to API fails."""

    pass


# Provider Errors
class ProviderError(KubiyaSDKError):
    """Base class for provider-related errors."""

    pass


# Tool Errors
class ToolError(KubiyaSDKError):
    """Base class for tool-related errors."""

    pass


class ToolDefinitionError(ToolError):
    """Raised when tool definition is invalid."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(self, message: str, tool_name: str, exit_code: Optional[int] = None):
        super().__init__(message, {"tool_name": tool_name, "exit_code": exit_code})
        self.tool_name = tool_name
        self.exit_code = exit_code


class ToolRegistryError(ToolError):
    """Raised when tool registry operations fail."""

    pass


# DSL Errors
class DSLError(KubiyaSDKError):
    """Base class for DSL-related errors."""

    pass


class StepConfigurationError(DSLError):
    """Raised when step configuration is invalid."""

    pass


class ExecutorConfigurationError(DSLError):
    """Raised when executor configuration is invalid."""

    pass


# Server Errors
class ServerError(KubiyaSDKError):
    """Base class for server-related errors."""

    pass


class StreamingError(ServerError):
    """Raised when SSE streaming fails."""

    pass
