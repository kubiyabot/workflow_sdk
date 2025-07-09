from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict, RootModel, field_serializer
from .scheduling import WorkflowType
from .data import Parameter, EnvironmentVariable, WorkflowParams, EnvironmentVariables
from .control_flow import Precondition, RetryPolicy
from .step import Step
from .lifecycle import HandlerOn, SMTPConfig, MailOn, MailConfig


# OpenTelemetry configuration
class OTelResource(BaseModel):
    """OpenTelemetry resource attributes"""

    service_name: str = Field(alias="service.name")
    deployment_environment: Optional[str] = Field(None, alias="deployment.environment")

    model_config = ConfigDict(populate_by_name=True)


class OTelConfig(BaseModel):
    """OpenTelemetry configuration"""

    enabled: bool = False
    endpoint: str
    resource: Optional[OTelResource] = None


# Main workflow model
class Workflow(BaseModel):
    """Complete workflow/DAG definition"""

    # Metadata
    name: Optional[str] = None  # Defaults to filename if not provided
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    group: Optional[str] = None

    # Scheduling
    schedule: Optional[str] = None  # Cron expression
    skip_if_successful: bool = Field(False, alias="skipIfSuccessful")

    # Execution control
    type: WorkflowType = WorkflowType.CHAIN
    max_active_runs: int = Field(1, alias="maxActiveRuns")
    max_active_steps: int = Field(1, alias="maxActiveSteps")
    delay_sec: int = Field(0, alias="delaySec")
    timeout_sec: Optional[int] = Field(None, alias="timeoutSec")
    max_cleanup_time_sec: int = Field(60, alias="maxCleanUpTimeSec")

    # Data and configuration
    params: Optional[WorkflowParams] = None
    env: Optional[EnvironmentVariables] = None
    dotenv: Optional[Union[str, List[str]]] = None
    preconditions: Optional[List[Union[str, Precondition]]] = None

    # Steps - the core of the workflow
    steps: List[Step]

    # Error handling and notifications
    handler_on: Optional[HandlerOn] = Field(None, alias="handlerOn")
    retry_policy: Optional[RetryPolicy] = Field(None, alias="retryPolicy")

    # Email configuration
    smtp: Optional[SMTPConfig] = None
    mail_on: Optional[MailOn] = Field(None, alias="mailOn")
    error_mail: Optional[MailConfig] = Field(None, alias="errorMail")
    info_mail: Optional[MailConfig] = Field(None, alias="infoMail")

    # Observability
    otel: Optional[OTelConfig] = None

    # Resource management
    queue: Optional[str] = None
    log_dir: Optional[str] = Field(None, alias="logDir")
    hist_retention_days: int = Field(30, alias="histRetentionDays")
    max_output_size: int = Field(1048576, alias="maxOutputSize")  # 1MB default

    model_config = ConfigDict(
        populate_by_name=True, extra="allow"  # Allow extra fields for extensibility
    )

    @field_validator("steps", mode="before")
    @classmethod
    def validate_steps(cls, v):
        """Ensure steps is always a list"""
        if isinstance(v, dict):
            # Convert dict format to list format
            return [{"name": k, **step_def} for k, step_def in v.items()]
        return v

    @field_serializer('params')
    def dump_params(self, v):
        return v.model_dump()

    @field_serializer('env')
    def dump_env(self, v):
        return v.model_dump()


# Multi-workflow file support
class WorkflowFile(BaseModel):
    """Represents a file that can contain multiple workflows"""

    workflows: List[Workflow]

    @classmethod
    def from_yaml_content(cls, content: str) -> "WorkflowFile":
        """Parse YAML content that may contain multiple workflows separated by ---"""
        # This would need actual YAML parsing logic
        # For now, just return a placeholder
        return cls(workflows=[])


# Base configuration that can be shared across workflows
class BaseConfig(BaseModel):
    """Base configuration shared across all workflows"""

    env: Optional[List[Union[str, Dict[str, str]]]] = None
    params: Optional[List[Union[str, Dict[str, Any]]]] = None
    log_dir: Optional[str] = Field(None, alias="logDir")
    hist_retention_days: int = Field(30, alias="histRetentionDays")
    max_active_runs: int = Field(1, alias="maxActiveRuns")
    smtp: Optional[SMTPConfig] = None
    error_mail: Optional[MailConfig] = Field(None, alias="errorMail")

    model_config = ConfigDict(populate_by_name=True)
