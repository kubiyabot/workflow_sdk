"""
Tool definitions for incident response workflows.

This module provides reusable tool classes that can be used in
Claude Code agents for investigation and remediation tasks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .models import KubernetesFindings, MonitoringFindings


class ToolConfig(BaseModel):
    """Base configuration for tools."""
    
    name: str = Field(..., description="Tool name")
    alias: str = Field(..., description="Tool alias")
    description: str = Field(..., description="Tool description")
    type: str = Field("docker", description="Tool type")
    image: str = Field(..., description="Docker image")
    timeout: int = Field(300, description="Tool timeout in seconds")
    retry_limit: int = Field(2, description="Retry limit")


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    def __init__(self, config: ToolConfig):
        self.config = config
    
    @abstractmethod
    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for workflow integration."""
        pass
    
    @abstractmethod
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """Validate tool arguments."""
        pass


class KubernetesTool(BaseTool):
    """Kubernetes investigation tool for cluster analysis."""
    
    def __init__(self, 
                 image: str = "bitnami/kubectl:latest",
                 enable_monitoring: bool = True,
                 enable_health_checks: bool = True):
        config = ToolConfig(
            name="kubectl",
            alias="kubectl",
            description="Execute kubectl commands for Kubernetes cluster investigation",
            image=image
        )
        super().__init__(config)
        self.enable_monitoring = enable_monitoring
        self.enable_health_checks = enable_health_checks
    
    def get_definition(self) -> Dict[str, Any]:
        """Get kubectl tool definition."""
        content = self._generate_kubectl_script()
        
        return {
            "name": self.config.name,
            "alias": self.config.alias,
            "description": self.config.description,
            "type": self.config.type,
            "image": self.config.image,
            "content": content,
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
            ] if self.enable_monitoring else []
        }
    
    def _generate_kubectl_script(self) -> str:
        """Generate kubectl script with optional features."""
        script_parts = [
            "#!/bin/bash",
            "set -e",
            "",
            "# Configure kubectl for in-cluster access if available",
            "if [ -f \"/var/run/secrets/kubernetes.io/serviceaccount/token\" ]; then",
            "    echo \"🔧 Configuring in-cluster kubectl access...\"",
            "    kubectl config set-cluster kubernetes --server=https://kubernetes.default.svc --certificate-authority=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
            "    kubectl config set-credentials kubernetes --token=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)",
            "    kubectl config set-context kubernetes --cluster=kubernetes --user=kubernetes",
            "    kubectl config use-context kubernetes",
            "    echo \"✅ kubectl configured for in-cluster access\"",
            "fi",
            "",
            "echo \"🔧 Executing kubectl command: $command\"",
            ""
        ]
        
        if self.enable_health_checks:
            script_parts.extend([
                "# Enhanced kubectl execution with health checks",
                "case \"$command\" in",
                "    \"get nodes\")",
                "        echo \"📊 Node Status Analysis:\"",
                "        kubectl get nodes -o wide",
                "        echo \"\"",
                "        echo \"📊 Node Resource Usage:\"",
                "        kubectl top nodes 2>/dev/null || echo \"⚠️ Metrics server not available\"",
                "        ;;",
                "    \"get pods --all-namespaces\")",
                "        echo \"📊 Pod Status Analysis:\"",
                "        kubectl get pods --all-namespaces",
                "        echo \"\"",
                "        echo \"📊 Problematic Pods:\"",
                "        kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded",
                "        ;;",
                "    \"cluster-health\")",
                "        echo \"🏥 Comprehensive Cluster Health Check\"",
                "        echo \"======================================\"",
                "        echo \"\"",
                "        echo \"🖥️ Node Status:\"",
                "        kubectl get nodes",
                "        echo \"\"",
                "        echo \"🛠️ Critical Pod Issues:\"",
                "        kubectl get pods --all-namespaces --field-selector=status.phase!=Running,status.phase!=Succeeded",
                "        echo \"\"",
                "        echo \"🚀 Deployment Health:\"",
                "        kubectl get deployments --all-namespaces",
                "        echo \"\"",
                "        echo \"🔍 Recent Events:\"",
                "        kubectl get events --all-namespaces --sort-by=.metadata.creationTimestamp | tail -10",
                "        ;;",
                "    *)",
                "        kubectl $command",
                "        ;;",
                "esac"
            ])
        else:
            script_parts.append("kubectl $command")
        
        return "\n".join(script_parts)
    
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """Validate kubectl arguments."""
        return "command" in args and isinstance(args["command"], str)


class MonitoringTool(BaseTool):
    """Monitoring and metrics analysis tool."""
    
    def __init__(self, 
                 provider: str = "mock",
                 image: str = "python:3.11-slim",
                 enable_alerting: bool = False):
        config = ToolConfig(
            name="metrics-query",
            alias="metrics",
            description="Query monitoring metrics and analyze performance data",
            image=image
        )
        super().__init__(config)
        self.provider = provider
        self.enable_alerting = enable_alerting
    
    def get_definition(self) -> Dict[str, Any]:
        """Get monitoring tool definition."""
        content = self._generate_monitoring_script()
        
        return {
            "name": self.config.name,
            "alias": self.config.alias,
            "description": self.config.description,
            "type": self.config.type,
            "image": self.config.image,
            "content": content,
            "args": [
                {
                    "name": "query",
                    "type": "string",
                    "description": "Metric query to execute",
                    "required": True
                },
                {
                    "name": "time_range",
                    "type": "string",
                    "description": "Time range for the query (e.g., '1h', '24h')",
                    "required": False
                }
            ]
        }
    
    def _generate_monitoring_script(self) -> str:
        """Generate monitoring script based on provider."""
        if self.provider == "datadog":
            return self._generate_datadog_script()
        elif self.provider == "prometheus":
            return self._generate_prometheus_script()
        else:
            return self._generate_mock_script()
    
    def _generate_datadog_script(self) -> str:
        """Generate Datadog-specific monitoring script."""
        return """#!/bin/bash
set -e

# Install required packages
pip install datadog-api-client requests >/dev/null 2>&1

echo "📊 Querying Datadog metrics: $query"

python3 << 'EOF'
import os
import json
import sys
from datetime import datetime, timedelta

# Extract credentials from environment
api_key = os.environ.get('DATADOG_API_KEY')
app_key = os.environ.get('DATADOG_APP_KEY')

if not api_key or not app_key:
    print("⚠️ Datadog API keys not available, using mock data")
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

# Real Datadog implementation would go here
print("✅ Datadog API available - would perform real metrics query")
EOF"""
    
    def _generate_prometheus_script(self) -> str:
        """Generate Prometheus-specific monitoring script."""
        return """#!/bin/bash
set -e

echo "📊 Querying Prometheus metrics: $query"

# Mock Prometheus implementation
cat << 'EOF'
{
  "status": "success",
  "data": {
    "resultType": "matrix",
    "result": [
      {
        "metric": {"__name__": "cpu_usage", "instance": "server-1"},
        "values": [
          [1641380400, "85.5"],
          [1641380460, "87.2"],
          [1641380520, "82.8"]
        ]
      }
    ]
  }
}
EOF"""
    
    def _generate_mock_script(self) -> str:
        """Generate mock monitoring script for testing."""
        return """#!/bin/sh
set -e

echo "📊 Querying metrics: $query (time_range: ${time_range:-1h})"

# Mock metrics responses based on query
case "$query" in
    "cpu_usage"|"system.cpu.user")
        cat << 'EOF'
{
  "metric": "cpu_usage",
  "value": 85.5,
  "unit": "percent",
  "timestamp": "2024-01-15T14:25:00Z",
  "status": "warning",
  "threshold": 80.0,
  "trend": "increasing"
}
EOF
        ;;
    "memory_usage"|"system.mem.used")
        cat << 'EOF'
{
  "metric": "memory_usage", 
  "value": 78.2,
  "unit": "percent",
  "timestamp": "2024-01-15T14:25:00Z",
  "status": "normal",
  "threshold": 90.0,
  "trend": "stable"
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
  "threshold": 5.0,
  "trend": "increasing"
}
EOF
        ;;
    "response_time")
        cat << 'EOF'
{
  "metric": "response_time",
  "value": 1200,
  "unit": "milliseconds",
  "timestamp": "2024-01-15T14:25:00Z",
  "status": "warning",
  "threshold": 1000,
  "trend": "increasing"
}
EOF
        ;;
    *)
        cat << 'EOF'
{
  "metric": "unknown",
  "value": 0,
  "unit": "unknown",
  "timestamp": "2024-01-15T14:25:00Z",
  "status": "unknown",
  "trend": "unknown"
}
EOF
        ;;
esac"""
    
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """Validate monitoring arguments."""
        return "query" in args and isinstance(args["query"], str)


class SlackTool(BaseTool):
    """Slack notification tool for incident communication."""
    
    def __init__(self, 
                 image: str = "curlimages/curl:latest",
                 enable_threading: bool = True,
                 enable_formatting: bool = True):
        config = ToolConfig(
            name="slack-notifier",
            alias="slack",
            description="Post notifications and updates to Slack channels",
            image=image
        )
        super().__init__(config)
        self.enable_threading = enable_threading
        self.enable_formatting = enable_formatting
    
    def get_definition(self) -> Dict[str, Any]:
        """Get Slack tool definition."""
        content = self._generate_slack_script()
        
        return {
            "name": self.config.name,
            "alias": self.config.alias,
            "description": self.config.description,
            "type": self.config.type,
            "image": self.config.image,
            "content": content,
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
                    "description": "Message to post",
                    "required": True
                },
                {
                    "name": "message_type",
                    "type": "string",
                    "description": "Message type (update, alert, summary)",
                    "required": False
                },
                {
                    "name": "slack_token",
                    "type": "string",
                    "description": "Slack API token",
                    "required": True
                }
            ]
        }
    
    def _generate_slack_script(self) -> str:
        """Generate Slack notification script."""
        base_script = """#!/bin/sh
set -e

echo "📤 Posting Slack notification to channel: $channel_id"

# Validate token
if [ -z "$slack_token" ]; then
    echo "❌ Slack token not provided"
    exit 1
fi

# Determine message formatting based on type
MESSAGE_TYPE="${message_type:-update}"
"""
        
        if self.enable_formatting:
            base_script += """
# Format message based on type
case "$MESSAGE_TYPE" in
    "alert")
        EMOJI="🚨"
        COLOR="danger"
        ;;
    "update")
        EMOJI="🔍"
        COLOR="good"
        ;;
    "summary")
        EMOJI="📋"
        COLOR="warning"
        ;;
    *)
        EMOJI="ℹ️"
        COLOR="good"
        ;;
esac

# Create formatted message
FORMATTED_MESSAGE="$EMOJI **Incident Response Update**\\n\\n$message"
"""
        else:
            base_script += """
FORMATTED_MESSAGE="$message"
COLOR="good"
"""
        
        base_script += """
# Post to Slack
curl -s -X POST "https://slack.com/api/chat.postMessage" \\
  -H "Authorization: Bearer $slack_token" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"channel\\": \\"$channel_id\\",
    \\"text\\": \\"Incident Response Notification\\",
    \\"attachments\\": [
      {
        \\"color\\": \\"$COLOR\\",
        \\"text\\": \\"$FORMATTED_MESSAGE\\",
        \\"footer\\": \\"Kubiya Incident Response\\",
        \\"ts\\": $(date +%s)
      }
    ]
  }" > /tmp/slack_response.json

# Check response
if grep -q '\\"ok\\":true' /tmp/slack_response.json; then
    echo "✅ Slack notification posted successfully"
else
    echo "❌ Failed to post Slack notification"
    cat /tmp/slack_response.json
    exit 1
fi
"""
        return base_script
    
    def validate_args(self, args: Dict[str, Any]) -> bool:
        """Validate Slack arguments."""
        required_fields = ["channel_id", "message", "slack_token"]
        return all(field in args and isinstance(args[field], str) for field in required_fields)


class ToolFactory:
    """Factory for creating tool instances."""
    
    @staticmethod
    def create_kubernetes_tool(
        enable_monitoring: bool = True,
        enable_health_checks: bool = True,
        custom_image: Optional[str] = None
    ) -> KubernetesTool:
        """Create a Kubernetes tool instance."""
        image = custom_image or "bitnami/kubectl:latest"
        return KubernetesTool(
            image=image,
            enable_monitoring=enable_monitoring,
            enable_health_checks=enable_health_checks
        )
    
    @staticmethod
    def create_monitoring_tool(
        provider: str = "mock",
        enable_alerting: bool = False,
        custom_image: Optional[str] = None
    ) -> MonitoringTool:
        """Create a monitoring tool instance."""
        image = custom_image or "python:3.11-slim"
        return MonitoringTool(
            provider=provider,
            image=image,
            enable_alerting=enable_alerting
        )
    
    @staticmethod
    def create_slack_tool(
        enable_threading: bool = True,
        enable_formatting: bool = True,
        custom_image: Optional[str] = None
    ) -> SlackTool:
        """Create a Slack tool instance."""
        image = custom_image or "curlimages/curl:latest"
        return SlackTool(
            image=image,
            enable_threading=enable_threading,
            enable_formatting=enable_formatting
        )
    
    @staticmethod
    def get_all_tools(
        k8s_config: Optional[Dict[str, Any]] = None,
        monitoring_config: Optional[Dict[str, Any]] = None,
        slack_config: Optional[Dict[str, Any]] = None
    ) -> List[BaseTool]:
        """Get all available tools with optional configurations."""
        tools = []
        
        # Kubernetes tool
        k8s_kwargs = k8s_config or {}
        tools.append(ToolFactory.create_kubernetes_tool(**k8s_kwargs))
        
        # Monitoring tool
        monitoring_kwargs = monitoring_config or {}
        tools.append(ToolFactory.create_monitoring_tool(**monitoring_kwargs))
        
        # Slack tool
        slack_kwargs = slack_config or {}
        tools.append(ToolFactory.create_slack_tool(**slack_kwargs))
        
        return tools