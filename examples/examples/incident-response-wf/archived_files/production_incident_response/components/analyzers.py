"""Analysis components for incident investigation."""

from typing import Dict, Any
from ..models.config import ClaudeCodeConfig
from ..tools.generator import ClaudeCodeToolGenerator


class ClaudeCodeAnalyzer:
    """Handles Claude Code investigation with configurable tools."""
    
    def __init__(self, config: ClaudeCodeConfig):
        self.config = config
        self.generator = ClaudeCodeToolGenerator(config)
    
    def generate_investigation_step(self) -> Dict[str, Any]:
        """Generate the complete Claude Code investigation step configuration."""
        
        return {
            "name": "claude-code-investigation",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "claude_code_investigation",
                        "description": "Configurable Claude Code investigation with CLI tools",
                        "type": "docker",
                        "image": self.config.base_image,
                        "content": self.generator.generate_installation_script()
                    },
                    "args": {
                        "incident_data": "${INCIDENT_DATA}",
                        "all_secrets": "${ALL_SECRETS}",
                        "slack_channel_id": "${SLACK_CHANNEL_ID}"
                    }
                }
            },
            "depends": ["create-incident-channel"],
            "output": "INVESTIGATION_ANALYSIS"
        }
    
    def create_custom_investigation_step(self, 
                                       tool_names: list,
                                       custom_analysis_script: str = None) -> Dict[str, Any]:
        """Create a custom investigation step with specific tools."""
        
        # Filter tools to only include requested ones
        enabled_tools = [tool for tool in self.config.tools if tool.name in tool_names]
        
        # Create a custom config with only the selected tools
        custom_config = ClaudeCodeConfig(
            base_image=self.config.base_image,
            tools=enabled_tools,
            global_environment=self.config.global_environment,
            kubernetes_enabled=self.config.kubernetes_enabled
        )
        
        custom_generator = ClaudeCodeToolGenerator(custom_config)
        
        # Use custom analysis script if provided
        if custom_analysis_script:
            script = custom_analysis_script
        else:
            script = custom_generator.generate_installation_script()
        
        return {
            "name": "custom-claude-code-investigation",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "custom_claude_investigation",
                        "description": f"Custom Claude Code investigation with tools: {', '.join(tool_names)}",
                        "type": "docker",
                        "image": custom_config.base_image,
                        "content": script
                    },
                    "args": {
                        "incident_data": "${INCIDENT_DATA}",
                        "all_secrets": "${ALL_SECRETS}",
                        "slack_channel_id": "${SLACK_CHANNEL_ID}"
                    }
                }
            },
            "depends": ["create-incident-channel"],
            "output": "CUSTOM_INVESTIGATION_ANALYSIS"
        }


class SecretsManager:
    """Handles secrets gathering and management."""
    
    @staticmethod
    def generate_secrets_step() -> Dict[str, Any]:
        """Generate secrets gathering step configuration."""
        
        return {
            "name": "get-secrets",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "gather_secrets",
                        "description": "Gather all required secrets for CLI tools",
                        "type": "docker",
                        "image": "alpine:latest",
                        "content": SecretsManager._generate_secrets_script()
                    },
                    "args": {
                        "slack_token": "${SLACK_TOKEN}"
                    }
                }
            },
            "depends": ["get-slack-token"],
            "output": "ALL_SECRETS"
        }
    
    @staticmethod
    def _generate_secrets_script() -> str:
        """Generate shell script for secrets gathering."""
        
        return '''#!/bin/sh
set -e
apk add --no-cache jq

echo "🔐 [STEP 3/7] Fetching required secrets..."
echo "📅 Timestamp: $(date)"

# Create comprehensive secrets bundle for all CLI tools
echo "🔑 Preparing secrets bundle for configurable tools..."

# Function to safely get environment variable or use default
get_env_or_default() {
    local var_name="$1"
    local default_value="$2"
    local current_value
    
    # Use parameter expansion to get the value
    eval "current_value=\\$${var_name}"
    
    if [ -z "$current_value" ]; then
        echo "$default_value"
    else
        echo "$current_value"
    fi
}

# Gather all possible secrets with fallbacks
DATADOG_API_KEY=$(get_env_or_default "DATADOG_API_KEY" "demo_datadog_key")
DATADOG_APP_KEY=$(get_env_or_default "DATADOG_APP_KEY" "demo_datadog_app_key")
OBSERVE_API_KEY=$(get_env_or_default "OBSERVE_API_KEY" "demo_observe_key")
OBSERVE_CUSTOMER=$(get_env_or_default "OBSERVE_CUSTOMER" "demo_customer")
ARGOCD_USERNAME=$(get_env_or_default "ARGOCD_USERNAME" "admin")
ARGOCD_PASSWORD=$(get_env_or_default "ARGOCD_PASSWORD" "demo_password")
ARGOCD_SERVER=$(get_env_or_default "ARGOCD_SERVER" "argocd.company.com")
GITHUB_TOKEN=$(get_env_or_default "GITHUB_TOKEN" "demo_github_token")
ANTHROPIC_API_KEY=$(get_env_or_default "ANTHROPIC_API_KEY" "sk-demo-anthropic-key")

# Kubernetes secrets (if available)
KUBERNETES_TOKEN=""
KUBERNETES_CA_CERT=""
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
    KUBERNETES_TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
fi
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt" ]; then
    KUBERNETES_CA_CERT=$(cat /var/run/secrets/kubernetes.io/serviceaccount/ca.crt | base64 -w 0)
fi

echo "🔍 Secrets validation:"
echo "  📊 Datadog API: $([ "$DATADOG_API_KEY" != "demo_datadog_key" ] && echo "REAL" || echo "DEMO")"
echo "  🔗 GitHub Token: $([ "$GITHUB_TOKEN" != "demo_github_token" ] && echo "REAL" || echo "DEMO")"
echo "  🚀 ArgoCD Server: $ARGOCD_SERVER"
echo "  🤖 Anthropic API: $([ "$ANTHROPIC_API_KEY" != "sk-demo-anthropic-key" ] && echo "REAL" || echo "DEMO")"
echo "  ☸️ Kubernetes: $([ -n "$KUBERNETES_TOKEN" ] && echo "IN-CLUSTER" || echo "EXTERNAL")"
echo "  💬 Slack: $([ "$slack_token" != "null" ] && echo "CONFIGURED" || echo "DEMO")"

# Create comprehensive secrets JSON
cat << EOF
{
  "SLACK_BOT_TOKEN": "$slack_token",
  "DATADOG_API_KEY": "$DATADOG_API_KEY",
  "DATADOG_APP_KEY": "$DATADOG_APP_KEY",
  "OBSERVE_API_KEY": "$OBSERVE_API_KEY",
  "OBSERVE_CUSTOMER": "$OBSERVE_CUSTOMER",
  "ARGOCD_USERNAME": "$ARGOCD_USERNAME",
  "ARGOCD_PASSWORD": "$ARGOCD_PASSWORD",
  "ARGOCD_SERVER": "$ARGOCD_SERVER",
  "GITHUB_TOKEN": "$GITHUB_TOKEN",
  "ANTHROPIC_API_KEY": "$ANTHROPIC_API_KEY",
  "KUBERNETES_TOKEN": "$KUBERNETES_TOKEN",
  "KUBERNETES_CA_CERT": "$KUBERNETES_CA_CERT",
  "secrets_fetched_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "step_status": "completed",
  "validation": {
    "datadog_real": $([ "$DATADOG_API_KEY" != "demo_datadog_key" ] && echo "true" || echo "false"),
    "github_real": $([ "$GITHUB_TOKEN" != "demo_github_token" ] && echo "true" || echo "false"),
    "anthropic_real": $([ "$ANTHROPIC_API_KEY" != "sk-demo-anthropic-key" ] && echo "true" || echo "false"),
    "kubernetes_available": $([ -n "$KUBERNETES_TOKEN" ] && echo "true" || echo "false"),
    "slack_configured": $([ "$slack_token" != "null" ] && echo "true" || echo "false")
  }
}
EOF

echo "✅ [STEP 3/7] All secrets prepared successfully"'''


class ValidationAnalyzer:
    """Handles workflow validation and health checks."""
    
    @staticmethod
    def generate_pre_execution_validation() -> str:
        """Generate validation script to run before workflow execution."""
        
        return '''#!/bin/sh
set -e

echo "🔍 Pre-execution validation..."

# Validate environment
if [ -z "$KUBIYA_API_KEY" ]; then
    echo "❌ KUBIYA_API_KEY not set"
    exit 1
fi

# Validate workflow parameters
if [ -z "$event" ]; then
    echo "❌ Event parameter required"
    exit 1
fi

# Validate JSON format
echo "$event" | jq . > /dev/null || {
    echo "❌ Event parameter is not valid JSON"
    exit 1
}

# Check required fields
INCIDENT_ID=$(echo "$event" | jq -r '.id // empty')
if [ -z "$INCIDENT_ID" ]; then
    echo "❌ Event must contain 'id' field"
    exit 1
fi

INCIDENT_TITLE=$(echo "$event" | jq -r '.title // empty')
if [ -z "$INCIDENT_TITLE" ]; then
    echo "❌ Event must contain 'title' field"
    exit 1
fi

echo "✅ Pre-execution validation passed"
echo "  🆔 Incident ID: $INCIDENT_ID"
echo "  📝 Incident Title: $INCIDENT_TITLE"'''
    
    @staticmethod
    def generate_post_execution_validation() -> str:
        """Generate validation script to run after workflow execution."""
        
        return '''#!/bin/sh
set -e

echo "🔍 Post-execution validation..."

# Check if all expected outputs exist
if [ -z "$INCIDENT_DATA" ]; then
    echo "⚠️ INCIDENT_DATA output missing"
fi

if [ -z "$INVESTIGATION_ANALYSIS" ]; then
    echo "⚠️ INVESTIGATION_ANALYSIS output missing"
fi

if [ -z "$SLACK_CHANNEL_ID" ]; then
    echo "⚠️ SLACK_CHANNEL_ID output missing"
fi

# Validate investigation analysis structure
if [ -n "$INVESTIGATION_ANALYSIS" ]; then
    CONFIDENCE=$(echo "$INVESTIGATION_ANALYSIS" | jq -r '.confidence_score // 0')
    TOOLS_READY=$(echo "$INVESTIGATION_ANALYSIS" | jq -r '.claude_code_integration.tools_ready_count // 0')
    
    echo "📊 Investigation Results:"
    echo "  🎯 Confidence: $(echo "scale=0; $CONFIDENCE * 100" | bc)%"
    echo "  🛠️ Tools Ready: $TOOLS_READY"
fi

echo "✅ Post-execution validation completed"'''