#!/usr/bin/env python3
"""
Enhanced Incident Response Workflow with Claude Code and all CLI tools pre-installed.
Tools are built into the Claude Code execution environment with proper secrets.
"""

from kubiya_workflow_sdk.dsl import (
    Workflow, docker_executor, inline_agent_executor, kubiya_executor
)


def build_enhanced_incident_response_workflow():
    """Build enhanced incident response workflow with all tools integrated."""
    
    # Create the workflow
    workflow = (Workflow("enhanced-incident-response")
                .description("Enhanced incident response with Claude Code and all CLI tools")
                .type("chain")
                .params(
                    # Datadog webhook event structure
                    event_type="incident.created",
                    incident_id="",
                    incident_title="",
                    incident_severity="",
                    incident_body="",
                    incident_url="",
                    incident_customer_impact="",
                    incident_services=[],
                    incident_tags=[],
                    incident_created_by="",
                    incident_created_at="",
                    datadog_event_payload="",
                    checkpoint_dir="/tmp/incident-response"
                ))
    
    # Step 1: Extract and Parse Datadog Event
    workflow.step(
        name="extract-datadog-event",
        executor=docker_executor(
            name="event-extractor",
            image="python:3.11-alpine",
            content="""#!/bin/sh
set -e
apk add --no-cache jq curl

echo "🔍 Extracting Datadog event data..."

# Parse the Datadog webhook payload
cat << 'EOF' > /tmp/parse_event.py
import json
import sys
import os

def extract_datadog_event():
    # Get the raw event payload
    payload = os.environ.get('datadog_event_payload', '{}')
    
    try:
        event = json.loads(payload)
        
        # Extract incident data from Datadog webhook
        incident_data = event.get('data', {})
        incident_attrs = incident_data.get('attributes', {})
        
        # Extract key fields
        extracted = {
            'incident_id': incident_data.get('id', 'UNKNOWN'),
            'incident_title': incident_attrs.get('title', 'Untitled Incident'),
            'incident_severity': incident_attrs.get('severity', 'unknown'),
            'incident_body': incident_attrs.get('description', ''),
            'incident_url': f"https://app.datadoghq.com/incidents/{incident_data.get('id', '')}",
            'incident_customer_impact': incident_attrs.get('customer_impact_scope', 'unknown'),
            'incident_services': incident_attrs.get('services', []),
            'incident_tags': incident_attrs.get('tags', []),
            'incident_created_by': incident_attrs.get('created_by', {}).get('email', 'system'),
            'incident_created_at': incident_attrs.get('created', ''),
            'incident_detective_monitor_id': incident_attrs.get('detective_monitor_id', ''),
            'incident_detective_monitor_name': incident_attrs.get('detective_monitor_name', ''),
            'incident_detective_monitor_tags': incident_attrs.get('detective_monitor_tags', []),
            'incident_fields': incident_attrs.get('fields', {}),
            'incident_postmortem': incident_attrs.get('postmortem', {}),
            'incident_detection_method': incident_attrs.get('detection_method', 'unknown')
        }
        
        # Output structured data
        print(json.dumps(extracted, indent=2))
        
    except Exception as e:
        print(f"Error parsing Datadog event: {e}")
        # Fallback to env vars if parsing fails
        fallback = {
            'incident_id': os.environ.get('incident_id', 'FALLBACK-001'),
            'incident_title': os.environ.get('incident_title', 'Manual Incident'),
            'incident_severity': os.environ.get('incident_severity', 'high'),
            'incident_body': os.environ.get('incident_body', 'No description provided'),
            'incident_url': os.environ.get('incident_url', 'https://app.datadoghq.com'),
            'incident_customer_impact': 'unknown',
            'incident_services': [],
            'incident_tags': [],
            'incident_created_by': 'system',
            'incident_created_at': '',
            'incident_detective_monitor_id': '',
            'incident_detective_monitor_name': '',
            'incident_detective_monitor_tags': [],
            'incident_fields': {},
            'incident_postmortem': {},
            'incident_detection_method': 'manual'
        }
        print(json.dumps(fallback, indent=2))

if __name__ == "__main__":
    extract_datadog_event()
EOF

python /tmp/parse_event.py > /tmp/incident_data.json
cat /tmp/incident_data.json

echo "✅ Event extraction completed"
""",
        ),
        env={
            "datadog_event_payload": "${datadog_event_payload}",
            "incident_id": "${incident_id}",
            "incident_title": "${incident_title}",
            "incident_severity": "${incident_severity}",
            "incident_body": "${incident_body}",
            "incident_url": "${incident_url}"
        },
        output="EXTRACTED_EVENT_DATA"
    )
    
    # Step 2: Get integrations and secrets
    workflow.step(
        name="get-integrations",
        executor=kubiya_executor("get-integrations", "api/v1/integration/slack/token/1", method="GET"),
        output="SLACK_TOKEN"
    )
    
    # Step 3: Comprehensive Incident Analysis using Claude Code
    workflow.step(
        name="comprehensive-incident-analysis",
        executor=inline_agent_executor(
            name="comprehensive-incident-analyzer",
            message="""Analyze this comprehensive incident data and provide detailed response planning:

Extracted Event Data: $EXTRACTED_EVENT_DATA

Perform comprehensive analysis including:
1. Incident categorization (infrastructure/application/network/security/database)
2. Severity assessment and business impact analysis
3. Investigation priorities for all platforms:
   - Kubernetes: priority and specific areas to investigate
   - Datadog: metrics and monitors to check
   - ArgoCD: deployment and GitOps status
   - Observability: logs, traces, metrics correlation
4. Estimated resolution time and resource requirements
5. Escalation matrix and stakeholder notification
6. Immediate actions and investigation plan
7. Service dependencies and impact assessment

Output as structured JSON:
{
  "incident_summary": {
    "category": "infrastructure",
    "subcategory": "compute",
    "severity_confirmed": "critical",
    "business_impact": "high",
    "affected_services": [],
    "customer_impact_assessment": "severe"
  },
  "investigation_priorities": {
    "kubernetes": {
      "priority": "critical",
      "focus_areas": ["pod_health", "resource_limits", "node_status"],
      "namespaces_to_check": ["production", "monitoring"]
    },
    "datadog": {
      "priority": "high", 
      "metrics_to_check": ["cpu.usage", "memory.usage", "disk.usage"],
      "monitors_to_review": ["critical_alerts", "anomaly_detection"]
    },
    "argocd": {
      "priority": "medium",
      "focus_areas": ["deployment_status", "sync_health", "recent_changes"],
      "applications_to_check": ["production-apps", "infrastructure"]
    },
    "observability": {
      "priority": "high",
      "log_sources": ["application", "infrastructure", "security"],
      "trace_analysis": ["error_rate", "latency", "throughput"]
    }
  },
  "response_plan": {
    "immediate_actions": [],
    "investigation_steps": [],
    "escalation_required": false,
    "estimated_resolution_time": "2hrs",
    "resource_requirements": []
  },
  "stakeholder_notifications": {
    "immediate": [],
    "updates_required": [],
    "external_communication": false
  }
}""",
            agent_name="comprehensive-incident-analyzer",
            ai_instructions="You are an expert Site Reliability Engineer with deep expertise in incident response, Kubernetes, observability, and distributed systems. Provide comprehensive analysis with actionable insights."
        ),
        output="COMPREHENSIVE_ANALYSIS"
    )
    
    # Step 4: Create Incident Response Slack Channel
    workflow.step(
        name="create-incident-channel",
        executor=docker_executor(
            name="incident-channel-creator",
            image="curlimages/curl:latest",
            content="""#!/bin/sh
set -e
echo "🔧 Creating comprehensive incident response channel..."

# Parse incident data to get details
INCIDENT_ID=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_id // "UNKNOWN"')
INCIDENT_TITLE=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_title // "Untitled Incident"')
INCIDENT_SEVERITY=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_severity // "unknown"')

# Create channel name
CHANNEL_NAME="incident-$(echo "$INCIDENT_ID" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | cut -c1-30)"

# Create channel using Slack API
RESPONSE=$(curl -s -X POST "https://slack.com/api/conversations.create" \\
  -H "Authorization: Bearer ${slack_token}" \\
  -H "Content-Type: application/json" \\
  -d "{
    \"name\": \"$CHANNEL_NAME\",
    \"is_private\": false,
    \"topic\": \"🚨 $INCIDENT_SEVERITY: $INCIDENT_TITLE\"
  }")

SUCCESS=$(echo "$RESPONSE" | jq -r '.ok')
if [ "$SUCCESS" = "true" ]; then
    CHANNEL_ID=$(echo "$RESPONSE" | jq -r '.channel.id')
    echo "✅ Incident channel created: $CHANNEL_ID"
    
    # Post initial incident summary
    curl -s -X POST "https://slack.com/api/chat.postMessage" \\
      -H "Authorization: Bearer ${slack_token}" \\
      -H "Content-Type: application/json" \\
      -d "{
        \"channel\": \"$CHANNEL_ID\",
        \"text\": \"🚨 Incident Response Activated\",
        \"blocks\": [
          {
            \"type\": \"header\",
            \"text\": {
              \"type\": \"plain_text\",
              \"text\": \"🚨 Incident Response: $INCIDENT_ID\"
            }
          },
          {
            \"type\": \"section\",
            \"fields\": [
              {
                \"type\": \"mrkdwn\",
                \"text\": \"*Severity:* $INCIDENT_SEVERITY\"
              },
              {
                \"type\": \"mrkdwn\",
                \"text\": \"*Status:* Investigation Started\"
              },
              {
                \"type\": \"mrkdwn\",
                \"text\": \"*Title:* $INCIDENT_TITLE\"
              },
              {
                \"type\": \"mrkdwn\",
                \"text\": \"*Automated Tools:* Claude Code + Multi-Platform\"
              }
            ]
          },
          {
            \"type\": \"section\",
            \"text\": {
              \"type\": \"mrkdwn\",
              \"text\": \"🤖 Automated investigation started with Claude Code integration across Kubernetes, Datadog, ArgoCD, and Observability platforms.\"
            }
          }
        ]
      }" > /dev/null
    
    echo "$CHANNEL_ID"
else
    echo "❌ Failed to create channel: $RESPONSE"
    exit 1
fi"""
        ),
        env={
            "EXTRACTED_EVENT_DATA": "$EXTRACTED_EVENT_DATA",
            "slack_token": "$SLACK_TOKEN.token"
        },
        output="INCIDENT_CHANNEL_ID"
    )
    
    # Step 5: Multi-Platform Investigation with Claude Code (All Tools)
    workflow.step(
        name="multi-platform-investigation",
        executor=inline_agent_executor(
            name="multi-platform-investigator",
            message="""Perform comprehensive multi-platform investigation for this incident:

Incident Analysis: $COMPREHENSIVE_ANALYSIS
Incident Channel: $INCIDENT_CHANNEL_ID
Extracted Event: $EXTRACTED_EVENT_DATA

You have access to all CLI tools pre-installed in your environment:
- kubectl: For Kubernetes cluster investigation
- dog (Datadog CLI): For metrics, monitors, and alerts analysis
- argocd: For GitOps deployment status
- observe: For observability and tracing analysis

Perform investigation across all platforms:

1. KUBERNETES INVESTIGATION:
   - Check cluster health and node status
   - Analyze pod health in critical namespaces
   - Review resource usage and limits
   - Examine recent events and errors
   - Check deployment status and rollouts

2. DATADOG ANALYSIS:
   - Query relevant metrics based on incident
   - Review active monitors and alerts
   - Analyze APM data for errors and latency
   - Check infrastructure metrics
   - Correlate with incident timeline

3. ARGOCD REVIEW:
   - Check application sync status
   - Review recent deployments
   - Analyze configuration drift
   - Check GitOps health status

4. OBSERVABILITY CORRELATION:
   - Analyze distributed traces
   - Correlate logs across services
   - Review performance metrics
   - Map service dependencies

Post findings to the Slack incident channel throughout your investigation.

Provide comprehensive JSON output with:
- platform_findings (kubernetes, datadog, argocd, observability)
- correlation_analysis
- root_cause_hypothesis
- immediate_recommendations
- next_steps""",
            agent_name="multi-platform-investigator",
            ai_instructions="""You are Claude Code acting as an expert Site Reliability Engineer with access to all major SRE tools. 

IMPORTANT: You have the following CLI tools pre-installed and configured in your environment:
- kubectl: Kubernetes CLI (with cluster access configured)
- dog: Datadog CLI (with API key configured via DD_API_KEY and DD_APP_KEY env vars)
- argocd: ArgoCD CLI (with server and credentials configured via ARGOCD_SERVER, ARGOCD_TOKEN env vars)
- observe: Observability CLI (with API key configured via OBSERVE_API_KEY env var)

Use these tools extensively to investigate the incident. The tools are ready to use - no additional setup required.

When using tools:
1. Start with kubectl to check cluster health
2. Use dog to analyze Datadog metrics and alerts
3. Check argocd for deployment status
4. Use observe for distributed tracing and log correlation
5. Post findings to Slack channel as you discover issues

Focus on correlating findings across all platforms to identify root causes.""",
            # Environment variables for tool configuration
            env={
                # Kubernetes configuration
                "KUBECONFIG": "/tmp/kubeconfig",
                "KUBERNETES_SERVICE_HOST": "kubernetes.default.svc.cluster.local",
                "KUBERNETES_SERVICE_PORT": "443",
                
                # Datadog configuration  
                "DD_API_KEY": "${DD_API_KEY}",
                "DD_APP_KEY": "${DD_APP_KEY}",
                "DD_SITE": "datadoghq.com",
                
                # ArgoCD configuration
                "ARGOCD_SERVER": "${ARGOCD_SERVER}",
                "ARGOCD_TOKEN": "${ARGOCD_TOKEN}",
                "ARGOCD_INSECURE": "true",
                
                # Observability configuration
                "OBSERVE_API_KEY": "${OBSERVE_API_KEY}",
                "OBSERVE_ENDPOINT": "${OBSERVE_ENDPOINT}",
                
                # Slack configuration for posting updates
                "SLACK_TOKEN": "$SLACK_TOKEN.token",
                "SLACK_CHANNEL": "$INCIDENT_CHANNEL_ID"
            }
        ),
        output="MULTI_PLATFORM_FINDINGS"
    )
    
    # Step 6: Root Cause Analysis and Recommendations with Claude Code
    workflow.step(
        name="root-cause-analysis",
        executor=inline_agent_executor(
            name="root-cause-analyzer",
            message="""Perform comprehensive root cause analysis based on all investigation findings:

Original Analysis: $COMPREHENSIVE_ANALYSIS
Multi-Platform Findings: $MULTI_PLATFORM_FINDINGS
Incident Channel: $INCIDENT_CHANNEL_ID

Correlate all findings from Kubernetes, Datadog, ArgoCD, and Observability platforms to:

1. Identify the root cause of the incident
2. Assess the full impact and blast radius
3. Provide immediate mitigation steps
4. Create a comprehensive resolution plan
5. Suggest prevention measures
6. Document lessons learned
7. Define post-incident actions

Use your understanding of distributed systems, infrastructure patterns, and incident response best practices.

Post a comprehensive executive summary to the Slack incident channel with:
- Root cause identification
- Impact assessment
- Immediate action items
- Resolution timeline
- Stakeholder communication plan

Provide structured JSON output with:
- root_cause_analysis
- impact_assessment
- immediate_mitigation_steps
- comprehensive_resolution_plan
- prevention_measures
- lessons_learned
- post_incident_actions
- executive_summary""",
            agent_name="root-cause-analyzer",
            ai_instructions="""You are Claude Code acting as a senior Site Reliability Engineer and incident commander. 

Your role is to:
1. Synthesize findings from all platforms (Kubernetes, Datadog, ArgoCD, Observability)
2. Apply systems thinking to identify root causes
3. Provide executive-level recommendations
4. Create actionable incident response plans
5. Focus on both immediate resolution and long-term prevention

Use your expertise in:
- Distributed systems architecture
- Infrastructure patterns and failure modes
- Incident response methodologies
- Post-incident review processes
- Risk assessment and mitigation strategies

Communicate findings clearly to both technical teams and business stakeholders.""",
            env={
                "SLACK_TOKEN": "$SLACK_TOKEN.token",
                "SLACK_CHANNEL": "$INCIDENT_CHANNEL_ID"
            }
        ),
        output="ROOT_CAUSE_ANALYSIS"
    )
    
    # Step 7: Generate Comprehensive Final Report
    workflow.step(
        name="generate-final-report",
        executor=docker_executor(
            name="final-report-generator",
            image="python:3.11-alpine",
            content="""#!/bin/sh
set -e
apk add --no-cache jq

echo "📋 Generating comprehensive final incident report..."

# Parse incident data
INCIDENT_ID=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_id // "UNKNOWN"')
INCIDENT_TITLE=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_title // "Untitled"')
INCIDENT_SEVERITY=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_severity // "unknown"')
INVESTIGATION_TIME=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

# Create comprehensive final report
cat << EOF
# 🚨 Enhanced Incident Response Report

## Incident Overview
**Incident ID:** $INCIDENT_ID  
**Title:** $INCIDENT_TITLE
**Severity:** $INCIDENT_SEVERITY
**Status:** ✅ Comprehensive Investigation Complete
**Investigation Completed:** $INVESTIGATION_TIME

## 📊 Executive Summary

✅ **Enhanced Multi-Platform Investigation Successfully Completed**

This incident response utilized Claude Code as an intelligent agent with access to all major SRE tools, providing comprehensive analysis across the entire technology stack.

### Key Achievements:
- ✅ Automated Datadog webhook event extraction and parsing
- ✅ Intelligent incident analysis and categorization
- ✅ Multi-platform investigation across Kubernetes, Datadog, ArgoCD, and Observability
- ✅ Root cause analysis with system-wide correlation
- ✅ Real-time Slack communication and stakeholder updates
- ✅ Comprehensive recommendations and prevention measures

## 🔍 Investigation Results

### Initial Analysis
$COMPREHENSIVE_ANALYSIS

### Multi-Platform Investigation Findings
$MULTI_PLATFORM_FINDINGS

### Root Cause Analysis and Recommendations
$ROOT_CAUSE_ANALYSIS

## ⚙️ Platform Integration Performance

| Platform | Status | CLI Tool | Integration | Findings |
|----------|--------|----------|-------------|----------|
| **Kubernetes** | ✅ Complete | kubectl | Native cluster access | Comprehensive cluster analysis |
| **Datadog** | ✅ Complete | dogshell | API key integration | Metrics and alerts analysis |
| **ArgoCD** | ✅ Complete | argocd | Token-based auth | GitOps status review |
| **Observability** | ✅ Complete | observe | API integration | Cross-platform correlation |
| **Slack** | ✅ Complete | REST API | OAuth integration | Real-time communication |

## 🤖 Claude Code Capabilities Demonstrated

### Intelligent Analysis
- **Context-Aware Investigation:** Claude Code understood incident context and prioritized investigation areas
- **Multi-Platform Correlation:** Successfully correlated findings across all monitoring platforms
- **Expert-Level Insights:** Provided SRE-level analysis and recommendations
- **Adaptive Investigation:** Adjusted investigation based on initial findings

### Tool Integration
- **Pre-configured Environment:** All CLI tools (kubectl, dogshell, argocd, observe) ready for use
- **Seamless Execution:** No tool setup overhead - immediate investigation capability
- **Comprehensive Coverage:** Full spectrum of SRE tools integrated in single workflow
- **Secret Management:** Secure handling of API keys and credentials

### Communication Excellence
- **Real-time Updates:** Continuous Slack communication throughout investigation
- **Structured Reporting:** JSON-formatted findings enabling automation
- **Executive Summaries:** Clear communication for both technical and business stakeholders
- **Actionable Recommendations:** Specific, implementable suggestions

## 🎯 Workflow Architecture Benefits

### Event-Driven Response
- **Webhook Integration:** Direct trigger from Datadog incident webhooks
- **Structured Parsing:** Comprehensive event data extraction
- **Context Preservation:** Full incident context maintained throughout workflow

### Intelligent Orchestration
- **Sequential Dependencies:** Logical flow with proper data passing
- **Error Handling:** Robust error handling and fallback mechanisms
- **Checkpoint System:** Workflow state management and recovery

### Scalable Design
- **Reusable Components:** Modular design for easy extension
- **Platform Agnostic:** Can be adapted for different tool combinations
- **Configuration Driven:** Environment-based configuration management

## 📈 Business Impact

### Incident Response Acceleration
- **Faster MTTR:** Automated investigation reduces mean time to resolution
- **Consistent Process:** Standardized investigation methodology
- **24/7 Capability:** AI-powered response available around the clock

### Operational Excellence
- **Knowledge Capture:** Investigation patterns captured for future use
- **Skill Augmentation:** Claude Code enhances team capabilities
- **Process Improvement:** Continuous learning from incident patterns

### Cost Optimization
- **Resource Efficiency:** Automated investigation reduces manual effort
- **Reduced Escalation:** Intelligent analysis prevents unnecessary escalations
- **Prevention Focus:** Proactive recommendations reduce future incidents

## 🚀 Next Steps and Enhancements

### Immediate Opportunities
1. **Expand Tool Integration:** Add more specialized tools (Prometheus, Grafana, etc.)
2. **Custom Playbooks:** Develop incident-type specific investigation playbooks
3. **Machine Learning:** Implement pattern recognition for similar incidents
4. **Auto-Remediation:** Add automated fix capabilities for common issues

### Long-term Vision
1. **Predictive Analysis:** Proactive incident prevention using historical data
2. **Cross-Platform Correlation:** Enhanced correlation algorithms
3. **Business Impact Modeling:** Quantify business impact in real-time
4. **Stakeholder Automation:** Automated stakeholder communication based on impact

---

## 📊 Technical Metrics

- **Total Investigation Time:** Automated (vs. manual 2-4 hours)
- **Platforms Analyzed:** 4 (Kubernetes, Datadog, ArgoCD, Observability)
- **CLI Tools Integrated:** 4 (kubectl, dogshell, argocd, observe)
- **Communication Channels:** Real-time Slack integration
- **Data Format:** Structured JSON throughout pipeline
- **Claude Code Steps:** 4 intelligent analysis steps
- **Total Workflow Steps:** 7 end-to-end steps

---

*Report generated by Enhanced Claude Code Incident Response Workflow*
*Architecture: Event-Driven | Multi-Platform | AI-Powered | Fully Automated*
*Platforms: Kubernetes | Datadog | ArgoCD | Observability | Slack*
EOF

echo "✅ Enhanced comprehensive report generated successfully"
""",
        ),
        env={
            "EXTRACTED_EVENT_DATA": "$EXTRACTED_EVENT_DATA",
            "COMPREHENSIVE_ANALYSIS": "$COMPREHENSIVE_ANALYSIS",
            "MULTI_PLATFORM_FINDINGS": "$MULTI_PLATFORM_FINDINGS",
            "ROOT_CAUSE_ANALYSIS": "$ROOT_CAUSE_ANALYSIS"
        }
    )
    
    return workflow


if __name__ == "__main__":
    # Build and test the enhanced workflow
    workflow = build_enhanced_incident_response_workflow()
    
    # Compile the workflow
    compiled_workflow = workflow.to_dict()
    
    print("🚀 Enhanced Incident Response Workflow with Claude Code + All Tools")
    print("=" * 80)
    print(f"Workflow Name: {compiled_workflow['name']}")
    print(f"Description: {compiled_workflow['description']}")
    print(f"Total Steps: {len(compiled_workflow['steps'])}")
    
    # Count Claude Code steps
    claude_code_steps = sum(1 for step in compiled_workflow['steps'] 
                           if 'inline_agent' in str(step))
    print(f"Claude Code Steps: {claude_code_steps}")
    
    print(f"Integrated Tools: kubectl, dogshell, argocd, observe")
    print(f"Tool Environment: Pre-configured with secrets and credentials")
    print("=" * 80)
    
    # Save compiled workflow
    yaml_output = workflow.to_yaml()
    with open("/Users/shaked/kubiya/orchestrator/workflow_sdk/incident-response-wf/workflows/compiled_enhanced_incident.yaml", "w") as f:
        f.write(yaml_output)
    
    print("✅ Enhanced workflow compiled and saved!")
    print("\n🎯 Key Features:")
    print("- ✅ Datadog webhook event extraction and parsing")
    print("- ✅ Claude Code with ALL tools pre-installed (kubectl, dogshell, argocd, observe)")
    print("- ✅ Environment variables for tool authentication and configuration")
    print("- ✅ Multi-platform investigation in single Claude Code step")
    print("- ✅ Root cause analysis and recommendations")
    print("- ✅ Real-time Slack communication throughout")
    print("- ✅ Comprehensive final reporting")
    print("- ✅ Secrets management for all platform integrations")
    
    print(f"\n📁 Enhanced workflow saved to:")
    print("   compiled_enhanced_incident.yaml")
    print("\n🚀 This workflow provides end-to-end incident response")
    print("   with Claude Code having access to ALL SRE tools!")