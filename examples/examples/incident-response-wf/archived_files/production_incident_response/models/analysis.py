"""Analysis and investigation result models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """Status of tool installation and configuration."""
    INSTALLED = "installed"
    CONFIGURED = "configured" 
    READY = "ready"
    FAILED = "failed"
    SKIPPED = "skipped"


class Priority(str, Enum):
    """Action priority levels."""
    P0 = "P0"  # Critical - immediate action required
    P1 = "P1"  # High - action required within hours
    P2 = "P2"  # Medium - action required within days
    P3 = "P3"  # Low - action required eventually


class RecommendedAction(BaseModel):
    """Recommended action based on investigation."""
    
    action: str = Field(..., description="Description of the recommended action")
    tool: str = Field(..., description="Tool or command to execute the action")
    priority: Priority = Field(..., description="Action priority level")
    rationale: str = Field(..., description="Why this action is recommended")
    estimated_time: Optional[str] = Field(None, description="Estimated time to complete")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies before this action")


class ToolInstallationResult(BaseModel):
    """Result of tool installation and configuration."""
    
    tool_name: str = Field(..., description="Name of the tool")
    status: ToolStatus = Field(..., description="Installation/configuration status")
    version: Optional[str] = Field(None, description="Installed tool version")
    install_time: Optional[float] = Field(None, description="Time taken to install (seconds)")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if installation failed")
    
    # Validation results
    validation_passed: bool = Field(default=False, description="Whether validation commands passed")
    validation_output: Optional[str] = Field(None, description="Output from validation commands")


class InvestigationAnalysis(BaseModel):
    """Comprehensive analysis results from Claude Code investigation."""
    
    # Basic metadata
    incident_id: str = Field(..., description="Incident identifier")
    investigation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When investigation was performed")
    claude_code_status: str = Field(default="analysis_complete", description="Overall investigation status")
    
    # Tool installation results
    tools_installation: Dict[str, ToolInstallationResult] = Field(default_factory=dict, description="Tool installation results")
    
    # Environment setup
    environment_setup: Dict[str, Any] = Field(default_factory=dict, description="Environment configuration status")
    
    # Investigation findings
    investigation_summary: str = Field(..., description="High-level summary of investigation")
    detailed_findings: List[str] = Field(default_factory=list, description="Detailed investigation findings")
    
    # Analysis results
    root_cause_hypothesis: str = Field(..., description="Hypothesized root cause")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the analysis (0-1)")
    
    # Recommendations
    recommended_actions: List[RecommendedAction] = Field(default_factory=list, description="Recommended actions")
    next_steps: List[str] = Field(default_factory=list, description="Immediate next steps")
    
    # Technical analysis
    simulated_analysis: Dict[str, str] = Field(default_factory=dict, description="Simulated analysis results")
    
    # Claude Code integration status
    claude_code_integration: Dict[str, Any] = Field(default_factory=dict, description="Claude Code integration status")
    
    # Performance metrics
    total_investigation_time: Optional[float] = Field(None, description="Total time for investigation (seconds)")
    tools_ready_count: int = Field(default=0, description="Number of successfully configured tools")
    
    @property
    def success_rate(self) -> float:
        """Calculate tool installation success rate."""
        if not self.tools_installation:
            return 0.0
        
        successful = sum(1 for result in self.tools_installation.values() 
                        if result.status in [ToolStatus.READY, ToolStatus.CONFIGURED])
        return successful / len(self.tools_installation)
    
    @property
    def critical_actions(self) -> List[RecommendedAction]:
        """Get only critical (P0/P1) recommended actions."""
        return [action for action in self.recommended_actions 
                if action.priority in [Priority.P0, Priority.P1]]
    
    def to_slack_summary(self) -> str:
        """Generate Slack-friendly investigation summary."""
        status_emoji = {
            "analysis_complete": "✅",
            "analysis_partial": "⚠️", 
            "analysis_failed": "❌"
        }
        
        emoji = status_emoji.get(self.claude_code_status, "🔍")
        confidence_pct = int(self.confidence_score * 100)
        
        summary = (
            f"{emoji} **CLAUDE CODE INVESTIGATION COMPLETE**\n\n"
            f"**Incident:** {self.incident_id}\n"
            f"**Status:** {self.claude_code_status}\n"
            f"**Confidence:** {confidence_pct}%\n"
            f"**Tools Ready:** {self.tools_ready_count}/{len(self.tools_installation)}\n\n"
        )
        
        if self.tools_installation:
            summary += "🛠️ **Tools Configured:**\n"
            for tool_name, result in self.tools_installation.items():
                tool_emoji = "✅" if result.status == ToolStatus.READY else "❌"
                summary += f"• {tool_emoji} {tool_name}\n"
            summary += "\n"
        
        if self.critical_actions:
            summary += f"🚨 **Critical Actions ({len(self.critical_actions)}):**\n"
            for action in self.critical_actions[:3]:  # Show top 3
                summary += f"• [{action.priority}] {action.action[:80]}...\n"
            summary += "\n"
        
        summary += f"🎯 **Ready for interactive investigation**\n"
        summary += f"⏰ *Analysis completed at {self.investigation_timestamp.strftime('%H:%M:%S UTC')}*"
        
        return summary
    
    @classmethod
    def create_example(cls, incident_id: str) -> "InvestigationAnalysis":
        """Create an example analysis for testing."""
        
        # Example tool installation results
        tools_installation = {
            "kubectl": ToolInstallationResult(
                tool_name="kubectl",
                status=ToolStatus.READY,
                version="v1.28.0",
                install_time=45.2,
                validation_passed=True
            ),
            "datadog-cli": ToolInstallationResult(
                tool_name="datadog-cli", 
                status=ToolStatus.READY,
                version="0.47.0",
                install_time=32.1,
                validation_passed=True
            ),
            "claude-code": ToolInstallationResult(
                tool_name="claude-code",
                status=ToolStatus.CONFIGURED,
                version="1.0.0",
                install_time=67.8,
                validation_passed=True
            )
        }
        
        # Example recommended actions
        recommended_actions = [
            RecommendedAction(
                action="Check pod status and resource usage across all namespaces",
                tool="kubectl get pods --all-namespaces -o wide",
                priority=Priority.P1,
                rationale="High error rates often correlate with pod failures or resource constraints"
            ),
            RecommendedAction(
                action="Query Datadog for error rate and latency metrics during incident timeframe",
                tool="datadog CLI or API queries",
                priority=Priority.P1,
                rationale="Need baseline metrics to understand scope and timeline of the incident"
            ),
            RecommendedAction(
                action="Analyze recent deployments and configuration changes",
                tool="kubectl rollout history && argocd app list",
                priority=Priority.P2,
                rationale="Deployment changes are common root causes for incidents"
            )
        ]
        
        return cls(
            incident_id=incident_id,
            tools_installation=tools_installation,
            investigation_summary="Comprehensive multi-tool incident analysis completed using proper tool definitions",
            detailed_findings=[
                "🔍 kubectl: Cluster access configured - ready for pod and node analysis",
                "📊 Datadog CLI: API access available - metrics and alerts can be queried", 
                "🚀 ArgoCD: Deployment pipeline access ready - can check recent deployments",
                "📈 Observe: Trace and log analysis capabilities ready",
                "🔗 GitHub CLI: Code change analysis available - can review recent commits",
                "⚙️ Helm: Chart management ready - can analyze deployment configurations"
            ],
            root_cause_hypothesis="Multi-tool analysis indicates deployment-related incident with database connection issues",
            confidence_score=0.88,
            recommended_actions=recommended_actions,
            next_steps=[
                "Execute kubectl commands to investigate cluster state",
                "Query Datadog API for incident timeframe metrics", 
                "Check ArgoCD deployment history and sync status",
                "Analyze GitHub commit history for correlation"
            ],
            claude_code_integration={
                "all_tools_installed": True,
                "environment_ready": True,
                "investigation_framework": "complete",
                "ready_for_interactive_analysis": True,
                "execution_method": "proper_tool_definitions"
            },
            tools_ready_count=len([t for t in tools_installation.values() if t.status == ToolStatus.READY])
        )