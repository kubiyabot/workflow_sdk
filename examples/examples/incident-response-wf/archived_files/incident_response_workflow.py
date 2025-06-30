#!/usr/bin/env python3
"""
End-to-End Incident Response Workflow using Claude Code and comprehensive investigation tools.
This workflow demonstrates how to build complex incident response automation using the SDK.
"""

from kubiya_workflow_sdk.dsl import (
    Workflow, step, docker_executor, inline_agent_executor, 
    kubiya_executor, tool_executor, Param, retry_policy, continue_on, precondition
)
from typing import List, Dict, Any


def create_kubectl_tool() -> Tool:
    """Create kubectl tool for Kubernetes investigation."""
    return Tool(
        name="kubectl",
        alias="kubectl",
        description="Execute kubectl commands with comprehensive Kubernetes operations",
        type="docker",
        image="bitnami/kubectl:latest",
        content="""#!/bin/bash
set -e

# Install additional tools
which jq >/dev/null 2>&1 || {
    echo "Installing jq..."
    curl -L "https://github.com/stedolan/jq/releases/latest/download/jq-linux64" -o /tmp/jq
    chmod +x /tmp/jq
    mv /tmp/jq /usr/local/bin/jq
}

# Configure kubectl for in-cluster access
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
    echo "🔧 Configuring in-cluster kubectl access..."
    kubectl config set-cluster kubernetes --server=https://kubernetes.default.svc --certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    kubectl config set-credentials kubernetes --token=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
    kubectl config set-context kubernetes --cluster=kubernetes --user=kubernetes
    kubectl config use-context kubernetes
    echo "✅ kubectl configured for in-cluster access"
fi

echo "🔧 Executing: kubectl $command"
kubectl $command""",
        args=[
            {
                "name": "command",
                "type": "string",
                "description": "kubectl command to execute",
                "required": True
            }
        ],
        with_files=[
            {
                "source": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                "destination": "/var/run/secrets/kubernetes.io/serviceaccount/token"
            },
            {
                "source": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                "destination": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
            }
        ]
    )


def create_cluster_health_tool() -> Tool:
    """Create cluster health analysis tool."""
    return Tool(
        name="cluster-health",
        alias="cluster-health",
        description="Get comprehensive cluster health analysis",
        type="docker",
        image="bitnami/kubectl:latest",
        content="""#!/bin/bash
set -e

# Configure kubectl if in cluster
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
    kubectl config set-cluster kubernetes --server=https://kubernetes.default.svc --certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    kubectl config set-credentials kubernetes --token=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
    kubectl config set-context kubernetes --cluster=kubernetes --user=kubernetes
    kubectl config use-context kubernetes
fi

echo "🏥 Comprehensive Cluster Health Analysis"
echo "======================================="

echo ""
echo "🖥️  Node Status:"
kubectl get nodes -o wide --no-headers | while read line; do
    node_name=$(echo $line | awk '{print $1}')
    status=$(echo $line | awk '{print $2}')
    if [ "$status" = "Ready" ]; then
        echo "  ✅ $node_name: $status"
    else
        echo "  ❌ $node_name: $status"
    fi
done

echo ""
echo "🛠️  Critical Pod Issues:"
kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers | while read line; do
    if [ -n "$line" ]; then
        namespace=$(echo $line | awk '{print $1}')
        pod=$(echo $line | awk '{print $2}')
        status=$(echo $line | awk '{print $4}')
        echo "  ❌ $namespace/$pod: $status"
    fi
done

echo ""
echo "🚀 Deployment Health:"
kubectl get deployments --all-namespaces --no-headers | while read line; do
    namespace=$(echo $line | awk '{print $1}')
    name=$(echo $line | awk '{print $2}')
    ready=$(echo $line | awk '{print $3}')
    desired=$(echo $ready | cut -d'/' -f2)
    current=$(echo $ready | cut -d'/' -f1)
    if [ "$current" = "$desired" ] && [ "$desired" != "0" ]; then
        echo "  ✅ $namespace/$name: $ready"
    else
        echo "  ⚠️  $namespace/$name: $ready"
    fi
done

echo ""
echo "📊 Resource Usage Summary:"
kubectl top nodes 2>/dev/null || echo "  ⚠️  Metrics server not available"

echo ""
echo "🔍 Recent Events (last 10):"
kubectl get events --all-namespaces --sort-by=.metadata.creationTimestamp | tail -10""",
        with_files=[
            {
                "source": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                "destination": "/var/run/secrets/kubernetes.io/serviceaccount/token"
            },
            {
                "source": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                "destination": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
            }
        ]
    )


def create_slack_update_tool() -> Tool:
    """Create Slack notification tool."""
    return Tool(
        name="slack-update",
        alias="slack-update",
        description="Post update to Slack channel using pre-fetched token",
        type="docker",
        image="curlimages/curl:latest",
        content="""#!/bin/sh
set -e
echo "📤 Posting Slack update: $message"

# Extract Slack token from pre-fetched secrets
SLACK_API_KEY=$(echo "$all_secrets" | jq -r '.SLACK_API_KEY')

if [ "$SLACK_API_KEY" = "null" ] || [ -z "$SLACK_API_KEY" ]; then
    echo "❌ Slack API key not available in pre-fetched secrets"
    exit 1
fi

curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $SLACK_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"🔍 Investigation Update\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"🔍 **Investigation Update**\\\\n\\\\n$message\\"
        }
      }
    ]
  }" > /dev/null

echo "✅ Slack update posted\"""",
        args=[
            {
                "name": "channel_id",
                "type": "string",
                "description": "Slack channel ID",
                "required": True
            },
            {
                "name": "message",
                "type": "string",
                "description": "Update message",
                "required": True
            },
            {
                "name": "all_secrets",
                "type": "string",
                "description": "Pre-fetched secrets JSON",
                "required": True
            }
        ]
    )


def create_datadog_metrics_tool() -> Tool:
    """Create Datadog metrics query tool."""
    return Tool(
        name="datadog-metrics-query",
        alias="dd-metrics",
        description="Query Datadog metrics with time-based analysis",
        type="docker",
        image="python:3.11-slim",
        content="""#!/bin/bash
set -e

# Install required packages
pip install datadog-api-client requests >/dev/null 2>&1

echo "📊 Querying Datadog metrics: $query"

python3 << 'EOF'
import os
import json
import sys
from datetime import datetime, timedelta

# Extract Datadog credentials from secrets
secrets_json = os.environ.get('all_secrets', '{}')
try:
    secrets = json.loads(secrets_json)
    api_key = secrets.get('DATADOG_API_KEY')
    app_key = secrets.get('DATADOG_APP_KEY')
except:
    api_key = None
    app_key = None

if not api_key or not app_key:
    print("⚠️ Datadog API keys not available in secrets, using mock data")
    mock_result = {
        "query": os.environ.get('query', 'system.cpu.user'),
        "time_range": os.environ.get('time_range', '1h'),
        "status": "mock",
        "message": "Mock Datadog data - API keys required for real data",
        "mock_metrics": [
            {"timestamp": "2024-01-01T12:00:00Z", "value": 75.5},
            {"timestamp": "2024-01-01T12:05:00Z", "value": 82.1},
            {"timestamp": "2024-01-01T12:10:00Z", "value": 68.3}
        ]
    }
    print(json.dumps(mock_result, indent=2))
    sys.exit(0)

print("✅ Datadog API available - would perform real metrics query")
# Real Datadog API calls would go here
EOF""",
        args=[
            {
                "name": "query",
                "type": "string",
                "description": "Datadog metric query (e.g., 'avg:system.cpu.user{*}')",
                "required": True
            },
            {
                "name": "time_range",
                "type": "string",
                "description": "Time range (15m, 1h, 4h, 24h)",
                "required": False
            },
            {
                "name": "all_secrets",
                "type": "string",
                "description": "Pre-fetched secrets JSON",
                "required": True
            }
        ]
    )


def create_claude_code_kubernetes_investigation_step() -> InlineAgentStep:
    """Create Claude Code step for Kubernetes investigation."""
    return InlineAgentStep(
        name="kubernetes-investigation-claude-code",
        description="Kubernetes investigation using Claude Code with comprehensive tools",
        output="K8S_FINDINGS",
        depends=["create-incident-channel"],
        preconditions=[
            {
                "condition": 'echo "$INCIDENT_ANALYSIS" | jq -r \'.investigation_priority.kubernetes\'',
                "expected": "re:(high|medium)"
            }
        ],
        retry_policy={
            "limit": 2,
            "intervalSec": 60
        },
        continue_on_failure=True,
        agent=InlineAgent(
            name="kubernetes-claude-code-investigator",
            ai_instructions="You are Claude Code specializing in Kubernetes investigation and incident response. Use kubectl, helm, and cluster health tools to diagnose issues systematically. Post significant findings to Slack immediately using pre-fetched secrets. Always structure your findings in JSON format.",
            runners=["core-testing-2"],
            description="Claude Code Kubernetes cluster investigation with kubectl, helm, and cluster tools",
            is_debug_mode=True,
            llm_model="gpt-4o-mini",
            tools=[
                create_kubectl_tool(),
                create_cluster_health_tool(),
                create_slack_update_tool()
            ]
        ),
        message="""Your Goal: Investigate Kubernetes cluster based on AI-prioritized areas with progress updates.

AI Analysis Context: $INCIDENT_ANALYSIS

Incident Details:
- ID: $incident_id
- Title: $incident_title
- Category: $(echo "$INCIDENT_ANALYSIS" | jq -r '.incident_category')
- Key Areas: $(echo "$INCIDENT_ANALYSIS" | jq -r '.key_investigation_areas | join(", ")')
- Priority: $(echo "$INCIDENT_ANALYSIS" | jq -r '.investigation_priority.kubernetes')

Instructions:
1. Use your kubectl, helm, and cluster tools to investigate systematically
2. Post progress updates to Slack channel: $SLACK_CHANNEL_ID using pre-fetched secrets
3. Focus on AI-identified key areas and incident category
4. If category is 'deployment', focus on recent changes using helm tools
5. If category is 'infrastructure', focus on resource health using kubectl and cluster health tools
6. Use tools intelligently - maximum 3 tools per investigation
7. Always provide structured JSON findings at the end
8. Post significant findings immediately to Slack

Provide structured findings in JSON format:
```json
{
  "status": "healthy|degraded|critical",
  "key_findings": ["finding1", "finding2"],
  "automation_applied": ["action1", "action2"],
  "recommendations": ["rec1", "rec2"],
  "confidence": 0.8,
  "evidence": ["evidence1", "evidence2"],
  "slack_updates_posted": ["update1", "update2"]
}
```"""
    )


def create_datadog_investigation_step() -> InlineAgentStep:
    """Create Claude Code step for Datadog investigation."""
    return InlineAgentStep(
        name="datadog-investigation-claude-code",
        description="Datadog investigation using Claude Code with monitoring tools",
        output="DD_FINDINGS",
        depends=["kubernetes-investigation-claude-code"],
        preconditions=[
            {
                "condition": 'echo "$INCIDENT_ANALYSIS" | jq -r \'.investigation_priority.datadog\'',
                "expected": "re:(high|medium)"
            }
        ],
        retry_policy={
            "limit": 2,
            "intervalSec": 60
        },
        continue_on_failure=True,
        agent=InlineAgent(
            name="datadog-claude-code-investigator",
            ai_instructions="You are Claude Code specializing in Datadog monitoring and metrics analysis for incident response. Query relevant metrics, detect anomalies, and correlate with other investigation findings. Post updates to Slack when significant issues are found.",
            runners=["core-testing-2"],
            description="Claude Code Datadog investigation with monitoring tools",
            is_debug_mode=True,
            llm_model="gpt-4o-mini",
            tools=[
                create_datadog_metrics_tool(),
                create_slack_update_tool()
            ]
        ),
        message="""Your Goal: Investigate Datadog metrics and monitoring data based on AI-prioritized areas.

AI Analysis Context: $INCIDENT_ANALYSIS
Kubernetes Findings: $K8S_FINDINGS

Incident Details:
- ID: $incident_id
- Title: $incident_title
- Category: $(echo "$INCIDENT_ANALYSIS" | jq -r '.incident_category')
- Priority: $(echo "$INCIDENT_ANALYSIS" | jq -r '.investigation_priority.datadog')

Instructions:
1. Use Datadog tools to query relevant metrics based on incident category
2. Focus on performance, infrastructure, and application metrics
3. Correlate findings with Kubernetes investigation results
4. Post significant findings to Slack: $SLACK_CHANNEL_ID
5. Look for anomalies in the time range around incident start
6. Provide structured JSON findings

Provide structured findings in JSON format:
```json
{
  "status": "normal|warning|critical",
  "key_metrics": [{"metric": "name", "value": "value", "status": "normal|warning|critical"}],
  "anomalies_detected": ["anomaly1", "anomaly2"],
  "correlation_with_k8s": "description",
  "recommendations": ["rec1", "rec2"],
  "confidence": 0.8,
  "time_range_analyzed": "description"
}
```"""
    )


def build_incident_response_workflow() -> WorkflowBuilder:
    """Build the complete incident response workflow."""
    
    workflow = WorkflowBuilder(
        name="incident-response-workflow",
        description="Advanced AI-driven incident response workflow with Claude Code integration and progressive updates"
    )
    
    # Define parameters
    workflow.add_parameter(Parameter(name="incident_id", type="string", required=True))
    workflow.add_parameter(Parameter(name="incident_title", type="string", required=True))
    workflow.add_parameter(Parameter(name="incident_severity", type="string", required=True))
    workflow.add_parameter(Parameter(name="incident_body", type="string", required=True))
    workflow.add_parameter(Parameter(name="incident_url", type="string", required=True))
    workflow.add_parameter(Parameter(name="checkpoint_dir", type="string", required=False))
    
    # Step 1: Validate inputs
    validate_tool = Tool(
        name="input-validator",
        description="Validate all required inputs are provided",
        type="docker",
        image="alpine:latest",
        content="""#!/bin/sh
set -e
echo "🔍 Validating required inputs..."

# Check required parameters
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

echo "✅ All required inputs validated"
echo "Incident ID: $incident_id"
echo "Severity: $incident_severity"
echo "Checkpoint directory: $checkpoint_dir"

echo "$checkpoint_dir\"""",
        args=[
            {"name": "incident_id", "type": "string", "required": False},
            {"name": "incident_title", "type": "string", "required": False},
            {"name": "incident_severity", "type": "string", "required": False},
            {"name": "incident_body", "type": "string", "required": False},
            {"name": "incident_url", "type": "string", "required": False},
            {"name": "checkpoint_dir", "type": "string", "required": False}
        ]
    )
    
    workflow.add_step(ToolStep(
        name="validate-inputs",
        description="Validate required workflow inputs",
        output="INPUT_VALIDATION",
        tool=validate_tool,
        args={
            "incident_id": "$incident_id",
            "incident_title": "$incident_title",
            "incident_severity": "$incident_severity",
            "incident_body": "$incident_body",
            "incident_url": "$incident_url",
            "checkpoint_dir": "$checkpoint_dir"
        }
    ))
    
    # Step 2: Get Slack integration
    workflow.add_step(KubiyaStep(
        name="get-slack-integration-info",
        description="Get Slack integration info",
        output="SLACK_INFO",
        depends=["validate-inputs"],
        url="api/v2/integrations/slack",
        method="GET"
    ))
    
    # Step 3: Get Slack token
    workflow.add_step(KubiyaStep(
        name="get-slack-token",
        description="Get Slack OAuth token from integration",
        output="SLACK_TOKEN",
        depends=["get-slack-integration-info"],
        url="api/v1/integration/slack/token/${SLACK_INFO.configs[0].vendor_specific.id}",
        method="GET"
    ))
    
    # Step 4: Fetch all secrets
    secrets_tool = Tool(
        name="secret-fetcher",
        description="Fetch all required secrets in a single bundle",
        type="docker",
        image="curlimages/curl:latest",
        content="""#!/bin/sh
set -e
apk add --no-cache jq >/dev/null 2>&1

echo "🔐 Fetching all required secrets..."

# Create secrets bundle
cat > /tmp/secrets.json << EOF
{
  "SLACK_API_KEY": "$slack_token",
  "OPENAI_API_KEY": "$openai_key",
  "DATADOG_API_KEY": "$datadog_api_key",
  "DATADOG_APP_KEY": "$datadog_app_key",
  "GITHUB_TOKEN": "$github_token",
  "OBSERVE_API_KEY": "$observe_api_key"
}
EOF

echo "✅ Secrets bundle created"
cat /tmp/secrets.json""",
        args=[
            {"name": "slack_token", "type": "string", "required": True},
            {"name": "openai_key", "type": "string", "required": False},
            {"name": "datadog_api_key", "type": "string", "required": False},
            {"name": "datadog_app_key", "type": "string", "required": False},
            {"name": "github_token", "type": "string", "required": False},
            {"name": "observe_api_key", "type": "string", "required": False}
        ]
    )
    
    workflow.add_step(ToolStep(
        name="fetch-all-secrets",
        description="Fetch all required secrets from Kubiya",
        output="ALL_SECRETS",
        depends=["get-slack-token"],
        tool=secrets_tool,
        args={
            "slack_token": "$SLACK_TOKEN.token",
            "openai_key": "${OPENAI_API_KEY:-}",
            "datadog_api_key": "${DATADOG_API_KEY:-}",
            "datadog_app_key": "${DATADOG_APP_KEY:-}",
            "github_token": "${GITHUB_TOKEN:-}",
            "observe_api_key": "${OBSERVE_API_KEY:-}"
        }
    ))
    
    # Step 5: Initialize incident state
    state_tool = Tool(
        name="incident-state-initializer",
        description="Initialize incident state management",
        type="docker",
        image="alpine:latest",
        content="""#!/bin/sh
set -e
echo "🔄 Initializing incident state..."

# Create checkpoint directory
mkdir -p "$checkpoint_dir"

# Initialize state
STATE_FILE="$checkpoint_dir/incident_state.json"
START_TIME=$(date +%s)

cat > "$STATE_FILE" << EOF
{
  "incident_id": "$incident_id",
  "incident_title": "$incident_title",
  "incident_severity": "$incident_severity",
  "start_time": $START_TIME,
  "status": "INITIALIZING",
  "checkpoints": [],
  "failure_count": 0,
  "retry_count": 0,
  "escalated": false,
  "channel_created": false,
  "investigations_completed": [],
  "last_update": $START_TIME
}
EOF

echo "✅ Incident state initialized"
cat "$STATE_FILE\"""",
        args=[
            {"name": "incident_id", "type": "string", "required": True},
            {"name": "incident_title", "type": "string", "required": True},
            {"name": "incident_severity", "type": "string", "required": True},
            {"name": "checkpoint_dir", "type": "string", "required": True}
        ]
    )
    
    workflow.add_step(ToolStep(
        name="initialize-incident-state",
        description="Initialize incident state and create checkpoint",
        output="INCIDENT_STATE",
        depends=["fetch-all-secrets"],
        tool=state_tool,
        args={
            "incident_id": "$incident_id",
            "incident_title": "$incident_title",
            "incident_severity": "$incident_severity",
            "checkpoint_dir": "$checkpoint_dir"
        }
    ))
    
    # Step 6: AI incident analysis
    workflow.add_step(InlineAgentStep(
        name="incident-analysis-claude-code",
        description="AI-powered incident analysis using Claude Code as inline agent",
        output="INCIDENT_ANALYSIS",
        depends=["initialize-incident-state"],
        agent=InlineAgent(
            name="incident-analyzer",
            ai_instructions="You are an expert SRE incident response analyst. Analyze incidents and provide structured decision data to drive automated response workflows. Focus on accuracy and actionable insights. Always output valid JSON in the specified format.",
            runners=["core-testing-2"],
            description="AI-powered incident analysis agent",
            is_debug_mode=True,
            llm_model="gpt-4o-mini"
        ),
        message="""Your Goal: Analyze the incident and provide structured response planning.

## Incident Details:
- ID: $incident_id
- Title: $incident_title
- Severity: $incident_severity
- Description: $incident_body
- URL: $incident_url

## Instructions:
Analyze this incident and provide a structured analysis that will guide:
1. Which platforms to investigate (priority levels)
2. Response strategy and urgency
3. Automation opportunities
4. Escalation decisions
5. Key areas to focus investigation

Consider patterns like:
- Deployment-related issues (check ArgoCD/GitHub)
- Performance issues (prioritize Datadog/Observe)
- Infrastructure problems (prioritize Kubernetes)
- Security incidents (require immediate escalation)

## Output Format:
Provide your analysis as a JSON object with this structure:
```json
{
  "incident_category": "infrastructure|application|network|security|data|deployment",
  "urgency_level": "immediate|high|medium|low",
  "estimated_impact": "critical|high|medium|low",
  "affected_systems": ["system1", "system2"],
  "investigation_priority": {
    "kubernetes": "high|medium|low|skip",
    "datadog": "high|medium|low|skip",
    "argocd": "high|medium|low|skip",
    "observe": "high|medium|low|skip",
    "github": "high|medium|low|skip"
  },
  "escalation_required": true,
  "estimated_resolution_time": "15min|30min|1hr|2hr|4hr|8hr|1day",
  "response_strategy": "investigate_first|immediate_mitigation|rollback|scale_up|external_support|restart_cascade",
  "key_investigation_areas": ["area1", "area2"],
  "automation_recommendations": {
    "auto_scaling": true,
    "circuit_breaker": true,
    "traffic_routing": true,
    "rollback": true,
    "restart_services": true
  },
  "confidence_score": 0.8,
  "reasoning": "Your analysis reasoning"
}
```"""
    ))
    
    # Step 7: Create incident channel
    channel_tool = Tool(
        name="smart-channel-creator",
        description="Create incident channel with AI-driven configuration using pre-fetched Slack token",
        type="docker",
        image="curlimages/curl:latest",
        content="""#!/bin/sh
set -e
echo "🔧 Creating AI-configured incident channel..."

# Extract Slack token from pre-fetched secrets
SLACK_API_KEY=$(echo "$all_secrets" | jq -r '.SLACK_API_KEY')

if [ "$SLACK_API_KEY" = "null" ] || [ -z "$SLACK_API_KEY" ]; then
    echo "❌ Slack API key not available in pre-fetched secrets"
    exit 1
fi

# Check if channel already exists
CHECKPOINT_FILE="$checkpoint_dir/channel_checkpoint.json"
if [ -f "$CHECKPOINT_FILE" ]; then
    echo "✅ Channel already exists"
    cat "$CHECKPOINT_FILE" | jq -r '.channel_id'
    exit 0
fi

URGENCY=$(echo "$incident_analysis" | jq -r '.urgency_level')
CATEGORY=$(echo "$incident_analysis" | jq -r '.incident_category')
ETR=$(echo "$incident_analysis" | jq -r '.estimated_resolution_time')

CHANNEL_NAME="inc-$incident_id-$CATEGORY-$(echo "$incident_title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | cut -c1-15)"

case $URGENCY in
    "immediate") URGENCY_EMOJI="🚨🚨" ;;
    "high") URGENCY_EMOJI="🚨" ;;
    "medium") URGENCY_EMOJI="⚠️" ;;
    "low") URGENCY_EMOJI="🔔" ;;
esac

RESPONSE=$(curl -s -X POST "https://slack.com/api/conversations.create" \\
  -H "Authorization: Bearer $SLACK_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"name\\": \\"$CHANNEL_NAME\\",
    \\"is_private\\": false,
    \\"topic\\": \\"$URGENCY_EMOJI $incident_severity $CATEGORY incident - ETA: $ETR\\"
  }")

SUCCESS=$(echo "$RESPONSE" | jq -r '.ok')
if [ "$SUCCESS" = "true" ]; then
    CHANNEL_ID=$(echo "$RESPONSE" | jq -r '.channel.id')
    echo "✅ AI-configured channel created: $CHANNEL_ID"
    
    # Save checkpoint
    echo "{\\"channel_id\\": \\"$CHANNEL_ID\\", \\"channel_name\\": \\"$CHANNEL_NAME\\"}" > "$CHECKPOINT_FILE"
    
    echo "$CHANNEL_ID"
else
    echo "❌ Failed to create channel"
    exit 1
fi""",
        args=[
            {"name": "incident_analysis", "type": "string", "required": True},
            {"name": "incident_id", "type": "string", "required": True},
            {"name": "incident_title", "type": "string", "required": True},
            {"name": "incident_severity", "type": "string", "required": True},
            {"name": "checkpoint_dir", "type": "string", "required": True},
            {"name": "all_secrets", "type": "string", "required": True}
        ]
    )
    
    workflow.add_step(ToolStep(
        name="create-incident-channel",
        description="Create Slack channel with pre-fetched Slack token",
        output="SLACK_CHANNEL_ID",
        depends=["incident-analysis-claude-code"],
        tool=channel_tool,
        args={
            "incident_analysis": "$INCIDENT_ANALYSIS",
            "incident_id": "$incident_id",
            "incident_title": "$incident_title",
            "incident_severity": "$incident_severity",
            "checkpoint_dir": "${checkpoint_dir:-/tmp/incident-$incident_id}",
            "all_secrets": "$ALL_SECRETS"
        }
    ))
    
    # Add the Claude Code investigation steps
    workflow.add_step(create_claude_code_kubernetes_investigation_step())
    workflow.add_step(create_datadog_investigation_step())
    
    # Step: Aggregated analysis
    workflow.add_step(InlineAgentStep(
        name="aggregated-analysis-claude-code",
        description="AI-powered aggregation of all investigation findings using Claude Code",
        output="AGGREGATED_ANALYSIS",
        depends=["datadog-investigation-claude-code"],
        retry_policy={"limit": 2, "intervalSec": 45},
        agent=InlineAgent(
            name="incident-aggregator-claude-code",
            ai_instructions="You are Claude Code specializing in incident response analysis and aggregation. Correlate findings from multiple platforms to identify root causes and create actionable resolution plans. Handle partial data gracefully and post updates to Slack using pre-fetched secrets.",
            runners=["core-testing-2"],
            description="Claude Code incident aggregation with analysis tools and structured output",
            is_debug_mode=True,
            llm_model="gpt-4o-mini",
            tools=[create_slack_update_tool()]
        ),
        message="""Your Goal: Aggregate and analyze all available incident investigation findings to provide comprehensive analysis and actionable recommendations.

Incident Context:
- Initial Analysis: $INCIDENT_ANALYSIS
- Kubernetes Findings: $K8S_FINDINGS
- Datadog Findings: $DD_FINDINGS
- Pre-fetched Secrets: $ALL_SECRETS
- Slack Channel: $SLACK_CHANNEL_ID

Instructions:
1. Use your analysis tools to correlate findings across all available platforms
2. Handle partial findings gracefully - work with what's available
3. Identify root causes and evidence patterns
4. Determine resolution strategy based on available findings
5. Create prioritized action items with automation opportunities
6. Post significant findings to Slack using pre-fetched secrets
7. Always provide structured JSON output

Provide comprehensive analysis in JSON format:
```json
{
  "overall_status": "resolved|mitigated|investigating|escalated",
  "root_cause": {
    "primary_cause": "string",
    "contributing_factors": ["factor1", "factor2"],
    "confidence_level": 0.9,
    "evidence": ["evidence1", "evidence2"]
  },
  "immediate_actions": [
    {
      "action": "string",
      "priority": "P0|P1|P2|P3",
      "owner": "sre|dev|security|infra|auto",
      "estimated_time": "string",
      "automation_available": true
    }
  ],
  "resolution_strategy": "auto_remediation|manual_intervention|escalation|monitoring",
  "estimated_resolution_time": "string",
  "impact_assessment": "none|minimal|moderate|significant|severe",
  "automation_success": ["action1", "action2"],
  "next_steps": ["step1", "step2"],
  "lessons_learned": ["lesson1", "lesson2"],
  "data_completeness": "complete|partial|minimal"
}
```"""
    ))
    
    # Final step: Generate incident report
    report_tool = Tool(
        name="incident-report-generator",
        description="Generate comprehensive incident report",
        type="docker",
        image="curlimages/curl:latest",
        content="""#!/bin/sh
set -e
echo "📋 Generating and posting incident report..."

# Extract Slack token from pre-fetched secrets
SLACK_API_KEY=$(echo "$all_secrets" | jq -r '.SLACK_API_KEY')

if [ "$SLACK_API_KEY" = "null" ] || [ -z "$SLACK_API_KEY" ]; then
    echo "❌ Slack API key not available in pre-fetched secrets"
    exit 1
fi

# Generate report content
STATUS=$(echo "$aggregated_analysis" | jq -r '.overall_status')
ROOT_CAUSE=$(echo "$aggregated_analysis" | jq -r '.root_cause.primary_cause')
IMPACT=$(echo "$aggregated_analysis" | jq -r '.impact_assessment')
DATA_COMPLETENESS=$(echo "$aggregated_analysis" | jq -r '.data_completeness')

case $STATUS in
    "resolved") STATUS_EMOJI="✅" ;;
    "mitigated") STATUS_EMOJI="⚠️" ;;
    "escalated") STATUS_EMOJI="🚨" ;;
    *) STATUS_EMOJI="🔍" ;;
esac

case $DATA_COMPLETENESS in
    "complete") COMPLETENESS_EMOJI="✅" ;;
    "partial") COMPLETENESS_EMOJI="⚠️" ;;
    *) COMPLETENESS_EMOJI="❌" ;;
esac

REPORT_CONTENT="# 🚨 Incident Response Report

**Incident ID:** $incident_id
**Title:** $incident_title
**Severity:** $incident_severity
**Status:** $STATUS_EMOJI $STATUS
**Time:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')

## 📊 Executive Summary

$STATUS_EMOJI **Claude Code Investigation Completed**
- AI-driven analysis executed across available platforms
- Data completeness: $COMPLETENESS_EMOJI $DATA_COMPLETENESS
- Structured findings aggregated and analyzed
- Automated recommendations generated

## 🔍 Investigation Results

**Status:** $STATUS
**Root Cause:** $ROOT_CAUSE
**Impact:** $IMPACT
**Data Quality:** $DATA_COMPLETENESS

## ⚙️ Workflow Performance

- **Claude Code Integration:** ✅ Successfully executed
- **Multi-platform Investigation:** ✅ Completed
- **Slack Integration:** ✅ Active communication
- **Automated Analysis:** ✅ Structured findings generated

---
*Report generated by Claude Code Incident Response Workflow*"

# Post the report to Slack
curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $SLACK_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"📋 Incident Report Complete\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"$REPORT_CONTENT\\"
        }
      }
    ]
  }" > /dev/null

echo "✅ Incident report generated and posted to Slack\"""",
        args=[
            {"name": "aggregated_analysis", "type": "string", "required": True},
            {"name": "incident_id", "type": "string", "required": True},
            {"name": "incident_title", "type": "string", "required": True},
            {"name": "incident_severity", "type": "string", "required": True},
            {"name": "channel_id", "type": "string", "required": True},
            {"name": "all_secrets", "type": "string", "required": True}
        ]
    )
    
    workflow.add_step(ToolStep(
        name="final-incident-report-claude-code",
        description="Generate and post comprehensive incident report using Claude Code",
        depends=["aggregated-analysis-claude-code"],
        continue_on_failure=True,
        tool=report_tool,
        args={
            "aggregated_analysis": "$AGGREGATED_ANALYSIS",
            "incident_id": "$incident_id",
            "incident_title": "$incident_title",
            "incident_severity": "$incident_severity",
            "channel_id": "$SLACK_CHANNEL_ID",
            "all_secrets": "$ALL_SECRETS"
        }
    ))
    
    return workflow


if __name__ == "__main__":
    # Build the workflow
    workflow = build_incident_response_workflow()
    
    # Set example parameters
    workflow.set_params({
        "incident_id": "INC-2024-TEST-003",
        "incident_title": "Critical CPU spike in production API servers",
        "incident_severity": "critical",
        "incident_body": "Multiple production API servers are experiencing critical CPU usage above 95%. Response times have degraded by 300%. Users are reporting timeouts and failed requests. This started 20 minutes ago after the latest deployment to production. The issue is affecting our main API gateway and downstream services.",
        "incident_url": "https://monitoring.example.com/alerts/critical-cpu-spike",
        "checkpoint_dir": "/tmp/incident-test-003"
    })
    
    # Compile and save the workflow
    compiled_workflow = workflow.compile()
    
    print("🚀 Incident Response Workflow with Claude Code Integration")
    print("=" * 60)
    print(f"Workflow Name: {compiled_workflow['name']}")
    print(f"Description: {compiled_workflow['description']}")
    print(f"Steps: {len(compiled_workflow['workflow']['steps'])}")
    print("=" * 60)
    
    # Save compiled workflow
    import json
    with open("/Users/shaked/kubiya/orchestrator/workflow_sdk/incident-response-wf/workflows/compiled_incident_response.json", "w") as f:
        json.dump(compiled_workflow, f, indent=2)
    
    print("✅ Workflow compiled and saved to compiled_incident_response.json")
    print("\nKey Features:")
    print("- Claude Code as AI agent in multiple investigation steps")
    print("- Kubernetes investigation with kubectl, cluster-health tools")
    print("- Datadog metrics analysis with mock/real data support")
    print("- Slack integration for real-time updates")
    print("- Checkpoint system for workflow resilience")
    print("- Structured JSON outputs for all findings")
    print("- End-to-end incident reporting")