#!/usr/bin/env python3
"""
Reusable Claude Code step helper for incident response workflows.
Creates standardized steps that leverage Claude Code as an AI agent with specific tools.
"""

import json
from typing import Dict, List, Optional, Any


def create_claude_code_step(
    name: str,
    description: str,
    message: str,
    depends: Optional[List[str]] = None,
    output: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    secrets: Optional[Dict[str, str]] = None,
    with_files: Optional[List[Dict]] = None,
    preconditions: Optional[List[Dict]] = None,
    continue_on_failure: bool = False,
    retry_policy: Optional[Dict] = None,
    llm_model: str = "gpt-4o-mini",
    runner: str = "core-testing-2"
) -> Dict[str, Any]:
    """
    Create a Claude Code workflow step with standardized configuration.
    
    Args:
        name: Step name
        description: Step description  
        message: Message/prompt for Claude Code
        depends: List of step dependencies
        output: Output variable name
        tools: List of tools available to Claude Code
        secrets: Dictionary of secrets to pass
        with_files: List of files to mount
        preconditions: List of preconditions
        continue_on_failure: Whether to continue on failure
        retry_policy: Retry configuration
        llm_model: LLM model to use
        runner: Kubiya runner to use
        
    Returns:
        Dictionary representing the workflow step
    """
    
    # Base step configuration
    step = {
        "name": name,
        "description": description,
        "executor": {
            "type": "inline_agent",
            "config": {
                "message": message,
                "agent": {
                    "name": f"claude-code-{name.replace('-', '_')}",
                    "ai_instructions": "You are Claude Code, an expert AI assistant specializing in incident response and system operations. Use your available tools systematically to investigate, analyze, and resolve issues. Always provide structured output and post updates to communication channels when significant findings are discovered.",
                    "runners": [runner],
                    "description": f"Claude Code agent for {description}",
                    "is_debug_mode": True,
                    "llm_model": llm_model
                }
            }
        }
    }
    
    # Add optional fields
    if depends:
        step["depends"] = depends
    if output:
        step["output"] = output
    if preconditions:
        step["preconditions"] = preconditions
    if continue_on_failure:
        step["continueOn"] = {"failure": True}
    if retry_policy:
        step["retryPolicy"] = retry_policy
        
    # Add tools if provided
    if tools:
        step["executor"]["config"]["agent"]["tools"] = tools
        
    return step


def create_kubernetes_investigation_tools() -> List[Dict]:
    """Create standardized Kubernetes investigation tools for Claude Code."""
    return [
        {
            "name": "kubectl",
            "alias": "kubectl",
            "description": "Execute kubectl commands with in-cluster context",
            "type": "docker",
            "content": """# Begin Kubernetes context setup
{
    # Define locations
    TOKEN_LOCATION="/tmp/kubernetes_context_token"
    CERT_LOCATION="/tmp/kubernetes_context_cert"

    # Verify required files exist and are readable
    if [ ! -f "$TOKEN_LOCATION" ]; then
        echo "❌ Error: Kubernetes token file not found at $TOKEN_LOCATION" >&2
        exit 1
    fi

    if [ ! -f "$CERT_LOCATION" ]; then
        echo "❌ Error: Kubernetes certificate file not found at $CERT_LOCATION" >&2
        exit 1
    fi

    # Read token securely
    KUBE_TOKEN=$(cat "$TOKEN_LOCATION")
    if [ -z "$KUBE_TOKEN" ]; then
        echo "❌ Error: Kubernetes token file is empty" >&2
        exit 1
    fi

    # Configure kubectl with proper error handling
    echo "🔧 Configuring Kubernetes context..."

    kubectl config set-cluster in-cluster --server=https://kubernetes.default.svc --certificate-authority="$CERT_LOCATION" >/dev/null 2>&1
    kubectl config set-credentials in-cluster --token="$KUBE_TOKEN" >/dev/null 2>&1
    kubectl config set-context in-cluster --cluster=in-cluster --user=in-cluster >/dev/null 2>&1
    kubectl config use-context in-cluster >/dev/null 2>&1

    echo "✅ Successfully configured Kubernetes context"
}

#!/bin/bash
set -e
echo "🔧 Executing: kubectl $command"
kubectl $command | head -n 100""",
            "args": [
                {
                    "name": "command",
                    "type": "string",
                    "description": "kubectl command to execute",
                    "required": True
                }
            ],
            "with_files": [
                {
                    "source": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                    "destination": "/tmp/kubernetes_context_token"
                },
                {
                    "source": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                    "destination": "/tmp/kubernetes_context_cert"
                }
            ],
            "image": "bitnami/kubectl:latest"
        },
        {
            "name": "cluster_health",
            "alias": "cluster-health",
            "description": "Get comprehensive cluster health status",
            "type": "docker",
            "content": """# Begin Kubernetes context setup
{
    # Define locations
    TOKEN_LOCATION="/tmp/kubernetes_context_token"
    CERT_LOCATION="/tmp/kubernetes_context_cert"

    # Read token securely
    KUBE_TOKEN=$(cat "$TOKEN_LOCATION")

    # Configure kubectl
    kubectl config set-cluster in-cluster --server=https://kubernetes.default.svc --certificate-authority="$CERT_LOCATION" >/dev/null 2>&1
    kubectl config set-credentials in-cluster --token="$KUBE_TOKEN" >/dev/null 2>&1
    kubectl config set-context in-cluster --cluster=in-cluster --user=in-cluster >/dev/null 2>&1
    kubectl config use-context in-cluster >/dev/null 2>&1
}

#!/bin/bash
set -e
echo "🏥 Cluster Health Summary:"
echo "========================="
echo "🖥️  Node Status:"
kubectl get nodes -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,REASON:.status.conditions[-1].reason | 
awk 'NR>1 {
    status = $2;
    emoji = "❓";
    if (status == "Ready") emoji = "✅";
    else if (status == "NotReady") emoji = "❌";
    else if (status == "SchedulingDisabled") emoji = "🚫";
    print "  " emoji " " $0;
}'
echo ""
echo "🛠️  Pod Status:"
kubectl get pods --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName | 
awk 'NR>1 {
    status = $3;
    emoji = "❓";
    if (status == "Running") emoji = "✅";
    else if (status == "Pending") emoji = "⏳";
    else if (status == "Succeeded") emoji = "🎉";
    else if (status == "Failed") emoji = "❌";
    else if (status == "Unknown") emoji = "❔";
    print "  " emoji " " $0;
}'
echo ""
echo "🚀 Deployment Status:"
kubectl get deployments --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,DESIRED:.spec.replicas,AVAILABLE:.status.availableReplicas,UP-TO-DATE:.status.updatedReplicas | 
awk 'NR>1 {
    if ($3 == $4 && $3 == $5) emoji = "✅";
    else if ($4 == "0") emoji = "❌";
    else emoji = "⚠️";
    print "  " emoji " " $0;
}'""",
            "with_files": [
                {
                    "source": "/var/run/secrets/kubernetes.io/serviceaccount/token",
                    "destination": "/tmp/kubernetes_context_token"
                },
                {
                    "source": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                    "destination": "/tmp/kubernetes_context_cert"
                }
            ],
            "image": "bitnami/kubectl:latest"
        }
    ]


def create_slack_notification_tool() -> Dict:
    """Create standardized Slack notification tool."""
    return {
        "name": "slack-update",
        "alias": "slack-update",
        "description": "Post update to Slack channel using pre-fetched token",
        "type": "docker",
        "image": "curlimages/curl:latest",
        "content": """#!/bin/sh
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
    }


def create_datadog_investigation_tools() -> List[Dict]:
    """Create Datadog investigation tools."""
    return [
        {
            "name": "datadog-metrics",
            "alias": "dd-metrics",
            "description": "Query Datadog metrics",
            "type": "docker",
            "image": "python:3.11-slim",
            "content": """#!/bin/bash
set -e
pip install datadog-api-client >/dev/null 2>&1

python3 << 'EOF'
import os
import json
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.metrics_api import MetricsApi
from datetime import datetime, timedelta

# Extract Datadog keys from secrets
secrets = json.loads(os.environ.get('all_secrets', '{}'))
api_key = secrets.get('DATADOG_API_KEY')
app_key = secrets.get('DATADOG_APP_KEY')

if not api_key or not app_key:
    print("❌ Datadog API keys not available")
    exit(1)

configuration = Configuration()
configuration.api_key["apiKeyAuth"] = api_key
configuration.api_key["appKeyAuth"] = app_key

query = os.environ.get('query', 'system.cpu.user')
time_range = os.environ.get('time_range', '1h')

# Calculate time range
now = datetime.now()
if time_range == '1h':
    start_time = now - timedelta(hours=1)
elif time_range == '4h':
    start_time = now - timedelta(hours=4)
elif time_range == '24h':
    start_time = now - timedelta(hours=24)
else:
    start_time = now - timedelta(hours=1)

start_ts = int(start_time.timestamp())
end_ts = int(now.timestamp())

with ApiClient(configuration) as api_client:
    api_instance = MetricsApi(api_client)
    try:
        response = api_instance.query_metrics(
            _from=start_ts,
            to=end_ts,
            query=query
        )
        print(f"📊 Datadog Query Results for: {query}")
        print(f"⏰ Time Range: {time_range}")
        print(json.dumps(response.to_dict(), indent=2))
    except Exception as e:
        print(f"❌ Error querying Datadog: {e}")
EOF""",
            "args": [
                {
                    "name": "query",
                    "type": "string",
                    "description": "Datadog metric query",
                    "required": True
                },
                {
                    "name": "time_range",
                    "type": "string",
                    "description": "Time range (1h, 4h, 24h)",
                    "required": False
                },
                {
                    "name": "all_secrets",
                    "type": "string",
                    "description": "Pre-fetched secrets JSON",
                    "required": True
                }
            ]
        }
    ]


if __name__ == "__main__":
    # Example usage
    step = create_claude_code_step(
        name="kubernetes-investigation",
        description="Investigate Kubernetes cluster issues",
        message="Investigate the Kubernetes cluster for issues related to: ${incident_description}",
        depends=["incident-analysis"],
        output="K8S_FINDINGS",
        tools=create_kubernetes_investigation_tools() + [create_slack_notification_tool()],
        continue_on_failure=True,
        retry_policy={"limit": 2, "intervalSec": 60}
    )
    
    print(json.dumps(step, indent=2))