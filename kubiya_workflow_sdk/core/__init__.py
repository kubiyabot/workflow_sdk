"""
Kubiya Workflow SDK Core Module

Enterprise-grade workflow automation SDK with:
- Object-oriented architecture
- Type safety and validation
- Async/sync support
- Comprehensive error handling
"""

from .types import (
    # Type variables
    T,
    StepFunction,
    # Core models
    RetryPolicy,
    StepOutput,
    StepResult,
    ExecutionResult,
    WorkflowMetadata,
    ExecutorConfig,
    StepModel,
    WorkflowModel,
    ToolDefinition,
    WorkflowValidationResult,
    Volume,
    ServiceSpec,
    # Protocols
    Executor,
    StreamHandler,
)

from .constants import (
    # Constants
    DEFAULT_API_URL,
    DEFAULT_RUNNER,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    SSE_RECONNECT_DELAY,
    SSE_KEEPALIVE_INTERVAL,
    SSE_MAX_RECONNECTS,
    MAX_PARALLEL_STEPS,
    MAX_WORKFLOW_DEPTH,
    MAX_STEP_OUTPUT_SIZE,
    MAX_WORKFLOW_SIZE,
    TOOL_EXEC_TIMEOUT,
    TOOL_OUTPUT_BUFFER_SIZE,
    ENV_VARS,
    METADATA_KEYS,
    RESERVED_PARAMS,
    # Enums
    ExecutorType,
    StepStatus,
    WorkflowStatus,
    RetryBackoff,
    LogLevel,
    AuthType,
    HttpMethod,
    ContentType,
    ToolType,
    QueuePriority,
    NotificationChannel,
)

from .exceptions import (
    # Base exception
    KubiyaSDKError,
    # Workflow errors
    WorkflowError,
    WorkflowValidationError,
    WorkflowExecutionError,
    WorkflowTimeoutError,
    # Client errors
    ClientError,
    AuthenticationError,
    APIError,
    ConnectionError,
    # Tool errors
    ToolError,
    ToolDefinitionError,
    ToolExecutionError,
    ToolRegistryError,
    # DSL errors
    DSLError,
    StepConfigurationError,
    ExecutorConfigurationError,
    # Server errors
    ServerError,
    StreamingError,
)

# Sentry configuration (optional)
try:
    from kubiya_workflow_sdk.core.sentry_config import (
        initialize_sentry,
        capture_exception,
        capture_message,
        add_breadcrumb,
        set_workflow_context,
        is_sentry_enabled,
        is_initialized as is_sentry_initialized,
        shutdown_sentry,
    )
except ImportError:
    # Sentry not available, create no-op functions
    initialize_sentry = lambda *args, **kwargs: False
    capture_exception = lambda *args, **kwargs: None
    capture_message = lambda *args, **kwargs: None
    add_breadcrumb = lambda *args, **kwargs: None
    set_user_context = lambda *args, **kwargs: None
    set_workflow_context = lambda *args, **kwargs: None
    is_sentry_enabled = lambda: False
    is_sentry_initialized = lambda: False
    shutdown_sentry = lambda: None

__all__ = [
    # Types
    "T",
    "StepFunction",
    # Core models
    "RetryPolicy",
    "StepOutput",
    "StepResult",
    "ExecutionResult",
    "WorkflowMetadata",
    "ExecutorConfig",
    "StepModel",
    "WorkflowModel",
    "ToolDefinition",
    "WorkflowValidationResult",
    "Volume",
    "ServiceSpec",
    # Protocols
    "Executor",
    "StreamHandler",
    # Constants
    "DEFAULT_API_URL",
    "DEFAULT_RUNNER",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
    "RETRY_BACKOFF_BASE",
    "SSE_RECONNECT_DELAY",
    "SSE_KEEPALIVE_INTERVAL",
    "SSE_MAX_RECONNECTS",
    "MAX_PARALLEL_STEPS",
    "MAX_WORKFLOW_DEPTH",
    "MAX_STEP_OUTPUT_SIZE",
    "MAX_WORKFLOW_SIZE",
    "TOOL_EXEC_TIMEOUT",
    "TOOL_OUTPUT_BUFFER_SIZE",
    "ENV_VARS",
    "METADATA_KEYS",
    "RESERVED_PARAMS",
    # Enums
    "ExecutorType",
    "StepStatus",
    "WorkflowStatus",
    "RetryBackoff",
    "LogLevel",
    "AuthType",
    "HttpMethod",
    "ContentType",
    "ToolType",
    "QueuePriority",
    "NotificationChannel",
    # Exceptions
    "KubiyaSDKError",
    "WorkflowError",
    "WorkflowValidationError",
    "WorkflowExecutionError",
    "WorkflowTimeoutError",
    "ClientError",
    "AuthenticationError",
    "APIError",
    "ConnectionError",
    "ToolError",
    "ToolDefinitionError",
    "ToolExecutionError",
    "ToolRegistryError",
    "DSLError",
    "StepConfigurationError",
    "ExecutorConfigurationError",
    "ServerError",
    "StreamingError",
    # Sentry (optional)
    "initialize_sentry",
    "capture_exception",
    "capture_message",
    "add_breadcrumb",
    "set_workflow_context",
    "is_sentry_enabled",
    "is_sentry_initialized",
    "shutdown_sentry",
]
