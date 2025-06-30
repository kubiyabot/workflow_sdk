"""Workflow builders for creating complete incident response workflows."""

from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from kubiya_workflow_sdk.dsl import Workflow, Step
from ..models.config import WorkflowConfig
from ..models.incident import IncidentEvent
from .parsers import IncidentParser
from .integrations import SlackIntegration, DatadogIntegration, GitHubIntegration
from .analyzers import ClaudeCodeAnalyzer, SecretsManager


class WorkflowBuilder:
    """Builds complete incident response workflows with configurable components."""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.slack_integration = SlackIntegration(config.slack)
        self.claude_analyzer = ClaudeCodeAnalyzer(config.claude_code)
        self.incident_parser = IncidentParser()
    
    def build_complete_workflow(self) -> Workflow:
        """Build the complete incident response workflow."""
        
        # Create base workflow
        workflow = (Workflow(self.config.name)
                   .description(self.config.description)
                   .type("chain")
                   .runner(self.config.runner))
        
        steps = []
        
        # Step 1: Parse incident event
        steps.append(self._create_parsing_step())
        
        # Step 2: Get Slack token
        steps.append(self._create_slack_token_step())
        
        # Step 3: Gather secrets
        steps.append(self._create_secrets_step())
        
        # Step 4: Create Slack channel
        steps.append(self._create_slack_channel_step())
        
        # Step 5: Claude Code investigation (configurable)
        steps.append(self._create_investigation_step())
        
        # Step 6: Update Slack with results
        steps.append(self._create_slack_update_step())
        
        # Optional: Datadog enrichment
        if self.config.enable_datadog_enrichment:
            steps.insert(-2, self._create_datadog_enrichment_step())
        
        # Optional: GitHub analysis
        if self.config.enable_github_analysis:
            steps.append(self._create_github_analysis_step())
        
        # Add all steps to workflow
        workflow.data["steps"] = [step.data if hasattr(step, 'data') else step for step in steps]
        
        return workflow
    
    def _create_parsing_step(self) -> Dict[str, Any]:
        """Create incident parsing step."""
        return {
            "name": "parse-incident-event",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "parse_incident_event",
                        "description": "Parse incident event data from JSON",
                        "type": "docker",
                        "image": "python:3.11-alpine",
                        "content": self.incident_parser.generate_parsing_script()
                    },
                    "args": {
                        "event": "${event}"
                    }
                }
            },
            "output": "INCIDENT_DATA"
        }
    
    def _create_slack_token_step(self) -> Dict[str, Any]:
        """Create Slack token fetching step."""
        return self.slack_integration.generate_token_fetch_script()
    
    def _create_secrets_step(self) -> Dict[str, Any]:
        """Create secrets gathering step."""
        return SecretsManager.generate_secrets_step()
    
    def _create_slack_channel_step(self) -> Dict[str, Any]:
        """Create Slack channel creation step."""
        return {
            "name": "create-incident-channel",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "create_slack_war_room",
                        "description": "Create Slack incident war room",
                        "type": "docker",
                        "image": "curlimages/curl:latest",
                        "content": self.slack_integration.generate_channel_creation_script()
                    },
                    "args": {
                        "incident_data": "${INCIDENT_DATA}",
                        "all_secrets": "${ALL_SECRETS}"
                    }
                }
            },
            "depends": ["get-secrets"],
            "output": "SLACK_CHANNEL_ID"
        }
    
    def _create_investigation_step(self) -> Dict[str, Any]:
        """Create Claude Code investigation step."""
        return self.claude_analyzer.generate_investigation_step()
    
    def _create_slack_update_step(self) -> Dict[str, Any]:
        """Create Slack update step."""
        return {
            "name": "update-slack-results",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "update_slack_with_results",
                        "description": "Update Slack with investigation results",
                        "type": "docker",
                        "image": "curlimages/curl:latest",
                        "content": self.slack_integration.generate_update_script()
                    },
                    "args": {
                        "incident_data": "${INCIDENT_DATA}",
                        "all_secrets": "${ALL_SECRETS}",
                        "slack_channel_id": "${SLACK_CHANNEL_ID}",
                        "investigation_analysis": "${INVESTIGATION_ANALYSIS}"
                    }
                }
            },
            "depends": ["claude-code-investigation"],
            "output": "SLACK_UPDATE_RESULT"
        }
    
    def _create_datadog_enrichment_step(self) -> Dict[str, Any]:
        """Create optional Datadog enrichment step."""
        return {
            "name": "enrich-with-datadog",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "datadog_enrichment",
                        "description": "Enrich incident with Datadog metrics",
                        "type": "docker",
                        "image": "python:3.11-alpine",
                        "content": DatadogIntegration.generate_enrichment_script()
                    },
                    "args": {
                        "incident_data": "${INCIDENT_DATA}",
                        "all_secrets": "${ALL_SECRETS}"
                    }
                }
            },
            "depends": ["get-secrets"],
            "output": "DATADOG_ENRICHMENT"
        }
    
    def _create_github_analysis_step(self) -> Dict[str, Any]:
        """Create optional GitHub analysis step."""
        return {
            "name": "analyze-github-changes",
            "executor": {
                "type": "tool",
                "config": {
                    "tool_def": {
                        "name": "github_analysis",
                        "description": "Analyze recent GitHub changes",
                        "type": "docker",
                        "image": "alpine:latest",
                        "content": GitHubIntegration.generate_analysis_script()
                    },
                    "args": {
                        "incident_data": "${INCIDENT_DATA}",
                        "all_secrets": "${ALL_SECRETS}"
                    }
                }
            },
            "depends": ["update-slack-results"],
            "output": "GITHUB_ANALYSIS"
        }
    
    def build_minimal_workflow(self) -> Workflow:
        """Build a minimal workflow for quick testing."""
        
        workflow = (Workflow(f"{self.config.name}-minimal")
                   .description("Minimal incident response workflow for testing")
                   .type("chain")
                   .runner(self.config.runner))
        
        steps = [
            self._create_parsing_step(),
            self._create_slack_token_step(),
            self._create_secrets_step(),
            {
                "name": "minimal-investigation",
                "executor": {
                    "type": "tool",
                    "config": {
                        "tool_def": {
                            "name": "minimal_investigation",
                            "description": "Minimal investigation for testing",
                            "type": "docker",
                            "image": "alpine:latest",
                            "content": '''#!/bin/sh
set -e
apk add --no-cache jq

echo "🔍 Minimal investigation starting..."
INCIDENT_ID=$(echo "$incident_data" | jq -r '.incident_id')

cat << EOF
{
  "incident_id": "$INCIDENT_ID",
  "investigation_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "claude_code_status": "minimal_complete",
  "confidence_score": 0.75,
  "investigation_summary": "Minimal investigation completed successfully"
}
EOF

echo "✅ Minimal investigation completed"'''
                        },
                        "args": {
                            "incident_data": "${INCIDENT_DATA}",
                            "all_secrets": "${ALL_SECRETS}"
                        }
                    }
                },
                "depends": ["get-secrets"],
                "output": "MINIMAL_ANALYSIS"
            }
        ]
        
        workflow.data["steps"] = steps
        return workflow
    
    def build_custom_workflow(self, 
                            enabled_steps: List[str],
                            tool_names: Optional[List[str]] = None) -> Workflow:
        """Build a custom workflow with specific steps enabled."""
        
        workflow = (Workflow(f"{self.config.name}-custom")
                   .description("Custom incident response workflow")
                   .type("chain")
                   .runner(self.config.runner))
        
        steps = []
        
        # Always include parsing as first step
        if "parse" in enabled_steps:
            steps.append(self._create_parsing_step())
        
        if "slack-token" in enabled_steps:
            steps.append(self._create_slack_token_step())
        
        if "secrets" in enabled_steps:
            steps.append(self._create_secrets_step())
        
        if "slack-channel" in enabled_steps:
            steps.append(self._create_slack_channel_step())
        
        if "investigation" in enabled_steps:
            if tool_names:
                # Use custom investigation with specific tools
                steps.append(self.claude_analyzer.create_custom_investigation_step(tool_names))
            else:
                # Use full investigation
                steps.append(self._create_investigation_step())
        
        if "slack-update" in enabled_steps:
            steps.append(self._create_slack_update_step())
        
        if "datadog" in enabled_steps and self.config.enable_datadog_enrichment:
            steps.append(self._create_datadog_enrichment_step())
        
        if "github" in enabled_steps and self.config.enable_github_analysis:
            steps.append(self._create_github_analysis_step())
        
        workflow.data["steps"] = steps
        return workflow


def create_production_workflow(config: Optional[WorkflowConfig] = None) -> Workflow:
    """Convenience function to create a production-ready workflow."""
    if config is None:
        config = WorkflowConfig.create_default()
    
    builder = WorkflowBuilder(config)
    return builder.build_complete_workflow()


def create_test_workflow(config: Optional[WorkflowConfig] = None) -> Workflow:
    """Convenience function to create a workflow for testing."""
    if config is None:
        config = WorkflowConfig.create_default()
        config.demo_mode = True
    
    builder = WorkflowBuilder(config)
    return builder.build_minimal_workflow()


def create_custom_tool_workflow(tool_names: List[str], config: Optional[WorkflowConfig] = None) -> Workflow:
    """Convenience function to create a workflow with specific tools."""
    if config is None:
        config = WorkflowConfig.create_default()
    
    builder = WorkflowBuilder(config)
    return builder.build_custom_workflow(
        enabled_steps=["parse", "secrets", "investigation"],
        tool_names=tool_names
    )