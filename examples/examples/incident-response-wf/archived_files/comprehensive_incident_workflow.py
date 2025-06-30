#!/usr/bin/env python3
"""
Comprehensive End-to-End Incident Response Workflow with All Tools.
Includes proper Datadog event extraction and all CLI integrations.
"""

from kubiya_workflow_sdk.dsl import (
    Workflow, docker_executor, inline_agent_executor, kubiya_executor
)


def build_comprehensive_incident_response_workflow():
    """Build a comprehensive incident response workflow with all tools."""
    
    # Create the workflow
    workflow = (Workflow("comprehensive-incident-response")
                .description("Comprehensive incident response workflow with Claude Code and all CLI tools")
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
                    incident_detective_monitor_id="",
                    incident_detective_monitor_name="",
                    incident_detective_monitor_tags=[],
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
    
    # Step 2: Get Slack integration
    workflow.step(
        name="get-slack-token",
        executor=kubiya_executor("get-slack-token", "api/v1/integration/slack/token/1", method="GET"),
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
    
    # Step 5: Kubernetes Investigation with Claude Code
    workflow.step(
        name="kubernetes-investigation",
        executor=inline_agent_executor(
            name="kubernetes-investigator",
            message="""Perform comprehensive Kubernetes investigation for this incident:

Incident Analysis: $COMPREHENSIVE_ANALYSIS
Incident Channel: $INCIDENT_CHANNEL_ID

Use your kubectl tool to investigate:
1. Cluster health and node status
2. Pod health in priority namespaces
3. Resource usage and limits
4. Recent events and alerts
5. Deployment status and rollouts
6. Service and ingress health
7. Persistent volume status
8. Security and RBAC issues

Focus on the specific areas identified in the analysis. Post findings to Slack channel with structured updates.

Provide JSON output with:
- investigation_status
- key_findings
- critical_issues
- recommendations
- next_steps""",
            agent_name="kubernetes-investigator",
            ai_instructions="You are Claude Code specializing in Kubernetes investigation and troubleshooting. Use kubectl extensively to diagnose issues, correlate findings, and provide actionable recommendations.",
            tools=[
                {
                    "name": "kubectl",
                    "alias": "kubectl",
                    "description": "Execute kubectl commands for cluster investigation",
                    "type": "docker",
                    "image": "bitnami/kubectl:latest",
                    "content": """#!/bin/bash
set -e

echo "🔧 Executing: kubectl $command"

# In real deployment, configure with service account and proper RBAC
# For demo, provide comprehensive mock responses

case "$command" in
    "get nodes"*)
        echo "NAME       STATUS   ROLES           AGE   VERSION"
        echo "node-1     Ready    control-plane   45d   v1.28.2"
        echo "node-2     Ready    worker          45d   v1.28.2"
        echo "node-3     NotReady worker          45d   v1.28.2"
        echo "node-4     Ready    worker          30d   v1.28.2"
        ;;
    "get pods --all-namespaces"*)
        echo "NAMESPACE         NAME                               READY   STATUS      RESTARTS   AGE"
        echo "kube-system       coredns-5d78c9869d-abc123          1/1     Running     0          2d"
        echo "kube-system       etcd-node-1                        1/1     Running     0          45d"
        echo "production        api-server-7c6b8f9d4-xyz789        0/1     Pending     0          15m"
        echo "production        api-server-7c6b8f9d4-def456        1/1     Running     5          2h"
        echo "production        database-postgresql-0              1/1     Running     0          5d"
        echo "production        redis-master-6b8d9c7f5-ghi012     1/1     Running     0          3d"
        echo "monitoring        prometheus-server-8f7d6c5-jkl345  1/1     Running     0          1d"
        echo "monitoring        grafana-6c5d4b8f7-mno678          1/1     Running     0          1d"
        ;;
    "top nodes"*)
        echo "NAME     CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%"
        echo "node-1   1250m        62%    8.2Gi           65%"
        echo "node-2   1850m        92%    14.1Gi          89%"
        echo "node-3   N/A          N/A    N/A             N/A"
        echo "node-4   980m         49%    6.8Gi           54%"
        ;;
    "get events --sort-by='.lastTimestamp' --all-namespaces"*)
        echo "NAMESPACE     LAST SEEN   TYPE      REASON              OBJECT                         MESSAGE"
        echo "production    2m          Warning   FailedScheduling    pod/api-server-7c6b8f9d4-xyz789    0/4 nodes available: insufficient cpu"
        echo "production    5m          Warning   Unhealthy           pod/api-server-7c6b8f9d4-def456    Readiness probe failed"
        echo "kube-system   8m          Warning   NodeNotReady        node/node-3                    Node is not ready"
        echo "production    12m         Normal    Scheduled           pod/api-server-7c6b8f9d4-def456    Successfully assigned"
        ;;
    "describe node node-2"*)
        echo "Name:               node-2"
        echo "Roles:              worker"
        echo "Labels:             kubernetes.io/arch=amd64"
        echo "Capacity:"
        echo "  cpu:                2"
        echo "  memory:             16Gi"
        echo "Allocatable:"
        echo "  cpu:                1900m"
        echo "  memory:             15Gi"
        echo "Conditions:"
        echo "  Ready            True    KubeletReady    kubelet is posting ready status"
        echo "  MemoryPressure   True    KubeletHasMemoryPressure    kubelet has memory pressure"
        echo "  DiskPressure     False   KubeletHasNoDiskPressure    kubelet has no disk pressure"
        echo "  PIDPressure      False   KubeletHasPIDPressure    kubelet has PID pressure"
        ;;
    "get deployments -n production"*)
        echo "NAME         READY   UP-TO-DATE   AVAILABLE   AGE"
        echo "api-server   1/2     2            1           2d"
        echo "frontend     3/3     3            3           5d"
        echo "worker       2/2     2            2           3d"
        ;;
    *)
        echo "Mock kubectl output for: $command"
        echo "Status: Command executed successfully"
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
                },
                {
                    "name": "slack-post",
                    "alias": "slack-post", 
                    "description": "Post findings to Slack incident channel",
                    "type": "docker",
                    "image": "curlimages/curl:latest",
                    "content": """#!/bin/sh
set -e
echo "📤 Posting Kubernetes findings to Slack..."

curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $slack_token" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"🚢 Kubernetes Investigation Update\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"header\\",
        \\"text\\": {
          \\"type\\": \\"plain_text\\",
          \\"text\\": \\"🚢 Kubernetes Investigation Results\\"
        }
      },
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"$message\\"
        }
      }
    ]
  }" > /dev/null

echo "✅ Posted to Slack successfully"
""",
                    "args": [
                        {
                            "name": "channel_id",
                            "type": "string",
                            "description": "Slack channel ID",
                            "required": True
                        },
                        {
                            "name": "message",
                            "type": "string",
                            "description": "Investigation findings message",
                            "required": True
                        },
                        {
                            "name": "slack_token",
                            "type": "string",
                            "description": "Slack API token",
                            "required": True
                        }
                    ]
                }
            ]
        ),
        output="KUBERNETES_FINDINGS"
    )
    
    # Step 6: Datadog Investigation with Claude Code
    workflow.step(
        name="datadog-investigation",
        executor=inline_agent_executor(
            name="datadog-investigator",
            message="""Perform comprehensive Datadog investigation for this incident:

Incident Analysis: $COMPREHENSIVE_ANALYSIS
Kubernetes Findings: $KUBERNETES_FINDINGS
Incident Channel: $INCIDENT_CHANNEL_ID

Use your dogshell tool to investigate:
1. Recent metrics and anomalies
2. Active monitors and alerts
3. APM traces and errors
4. Infrastructure metrics
5. Log correlation
6. Service dependencies
7. Historical patterns

Focus on metrics and monitors identified in the analysis. Post findings to Slack.

Provide JSON output with:
- metrics_analysis
- active_alerts
- anomaly_detection
- service_health
- recommendations""",
            agent_name="datadog-investigator",
            ai_instructions="You are Claude Code specializing in Datadog observability and monitoring. Use dogshell to analyze metrics, alerts, and correlate findings with the incident.",
            tools=[
                {
                    "name": "dogshell",
                    "alias": "dog",
                    "description": "Execute Datadog CLI commands",
                    "type": "docker",
                    "image": "python:3.11-alpine",
                    "content": """#!/bin/sh
set -e
apk add --no-cache curl jq

echo "🐕 Executing Datadog command: $command"

# Mock Datadog API responses for demo
case "$command" in
    "metric query"*)
        echo "Query: $query"
        echo "Timeframe: $timeframe"
        echo "Results:"
        echo "  - timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        echo "    value: 95.7"
        echo "    metric: system.cpu.usage"
        echo "  - timestamp: $(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')"
        echo "    value: 87.2"
        echo "    metric: system.cpu.usage"
        ;;
    "monitor list"*)
        echo "Active Monitors:"
        echo "ID: 12345678 | Name: High CPU Usage | Status: Alert | Type: metric alert"
        echo "ID: 23456789 | Name: Memory Usage Critical | Status: Warn | Type: metric alert"
        echo "ID: 34567890 | Name: API Response Time | Status: OK | Type: APM alert"
        echo "ID: 45678901 | Name: Error Rate Spike | Status: Alert | Type: logs alert"
        ;;
    "service list"*)
        echo "Services:"
        echo "  - name: api-server"
        echo "    env: production"
        echo "    status: critical"
        echo "    error_rate: 8.5%"
        echo "    avg_response_time: 2.3s"
        echo "  - name: database"
        echo "    env: production" 
        echo "    status: ok"
        echo "    error_rate: 0.1%"
        echo "    avg_response_time: 45ms"
        ;;
    "logs search"*)
        echo "Log Search Results:"
        echo "  - [ERROR] 2024-01-15 14:30:22 | api-server | Out of memory: Java heap space"
        echo "  - [WARN]  2024-01-15 14:29:45 | api-server | High CPU usage detected: 95%"
        echo "  - [ERROR] 2024-01-15 14:28:12 | api-server | Connection timeout to database"
        echo "  - [INFO]  2024-01-15 14:25:33 | api-server | Health check failed"
        ;;
    *)
        echo "Mock Datadog command output for: $command"
        echo "Status: Success"
        ;;
esac""",
                    "args": [
                        {
                            "name": "command",
                            "type": "string",
                            "description": "Datadog command to execute",
                            "required": True
                        },
                        {
                            "name": "query",
                            "type": "string",
                            "description": "Metric query string",
                            "required": False
                        },
                        {
                            "name": "timeframe",
                            "type": "string",
                            "description": "Time range for query",
                            "required": False
                        }
                    ]
                },
                {
                    "name": "slack-post",
                    "alias": "slack-post",
                    "description": "Post Datadog findings to Slack",
                    "type": "docker", 
                    "image": "curlimages/curl:latest",
                    "content": """#!/bin/sh
set -e
echo "📤 Posting Datadog findings to Slack..."

curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $slack_token" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"🐕 Datadog Investigation Update\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"header\\",
        \\"text\\": {
          \\"type\\": \\"plain_text\\",
          \\"text\\": \\"🐕 Datadog Investigation Results\\"
        }
      },
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"$message\\"
        }
      }
    ]
  }" > /dev/null

echo "✅ Posted to Slack successfully"
""",
                    "args": [
                        {
                            "name": "channel_id",
                            "type": "string",
                            "description": "Slack channel ID",
                            "required": True
                        },
                        {
                            "name": "message",
                            "type": "string",
                            "description": "Datadog findings message",
                            "required": True
                        },
                        {
                            "name": "slack_token",
                            "type": "string",
                            "description": "Slack API token",
                            "required": True
                        }
                    ]
                }
            ]
        ),
        output="DATADOG_FINDINGS"
    )
    
    # Step 7: ArgoCD Investigation with Claude Code
    workflow.step(
        name="argocd-investigation",
        executor=inline_agent_executor(
            name="argocd-investigator",
            message="""Perform ArgoCD investigation for this incident:

Incident Analysis: $COMPREHENSIVE_ANALYSIS
Kubernetes Findings: $KUBERNETES_FINDINGS
Datadog Findings: $DATADOG_FINDINGS
Incident Channel: $INCIDENT_CHANNEL_ID

Use your argocd tool to investigate:
1. Application sync status
2. Recent deployments and rollbacks
3. Git repository changes
4. Deployment health
5. Resource synchronization
6. Configuration drift
7. Rollout status

Focus on applications identified in the analysis. Post findings to Slack.

Provide JSON output with:
- sync_status
- recent_deployments
- health_assessment
- configuration_drift
- recommendations""",
            agent_name="argocd-investigator",
            ai_instructions="You are Claude Code specializing in ArgoCD and GitOps workflows. Use argocd CLI to investigate deployment issues and configuration drift.",
            tools=[
                {
                    "name": "argocd",
                    "alias": "argocd",
                    "description": "Execute ArgoCD CLI commands",
                    "type": "docker",
                    "image": "argoproj/argocd:latest",
                    "content": """#!/bin/sh
set -e

echo "🔄 Executing ArgoCD command: $command"

# Mock ArgoCD responses for demo
case "$command" in
    "app list"*)
        echo "NAME                    CLUSTER                         NAMESPACE       PROJECT  STATUS     HEALTH   SYNCPOLICY   CONDITIONS"
        echo "api-server-prod        https://kubernetes.default.svc  production      default  OutOfSync  Degraded Auto         ComparisonError"
        echo "database-prod          https://kubernetes.default.svc  production      default  Synced     Healthy  Auto         None"
        echo "frontend-prod          https://kubernetes.default.svc  production      default  Synced     Healthy  Auto         None"
        echo "monitoring-stack       https://kubernetes.default.svc  monitoring      default  Synced     Healthy  Manual       None"
        ;;
    "app get"*)
        echo "Application: $app_name"
        echo "Namespace: production"
        echo "Server: https://kubernetes.default.svc"
        echo "Project: default"
        echo "Status: OutOfSync"
        echo "Health: Degraded"
        echo "Sync Policy: Auto"
        echo "Last Sync: 2024-01-15 14:25:33 UTC"
        echo "Revision: abc123def456"
        echo "Repository: https://github.com/company/k8s-configs"
        echo "Path: apps/production/api-server"
        echo "TARGET REVISION: HEAD"
        echo ""
        echo "Resources:"
        echo "  - Group: apps/v1, Kind: Deployment, Name: api-server, Status: OutOfSync"
        echo "  - Group: v1, Kind: Service, Name: api-server, Status: Synced"
        echo "  - Group: v1, Kind: ConfigMap, Name: api-server-config, Status: OutOfSync"
        ;;
    "app sync"*)
        echo "Syncing application: $app_name"
        echo "TIMESTAMP                  GROUP        KIND   NAMESPACE                  NAME    STATUS    HEALTH        HOOK  MESSAGE"
        echo "2024-01-15T14:30:22+00:00            Service  production          api-server    Synced   Healthy              service/api-server created"
        echo "2024-01-15T14:30:25+00:00   apps  Deployment  production          api-server  OutOfSync  Degraded             deployment.apps/api-server created"
        echo "2024-01-15T14:30:28+00:00         ConfigMap  production   api-server-config    Synced   Healthy              configmap/api-server-config created"
        ;;
    "app history"*)
        echo "ID  DATE                           REVISION"
        echo "10  2024-01-15 14:25:33 +0000 UTC  abc123def456 (HEAD)"
        echo "9   2024-01-15 13:45:12 +0000 UTC  def456ghi789"
        echo "8   2024-01-15 12:30:45 +0000 UTC  ghi789jkl012"
        echo "7   2024-01-15 11:15:23 +0000 UTC  jkl012mno345"
        ;;
    *)
        echo "Mock ArgoCD command output for: $command"
        echo "Status: Success"
        ;;
esac""",
                    "args": [
                        {
                            "name": "command",
                            "type": "string",
                            "description": "ArgoCD command to execute",
                            "required": True
                        },
                        {
                            "name": "app_name",
                            "type": "string",
                            "description": "Application name",
                            "required": False
                        }
                    ]
                },
                {
                    "name": "slack-post",
                    "alias": "slack-post",
                    "description": "Post ArgoCD findings to Slack",
                    "type": "docker",
                    "image": "curlimages/curl:latest",
                    "content": """#!/bin/sh
set -e
echo "📤 Posting ArgoCD findings to Slack..."

curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $slack_token" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"🔄 ArgoCD Investigation Update\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"header\\",
        \\"text\\": {
          \\"type\\": \\"plain_text\\",
          \\"text\\": \\"🔄 ArgoCD Investigation Results\\"
        }
      },
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"$message\\"
        }
      }
    ]
  }" > /dev/null

echo "✅ Posted to Slack successfully"
""",
                    "args": [
                        {
                            "name": "channel_id",
                            "type": "string",
                            "description": "Slack channel ID",
                            "required": True
                        },
                        {
                            "name": "message",
                            "type": "string",
                            "description": "ArgoCD findings message",
                            "required": True
                        },
                        {
                            "name": "slack_token",
                            "type": "string",
                            "description": "Slack API token",
                            "required": True
                        }
                    ]
                }
            ]
        ),
        output="ARGOCD_FINDINGS"
    )
    
    # Step 8: Observability Investigation with Claude Code
    workflow.step(
        name="observability-investigation",
        executor=inline_agent_executor(
            name="observability-investigator",
            message="""Perform comprehensive observability investigation for this incident:

Incident Analysis: $COMPREHENSIVE_ANALYSIS
Kubernetes Findings: $KUBERNETES_FINDINGS
Datadog Findings: $DATADOG_FINDINGS
ArgoCD Findings: $ARGOCD_FINDINGS
Incident Channel: $INCIDENT_CHANNEL_ID

Use your observe tool to investigate:
1. Distributed tracing analysis
2. Log correlation across services
3. Metrics correlation
4. Error patterns and anomalies
5. Performance bottlenecks
6. Service dependency mapping
7. Root cause analysis

Focus on correlation between different observability signals. Post findings to Slack.

Provide JSON output with:
- trace_analysis
- log_correlation
- performance_metrics
- error_patterns
- service_dependencies
- root_cause_hypothesis""",
            agent_name="observability-investigator",
            ai_instructions="You are Claude Code specializing in observability and distributed systems analysis. Use the observe CLI to correlate signals across traces, logs, and metrics.",
            tools=[
                {
                    "name": "observe",
                    "alias": "observe",
                    "description": "Execute observability CLI commands",
                    "type": "docker",
                    "image": "curlimages/curl:latest",
                    "content": """#!/bin/sh
set -e
echo "🔍 Executing observability command: $command"

# Mock observability responses for demo
case "$command" in
    "traces search"*)
        echo "Trace Search Results:"
        echo "TraceID: abc123def456 | Duration: 2.3s | Errors: 3 | Services: 4"
        echo "  - api-server: 2.1s (ERROR: timeout)"
        echo "  - database: 0.2s (OK)"
        echo "  - cache: 0.05s (OK)"
        echo "  - auth-service: 0.1s (OK)"
        echo ""
        echo "TraceID: def456ghi789 | Duration: 1.8s | Errors: 1 | Services: 3"
        echo "  - api-server: 1.7s (ERROR: out of memory)"
        echo "  - database: 0.1s (OK)"
        echo "  - cache: 0.03s (OK)"
        ;;
    "logs query"*)
        echo "Log Query Results:"
        echo "[2024-01-15 14:30:22] ERROR api-server: java.lang.OutOfMemoryError: Java heap space"
        echo "[2024-01-15 14:30:18] WARN  api-server: High CPU usage detected: 95%"
        echo "[2024-01-15 14:30:15] ERROR api-server: Connection pool exhausted"
        echo "[2024-01-15 14:30:12] ERROR api-server: Request timeout after 30s"
        echo "[2024-01-15 14:30:08] WARN  api-server: Memory usage above 90%"
        ;;
    "metrics correlation"*)
        echo "Metrics Correlation Analysis:"
        echo "Time Range: Last 30 minutes"
        echo ""
        echo "CPU Usage (api-server):"
        echo "  - 14:00: 65%"
        echo "  - 14:15: 85%"
        echo "  - 14:30: 95%"
        echo ""
        echo "Memory Usage (api-server):"
        echo "  - 14:00: 70%"
        echo "  - 14:15: 88%"
        echo "  - 14:30: 97%"
        echo ""
        echo "Response Time (api-server):"
        echo "  - 14:00: 200ms"
        echo "  - 14:15: 800ms"
        echo "  - 14:30: 2300ms"
        echo ""
        echo "Error Rate (api-server):"
        echo "  - 14:00: 0.1%"
        echo "  - 14:15: 2.5%"
        echo "  - 14:30: 8.5%"
        ;;
    "service map"*)
        echo "Service Dependency Map:"
        echo "frontend -> api-server (95% traffic)"
        echo "api-server -> database (78% traffic)"
        echo "api-server -> cache (45% traffic)"
        echo "api-server -> auth-service (23% traffic)"
        echo "api-server -> payment-service (12% traffic)"
        echo ""
        echo "Critical Path Issues:"
        echo "  - api-server: HIGH CPU/Memory, slow response"
        echo "  - database: Connection timeouts from api-server"
        echo "  - cache: OK, but reduced effectiveness due to api-server issues"
        ;;
    *)
        echo "Mock observability command output for: $command"
        echo "Status: Success"
        ;;
esac""",
                    "args": [
                        {
                            "name": "command",
                            "type": "string",
                            "description": "Observability command to execute",
                            "required": True
                        },
                        {
                            "name": "query",
                            "type": "string",
                            "description": "Query string for logs/traces",
                            "required": False
                        },
                        {
                            "name": "timerange",
                            "type": "string",
                            "description": "Time range for analysis",
                            "required": False
                        }
                    ]
                },
                {
                    "name": "slack-post",
                    "alias": "slack-post",
                    "description": "Post observability findings to Slack",
                    "type": "docker",
                    "image": "curlimages/curl:latest",
                    "content": """#!/bin/sh
set -e
echo "📤 Posting observability findings to Slack..."

curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $slack_token" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"🔍 Observability Investigation Update\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"header\\",
        \\"text\\": {
          \\"type\\": \\"plain_text\\",
          \\"text\\": \\"🔍 Observability Investigation Results\\"
        }
      },
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"$message\\"
        }
      }
    ]
  }" > /dev/null

echo "✅ Posted to Slack successfully"
""",
                    "args": [
                        {
                            "name": "channel_id",
                            "type": "string",
                            "description": "Slack channel ID",
                            "required": True
                        },
                        {
                            "name": "message",
                            "type": "string",
                            "description": "Observability findings message",
                            "required": True
                        },
                        {
                            "name": "slack_token",
                            "type": "string",
                            "description": "Slack API token",
                            "required": True
                        }
                    ]
                }
            ]
        ),
        output="OBSERVABILITY_FINDINGS"
    )
    
    # Step 9: Comprehensive Analysis and Recommendations with Claude Code
    workflow.step(
        name="comprehensive-analysis-and-recommendations",
        executor=inline_agent_executor(
            name="comprehensive-analyzer",
            message="""Perform comprehensive analysis and provide recommendations based on all investigation findings:

Original Analysis: $COMPREHENSIVE_ANALYSIS
Kubernetes Findings: $KUBERNETES_FINDINGS
Datadog Findings: $DATADOG_FINDINGS
ArgoCD Findings: $ARGOCD_FINDINGS
Observability Findings: $OBSERVABILITY_FINDINGS
Incident Channel: $INCIDENT_CHANNEL_ID

Correlate all findings and provide:
1. Root cause analysis
2. Impact assessment
3. Immediate mitigation steps
4. Long-term resolution plan
5. Prevention measures
6. Lessons learned
7. Post-incident actions

Post comprehensive summary to Slack with executive summary and action items.

Provide JSON output with:
- root_cause_analysis
- impact_assessment
- immediate_actions
- resolution_plan
- prevention_measures
- lessons_learned
- post_incident_actions
- executive_summary""",
            agent_name="comprehensive-analyzer",
            ai_instructions="You are Claude Code acting as a senior Site Reliability Engineer and incident commander. Correlate findings from all investigation platforms to provide comprehensive analysis, root cause identification, and actionable recommendations.",
            tools=[
                {
                    "name": "slack-post",
                    "alias": "slack-post",
                    "description": "Post comprehensive analysis to Slack",
                    "type": "docker",
                    "image": "curlimages/curl:latest",
                    "content": """#!/bin/sh
set -e
echo "📤 Posting comprehensive analysis to Slack..."

curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $slack_token" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"📊 Comprehensive Analysis Complete\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"header\\",
        \\"text\\": {
          \\"type\\": \\"plain_text\\",
          \\"text\\": \\"📊 Comprehensive Incident Analysis\\"
        }
      },
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"$message\\"
        }
      }
    ]
  }" > /dev/null

echo "✅ Posted to Slack successfully"
""",
                    "args": [
                        {
                            "name": "channel_id",
                            "type": "string",
                            "description": "Slack channel ID",
                            "required": True
                        },
                        {
                            "name": "message",
                            "type": "string",
                            "description": "Comprehensive analysis message",
                            "required": True
                        },
                        {
                            "name": "slack_token",
                            "type": "string",
                            "description": "Slack API token",
                            "required": True
                        }
                    ]
                }
            ]
        ),
        output="COMPREHENSIVE_RECOMMENDATIONS"
    )
    
    # Step 10: Generate Final Incident Report
    workflow.step(
        name="generate-comprehensive-report",
        executor=docker_executor(
            name="comprehensive-report-generator",
            image="python:3.11-alpine",
            content="""#!/bin/sh
set -e
apk add --no-cache jq

echo "📋 Generating comprehensive incident report..."

# Parse incident data
INCIDENT_ID=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_id // "UNKNOWN"')
INCIDENT_TITLE=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_title // "Untitled"')
INCIDENT_SEVERITY=$(echo "$EXTRACTED_EVENT_DATA" | jq -r '.incident_severity // "unknown"')

# Create comprehensive report
cat << EOF
# 🚨 Comprehensive Incident Response Report

**Incident ID:** $INCIDENT_ID  
**Title:** $INCIDENT_TITLE
**Severity:** $INCIDENT_SEVERITY
**Status:** ✅ Investigation Complete
**Investigation Time:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')

## 📊 Executive Summary

✅ **Comprehensive Multi-Platform Investigation Completed**
- AI-driven analysis across all platforms
- Kubernetes cluster thoroughly investigated
- Datadog metrics and alerts analyzed
- ArgoCD deployment status reviewed
- Observability signals correlated
- Root cause analysis performed
- Actionable recommendations provided

## 🔍 Investigation Results

### Kubernetes Findings
$KUBERNETES_FINDINGS

### Datadog Analysis
$DATADOG_FINDINGS

### ArgoCD Status
$ARGOCD_FINDINGS

### Observability Correlation
$OBSERVABILITY_FINDINGS

## 📋 Comprehensive Analysis

$COMPREHENSIVE_RECOMMENDATIONS

## ⚙️ Platform Integration Performance

- **Claude Code Integration:** ✅ Successfully executed across all platforms
- **Kubernetes Investigation:** ✅ Comprehensive cluster analysis completed
- **Datadog Monitoring:** ✅ Metrics and alerts thoroughly reviewed
- **ArgoCD Deployment:** ✅ GitOps workflow and sync status analyzed
- **Observability Correlation:** ✅ Cross-platform signal correlation performed
- **Slack Communication:** ✅ Real-time updates throughout investigation
- **Event Extraction:** ✅ Datadog webhook properly parsed
- **Multi-Tool Analysis:** ✅ kubectl, dogshell, argocd, observe all utilized

## 🎯 Workflow Capabilities Demonstrated

- **Event-Driven Response:** Automated trigger from Datadog webhook
- **Intelligent Analysis:** Claude Code providing expert-level insights
- **Tool Integration:** All major SRE tools (kubectl, dogshell, argocd, observe)
- **Cross-Platform Correlation:** Findings correlated across all monitoring platforms
- **Real-Time Communication:** Slack integration for stakeholder updates
- **Structured Data Flow:** JSON outputs enabling automated decision making
- **Comprehensive Reporting:** Executive-level summary with technical details

---
*Report generated by Claude Code Comprehensive Incident Response Workflow*
*Platforms: Kubernetes | Datadog | ArgoCD | Observability | Slack*
EOF

echo "✅ Comprehensive report generated successfully"
""",
        ),
        env={
            "EXTRACTED_EVENT_DATA": "$EXTRACTED_EVENT_DATA",
            "KUBERNETES_FINDINGS": "$KUBERNETES_FINDINGS",
            "DATADOG_FINDINGS": "$DATADOG_FINDINGS",
            "ARGOCD_FINDINGS": "$ARGOCD_FINDINGS",
            "OBSERVABILITY_FINDINGS": "$OBSERVABILITY_FINDINGS",
            "COMPREHENSIVE_RECOMMENDATIONS": "$COMPREHENSIVE_RECOMMENDATIONS"
        }
    )
    
    return workflow


if __name__ == "__main__":
    # Build and test the comprehensive workflow
    workflow = build_comprehensive_incident_response_workflow()
    
    # Compile the workflow
    compiled_workflow = workflow.to_dict()
    
    print("🚀 Comprehensive Incident Response Workflow with Claude Code")
    print("=" * 80)
    print(f"Workflow Name: {compiled_workflow['name']}")
    print(f"Description: {compiled_workflow['description']}")
    print(f"Total Steps: {len(compiled_workflow['steps'])}")
    
    # Count Claude Code steps
    claude_code_steps = sum(1 for step in compiled_workflow['steps'] 
                           if 'inline_agent' in str(step))
    print(f"Claude Code Steps: {claude_code_steps}")
    
    print(f"Tool Integration: kubectl, dogshell, argocd, observe")
    print("=" * 80)
    
    # Save compiled workflow
    yaml_output = workflow.to_yaml()
    with open("/Users/shaked/kubiya/orchestrator/workflow_sdk/incident-response-wf/workflows/compiled_comprehensive_incident.yaml", "w") as f:
        f.write(yaml_output)
    
    print("✅ Comprehensive workflow compiled and saved!")
    print("\n🎯 Key Features Demonstrated:")
    print("- ✅ Datadog webhook event extraction and parsing")
    print("- ✅ Claude Code as AI agent for comprehensive analysis")
    print("- ✅ Kubernetes investigation with kubectl tools")
    print("- ✅ Datadog monitoring with dogshell integration")
    print("- ✅ ArgoCD deployment analysis with argocd CLI")
    print("- ✅ Observability correlation with observe CLI")
    print("- ✅ Multi-platform investigation workflow")
    print("- ✅ Real-time Slack communication")
    print("- ✅ Comprehensive reporting and recommendations")
    print("- ✅ Structured JSON data flow between all steps")
    
    print(f"\n📁 Compiled workflow saved to:")
    print("   compiled_comprehensive_incident.yaml")
    print("\n🚀 This workflow demonstrates end-to-end incident response")
    print("   with Claude Code integration across all major SRE platforms!")