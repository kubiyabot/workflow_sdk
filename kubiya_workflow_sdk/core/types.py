"""
Type Definitions for Kubiya Workflow SDK

This module defines all core types, enums, and data structures used throughout the SDK.
"""

from typing import Dict, Any, List, Optional, Union, Literal, TypedDict, Protocol, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import uuid

from .constants import (
    ExecutorType,
    StepStatus,
    WorkflowStatus,
    RetryBackoff,
    HttpMethod,
    ContentType,
)


# Type variables
T = TypeVar("T")
StepFunction = TypeVar("StepFunction", bound=Callable[..., Any])


@dataclass
class Volume:
    """Volume specification for containers."""

    host_path: str
    container_path: str
    read_only: bool = False

    def __post_init__(self):
        """Validate volume specification after initialization."""
        errors = self._validate_without_exception()
        if errors:
            raise ValueError(f"Volume validation failed: {'; '.join(errors)}")

    def _validate_without_exception(self) -> List[str]:
        """Internal validation that returns errors instead of raising."""
        errors = []

        # Validate host path
        if not self.host_path or not self.host_path.strip():
            errors.append("Volume host_path cannot be empty")
        elif not self.host_path.startswith("/"):
            errors.append("Volume host_path must be an absolute path starting with '/'")

        # Validate container path
        if not self.container_path or not self.container_path.strip():
            errors.append("Volume container_path cannot be empty")
        elif not self.container_path.startswith("/"):
            errors.append("Volume container_path must be an absolute path starting with '/'")

        # Validate read_only
        if not isinstance(self.read_only, bool):
            errors.append("Volume read_only must be a boolean")

        return errors

    def validate(self) -> List[str]:
        """Validate volume specification and return list of errors."""
        errors = self._validate_without_exception()
        if errors:
            raise ValueError(f"Volume validation failed: {'; '.join(errors)}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        return {
            "host_path": self.host_path,
            "container_path": self.container_path,
            "read_only": self.read_only,
        }


@dataclass
class ServiceSpec:
    """Service specification for bounded services."""

    name: str
    image: str
    env: Dict[str, str] = field(default_factory=dict)
    entrypoint: List[str] = field(default_factory=list)
    exposed_ports: List[int] = field(default_factory=list)
    volumes: List[Volume] = field(default_factory=list)

    def __post_init__(self):
        """Validate service specification after initialization."""
        errors = self._validate_without_exception()
        if errors:
            raise ValueError(f"ServiceSpec validation failed: {'; '.join(errors)}")

    def _validate_without_exception(self) -> List[str]:
        """Internal validation that returns errors instead of raising."""
        errors = []

        # Validate name
        if not self.name or not self.name.strip():
            errors.append("Service name cannot be empty")
        elif not self.name.replace("-", "").replace("_", "").isalnum():
            errors.append(
                "Service name must contain only alphanumeric characters, hyphens, and underscores"
            )
        elif len(self.name) > 63:
            errors.append("Service name must be 63 characters or less")

        # Validate image
        if not self.image or not self.image.strip():
            errors.append("Service image cannot be empty")
        elif ":" not in self.image and not self.image.endswith(":latest"):
            errors.append("Service image should include a tag (e.g., 'redis:7-alpine')")

        # Validate ports
        for port in self.exposed_ports:
            if not isinstance(port, int):
                errors.append(f"Port {port} must be an integer")
            elif port < 1 or port > 65535:
                errors.append(f"Port {port} must be between 1 and 65535")

        # Check for duplicate ports
        if len(self.exposed_ports) != len(set(self.exposed_ports)):
            errors.append("Duplicate ports found in exposed_ports")

        # Validate environment variables
        for key, value in self.env.items():
            if not key or not key.strip():
                errors.append("Environment variable key cannot be empty")
            elif not key.replace("_", "").isalnum():
                errors.append(
                    f"Environment variable key '{key}' must contain only alphanumeric characters and underscores"
                )
            if not isinstance(value, str):
                errors.append(f"Environment variable value for '{key}' must be a string")

        # Validate entrypoint
        for i, cmd in enumerate(self.entrypoint):
            if not isinstance(cmd, str):
                errors.append(f"Entrypoint command at index {i} must be a string")

        # Validate volumes
        for i, volume in enumerate(self.volumes):
            if not isinstance(volume, Volume):
                errors.append(f"Volume at index {i} must be a Volume instance")
            else:
                vol_errors = volume._validate_without_exception()
                errors.extend([f"Volume {i}: {err}" for err in vol_errors])

        return errors

    def validate(self) -> List[str]:
        """Validate service specification and return list of errors."""
        errors = self._validate_without_exception()
        if errors:
            raise ValueError(f"ServiceSpec validation failed: {'; '.join(errors)}")
        return errors

    def endpoint(self) -> str:
        """Get the service endpoint for connecting from tools."""
        if not self.exposed_ports:
            return f"{self.name}-svc"
        return f"{self.name}-svc:{self.exposed_ports[0]}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        result = {"name": self.name, "image": self.image}

        if self.env:
            result["env"] = self.env
        if self.entrypoint:
            result["entrypoint"] = self.entrypoint
        if self.exposed_ports:
            result["exposed_ports"] = self.exposed_ports
        if self.volumes:
            result["with_volumes"] = [vol.to_dict() for vol in self.volumes]

        return result


class ConditionOperator(str, Enum):
    """Operators for step execution conditions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class RetryStrategy(str, Enum):
    """Retry backoff strategies."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "expo"


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3
    delay_seconds: int = 60

    def to_dict(self) -> Dict[str, Any]:
        """Convert to workflow format."""
        return {
            "limit": self.max_attempts,
            "intervalSec": self.delay_seconds,

        }


@dataclass
class StepCondition:
    """Condition for conditional step execution."""

    expression: str
    operator: ConditionOperator
    expected_value: Any
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        expected = self.expected_value

        if self.operator == ConditionOperator.REGEX_MATCH:
            expected = f"re:{expected}"
        elif self.operator in [ConditionOperator.CONTAINS, ConditionOperator.NOT_CONTAINS]:
            expected = f"*{expected}*" if self.operator == ConditionOperator.CONTAINS else expected

        return {"condition": self.expression, "expected": str(expected)}


@dataclass
class StepOutput:
    """Step execution output."""

    name: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionMetrics:
    """Metrics for workflow/step execution."""

    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_received: Optional[int] = None


@dataclass
class StepResult:
    """Result of a step execution."""

    step_name: str
    status: StepStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0

    @property
    def is_success(self) -> bool:
        return self.status == StepStatus.COMPLETED

    @property
    def is_finished(self) -> bool:
        return self.status in [
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.CANCELLED,
            StepStatus.TIMEOUT,
            StepStatus.SKIPPED,
        ]


@dataclass
class ExecutionResult:
    """Workflow execution result."""

    execution_id: str
    workflow_name: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    steps: List[StepResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_finished(self) -> bool:
        return self.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.TIMEOUT,
        ]

    @property
    def steps_completed(self) -> int:
        return len([s for s in self.steps if s.is_finished])

    @property
    def steps_total(self) -> int:
        return len(self.steps)


class ToolDefinition(TypedDict, total=False):
    """Type definition for tool configurations."""

    name: str
    description: str
    type: str
    image: Optional[str]
    content: Optional[str]
    args: Optional[List[Dict[str, Any]]]
    env: Optional[Dict[str, str]]
    volumes: Optional[List[Dict[str, str]]]
    secrets: Optional[List[str]]
    with_services: Optional[List[Dict[str, Any]]]


class AgentConfiguration(TypedDict, total=False):
    """Configuration for inline AI agents."""

    name: str
    ai_instructions: str
    llm_model: str
    runners: Optional[List[str]]
    description: Optional[str]
    is_debug_mode: Optional[bool]
    tools: Optional[List[ToolDefinition]]
    temperature: Optional[float]
    max_tokens: Optional[int]


@dataclass
class WorkflowMetadata:
    """Workflow metadata."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    schema_version: str = "v1"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "schema_version": self.schema_version,
        }


@dataclass
class ExecutorConfig:
    """Executor configuration."""

    type: ExecutorType
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to workflow format."""
        return {"type": self.type.value, "config": self.config}


@dataclass
class StepModel:
    """Step model for workflows."""

    name: str
    description: str = ""
    executor: Optional[ExecutorConfig] = None
    depends: List[str] = field(default_factory=list)
    output: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    secrets: List[str] = field(default_factory=list)
    retry_policy: Optional[RetryPolicy] = None
    timeout: Optional[int] = None
    continue_on_failure: bool = False
    preconditions: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to workflow format."""
        result = {"name": self.name, "description": self.description}

        if self.executor:
            result["executor"] = self.executor.to_dict()

        if self.depends:
            result["depends"] = self.depends

        if self.output:
            result["output"] = self.output

        if self.env:
            result["env"] = self.env

        if self.secrets:
            result["secrets"] = self.secrets

        if self.retry_policy:
            result["retryPolicy"] = self.retry_policy.to_dict()

        if self.timeout:
            result["timeout"] = self.timeout

        if self.continue_on_failure:
            result["continueOn"] = {"failure": True}

        if self.preconditions:
            result["preconditions"] = self.preconditions

        if self.tags:
            result["tags"] = self.tags

        return result


@dataclass
class WorkflowModel:
    """Complete workflow model."""

    metadata: WorkflowMetadata
    params: Dict[str, Any] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    constants: Dict[str, Any] = field(default_factory=dict)
    steps: List[StepModel] = field(default_factory=list)
    handlers: Dict[str, Any] = field(default_factory=dict)
    notifications: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None
    queue: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to workflow format."""
        result = self.metadata.to_dict()

        if self.params:
            result["params"] = self.params

        if self.env:
            result["env"] = self.env

        if self.constants:
            result["constants"] = self.constants

        if self.steps:
            result["steps"] = [step.to_dict() for step in self.steps]

        if self.handlers:
            result["handlers"] = self.handlers

        if self.notifications:
            result["notifications"] = self.notifications

        if self.schedule:
            result["schedule"] = self.schedule

        if self.queue:
            result["queue"] = self.queue

        return result


@dataclass
class ToolDefinition:
    """Tool definition."""

    name: str
    description: str
    type: str  # docker, python, shell, etc.
    image: Optional[str] = None
    content: Optional[str] = None
    command: Optional[str] = None
    args: List[Dict[str, Any]] = field(default_factory=list)
    env: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    with_files: List[Dict[str, str]] = field(default_factory=list)
    with_volumes: List[Dict[str, str]] = field(default_factory=list)
    with_services: List[ServiceSpec] = field(default_factory=list)
    icon_url: Optional[str] = None
    mermaid: Optional[str] = None

    def __post_init__(self):
        """Validate tool definition after initialization."""
        errors = self._validate_without_exception()
        if errors:
            raise ValueError(f"ToolDefinition validation failed: {'; '.join(errors)}")

    def _validate_without_exception(self) -> List[str]:
        """Internal validation that returns errors instead of raising."""
        errors = []

        # Validate name
        if not self.name or not self.name.strip():
            errors.append("Tool name cannot be empty")
        elif not self.name.replace("-", "").replace("_", "").isalnum():
            errors.append(
                "Tool name must contain only alphanumeric characters, hyphens, and underscores"
            )

        # Validate description
        if not self.description or not self.description.strip():
            errors.append("Tool description cannot be empty")

        # Validate type
        valid_types = {"docker", "shell", "python", "http", "ssh", "kubiya", "jq"}
        if self.type not in valid_types:
            errors.append(f"Tool type '{self.type}' must be one of: {', '.join(valid_types)}")

        # Type-specific validations
        if self.type == "docker":
            if not self.image:
                errors.append("Docker tools must specify an image")
            elif ":" not in self.image and not self.image.endswith(":latest"):
                errors.append("Docker image should include a tag (e.g., 'alpine:3.18')")

        # Validate args
        for i, arg in enumerate(self.args):
            if not isinstance(arg, dict):
                errors.append(f"Argument at index {i} must be a dictionary")
            elif "name" not in arg:
                errors.append(f"Argument at index {i} must have a 'name' field")
            elif "type" not in arg:
                errors.append(f"Argument at index {i} must have a 'type' field")

        # Validate services
        service_names = set()
        for i, service in enumerate(self.with_services):
            if not isinstance(service, ServiceSpec):
                errors.append(f"Service at index {i} must be a ServiceSpec instance")
            else:
                try:
                    service_errors = service._validate_without_exception()
                    if service_errors:
                        errors.extend(
                            [f"Service {i} ({service.name}): {err}" for err in service_errors]
                        )
                except Exception as e:
                    errors.append(f"Service {i}: {str(e)}")

                # Check for duplicate service names
                if service.name in service_names:
                    errors.append(f"Duplicate service name '{service.name}' found")
                service_names.add(service.name)

        # Validate secrets
        for i, secret in enumerate(self.secrets):
            if not isinstance(secret, str) or not secret.strip():
                errors.append(f"Secret at index {i} must be a non-empty string")

        return errors

    def validate(self) -> List[str]:
        """Validate tool definition and return list of errors."""
        errors = self._validate_without_exception()
        if errors:
            raise ValueError(f"ToolDefinition validation failed: {'; '.join(errors)}")
        return errors

    def get_service_endpoints(self) -> Dict[str, str]:
        """Get a mapping of service names to their endpoints."""
        return {service.name: service.endpoint() for service in self.with_services}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        result = {"name": self.name, "description": self.description, "type": self.type}

        if self.image:
            result["image"] = self.image
        if self.content:
            result["content"] = self.content
        if self.command:
            result["command"] = self.command
        if self.args:
            result["args"] = self.args
        if self.env:
            result["env"] = self.env
        if self.secrets:
            result["secrets"] = self.secrets
        if self.with_files:
            result["with_files"] = self.with_files
        if self.with_volumes:
            result["with_volumes"] = self.with_volumes
        if self.with_services:
            result["with_services"] = [service.to_dict() for service in self.with_services]
        if self.icon_url:
            result["icon_url"] = self.icon_url
        if self.mermaid:
            result["mermaid"] = self.mermaid

        return result


@dataclass
class WorkflowValidationResult:
    """Result of workflow validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)

    def add_suggestion(self, suggestion: str) -> None:
        """Add validation suggestion."""
        self.suggestions.append(suggestion)


# Protocol definitions for extensibility
class Executor(Protocol):
    """Protocol for custom executors."""

    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the step with given configuration."""
        ...

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate executor configuration."""
        ...


class StreamHandler(Protocol):
    """Protocol for handling execution streams."""

    def on_step_start(self, step_name: str) -> None:
        """Called when a step starts."""
        ...

    def on_step_output(self, step_name: str, output: str) -> None:
        """Called when a step produces output."""
        ...

    def on_step_complete(self, step_name: str, result: StepResult) -> None:
        """Called when a step completes."""
        ...

    def on_workflow_complete(self, result: ExecutionResult) -> None:
        """Called when workflow completes."""
        ...


# Export all public types
__all__ = [
    "ExecutorType",
    "StepStatus",
    "WorkflowStatus",
    "ConditionOperator",
    "RetryStrategy",
    "RetryPolicy",
    "StepCondition",
    "StepOutput",
    "ExecutionMetrics",
    "StepResult",
    "ExecutionResult",
    "ToolDefinition",
    "AgentConfiguration",
    "WorkflowMetadata",
    "ExecutorConfig",
    "StepModel",
    "WorkflowModel",
    "WorkflowValidationResult",
    "Executor",
    "StreamHandler",
    "Volume",
    "ServiceSpec",
]
