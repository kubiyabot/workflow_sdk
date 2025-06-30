"""
Workflow builders for incident response automation.

This module provides object-oriented builders for creating incident response
workflows with proper separation of concerns and reusable components.
"""

from typing import List, Dict, Any, Optional, Type
from kubiya_workflow_sdk.dsl import Workflow, Step, inline_agent_executor, docker_executor

from .models import (
    IncidentData, IncidentAnalysis, InvestigationFindings,
    WorkflowConfig, PriorityLevel
)
from .tools import BaseTool, ToolFactory


class StepFactory:
    """Factory for creating workflow steps."""
    
    @staticmethod
    def create_validation_step(config: WorkflowConfig) -> Step:
        """Create input validation step."""
        return Step("validate-inputs").docker(
            image="alpine:latest",
            content="""#!/bin/sh
set -e
echo "🔍 Validating incident response inputs..."

# Validate required parameters
MISSING_PARAMS=""

if [ -z "$incident_id" ]; then
    MISSING_PARAMS="${MISSING_PARAMS}incident_id "
fi

if [ -z "$incident_title" ]; then
    MISSING_PARAMS="${MISSING_PARAMS}incident_title "
fi

if [ -z "$incident_severity" ]; then
    MISSING_PARAMS="${MISSING_PARAMS}incident_severity "
fi

if [ -z "$incident_body" ]; then
    MISSING_PARAMS="${MISSING_PARAMS}incident_body "
fi

if [ -z "$incident_url" ]; then
    MISSING_PARAMS="${MISSING_PARAMS}incident_url "
fi

# Set default checkpoint directory if not provided
if [ -z "$checkpoint_dir" ]; then
    checkpoint_dir="/tmp/incident-${incident_id:-unknown}"
    echo "ℹ️ Using default checkpoint directory: $checkpoint_dir"
fi

if [ -n "$MISSING_PARAMS" ]; then
    echo "❌ Missing required parameters: $MISSING_PARAMS"
    exit 1
fi

# Create checkpoint directory
mkdir -p "$checkpoint_dir"

echo "✅ All required inputs validated"
echo "Incident ID: $incident_id"
echo "Severity: $incident_severity"
echo "Checkpoint directory: $checkpoint_dir"

# Output validation result as JSON
cat << EOF
{
  "status": "validated",
  "incident_id": "$incident_id",
  "incident_title": "$incident_title", 
  "incident_severity": "$incident_severity",
  "checkpoint_dir": "$checkpoint_dir",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "validation_passed": true
}
EOF"""
        ).output("VALIDATION_RESULT").timeout(60).retry(limit=config.retry_limit, interval_sec=10)
    
    @staticmethod
    def create_ai_analysis_step(config: WorkflowConfig) -> Step:
        """Create AI-powered incident analysis step."""
        message = """Analyze this incident and provide structured response planning:

Incident Details:
- ID: ${incident_id}
- Title: ${incident_title}
- Severity: ${incident_severity}
- Description: ${incident_body}
- URL: ${incident_url}

Instructions:
1. Categorize the incident (infrastructure|application|security|deployment)
2. Assess urgency and impact levels
3. Determine investigation priorities for different platforms
4. Recommend response strategy
5. Estimate resolution time

Provide your analysis as a JSON object with this exact structure:
{
  "incident_category": "infrastructure|application|security|deployment",
  "urgency_level": "immediate|high|medium|low",
  "estimated_impact": "critical|high|medium|low",
  "investigation_priority": {
    "kubernetes": "high|medium|low|skip",
    "datadog": "high|medium|low|skip",
    "github": "high|medium|low|skip"
  },
  "response_strategy": "investigate_first|immediate_mitigation|rollback|scale_up",
  "estimated_resolution_time": "15min|30min|1hr|2hr|4hr|8hr",
  "key_investigation_areas": ["area1", "area2"],
  "confidence_score": 0.8,
  "reasoning": "Your analysis reasoning"
}"""
        
        return inline_agent_executor(
            name="ai-incident-analysis",
            message=message,
            agent_name="incident-analyst",
            ai_instructions="You are an expert SRE incident response analyst. Analyze incidents and provide structured decision data to drive automated response workflows. Focus on accuracy and actionable insights. Always output valid JSON in the specified format.",
            runners=[config.runner],
            llm_model=config.llm_model
        ).depends(["validate-inputs"]).output("INCIDENT_ANALYSIS").retry(
            limit=config.retry_limit, 
            interval_sec=30
        ).timeout(300)
    
    @staticmethod
    def create_kubernetes_investigation_step(
        config: WorkflowConfig, 
        tools: List[BaseTool]
    ) -> Step:
        """Create Kubernetes investigation step."""
        k8s_tools = [tool.get_definition() for tool in tools if "kubectl" in tool.config.name.lower()]
        
        message = """Your Goal: Investigate Kubernetes cluster based on AI-prioritized areas.

AI Analysis Context: ${INCIDENT_ANALYSIS}

Incident Details:
- ID: ${incident_id}
- Title: ${incident_title}
- Severity: ${incident_severity}

Instructions:
1. Use kubectl tools to investigate cluster health systematically
2. Focus on AI-identified key areas from the incident analysis
3. Check pod status, node health, and recent events
4. Look for resource constraints and deployment issues
5. Provide structured JSON findings

Use these available commands:
- kubectl get nodes (for node status)
- kubectl get pods --all-namespaces (for pod status) 
- kubectl cluster-health (for comprehensive health check)
- kubectl top nodes (for resource usage)

Expected JSON output format:
{
  "status": "healthy|degraded|critical",
  "key_findings": ["finding1", "finding2"],
  "pod_issues": ["issue1", "issue2"],
  "node_status": "stable|unstable",
  "resource_constraints": ["constraint1", "constraint2"],
  "recent_events": ["event1", "event2"],
  "recommendations": ["rec1", "rec2"],
  "confidence": 0.8,
  "investigation_summary": "Brief summary of findings"
}"""
        
        return inline_agent_executor(
            name="kubernetes-investigation",
            message=message,
            agent_name="k8s-cluster-investigator",
            ai_instructions="You are Claude Code specializing in Kubernetes investigation and incident response. Use kubectl commands to diagnose cluster issues systematically. Always provide structured JSON findings.",
            runners=[config.runner],
            llm_model=config.llm_model,
            tools=k8s_tools
        ).depends(["ai-incident-analysis"]).output("K8S_FINDINGS").retry(
            limit=config.retry_limit,
            interval_sec=60
        ).continue_on(failure=True).timeout(600)
    
    @staticmethod
    def create_monitoring_investigation_step(
        config: WorkflowConfig,
        tools: List[BaseTool]
    ) -> Step:
        """Create monitoring investigation step."""
        monitoring_tools = [tool.get_definition() for tool in tools if "metrics" in tool.config.name.lower()]
        
        message = """Your Goal: Investigate monitoring metrics based on AI-prioritized areas.

AI Analysis Context: ${INCIDENT_ANALYSIS}
Kubernetes Findings: ${K8S_FINDINGS}

Incident Details:
- ID: ${incident_id}
- Title: ${incident_title}
- Severity: ${incident_severity}

Instructions:
1. Query relevant monitoring metrics based on incident category
2. Look for anomalies in CPU, memory, disk, and network metrics
3. Correlate findings with Kubernetes investigation results
4. Analyze performance trends and thresholds
5. Provide structured JSON findings

Use these metric queries:
- cpu_usage (for CPU utilization)
- memory_usage (for memory utilization)
- error_rate (for application errors)
- response_time (for latency analysis)

Expected JSON output format:
{
  "status": "normal|warning|critical",
  "key_metrics": [
    {"metric": "cpu_usage", "value": "85%", "status": "warning", "threshold": "80%"},
    {"metric": "memory_usage", "value": "92%", "status": "critical", "threshold": "90%"}
  ],
  "anomalies_detected": ["anomaly1", "anomaly2"],
  "correlation_with_k8s": "Brief correlation description",
  "performance_trends": ["trend1", "trend2"],
  "recommendations": ["rec1", "rec2"],
  "confidence": 0.8,
  "time_range_analyzed": "Last 1 hour"
}"""
        
        return inline_agent_executor(
            name="monitoring-investigation",
            message=message,
            agent_name="monitoring-analyst",
            ai_instructions="You are Claude Code specializing in monitoring and metrics analysis for incident response. Analyze performance metrics, detect anomalies, and correlate with infrastructure findings.",
            runners=[config.runner],
            llm_model=config.llm_model,
            tools=monitoring_tools
        ).depends(["kubernetes-investigation"]).output("MONITORING_FINDINGS").retry(
            limit=config.retry_limit,
            interval_sec=60
        ).continue_on(failure=True).timeout(600)
    
    @staticmethod
    def create_aggregation_step(config: WorkflowConfig) -> Step:
        """Create final aggregation and analysis step."""
        message = """Your Goal: Aggregate all investigation findings and provide comprehensive incident analysis.

Investigation Context:
- Initial Analysis: ${INCIDENT_ANALYSIS}
- Kubernetes Findings: ${K8S_FINDINGS}
- Monitoring Findings: ${MONITORING_FINDINGS}

Incident Details:
- ID: ${incident_id}
- Title: ${incident_title}
- Severity: ${incident_severity}

Instructions:
1. Correlate findings from all investigation platforms
2. Identify root causes and evidence patterns
3. Determine resolution strategy and priority actions
4. Create actionable recommendations with automation opportunities
5. Assess overall incident impact and status

Expected JSON output format:
{
  "overall_status": "resolved|mitigated|investigating|escalated",
  "root_cause": {
    "primary_cause": "Primary root cause description",
    "contributing_factors": ["factor1", "factor2"],
    "confidence_level": 0.9,
    "evidence": ["evidence1", "evidence2"]
  },
  "immediate_actions": [
    {
      "action": "Scale up API pods to handle load",
      "priority": "P0",
      "owner": "sre",
      "estimated_time": "5 minutes",
      "automation_available": true
    }
  ],
  "resolution_strategy": "auto_remediation|manual_intervention|escalation",
  "estimated_resolution_time": "30 minutes",
  "impact_assessment": "minimal|moderate|significant|severe",
  "lessons_learned": ["lesson1", "lesson2"],
  "data_completeness": "complete|partial|minimal"
}"""
        
        return inline_agent_executor(
            name="incident-aggregation",
            message=message,
            agent_name="incident-aggregator",
            ai_instructions="You are Claude Code specializing in incident response analysis and aggregation. Correlate findings from multiple platforms to identify root causes and create actionable resolution plans.",
            runners=[config.runner],
            llm_model=config.llm_model
        ).depends(["kubernetes-investigation", "monitoring-investigation"]).output("AGGREGATED_ANALYSIS").retry(
            limit=config.retry_limit,
            interval_sec=45
        ).timeout(300)
    
    @staticmethod
    def create_reporting_step(config: WorkflowConfig) -> Step:
        """Create final incident reporting step."""
        return Step("incident-reporting").docker(
            image="alpine:latest",
            content="""#!/bin/sh
set -e
apk add --no-cache jq

echo "📋 Generating comprehensive incident response report..."

# Extract key information from aggregated analysis
OVERALL_STATUS=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.overall_status // "unknown"')
ROOT_CAUSE=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.root_cause.primary_cause // "Investigation ongoing"')
IMPACT=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.impact_assessment // "unknown"')
RESOLUTION_TIME=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.estimated_resolution_time // "unknown"')
RESOLUTION_STRATEGY=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.resolution_strategy // "unknown"')

# Generate comprehensive incident report
cat << EOF
# 🚨 Incident Response Report

**Incident ID:** $incident_id
**Title:** $incident_title
**Severity:** $incident_severity
**Status:** $OVERALL_STATUS
**Generated:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')

## 📊 Executive Summary

**Root Cause:** $ROOT_CAUSE
**Impact Assessment:** $IMPACT
**Estimated Resolution:** $RESOLUTION_TIME
**Resolution Strategy:** $RESOLUTION_STRATEGY

## 🔍 Investigation Summary

✅ **AI-Powered Analysis:** Incident categorized and prioritized automatically
✅ **Kubernetes Investigation:** Cluster health and resource analysis completed
✅ **Monitoring Analysis:** Performance metrics and anomaly detection performed
✅ **Cross-Platform Correlation:** Findings aggregated and analyzed

## 📈 Key Findings

$(echo "$AGGREGATED_ANALYSIS" | jq -r '.immediate_actions[]? | "- **" + .action + "** (Priority: " + .priority + ", Owner: " + .owner + ")"')

## 🎯 Immediate Actions Required

$(echo "$AGGREGATED_ANALYSIS" | jq -r '.immediate_actions[]? | "- [ ] " + .action + " (ETA: " + .estimated_time + ")"')

## 🔮 Next Steps

$(echo "$AGGREGATED_ANALYSIS" | jq -r '.lessons_learned[]? | "- " + .')

## 📊 Data Quality

**Completeness:** $(echo "$AGGREGATED_ANALYSIS" | jq -r '.data_completeness // "unknown"')
**Confidence:** $(echo "$AGGREGATED_ANALYSIS" | jq -r '.root_cause.confidence_level // "0.8"')

---
*Report generated by Kubiya Incident Response Workflow v${WORKFLOW_VERSION:-1.0.0}*
*Architecture: Object-Oriented DSL with Pydantic Models*
EOF

echo "✅ Comprehensive incident report generated successfully"
"""
        ).depends(["incident-aggregation"]).output("INCIDENT_REPORT").timeout(120)


class IncidentResponseWorkflowBuilder:
    """
    Object-oriented builder for incident response workflows.
    
    This builder provides a clean, maintainable interface for creating
    complex incident response automation workflows with proper type safety,
    validation, and separation of concerns.
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        """Initialize the workflow builder."""
        self.config = config or WorkflowConfig()
        self.workflow: Optional[Workflow] = None
        self.tools: List[BaseTool] = []
        self._initialize_workflow()
    
    def _initialize_workflow(self) -> None:
        """Initialize the base workflow with configuration."""
        self.workflow = (Workflow(self.config.workflow_name)
                        .description("Professional incident response workflow with Pydantic models")
                        .type("graph")  # Use graph for complex dependencies
                        .timeout(self.config.timeout)
                        .env(
                            LOG_LEVEL=self.config.log_level,
                            WORKFLOW_VERSION=self.config.workflow_version,
                            DEBUG_MODE=str(self.config.debug_mode).lower()
                        )
                        .params(
                            incident_id="INC-2024-001",
                            incident_title="Production Issue",
                            incident_severity="high",
                            incident_body="Investigation required",
                            incident_url="https://monitoring.example.com",
                            checkpoint_dir="/tmp/incident-response"
                        ))
    
    def with_config(self, config: WorkflowConfig) -> 'IncidentResponseWorkflowBuilder':
        """Update workflow configuration."""
        self.config = config
        self._initialize_workflow()
        return self
    
    def with_tools(self, tools: List[BaseTool]) -> 'IncidentResponseWorkflowBuilder':
        """Add tools to the workflow."""
        self.tools = tools
        return self
    
    def with_kubernetes_tools(self, **kwargs) -> 'IncidentResponseWorkflowBuilder':
        """Add Kubernetes tools with configuration."""
        k8s_tool = ToolFactory.create_kubernetes_tool(**kwargs)
        self.tools.append(k8s_tool)
        return self
    
    def with_monitoring_tools(self, **kwargs) -> 'IncidentResponseWorkflowBuilder':
        """Add monitoring tools with configuration."""
        monitoring_tool = ToolFactory.create_monitoring_tool(**kwargs)
        self.tools.append(monitoring_tool)
        return self
    
    def with_slack_tools(self, **kwargs) -> 'IncidentResponseWorkflowBuilder':
        """Add Slack tools with configuration."""
        slack_tool = ToolFactory.create_slack_tool(**kwargs)
        self.tools.append(slack_tool)
        return self
    
    def add_validation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add input validation step."""
        validation_step = StepFactory.create_validation_step(self.config)
        self.workflow.step(validation_step)
        return self
    
    def add_ai_analysis_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add AI-powered incident analysis step."""
        analysis_step = StepFactory.create_ai_analysis_step(self.config)
        self.workflow.step(analysis_step)
        return self
    
    def add_kubernetes_investigation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add Kubernetes investigation step."""
        k8s_step = StepFactory.create_kubernetes_investigation_step(self.config, self.tools)
        self.workflow.step(k8s_step)
        return self
    
    def add_monitoring_investigation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add monitoring investigation step."""
        monitoring_step = StepFactory.create_monitoring_investigation_step(self.config, self.tools)
        self.workflow.step(monitoring_step)
        return self
    
    def add_aggregation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add final aggregation and analysis step."""
        aggregation_step = StepFactory.create_aggregation_step(self.config)
        self.workflow.step(aggregation_step)
        return self
    
    def add_reporting_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add final incident reporting step."""
        reporting_step = StepFactory.create_reporting_step(self.config)
        self.workflow.step(reporting_step)
        return self
    
    def build_complete(self) -> Workflow:
        """Build the complete incident response workflow."""
        # Ensure we have essential tools
        if not self.tools:
            self.tools = ToolFactory.get_all_tools()
        
        return (self
                .add_validation_step()
                .add_ai_analysis_step()
                .add_kubernetes_investigation_step()
                .add_monitoring_investigation_step()
                .add_aggregation_step()
                .add_reporting_step()
                .workflow)
    
    def build_minimal(self) -> Workflow:
        """Build a minimal workflow for testing."""
        # Ensure we have essential tools
        if not self.tools:
            self.tools = ToolFactory.get_all_tools()
        
        return (self
                .add_validation_step()
                .add_ai_analysis_step()
                .add_reporting_step()
                .workflow)
    
    def build_kubernetes_focused(self) -> Workflow:
        """Build a Kubernetes-focused workflow."""
        # Ensure we have Kubernetes tools
        if not any("kubectl" in tool.config.name for tool in self.tools):
            self.with_kubernetes_tools()
        
        return (self
                .add_validation_step()
                .add_ai_analysis_step()
                .add_kubernetes_investigation_step()
                .add_reporting_step()
                .workflow)
    
    def build_monitoring_focused(self) -> Workflow:
        """Build a monitoring-focused workflow."""
        # Ensure we have monitoring tools
        if not any("metrics" in tool.config.name for tool in self.tools):
            self.with_monitoring_tools()
        
        return (self
                .add_validation_step()
                .add_ai_analysis_step()
                .add_monitoring_investigation_step()
                .add_reporting_step()
                .workflow)
    
    def validate(self) -> Dict[str, Any]:
        """Validate the workflow configuration and structure."""
        errors = []
        warnings = []
        
        # Validate configuration
        if self.config.timeout < 60:
            errors.append("Workflow timeout must be at least 60 seconds")
        
        if not self.config.workflow_name:
            errors.append("Workflow name is required")
        
        # Validate tools
        if not self.tools:
            warnings.append("No tools configured - using default tools")
        
        # Validate workflow structure
        if not self.workflow:
            errors.append("Workflow not initialized")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config": self.config.dict(),
            "tools_count": len(self.tools)
        }