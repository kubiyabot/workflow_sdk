"""Kubiya Workflow SDK constants and enumerations."""

from enum import Enum, auto
from typing import Final


# API Configuration
DEFAULT_API_URL: Final[str] = "https://api.kubiya.ai"
DEFAULT_RUNNER: Final[str] = "default"
DEFAULT_TIMEOUT: Final[int] = 300
MAX_RETRIES: Final[int] = 3
RETRY_BACKOFF_BASE: Final[float] = 2.0

# Streaming Configuration
SSE_RECONNECT_DELAY: Final[int] = 3
SSE_KEEPALIVE_INTERVAL: Final[int] = 30
SSE_MAX_RECONNECTS: Final[int] = 10

# Execution Limits
MAX_PARALLEL_STEPS: Final[int] = 50
MAX_WORKFLOW_DEPTH: Final[int] = 10
MAX_STEP_OUTPUT_SIZE: Final[int] = 1024 * 1024  # 1MB
MAX_WORKFLOW_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB

# Tool Execution
TOOL_EXEC_TIMEOUT: Final[int] = 600  # 10 minutes
TOOL_OUTPUT_BUFFER_SIZE: Final[int] = 8192

# Sentry Configuration
SENTRY_DEFAULT_TRACES_SAMPLE_RATE: Final[float] = 0.1
SENTRY_DEFAULT_PROFILES_SAMPLE_RATE: Final[float] = 0.1
SENTRY_DEFAULT_ENVIRONMENT: Final[str] = "development"


class ExecutorType(str, Enum):
    """Supported executor types."""

    PYTHON = "python"
    SHELL = "shell"
    DOCKER = "docker"
    TOOL = "tool"
    INLINE_AGENT = "inline_agent"
    KUBIYA_API = "kubiya"
    HTTP = "http"
    SSH = "ssh"
    JQ = "jq"
    CUSTOM = "custom"


class StepStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    SUSPENDED = "suspended"


class RetryBackoff(str, Enum):
    """Retry backoff strategies."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "expo"


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuthType(str, Enum):
    """Authentication types."""

    API_KEY = "UserKey"
    BEARER = "Bearer"
    BASIC = "Basic"
    OAUTH2 = "OAuth2"


class HttpMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ContentType(str, Enum):
    """Common content types."""

    JSON = "application/json"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    TEXT = "text/plain"
    XML = "application/xml"
    YAML = "application/yaml"
    BINARY = "application/octet-stream"


class ToolType(str, Enum):
    """Tool types."""

    DOCKER = "docker"
    PYTHON = "python"
    SHELL = "shell"
    HTTP = "http"
    GRPC = "grpc"
    CUSTOM = "custom"


class QueuePriority(int, Enum):
    """Queue priorities."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class NotificationChannel(str, Enum):
    """Notification channels."""

    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"
    CUSTOM = "custom"


# Standard environment variables
ENV_VARS = {
    "API_KEY": "KUBIYA_API_KEY",
    "API_TOKEN": "KUBIYA_API_TOKEN",
    "API_URL": "KUBIYA_API_URL",
    "RUNNER": "KUBIYA_RUNNER",
    "LOG_LEVEL": "KUBIYA_LOG_LEVEL",
    "WORKSPACE": "KUBIYA_WORKSPACE",
    "EXECUTION_ID": "KUBIYA_EXECUTION_ID",
    "SENTRY_DSN": "KUBIYA_SENTRY_DSN",
    "SENTRY_ENVIRONMENT": "KUBIYA_SENTRY_ENVIRONMENT",
    "SENTRY_RELEASE": "KUBIYA_SENTRY_RELEASE",
    "SENTRY_ENABLED": "KUBIYA_SENTRY_ENABLED",
}

# Workflow metadata keys
METADATA_KEYS = {
    "name": "name",
    "version": "version",
    "description": "description",
    "tags": "tags",
    "author": "author",
    "created_at": "created_at",
    "updated_at": "updated_at",
    "schema_version": "schema_version",
}

# Reserved parameter names
RESERVED_PARAMS = {
    "ctx",
    "context",
    "workflow",
    "execution",
    "runner",
    "env",
    "secrets",
}
