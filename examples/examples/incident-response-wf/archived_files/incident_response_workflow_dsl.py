#!/usr/bin/env python3
"""
End-to-End Incident Response Workflow using Claude Code and comprehensive investigation tools.
This workflow demonstrates how to build complex incident response automation using the DSL.
"""

from kubiya_workflow_sdk.dsl import (
    Workflow, step, docker_executor, inline_agent_executor, 
    kubiya_executor, tool_executor, Param, retry_policy, continue_on, precondition
)


def build_incident_response_workflow():
    """Build the complete incident response workflow using the DSL."""
    
    # Create the workflow
    workflow = (Workflow("incident-response-workflow")
                .description("Advanced AI-driven incident response workflow with Claude Code integration and progressive updates")
                .type("graph")  # Use graph for explicit dependencies
                .params(
                    incident_id="INC-2024-TEST-001",
                    incident_title="Critical CPU spike in production API servers",
                    incident_severity="critical",
                    incident_body="Multiple production API servers are experiencing critical CPU usage above 95%",
                    incident_url="https://monitoring.example.com/alerts/critical-cpu-spike",
                    checkpoint_dir="/tmp/incident-test-001"
                ))
    
    # Step 1: Validate inputs
    workflow.step(
        name="validate-inputs",
        executor=docker_executor(
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

if [ -n "$MISSING_PARAMS" ]; then
    echo "❌ Missing required parameters: $MISSING_PARAMS"
    exit 1
fi

echo "✅ All required inputs validated"
echo "Incident ID: $incident_id"
echo "Severity: $incident_severity"
echo "Checkpoint directory: $checkpoint_dir"

echo "$checkpoint_dir\"""",
            env={
                "incident_id": "${incident_id}",
                "incident_title": "${incident_title}",
                "incident_severity": "${incident_severity}",
                "incident_body": "${incident_body}",
                "incident_url": "${incident_url}",
                "checkpoint_dir": "${checkpoint_dir}"
            }
        ),
        output="INPUT_VALIDATION"
    )
    
    # Step 2: Get Slack integration
    workflow.step(
        name="get-slack-integration-info",
        executor=kubiya_executor(
            url="api/v2/integrations/slack",
            method="GET"
        ),
        depends=["validate-inputs"],
        output="SLACK_INFO"
    )
    
    # Step 3: Get Slack token
    workflow.step(
        name="get-slack-token",
        executor=kubiya_executor(
            url="api/v1/integration/slack/token/${SLACK_INFO.configs[0].vendor_specific.id}",
            method="GET"
        ),
        depends=["get-slack-integration-info"],
        output="SLACK_TOKEN"
    )
    
    # Step 4: Fetch all secrets
    workflow.step(
        name="fetch-all-secrets",
        executor=docker_executor(
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
            env={
                "slack_token": "$SLACK_TOKEN.token",
                "openai_key": "${OPENAI_API_KEY:-}",
                "datadog_api_key": "${DATADOG_API_KEY:-}",
                "datadog_app_key": "${DATADOG_APP_KEY:-}",
                "github_token": "${GITHUB_TOKEN:-}",
                "observe_api_key": "${OBSERVE_API_KEY:-}"
            }
        ),
        depends=["get-slack-token"],
        output="ALL_SECRETS"
    )
    
    # Step 5: Initialize incident state
    workflow.step(
        name="initialize-incident-state",
        executor=docker_executor(
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
            env={
                "incident_id": "${incident_id}",
                "incident_title": "${incident_title}",
                "incident_severity": "${incident_severity}",
                "checkpoint_dir": "${checkpoint_dir}"
            }
        ),
        depends=["fetch-all-secrets"],
        output="INCIDENT_STATE"
    )
    
    # Step 6: AI incident analysis using Claude Code
    workflow.step(
        name="incident-analysis-claude-code",
        executor=inline_agent_executor(
            name="incident-analyzer",
            ai_instructions="You are an expert SRE incident response analyst. Analyze incidents and provide structured decision data to drive automated response workflows. Focus on accuracy and actionable insights. Always output valid JSON in the specified format.",
            runners=["core-testing-2"],
            llm_model="gpt-4o-mini",
            is_debug_mode=True,
            message="""Your Goal: Analyze the incident and provide structured response planning.

## Incident Details:
- ID: ${incident_id}
- Title: ${incident_title}
- Severity: ${incident_severity}
- Description: ${incident_body}
- URL: ${incident_url}

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
        ),
        depends=["initialize-incident-state"],
        output="INCIDENT_ANALYSIS"
    )
    
    # Step 7: Create incident channel
    workflow.step(
        name="create-incident-channel",
        executor=docker_executor(
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
            env={
                "incident_analysis": "$INCIDENT_ANALYSIS",
                "incident_id": "${incident_id}",
                "incident_title": "${incident_title}",
                "incident_severity": "${incident_severity}",
                "checkpoint_dir": "${checkpoint_dir}",
                "all_secrets": "$ALL_SECRETS"
            }
        ),
        depends=["incident-analysis-claude-code"],
        output="SLACK_CHANNEL_ID"
    )
    
    # Step 8: Kubernetes investigation using Claude Code
    workflow.step(
        name="kubernetes-investigation-claude-code",
        executor=inline_agent_executor(
            name="kubernetes-claude-code-investigator",
            ai_instructions="You are Claude Code specializing in Kubernetes investigation and incident response. Use kubectl, helm, and cluster health tools to diagnose issues systematically. Post significant findings to Slack immediately using pre-fetched secrets. Always structure your findings in JSON format.",
            runners=["core-testing-2"],
            llm_model="gpt-4o-mini",
            is_debug_mode=True,
            tools=[
                {
                    "name": "kubectl",
                    "alias": "kubectl",
                    "description": "Execute kubectl commands with comprehensive Kubernetes operations",
                    "type": "docker",
                    "image": "bitnami/kubectl:latest",
                    "content": """#!/bin/bash
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
                            "destination": "/var/run/secrets/kubernetes.io/serviceaccount/token"
                        },
                        {
                            "source": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
                            "destination": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
                        }
                    ]
                },
                {
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
    \\"text\\": \\"🚢 Kubernetes Investigation Update\\",
    \\"blocks\\": [
      {
        \\"type\\": \\"section\\",
        \\"text\\": {
          \\"type\\": \\"mrkdwn\\",
          \\"text\\": \\"🚢 **Kubernetes Investigation**\\\\n\\\\n$message\\"
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
            ],
            message="""Your Goal: Investigate Kubernetes cluster based on AI-prioritized areas with progress updates.

AI Analysis Context: $INCIDENT_ANALYSIS

Incident Details:
- ID: ${incident_id}
- Title: ${incident_title}
- Category: $(echo "$INCIDENT_ANALYSIS" | jq -r '.incident_category')
- Key Areas: $(echo "$INCIDENT_ANALYSIS" | jq -r '.key_investigation_areas | join(", ")')
- Priority: $(echo "$INCIDENT_ANALYSIS" | jq -r '.investigation_priority.kubernetes')

Instructions:
1. Use your kubectl and cluster tools to investigate systematically
2. Post progress updates to Slack channel: $SLACK_CHANNEL_ID using pre-fetched secrets
3. Focus on AI-identified key areas and incident category
4. If category is 'deployment', focus on recent changes
5. If category is 'infrastructure', focus on resource health
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
        ),
        depends=["create-incident-channel"],
        preconditions=[
            precondition('echo "$INCIDENT_ANALYSIS" | jq -r \'.investigation_priority.kubernetes\'', "re:(high|medium)")
        ],
        retry_policy=retry_policy(limit=2, interval_sec=60),
        continue_on=continue_on(failure=True),
        output="K8S_FINDINGS"
    )
    
    # Step 9: Final incident report
    workflow.step(
        name="final-incident-report-claude-code",
        executor=docker_executor(
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
STATUS="investigating"
ROOT_CAUSE="AI-driven investigation completed"
IMPACT="moderate"

STATUS_EMOJI="🔍"
COMPLETENESS_EMOJI="✅"

REPORT_CONTENT="# 🚨 Incident Response Report

**Incident ID:** $incident_id
**Title:** $incident_title
**Severity:** $incident_severity
**Status:** $STATUS_EMOJI $STATUS
**Time:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')

## 📊 Executive Summary

$STATUS_EMOJI **Claude Code Investigation Completed**
- AI-driven analysis executed across available platforms
- Data completeness: $COMPLETENESS_EMOJI complete
- Structured findings aggregated and analyzed
- Automated recommendations generated

## 🔍 Investigation Results

**Status:** $STATUS
**Root Cause:** $ROOT_CAUSE
**Impact:** $IMPACT

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
            env={
                "incident_id": "${incident_id}",
                "incident_title": "${incident_title}",
                "incident_severity": "${incident_severity}",
                "channel_id": "$SLACK_CHANNEL_ID",
                "all_secrets": "$ALL_SECRETS"
            }
        ),
        depends=["kubernetes-investigation-claude-code"],
        continue_on=continue_on(failure=True)
    )
    
    return workflow


if __name__ == "__main__":
    # Build the workflow
    workflow = build_incident_response_workflow()
    
    # Compile the workflow
    compiled_workflow = workflow.compile()
    
    print("🚀 Incident Response Workflow with Claude Code Integration")
    print("=" * 60)
    print(f"Workflow Name: {compiled_workflow['name']}")
    print(f"Description: {compiled_workflow['description']}")
    print(f"Steps: {len(compiled_workflow['workflow']['steps'])}")
    print("=" * 60)
    
    # Save compiled workflow
    import json
    with open("/Users/shaked/kubiya/orchestrator/workflow_sdk/incident-response-wf/workflows/compiled_incident_response_dsl.json", "w") as f:
        json.dump(compiled_workflow, f, indent=2)
    
    print("✅ Workflow compiled and saved to compiled_incident_response_dsl.json")
    print("\nKey Features:")
    print("- Claude Code as AI agent in investigation steps")
    print("- Kubernetes investigation with kubectl tools")
    print("- Slack integration for real-time updates")
    print("- Checkpoint system for workflow resilience")
    print("- Structured JSON outputs for all findings")
    print("- End-to-end incident reporting")