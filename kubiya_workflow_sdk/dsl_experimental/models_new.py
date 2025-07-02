from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


# Enums for type safety
class ExecutorType(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    SSH = "ssh"
    HTTP = "http" 
    MAIL = "mail"
    JQ = "jq"
    DAG = "dag"
    TOOL = "tool"
    KUBIYA = "kubiya"
    AGENT = "agent"


class WorkflowType(str, Enum):
    CHAIN = "chain"
    GRAPH = "graph"


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class SignalType(str, Enum):
    SIGTERM = "SIGTERM"
    SIGKILL = "SIGKILL"
    SIGINT = "SIGINT"


# Basic definitions
class FileDefinition(BaseModel):
    destination: str
    content: str


class ArgDefinition(BaseModel):
    name: str
    type: str
    required: bool = False
    default: Optional[Any] = None


class Parameter(BaseModel):
    """Represents a workflow parameter"""
    name: str
    value: Any
    description: Optional[str] = None


class EnvironmentVariable(BaseModel):
    """Represents an environment variable"""
    name: str
    value: str


class Precondition(BaseModel):
    """Represents a precondition for step execution"""
    condition: str
    expected: str
    description: Optional[str] = None


class RetryPolicy(BaseModel):
    """Retry configuration for steps"""
    limit: int = 3
    interval_sec: int = 30
    exit_codes: Optional[List[int]] = None


class RepeatPolicy(BaseModel):
    """Repeat configuration for steps"""
    repeat: bool = True
    interval_sec: int = 60
    limit: Optional[int] = None
    exit_code: Optional[List[int]] = None
    condition: Optional[str] = None
    expected: Optional[str] = None


class ContinueOn(BaseModel):
    """Configuration for continuing workflow on various conditions"""
    failure: bool = False
    skipped: bool = False
    exit_code: Optional[List[int]] = None
    output: Optional[List[str]] = None
    mark_success: bool = False


class ParallelConfig(BaseModel):
    """Configuration for parallel step execution"""
    items: List[str]
    max_concurrent: int = Field(default=1, alias="maxConcurrent")


# Executor configurations
class DockerExecutorConfig(BaseModel):
    image: str
    volumes: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    network: Optional[str] = None
    platform: Optional[str] = None
    auto_remove: bool = True


class SSHExecutorConfig(BaseModel):
    host: str
    user: str
    port: int = 22
    key_file: Optional[str] = None
    password: Optional[str] = None
    strict_host_key_checking: bool = True


class HTTPExecutorConfig(BaseModel):
    url: str
    method: HTTPMethod = HTTPMethod.GET
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    timeout_sec: int = 30
    silent: bool = False


class MailExecutorConfig(BaseModel):
    to: str
    from_address: str = Field(alias="from")
    subject: str
    message: str
    attachments: Optional[List[str]] = None


class JQExecutorConfig(BaseModel):
    query: str
    raw: bool = False


class DAGExecutorConfig(BaseModel):
    params: Optional[str] = None


class ToolExecutorConfig(BaseModel):
    tool_def: 'ToolDef'
    args: Optional[Dict[str, Any]] = None
    secrets: Optional[Dict[str, Any]] = None


class KubiyaExecutorConfig(BaseModel):
    url: str
    method: HTTPMethod = HTTPMethod.GET
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None


class AgentExecutorConfig(BaseModel):
    agent_name: str
    message: str
    context: Optional[Dict[str, Any]] = None


# Tool definition
class ToolDef(BaseModel):
    name: str
    description: str = ''
    type: str
    image: str
    content: str
    with_files: Optional[List[FileDefinition]] = None
    args: Optional[List[ArgDefinition]] = None
    secrets: Optional[List[str]] = None


# Executor base model
class Executor(BaseModel):
    type: ExecutorType
    config: Optional[Union[
        DockerExecutorConfig,
        SSHExecutorConfig, 
        HTTPExecutorConfig,
        MailExecutorConfig,
        JQExecutorConfig,
        DAGExecutorConfig,
        ToolExecutorConfig,
        KubiyaExecutorConfig,
        AgentExecutorConfig,
        Dict[str, Any]  # Fallback for custom executors
    ]] = None


# Step definitions
class BaseStep(BaseModel):
    """Base step model with common fields"""
    name: str
    description: Optional[str] = None
    depends: Optional[Union[str, List[str]]] = None
    id: Optional[str] = None  # Short identifier for referencing
    dir: Optional[str] = None  # Working directory
    output: Optional[str] = None  # Output variable name
    stdout: Optional[str] = None  # Redirect stdout to file
    stderr: Optional[str] = None  # Redirect stderr to file
    env: Optional[List[Union[str, Dict[str, str]]]] = None
    preconditions: Optional[List[Union[str, Precondition]]] = None
    retry_policy: Optional[RetryPolicy] = Field(None, alias="retryPolicy")
    repeat_policy: Optional[RepeatPolicy] = Field(None, alias="repeatPolicy")
    continue_on: Optional[ContinueOn] = Field(None, alias="continueOn")
    timeout_sec: Optional[int] = Field(None, alias="timeoutSec")
    signal_on_stop: SignalType = Field(SignalType.SIGTERM, alias="signalOnStop")
    mail_on_error: bool = Field(False, alias="mailOnError")
    
    model_config = ConfigDict(populate_by_name=True)


class CommandStep(BaseStep):
    """Step that executes a command"""
    command: str
    shell: Optional[str] = None


class ScriptStep(BaseStep):
    """Step that executes a script"""
    script: str
    shell: Optional[str] = None


class ExecutorStep(BaseStep):
    """Step that uses a specific executor"""
    executor: Executor
    command: Optional[str] = None
    script: Optional[str] = None


class DAGStep(BaseStep):
    """Step that runs another DAG/workflow"""
    run: str  # Path to the DAG file or DAG name
    params: Optional[str] = None


class ParallelStep(BaseStep):
    """Step that executes in parallel"""
    parallel: Union[List[str], ParallelConfig]
    run: Optional[str] = None  # Sub-workflow to run for each item
    command: Optional[str] = None
    script: Optional[str] = None
    executor: Optional[Executor] = None


# Union type for all step types
Step = Union[CommandStep, ScriptStep, ExecutorStep, DAGStep, ParallelStep]


# Handler definitions
class Handler(BaseModel):
    """Handler for workflow events"""
    command: Optional[str] = None
    script: Optional[str] = None
    executor: Optional[Executor] = None


class HandlerOn(BaseModel):
    """Handlers for different workflow events"""
    success: Optional[Handler] = None
    failure: Optional[Handler] = None
    cancel: Optional[Handler] = None
    exit: Optional[Handler] = None


# SMTP and email configuration
class SMTPConfig(BaseModel):
    """SMTP configuration for email notifications"""
    host: str
    port: str = "587"
    username: str
    password: str


class MailConfig(BaseModel):
    """Email configuration"""
    from_address: str = Field(alias="from")
    to: str
    prefix: Optional[str] = None
    attach_logs: bool = Field(False, alias="attachLogs")
    
    model_config = ConfigDict(populate_by_name=True)


class MailOn(BaseModel):
    """Email notification triggers"""
    success: bool = False
    failure: bool = True


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


# Queue configuration
class QueueConfig(BaseModel):
    """Queue configuration"""
    name: str
    max_active_runs: int = Field(1, alias="maxActiveRuns")
    
    model_config = ConfigDict(populate_by_name=True)


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
    params: Optional[List[Union[str, Parameter, Dict[str, Any]]]] = None
    env: Optional[List[Union[str, EnvironmentVariable, Dict[str, str]]]] = None
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
        populate_by_name=True,
        extra="allow"  # Allow extra fields for extensibility
    )
    
    @field_validator('steps', mode='before')
    @classmethod
    def validate_steps(cls, v):
        """Ensure steps is always a list"""
        if isinstance(v, dict):
            # Convert dict format to list format
            return [{"name": k, **step_def} for k, step_def in v.items()]
        return v


# Update forward references
ToolExecutorConfig.model_rebuild()
