"""Incident data models."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KubiyaMetadata(BaseModel):
    """Kubiya-specific metadata for incidents."""
    slack_channel_id: str = Field(..., description="Suggested Slack channel ID for war room")


class IncidentEvent(BaseModel):
    """Raw incident event from external systems (Datadog, PagerDuty, etc)."""
    
    id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., description="Incident title/summary")
    url: Optional[str] = Field(None, description="Link to incident in external system")
    severity: IncidentSeverity = Field(default=IncidentSeverity.MEDIUM, description="Incident severity")
    body: str = Field(default="", description="Detailed incident description")
    kubiya: KubiyaMetadata = Field(..., description="Kubiya workflow metadata")
    
    # Additional fields that might come from different systems
    source: Optional[str] = Field(None, description="Source system (datadog, pagerduty, etc)")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Incident tags")
    created_at: Optional[datetime] = Field(None, description="Incident creation timestamp")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Incident ID cannot be empty")
        return v.strip()
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError("Incident title cannot be empty")
        return v.strip()


class IncidentData(BaseModel):
    """Processed incident data used throughout the workflow."""
    
    incident_id: str = Field(..., description="Unique incident identifier")
    incident_title: str = Field(..., description="Incident title/summary")
    incident_severity: IncidentSeverity = Field(..., description="Incident severity level")
    incident_description: str = Field(default="", description="Detailed incident description")
    incident_url: Optional[str] = Field(None, description="Link to incident in external system")
    slack_channel_suggestion: str = Field(..., description="Suggested Slack channel ID")
    
    # Processing metadata
    parsed_at: datetime = Field(default_factory=datetime.utcnow, description="When incident was parsed")
    step_status: str = Field(default="completed", description="Processing step status")
    
    # Additional context
    source_system: Optional[str] = Field(None, description="Original source system")
    tags: Dict[str, str] = Field(default_factory=dict, description="Incident tags")
    
    @classmethod
    def from_incident_event(cls, event: IncidentEvent) -> "IncidentData":
        """Create IncidentData from raw IncidentEvent."""
        return cls(
            incident_id=event.id,
            incident_title=event.title,
            incident_severity=event.severity,
            incident_description=event.body,
            incident_url=event.url,
            slack_channel_suggestion=event.kubiya.slack_channel_id,
            source_system=event.source,
            tags=event.tags or {},
            parsed_at=datetime.utcnow(),
        )
    
    def to_slack_summary(self) -> str:
        """Generate Slack-friendly incident summary."""
        severity_emoji = {
            IncidentSeverity.CRITICAL: "🔴",
            IncidentSeverity.HIGH: "🟠", 
            IncidentSeverity.MEDIUM: "🟡",
            IncidentSeverity.LOW: "🟢"
        }
        
        emoji = severity_emoji.get(self.incident_severity, "⚪")
        
        return (
            f"{emoji} **{self.incident_severity.upper()} INCIDENT**\n\n"
            f"**ID:** {self.incident_id}\n"
            f"**Title:** {self.incident_title}\n"
            f"**Description:** {self.incident_description[:200]}{'...' if len(self.incident_description) > 200 else ''}\n"
            f"**Time:** {self.parsed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )