#!/usr/bin/env python3
"""
Object-Oriented Incident Response Workflow using proper DSL patterns.
This workflow demonstrates best practices for building complex workflows using the Kubiya SDK DSL.
"""

from kubiya_workflow_sdk.dsl import (
    Workflow, Step, workflow, 
    docker_executor, shell_executor, python_executor, inline_agent_executor,
    retry_policy, continue_on, when, precondition
)
from typing import Dict, List, Any


class IncidentResponseWorkflowBuilder:
    """
    Object-oriented builder for incident response workflows following DSL best practices.
    Provides a clean, maintainable interface for creating complex incident response automation.
    """
    
    def __init__(self, workflow_name: str = "oo-incident-response"):
        """Initialize the workflow builder with default settings."""
        self.workflow_name = workflow_name
        self.workflow = None
        self._initialize_workflow()
    
    def _initialize_workflow(self) -> None:
        """Initialize the base workflow with common settings."""
        self.workflow = (Workflow(self.workflow_name)
                        .description("Object-oriented incident response workflow with Claude Code integration")
                        .type("graph")  # Use graph for complex dependencies
                        .timeout(3600)  # 1 hour timeout
                        .env(
                            LOG_LEVEL="info",
                            WORKFLOW_VERSION="2.0.0",
                            DEBUG_MODE="true"
                        )
                        .params(
                            incident_id="INC-2024-001",
                            incident_title="Production Issue",
                            incident_severity="high",
                            incident_body="Investigation required",
                            incident_url="https://monitoring.example.com",
                            checkpoint_dir="/tmp/incident-response"
                        ))
    
    def add_validation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add input validation step using Docker executor."""
        validation_step = (Step("validate-inputs")
                          .docker(
                              image="alpine:latest",
                              content="""#!/bin/sh
set -e
echo "🔍 Validating incident response inputs..."

# Validate required parameters
if [ -z "$incident_id" ]; then
    echo "❌ Missing incident_id"
    exit 1
fi

if [ -z "$incident_title" ]; then
    echo "❌ Missing incident_title" 
    exit 1
fi

if [ -z "$incident_severity" ]; then
    echo "❌ Missing incident_severity"
    exit 1
fi

# Create checkpoint directory
mkdir -p "$checkpoint_dir"
echo "✅ Checkpoint directory created: $checkpoint_dir"

# Output validation result
cat << EOF
{
  "status": "validated",
  "incident_id": "$incident_id",
  "incident_title": "$incident_title", 
  "incident_severity": "$incident_severity",
  "checkpoint_dir": "$checkpoint_dir",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF"""
                          )
                          .output("VALIDATION_RESULT")
                          .timeout(60)
                          .retry(limit=2, interval_sec=10))
        
        self.workflow.step(validation_step)
        return self
    
    def add_incident_analysis_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add AI-powered incident analysis using inline agent."""
        analysis_step = (Step("ai-incident-analysis")
                        .inline_agent(
                            name="incident-analyzer",
                            message="""Analyze this incident and provide structured response planning:

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

Provide your analysis as a JSON object with this structure:
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
}""",
                            agent_name="incident-analyst",
                            ai_instructions="You are an expert SRE incident response analyst. Analyze incidents and provide structured decision data to drive automated response workflows. Focus on accuracy and actionable insights.",
                            runners=["core-testing-2"],
                            llm_model="gpt-4o-mini",
                            is_debug_mode=True
                        )
                        .depends(["validate-inputs"])
                        .output("INCIDENT_ANALYSIS")
                        .retry(limit=2, interval_sec=30)
                        .timeout(300))
        
        self.workflow.step(analysis_step)
        return self
    
    def add_kubernetes_investigation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add Kubernetes investigation using Claude Code with kubectl tools."""
        k8s_step = (Step("kubernetes-investigation")
                   .inline_agent(
                       name="k8s-investigator",
                       message="""Your Goal: Investigate Kubernetes cluster based on AI-prioritized areas.

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
}""",
                       agent_name="k8s-cluster-investigator",
                       ai_instructions="You are Claude Code specializing in Kubernetes investigation and incident response. Use kubectl commands to diagnose cluster issues systematically. Always provide structured JSON findings.",
                       runners=["core-testing-2"],
                       llm_model="gpt-4o-mini",
                       is_debug_mode=True,
                       tools=[self._create_kubectl_tool()]
                   )
                   .depends(["ai-incident-analysis"])
                   .preconditions([
                       precondition('echo "${INCIDENT_ANALYSIS}" | jq -r \'.investigation_priority.kubernetes\'', 
                                  expected="re:(high|medium)")
                   ])
                   .output("K8S_FINDINGS")
                   .retry(limit=2, interval_sec=60)
                   .continue_on(failure=True)
                   .timeout(600))
        
        self.workflow.step(k8s_step)
        return self
    
    def add_monitoring_investigation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add monitoring/metrics analysis using Claude Code."""
        monitoring_step = (Step("monitoring-investigation")
                          .inline_agent(
                              name="monitoring-investigator",
                              message="""Your Goal: Investigate monitoring metrics based on AI-prioritized areas.

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
}""",
                              agent_name="monitoring-analyst",
                              ai_instructions="You are Claude Code specializing in monitoring and metrics analysis for incident response. Analyze performance metrics, detect anomalies, and correlate with infrastructure findings.",
                              runners=["core-testing-2"],
                              llm_model="gpt-4o-mini",
                              is_debug_mode=True,
                              tools=[self._create_monitoring_tool()]
                          )
                          .depends(["kubernetes-investigation"])
                          .preconditions([
                              precondition('echo "${INCIDENT_ANALYSIS}" | jq -r \'.investigation_priority.datadog\'',
                                         expected="re:(high|medium)")
                          ])
                          .output("MONITORING_FINDINGS")
                          .retry(limit=2, interval_sec=60)
                          .continue_on(failure=True)
                          .timeout(600))
        
        self.workflow.step(monitoring_step)
        return self
    
    def add_aggregation_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add final aggregation and analysis using Claude Code."""
        aggregation_step = (Step("incident-aggregation")
                           .inline_agent(
                               name="incident-aggregator",
                               message="""Your Goal: Aggregate all investigation findings and provide comprehensive incident analysis.

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
}""",
                               agent_name="incident-aggregator",
                               ai_instructions="You are Claude Code specializing in incident response analysis and aggregation. Correlate findings from multiple platforms to identify root causes and create actionable resolution plans.",
                               runners=["core-testing-2"],
                               llm_model="gpt-4o-mini",
                               is_debug_mode=True
                           )
                           .depends(["kubernetes-investigation", "monitoring-investigation"])
                           .output("AGGREGATED_ANALYSIS")
                           .retry(limit=2, interval_sec=45)
                           .timeout(300))
        
        self.workflow.step(aggregation_step)
        return self
    
    def add_reporting_step(self) -> 'IncidentResponseWorkflowBuilder':
        """Add final incident reporting step."""
        reporting_step = (Step("incident-reporting")
                         .docker(
                             image="alpine:latest",
                             content="""#!/bin/sh
set -e
apk add --no-cache jq

echo "📋 Generating incident response report..."

# Extract key information
OVERALL_STATUS=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.overall_status // "unknown"')
ROOT_CAUSE=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.root_cause.primary_cause // "Investigation ongoing"')
IMPACT=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.impact_assessment // "unknown"')
RESOLUTION_TIME=$(echo "$AGGREGATED_ANALYSIS" | jq -r '.estimated_resolution_time // "unknown"')

# Generate comprehensive report
cat << EOF
# 🚨 Incident Response Report

**Incident ID:** $incident_id
**Title:** $incident_title
**Severity:** $incident_severity
**Status:** $OVERALL_STATUS
**Time:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')

## 📊 Executive Summary

**Root Cause:** $ROOT_CAUSE
**Impact:** $IMPACT
**Estimated Resolution:** $RESOLUTION_TIME

## 🔍 Investigation Summary

- ✅ AI-powered incident analysis completed
- ✅ Kubernetes cluster investigation performed
- ✅ Monitoring metrics analysis conducted
- ✅ Cross-platform correlation completed

## 📈 Key Findings

$(echo "$AGGREGATED_ANALYSIS" | jq -r '.immediate_actions[]? | "- " + .action + " (Priority: " + .priority + ")"')

## 🎯 Next Steps

$(echo "$AGGREGATED_ANALYSIS" | jq -r '.lessons_learned[]? | "- " + .')

---
*Report generated by Object-Oriented Incident Response Workflow*
EOF

echo "✅ Incident report generated successfully"
"""
                         )
                         .depends(["incident-aggregation"])
                         .output("INCIDENT_REPORT")
                         .timeout(120))
        
        self.workflow.step(reporting_step)
        return self
    
    def _create_kubectl_tool(self) -> Dict[str, Any]:
        """Create kubectl tool definition for Kubernetes investigation."""
        return {
            "name": "kubectl",
            "alias": "kubectl",
            "description": "Execute kubectl commands for cluster investigation",
            "type": "docker",
            "image": "bitnami/kubectl:latest",
            "content": """#!/bin/bash
set -e

echo "🔧 Executing kubectl command: $command"

# Mock kubectl responses for demonstration
case "$command" in
    "get nodes")
        cat << 'EOF'
NAME           STATUS   ROLES    AGE   VERSION
node-1         Ready    master   30d   v1.28.0
node-2         Ready    worker   30d   v1.28.0
node-3         Ready    worker   30d   v1.28.0
EOF
        ;;
    "get pods --all-namespaces")
        cat << 'EOF'
NAMESPACE     NAME                                READY   STATUS    RESTARTS   AGE
kube-system   coredns-558bd4d5db-xyz123          1/1     Running   0          1d
default       api-server-abc123                  1/1     Running   0          2h
default       web-app-def456                     0/1     CrashLoopBackOff   5          1h
EOF
        ;;
    "top nodes")
        cat << 'EOF'
NAME      CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%   
node-1    250m         12%    2048Mi          64%       
node-2    1200m        60%    1536Mi          48%       
node-3    800m         40%    2560Mi          80%
EOF
        ;;
    *)
        echo "Executing: kubectl $command"
        echo "Mock response for demonstration purposes"
        ;;
esac""",
            "args": [
                {
                    "name": "command",
                    "type": "string",
                    "description": "kubectl command to execute",
                    "required": True
                }
            ]
        }
    
    def _create_monitoring_tool(self) -> Dict[str, Any]:
        """Create monitoring tool definition for metrics analysis."""
        return {
            "name": "metrics-query",
            "alias": "metrics",
            "description": "Query monitoring metrics for analysis",
            "type": "docker",
            "image": "alpine:latest",
            "content": """#!/bin/sh
set -e

echo "📊 Querying metrics: $query"

# Mock metrics responses for demonstration
case "$query" in
    "cpu_usage")
        cat << 'EOF'
{
  "metric": "cpu_usage",
  "value": 85.5,
  "unit": "percent",
  "timestamp": "2024-01-15T14:25:00Z",
  "status": "warning",
  "threshold": 80.0
}
EOF
        ;;
    "memory_usage")
        cat << 'EOF'
{
  "metric": "memory_usage", 
  "value": 78.2,
  "unit": "percent",
  "timestamp": "2024-01-15T14:25:00Z",
  "status": "normal",
  "threshold": 90.0
}
EOF
        ;;
    "error_rate")
        cat << 'EOF'
{
  "metric": "error_rate",
  "value": 12.5,
  "unit": "percent", 
  "timestamp": "2024-01-15T14:25:00Z",
  "status": "critical",
  "threshold": 5.0
}
EOF
        ;;
    *)
        echo '{"metric": "unknown", "value": 0, "status": "unknown"}'
        ;;
esac""",
            "args": [
                {
                    "name": "query",
                    "type": "string",
                    "description": "Metric query to execute",
                    "required": True
                }
            ]
        }
    
    def build(self) -> Workflow:
        """Build the complete workflow with all steps."""
        return (self
                .add_validation_step()
                .add_incident_analysis_step()
                .add_kubernetes_investigation_step()
                .add_monitoring_investigation_step()
                .add_aggregation_step()
                .add_reporting_step()
                .workflow)
    
    def build_minimal(self) -> Workflow:
        """Build a minimal version for testing."""
        return (self
                .add_validation_step()
                .add_incident_analysis_step()
                .add_reporting_step()
                .workflow)


def create_incident_response_workflow() -> Workflow:
    """Factory function to create the complete incident response workflow."""
    builder = IncidentResponseWorkflowBuilder("oo-incident-response-v2")
    return builder.build()


def create_minimal_incident_workflow() -> Workflow:
    """Factory function to create a minimal version for testing."""
    builder = IncidentResponseWorkflowBuilder("oo-incident-minimal")
    return builder.build_minimal()


if __name__ == "__main__":
    # Build both versions of the workflow
    full_workflow = create_incident_response_workflow()
    minimal_workflow = create_minimal_incident_workflow()
    
    # Validate workflows
    print("🧪 Object-Oriented Incident Response Workflow")
    print("=" * 60)
    
    full_validation = full_workflow.validate()
    minimal_validation = minimal_workflow.validate()
    
    if full_validation.get("errors"):
        print("❌ Full workflow validation errors:")
        for error in full_validation["errors"]:
            print(f"  - {error}")
    else:
        print("✅ Full workflow validation passed")
    
    if minimal_validation.get("errors"):
        print("❌ Minimal workflow validation errors:")
        for error in minimal_validation["errors"]:
            print(f"  - {error}")
    else:
        print("✅ Minimal workflow validation passed")
    
    # Compile workflows
    try:
        full_dict = full_workflow.to_dict()
        minimal_dict = minimal_workflow.to_dict()
        
        print(f"✅ Full workflow compiled: {len(full_dict['steps'])} steps")
        print(f"✅ Minimal workflow compiled: {len(minimal_dict['steps'])} steps")
        
        # Save compiled workflows
        import json
        import os
        
        output_dir = os.path.dirname(__file__)
        
        with open(os.path.join(output_dir, "compiled_oo_full_workflow.json"), "w") as f:
            json.dump(full_dict, f, indent=2)
        
        with open(os.path.join(output_dir, "compiled_oo_minimal_workflow.json"), "w") as f:
            json.dump(minimal_dict, f, indent=2)
        
        print("✅ Workflows saved to JSON files")
        
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\n🎉 Object-Oriented Workflow Builder Demonstration Complete!")
    print("Key Features:")
    print("- ✅ Clean object-oriented design with builder pattern")
    print("- ✅ Proper DSL usage with fluent interfaces")
    print("- ✅ Type hints and documentation")
    print("- ✅ Modular step construction")
    print("- ✅ Comprehensive error handling and retries")
    print("- ✅ Claude Code integration with custom tools")
    print("- ✅ Validation and compilation support")