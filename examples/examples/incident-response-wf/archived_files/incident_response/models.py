"""
Pydantic models for incident response workflow.

This module defines all data models used throughout the incident response
workflow system with proper type validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator


class SeverityLevel(str, Enum):
    """Incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UrgencyLevel(str, Enum):
    """Incident urgency levels."""
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ImpactLevel(str, Enum):
    """Incident impact levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class PriorityLevel(str, Enum):
    """Investigation priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SKIP = "skip"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InvestigationCategory(str, Enum):
    """Types of incident categories."""
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    NETWORK = "network"
    SECURITY = "security"
    DATA = "data"
    DEPLOYMENT = "deployment"


class ResolutionStrategy(str, Enum):
    """Available resolution strategies."""
    INVESTIGATE_FIRST = "investigate_first"
    IMMEDIATE_MITIGATION = "immediate_mitigation"
    ROLLBACK = "rollback"
    SCALE_UP = "scale_up"
    EXTERNAL_SUPPORT = "external_support"
    RESTART_CASCADE = "restart_cascade"
    AUTO_REMEDIATION = "auto_remediation"
    MANUAL_INTERVENTION = "manual_intervention"
    ESCALATION = "escalation"


class IncidentData(BaseModel):
    """Core incident data model."""
    
    incident_id: str = Field(..., description="Unique incident identifier")
    incident_title: str = Field(..., description="Human-readable incident title")
    incident_severity: SeverityLevel = Field(..., description="Incident severity level")
    incident_body: str = Field(..., description="Detailed incident description")
    incident_url: str = Field(..., description="Link to incident details")
    
    # Optional fields with defaults
    incident_customer_impact: Optional[str] = Field(None, description="Customer impact description")
    incident_services: List[Dict[str, Any]] = Field(default_factory=list, description="Affected services")
    incident_tags: List[str] = Field(default_factory=list, description="Incident tags")
    incident_created_by: Optional[str] = Field(None, description="Incident creator")
    incident_created_at: Optional[datetime] = Field(None, description="Incident creation time")
    checkpoint_dir: str = Field("/tmp/incident-response", description="Checkpoint directory")
    
    # Datadog webhook specific
    datadog_event_payload: Optional[str] = Field(None, description="Raw Datadog webhook payload")
    
    @validator('incident_severity', pre=True)
    def validate_severity(cls, v):
        """Normalize severity values."""
        if isinstance(v, str):
            return v.lower()
        return v
    
    @validator('incident_url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('incident_url must be a valid HTTP/HTTPS URL')
        return v
    
    @validator('checkpoint_dir')
    def validate_checkpoint_dir(cls, v):
        """Ensure checkpoint directory is absolute path."""
        if not v.startswith('/'):
            return f"/tmp/{v}"
        return v


class InvestigationPriority(BaseModel):
    """Investigation priorities for different platforms."""
    
    kubernetes: PriorityLevel = Field(PriorityLevel.MEDIUM, description="Kubernetes investigation priority")
    datadog: PriorityLevel = Field(PriorityLevel.MEDIUM, description="Datadog investigation priority")
    github: PriorityLevel = Field(PriorityLevel.LOW, description="GitHub investigation priority")
    argocd: PriorityLevel = Field(PriorityLevel.LOW, description="ArgoCD investigation priority")
    observe: PriorityLevel = Field(PriorityLevel.LOW, description="Observe investigation priority")


class AutomationRecommendations(BaseModel):
    """Automation recommendations for incident response."""
    
    auto_scaling: bool = Field(False, description="Recommend auto-scaling")
    circuit_breaker: bool = Field(False, description="Recommend circuit breaker")
    traffic_routing: bool = Field(False, description="Recommend traffic routing")
    rollback: bool = Field(False, description="Recommend rollback")
    restart_services: bool = Field(False, description="Recommend service restart")


class IncidentAnalysis(BaseModel):
    """AI-generated incident analysis results."""
    
    incident_category: InvestigationCategory = Field(..., description="Incident category")
    urgency_level: UrgencyLevel = Field(..., description="Urgency assessment")
    estimated_impact: ImpactLevel = Field(..., description="Estimated impact level")
    affected_systems: List[str] = Field(default_factory=list, description="List of affected systems")
    
    investigation_priority: InvestigationPriority = Field(
        default_factory=InvestigationPriority,
        description="Platform investigation priorities"
    )
    
    escalation_required: bool = Field(False, description="Whether escalation is required")
    estimated_resolution_time: str = Field("1hr", description="Estimated resolution time")
    response_strategy: ResolutionStrategy = Field(
        ResolutionStrategy.INVESTIGATE_FIRST,
        description="Recommended response strategy"
    )
    
    key_investigation_areas: List[str] = Field(
        default_factory=list,
        description="Key areas to investigate"
    )
    
    automation_recommendations: AutomationRecommendations = Field(
        default_factory=AutomationRecommendations,
        description="Automation recommendations"
    )
    
    confidence_score: float = Field(0.8, ge=0.0, le=1.0, description="Analysis confidence score")
    reasoning: str = Field("", description="Analysis reasoning")


class MetricStatus(str, Enum):
    """Metric status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class Metric(BaseModel):
    """Individual metric data."""
    
    name: str = Field(..., description="Metric name")
    value: Union[float, str] = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    status: MetricStatus = Field(MetricStatus.NORMAL, description="Metric status")
    threshold: Optional[Union[float, str]] = Field(None, description="Metric threshold")
    timestamp: Optional[datetime] = Field(None, description="Metric timestamp")


class InvestigationFindings(BaseModel):
    """Generic investigation findings model."""
    
    status: str = Field(..., description="Overall investigation status")
    key_findings: List[str] = Field(default_factory=list, description="Key findings")
    metrics: List[Metric] = Field(default_factory=list, description="Relevant metrics")
    anomalies_detected: List[str] = Field(default_factory=list, description="Detected anomalies")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="Findings confidence")
    investigation_summary: str = Field("", description="Summary of investigation")


class KubernetesFindings(InvestigationFindings):
    """Kubernetes-specific investigation findings."""
    
    pod_issues: List[str] = Field(default_factory=list, description="Pod-related issues")
    node_status: str = Field("unknown", description="Node status summary")
    resource_constraints: List[str] = Field(default_factory=list, description="Resource constraints")
    recent_events: List[str] = Field(default_factory=list, description="Recent cluster events")
    deployment_health: Dict[str, str] = Field(default_factory=dict, description="Deployment health status")


class MonitoringFindings(InvestigationFindings):
    """Monitoring-specific investigation findings."""
    
    time_range_analyzed: str = Field("1h", description="Time range analyzed")
    correlation_with_k8s: str = Field("", description="Correlation with Kubernetes findings")
    performance_trends: List[str] = Field(default_factory=list, description="Performance trends")
    alert_history: List[str] = Field(default_factory=list, description="Recent alerts")


class ActionItem(BaseModel):
    """Individual action item."""
    
    action: str = Field(..., description="Action description")
    priority: str = Field("P2", description="Action priority (P0-P3)")
    owner: str = Field("sre", description="Action owner")
    estimated_time: str = Field("unknown", description="Estimated completion time")
    automation_available: bool = Field(False, description="Whether automation is available")


class RootCause(BaseModel):
    """Root cause analysis."""
    
    primary_cause: str = Field(..., description="Primary root cause")
    contributing_factors: List[str] = Field(default_factory=list, description="Contributing factors")
    confidence_level: float = Field(0.8, ge=0.0, le=1.0, description="Confidence in root cause")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")


class AggregatedAnalysis(BaseModel):
    """Final aggregated analysis results."""
    
    overall_status: str = Field(..., description="Overall incident status")
    root_cause: RootCause = Field(..., description="Root cause analysis")
    immediate_actions: List[ActionItem] = Field(default_factory=list, description="Immediate actions needed")
    resolution_strategy: ResolutionStrategy = Field(..., description="Resolution strategy")
    estimated_resolution_time: str = Field("unknown", description="Estimated resolution time")
    impact_assessment: ImpactLevel = Field(..., description="Impact assessment")
    automation_success: List[str] = Field(default_factory=list, description="Successful automations")
    next_steps: List[str] = Field(default_factory=list, description="Next steps")
    lessons_learned: List[str] = Field(default_factory=list, description="Lessons learned")
    data_completeness: str = Field("partial", description="Data completeness assessment")


class WorkflowConfig(BaseModel):
    """Workflow configuration settings."""
    
    workflow_name: str = Field("incident-response", description="Workflow name")
    workflow_version: str = Field("1.0.0", description="Workflow version")
    runner: str = Field("core-testing-2", description="Workflow runner")
    timeout: int = Field(3600, description="Workflow timeout in seconds")
    retry_limit: int = Field(3, description="Default retry limit")
    debug_mode: bool = Field(True, description="Enable debug mode")
    
    # LLM settings
    llm_model: str = Field("gpt-4o-mini", description="Default LLM model")
    llm_temperature: float = Field(0.1, ge=0.0, le=2.0, description="LLM temperature")
    
    # Environment settings
    log_level: str = Field("info", description="Logging level")
    checkpoint_enabled: bool = Field(True, description="Enable checkpointing")
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout is reasonable."""
        if v < 60:
            raise ValueError('Timeout must be at least 60 seconds')
        if v > 14400:  # 4 hours
            raise ValueError('Timeout cannot exceed 4 hours')
        return v


class ExecutionResult(BaseModel):
    """Workflow execution result."""
    
    execution_id: Optional[str] = Field(None, description="Execution ID")
    workflow_id: Optional[str] = Field(None, description="Workflow ID")
    status: WorkflowStatus = Field(WorkflowStatus.PENDING, description="Execution status")
    
    # Results
    incident_data: Optional[IncidentData] = Field(None, description="Input incident data")
    incident_analysis: Optional[IncidentAnalysis] = Field(None, description="AI incident analysis")
    kubernetes_findings: Optional[KubernetesFindings] = Field(None, description="Kubernetes findings")
    monitoring_findings: Optional[MonitoringFindings] = Field(None, description="Monitoring findings")
    aggregated_analysis: Optional[AggregatedAnalysis] = Field(None, description="Final analysis")
    
    # Execution metadata
    start_time: Optional[datetime] = Field(None, description="Execution start time")
    end_time: Optional[datetime] = Field(None, description="Execution end time")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Execution errors")
    warnings: List[str] = Field(default_factory=list, description="Execution warnings")
    
    # Step results
    step_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Individual step results")
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.status == WorkflowStatus.COMPLETED and not self.errors
    
    def get_duration(self) -> Optional[float]:
        """Calculate execution duration."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return self.duration_seconds


class ValidationError(BaseModel):
    """Validation error details."""
    
    field: str = Field(..., description="Field with error")
    message: str = Field(..., description="Error message")
    value: Any = Field(None, description="Invalid value")


class ValidationResult(BaseModel):
    """Validation result."""
    
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")