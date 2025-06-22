"""
API Models for Kubiya Workflow SDK Server

Comprehensive Pydantic models for request/response validation with:
- Full type safety
- OpenAPI schema generation
- Request validation
- Response serialization
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from enum import Enum

from ..core.types import WorkflowStatus, StepStatus, ExecutorType


# Base Models

class BaseRequest(BaseModel):
    """Base request model with common configuration."""
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {}
        }
    )


class BaseResponse(BaseModel):
    """Base response model with timestamp."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


# Workflow Models

class WorkflowExecutionRequest(BaseRequest):
    """Request to execute a workflow."""
    workflow: Dict[str, Any] = Field(
        ...,
        description="Workflow definition in Kubiya format",
        json_schema_extra={
            "example": {
                "name": "example-workflow",
                "version": "1.0.0",
                "steps": []
            }
        }
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Runtime parameters for workflow execution"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Execution options (timeout, retry policy, etc.)"
    )
    
    @field_validator('workflow')
    def validate_workflow_structure(cls, v):
        """Ensure workflow has required fields."""
        if not isinstance(v, dict):
            raise ValueError("Workflow must be a dictionary")
        if 'name' not in v:
            raise ValueError("Workflow must have a name")
        if 'steps' not in v or not isinstance(v['steps'], list):
            raise ValueError("Workflow must have a steps array")
        return v


class WorkflowExecutionResponse(BaseResponse):
    """Response for workflow execution request."""
    execution_id: str = Field(..., description="Unique execution identifier")
    status: WorkflowStatus = Field(..., description="Current execution status")
    message: str = Field(..., description="Status message")
    stream_url: Optional[str] = Field(
        None,
        description="URL for SSE streaming of execution events"
    )
    webhook_url: Optional[str] = Field(
        None,
        description="URL for webhook notifications"
    )


class WorkflowStatusResponse(BaseResponse):
    """Workflow execution status response."""
    execution_id: str
    status: WorkflowStatus
    workflow_name: str = Field(..., description="Name of the workflow")
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    outputs: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    step_count: int = Field(..., description="Total number of steps")
    completed_steps: int = Field(..., description="Number of completed steps")
    progress_percentage: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Execution progress percentage"
    )
    
    @model_validator(mode='after')
    def calculate_progress(self):
        """Calculate progress percentage."""
        if self.step_count > 0:
            self.progress_percentage = (self.completed_steps / self.step_count) * 100
        return self


class WorkflowValidationRequest(BaseRequest):
    """Request to validate a workflow."""
    workflow: Dict[str, Any] = Field(
        ...,
        description="Workflow definition to validate"
    )
    strict: bool = Field(
        default=True,
        description="Enable strict validation mode"
    )
    validate_executors: bool = Field(
        default=True,
        description="Validate executor configurations"
    )


class WorkflowValidationResponse(BaseResponse):
    """Workflow validation response."""
    valid: bool = Field(..., description="Whether the workflow is valid")
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation warnings"
    )
    info: List[str] = Field(
        default_factory=list,
        description="Informational messages"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Improvement suggestions"
    )


# Python Execution Models

class PythonExecutionRequest(BaseRequest):
    """Request to execute Python code."""
    code: str = Field(
        ...,
        description="Python code to execute",
        min_length=1,
        max_length=1_000_000  # 1MB limit
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Execution context (variables, imports, etc.)"
    )
    timeout: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Execution timeout in seconds"
    )
    capture_output: bool = Field(
        default=True,
        description="Capture stdout/stderr"
    )


class PythonExecutionResponse(BaseResponse):
    """Python execution response."""
    execution_id: str
    status: str = Field(..., description="Execution status (success/error)")
    output: Optional[str] = Field(None, description="Captured stdout")
    error: Optional[str] = Field(None, description="Error message if failed")
    traceback: Optional[str] = Field(None, description="Python traceback")
    results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution results (variables)"
    )
    duration_seconds: float = Field(..., description="Execution duration")


# Server Status Models

class ServerHealthResponse(BaseResponse):
    """Server health check response."""
    status: str = Field(..., description="Server health status")
    version: str = Field(..., description="Server version")
    uptime_seconds: Optional[float] = Field(
        None,
        description="Server uptime in seconds"
    )
    active_executions: int = Field(
        ...,
        description="Number of active workflow executions"
    )
    max_executions: int = Field(
        ...,
        description="Maximum concurrent executions allowed"
    )
    memory_usage_mb: Optional[float] = Field(
        None,
        description="Current memory usage in MB"
    )
    cpu_percent: Optional[float] = Field(
        None,
        description="Current CPU usage percentage"
    )


class ServerConfigResponse(BaseResponse):
    """Server configuration response."""
    version: str
    api_prefix: str
    max_concurrent_executions: int
    execution_timeout: int
    keep_alive_interval: int
    features: Dict[str, bool] = Field(
        ...,
        description="Enabled server features"
    )
    supported_executors: List[ExecutorType] = Field(
        default_factory=lambda: list(ExecutorType)
    )
    authentication_required: bool = Field(
        default=False,
        description="Whether authentication is required"
    )


# SSE Event Models

class SSEEventType(str, Enum):
    """Server-sent event types."""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRY = "step_retry"
    LOG = "log"
    OUTPUT = "output"
    ERROR = "error"
    KEEP_ALIVE = "keep_alive"


class SSEEvent(BaseModel):
    """Server-sent event structure."""
    id: Optional[str] = Field(None, description="Event ID")
    event: SSEEventType = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    retry: Optional[int] = Field(None, description="Retry delay in milliseconds")
    
    def to_sse_string(self) -> str:
        """Convert to SSE format string."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"event: {self.event.value}")
        lines.append(f"data: {self.data}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        lines.append("")  # Empty line to end event
        return "\n".join(lines)


# Step Execution Models

class StepExecutionEvent(BaseModel):
    """Step execution event for SSE streaming."""
    execution_id: str
    step_name: str
    status: StepStatus
    timestamp: datetime
    duration_seconds: Optional[float] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Error Models

class ErrorResponse(BaseResponse):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type/category")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracing"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Workflow validation failed",
                "error_type": "ValidationError",
                "details": {
                    "field": "steps",
                    "message": "Steps cannot be empty"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )


# Batch Operations

class BatchWorkflowExecutionRequest(BaseRequest):
    """Request to execute multiple workflows."""
    workflows: List[WorkflowExecutionRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of workflows to execute"
    )
    execution_mode: str = Field(
        default="parallel",
        pattern="^(parallel|sequential)$",
        description="How to execute the workflows"
    )
    stop_on_failure: bool = Field(
        default=False,
        description="Stop batch execution on first failure"
    )


class BatchWorkflowExecutionResponse(BaseResponse):
    """Response for batch workflow execution."""
    batch_id: str = Field(..., description="Batch execution ID")
    total_workflows: int
    execution_ids: List[str] = Field(
        ...,
        description="Individual workflow execution IDs"
    )
    status: str = Field(..., description="Batch status")


# Pagination Models

class PaginationParams(BaseModel):
    """Common pagination parameters."""
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum items to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )
    sort_by: Optional[str] = Field(
        None,
        description="Field to sort by"
    )
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order"
    )


class PaginatedResponse(BaseResponse):
    """Base paginated response."""
    total: int = Field(..., description="Total number of items")
    limit: int
    offset: int
    has_more: bool = Field(..., description="Whether more items exist")
    
    @model_validator(mode='after')
    def calculate_has_more(self):
        """Calculate if more items exist."""
        self.has_more = (self.offset + self.limit) < self.total
        return self


# Export all models
__all__ = [
    # Base
    "BaseRequest",
    "BaseResponse",
    
    # Workflow
    "WorkflowExecutionRequest",
    "WorkflowExecutionResponse",
    "WorkflowStatusResponse",
    "WorkflowValidationRequest",
    "WorkflowValidationResponse",
    
    # Python
    "PythonExecutionRequest",
    "PythonExecutionResponse",
    
    # Server
    "ServerHealthResponse",
    "ServerConfigResponse",
    
    # Events
    "SSEEventType",
    "SSEEvent",
    "StepExecutionEvent",
    
    # Error
    "ErrorResponse",
    
    # Batch
    "BatchWorkflowExecutionRequest",
    "BatchWorkflowExecutionResponse",
    
    # Pagination
    "PaginationParams",
    "PaginatedResponse",
] 