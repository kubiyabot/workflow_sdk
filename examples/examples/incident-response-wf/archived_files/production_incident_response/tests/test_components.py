"""Tests for workflow components."""

import pytest
import json
from unittest.mock import Mock, patch

from components.parsers import IncidentParser
from components.integrations import SlackIntegration, DatadogIntegration
from components.analyzers import ClaudeCodeAnalyzer, SecretsManager
from components.builders import WorkflowBuilder, create_production_workflow, create_test_workflow
from models.config import WorkflowConfig, ClaudeCodeConfig, SlackConfig
from models.incident import IncidentEvent, KubiyaMetadata, IncidentSeverity
from tools.registry import get_default_tools


class TestIncidentParser:
    """Test incident parsing functionality."""
    
    def test_generate_parsing_script(self):
        """Test parsing script generation."""
        
        script = IncidentParser.generate_parsing_script()
        
        assert "#!/bin/sh" in script
        assert "apk add --no-cache jq" in script
        assert "INCIDENT_ID=" in script
        assert "INCIDENT_TITLE=" in script
        assert "INCIDENT_SEVERITY=" in script
        
        # Check for validation logic
        assert "Incident ID is required" in script
        assert "Incident title is required" in script
    
    def test_validate_incident_data(self):
        """Test incident data validation."""
        
        # Valid data
        valid_data = {
            "incident_id": "INC-001",
            "incident_title": "Test Incident",
            "incident_severity": "high"
        }
        assert IncidentParser.validate_incident_data(valid_data) == True
        
        # Missing required field
        invalid_data = {
            "incident_title": "Test Incident",
            "incident_severity": "high"
            # Missing incident_id
        }
        assert IncidentParser.validate_incident_data(invalid_data) == False
        
        # Invalid severity
        invalid_severity = {
            "incident_id": "INC-001",
            "incident_title": "Test Incident",
            "incident_severity": "invalid"
        }
        assert IncidentParser.validate_incident_data(invalid_severity) == False
    
    def test_create_test_event(self):
        """Test test event creation."""
        
        event = IncidentParser.create_test_event()
        
        assert isinstance(event, IncidentEvent)
        assert event.id.startswith("INC-2024-PROD-TEST")
        assert event.severity == IncidentSeverity.CRITICAL
        assert "Payment Gateway" in event.title
        assert event.source == "datadog"
        assert len(event.tags) > 0


class TestSlackIntegration:
    """Test Slack integration functionality."""
    
    def test_slack_config_creation(self):
        """Test Slack configuration creation."""
        
        config = SlackConfig(
            channel_prefix="test",
            channel_suffix_length=15,
            use_blocks=True
        )
        
        integration = SlackIntegration(config)
        assert integration.config.channel_prefix == "test"
        assert integration.config.use_blocks == True
    
    def test_token_fetch_script_generation(self):
        """Test Slack token fetch step generation."""
        
        config = SlackConfig()
        integration = SlackIntegration(config)
        
        step_config = integration.generate_token_fetch_script()
        
        assert step_config["name"] == "get-slack-token"
        assert step_config["executor"]["type"] == "kubiya"
        assert "slack/token" in step_config["executor"]["config"]["url"]
        assert step_config["depends"] == ["parse-incident-event"]
        assert step_config["output"] == "SLACK_TOKEN"
    
    def test_channel_creation_script(self):
        """Test Slack channel creation script."""
        
        config = SlackConfig(channel_prefix="test", channel_suffix_length=10)
        integration = SlackIntegration(config)
        
        script = integration.generate_channel_creation_script()
        
        assert "#!/bin/sh" in script
        assert "Creating Slack incident channel" in script
        assert "test-" in script  # Channel prefix
        assert "conversations.create" in script
        assert "Authorization: Bearer" in script
    
    def test_update_script_generation(self):
        """Test Slack update script generation."""
        
        config = SlackConfig()
        integration = SlackIntegration(config)
        
        script = integration.generate_update_script()
        
        assert "#!/bin/sh" in script
        assert "Updating Slack with investigation results" in script
        assert "CLAUDE CODE INVESTIGATION COMPLETE" in script
        assert "chat.postMessage" in script


class TestDatadogIntegration:
    """Test Datadog integration functionality."""
    
    def test_enrichment_script_generation(self):
        """Test Datadog enrichment script generation."""
        
        script = DatadogIntegration.generate_enrichment_script()
        
        assert "#!/bin/sh" in script
        assert "Enriching incident with Datadog metrics" in script
        assert "pip3 install datadog" in script
        assert "DATADOG_API_KEY" in script
        assert "DATADOG_APP_KEY" in script
        
        # Check for demo mode handling
        assert "demo_datadog_key" in script
        assert "simulated data" in script
        
        # Check for real API integration
        assert "api.datadoghq.com" in script


class TestClaudeCodeAnalyzer:
    """Test Claude Code analyzer functionality."""
    
    def test_analyzer_creation(self):
        """Test creating Claude Code analyzer."""
        
        config = ClaudeCodeConfig(
            base_image="ubuntu:22.04",
            tools=get_default_tools()[:2],  # Just first 2 tools for testing
            installation_timeout=300
        )
        
        analyzer = ClaudeCodeAnalyzer(config)
        assert analyzer.config.base_image == "ubuntu:22.04"
        assert len(analyzer.config.tools) == 2
    
    def test_investigation_step_generation(self):
        """Test investigation step generation."""
        
        config = ClaudeCodeConfig(
            base_image="alpine:latest",
            tools=get_default_tools()[:1],  # Just one tool
            kubernetes_enabled=False
        )
        
        analyzer = ClaudeCodeAnalyzer(config)
        step = analyzer.generate_investigation_step()
        
        assert step["name"] == "claude-code-investigation"
        assert step["executor"]["type"] == "tool"
        assert step["executor"]["config"]["tool_def"]["type"] == "docker"
        assert step["executor"]["config"]["tool_def"]["image"] == "alpine:latest"
        assert "claude_code_investigation" == step["executor"]["config"]["tool_def"]["name"]
        assert step["depends"] == ["create-incident-channel"]
        assert step["output"] == "INVESTIGATION_ANALYSIS"
    
    def test_custom_investigation_step(self):
        """Test custom investigation step with specific tools."""
        
        config = ClaudeCodeConfig(
            tools=get_default_tools()
        )
        
        analyzer = ClaudeCodeAnalyzer(config)
        
        # Create custom step with specific tools
        custom_step = analyzer.create_custom_investigation_step(
            tool_names=["kubectl", "jq"],
            custom_analysis_script="echo 'Custom analysis'"
        )
        
        assert custom_step["name"] == "custom-claude-code-investigation"
        assert "Custom analysis" in custom_step["executor"]["config"]["tool_def"]["content"]


class TestSecretsManager:
    """Test secrets management functionality."""
    
    def test_secrets_step_generation(self):
        """Test secrets gathering step generation."""
        
        step = SecretsManager.generate_secrets_step()
        
        assert step["name"] == "get-secrets"
        assert step["executor"]["type"] == "tool"
        assert step["executor"]["config"]["tool_def"]["name"] == "gather_secrets"
        assert step["depends"] == ["get-slack-token"]
        assert step["output"] == "ALL_SECRETS"
    
    def test_secrets_script_content(self):
        """Test secrets gathering script content."""
        
        script = SecretsManager._generate_secrets_script()
        
        assert "#!/bin/sh" in script
        assert "Fetching required secrets" in script
        assert "DATADOG_API_KEY" in script
        assert "GITHUB_TOKEN" in script
        assert "get_env_or_default" in script
        
        # Check for demo fallbacks
        assert "demo_datadog_key" in script
        assert "demo_github_token" in script


class TestWorkflowBuilder:
    """Test workflow building functionality."""
    
    def test_builder_creation(self):
        """Test creating workflow builder."""
        
        config = WorkflowConfig.create_default()
        builder = WorkflowBuilder(config)
        
        assert builder.config.name == config.name
        assert isinstance(builder.slack_integration, SlackIntegration)
        assert isinstance(builder.claude_analyzer, ClaudeCodeAnalyzer)
    
    def test_complete_workflow_building(self):
        """Test building complete workflow."""
        
        config = WorkflowConfig.create_default()
        builder = WorkflowBuilder(config)
        
        workflow = builder.build_complete_workflow()
        workflow_dict = workflow.to_dict()
        
        assert workflow_dict["name"] == config.name
        assert workflow_dict["description"] == config.description
        assert workflow_dict["type"] == "chain"
        assert workflow_dict["runner"] == config.runner
        assert len(workflow_dict["steps"]) >= 6  # Base steps
        
        # Check step names
        step_names = [step["name"] for step in workflow_dict["steps"]]
        expected_steps = [
            "parse-incident-event",
            "get-slack-token", 
            "get-secrets",
            "create-incident-channel",
            "claude-code-investigation",
            "update-slack-results"
        ]
        
        for expected_step in expected_steps:
            assert expected_step in step_names
    
    def test_minimal_workflow_building(self):
        """Test building minimal workflow."""
        
        config = WorkflowConfig.create_default()
        builder = WorkflowBuilder(config)
        
        workflow = builder.build_minimal_workflow()
        workflow_dict = workflow.to_dict()
        
        assert "minimal" in workflow_dict["name"]
        assert len(workflow_dict["steps"]) == 4  # Minimal steps
        
        # Check for minimal investigation step
        step_names = [step["name"] for step in workflow_dict["steps"]]
        assert "minimal-investigation" in step_names
    
    def test_custom_workflow_building(self):
        """Test building custom workflow with specific steps."""
        
        config = WorkflowConfig.create_default()
        builder = WorkflowBuilder(config)
        
        enabled_steps = ["parse", "secrets", "investigation"]
        tool_names = ["kubectl", "jq"]
        
        workflow = builder.build_custom_workflow(enabled_steps, tool_names)
        workflow_dict = workflow.to_dict()
        
        assert "custom" in workflow_dict["name"]
        assert len(workflow_dict["steps"]) == 3  # Only enabled steps
        
        step_names = [step["name"] for step in workflow_dict["steps"]]
        assert "parse-incident-event" in step_names
        assert "get-secrets" in step_names
        assert "custom-claude-code-investigation" in step_names
    
    def test_optional_steps_integration(self):
        """Test optional steps integration."""
        
        config = WorkflowConfig.create_default()
        config.enable_datadog_enrichment = True
        config.enable_github_analysis = True
        
        builder = WorkflowBuilder(config)
        workflow = builder.build_complete_workflow()
        workflow_dict = workflow.to_dict()
        
        step_names = [step["name"] for step in workflow_dict["steps"]]
        
        # Check for optional steps
        assert "enrich-with-datadog" in step_names
        assert "analyze-github-changes" in step_names


class TestConvenienceFunctions:
    """Test convenience functions for workflow creation."""
    
    def test_create_production_workflow(self):
        """Test production workflow creation."""
        
        workflow = create_production_workflow()
        workflow_dict = workflow.to_dict()
        
        assert "production" in workflow_dict["name"].lower()
        assert len(workflow_dict["steps"]) >= 6
    
    def test_create_test_workflow(self):
        """Test test workflow creation."""
        
        workflow = create_test_workflow()
        workflow_dict = workflow.to_dict()
        
        assert "test" in workflow_dict["name"].lower() or "minimal" in workflow_dict["name"].lower()
        # Test workflows should be simpler
        assert len(workflow_dict["steps"]) <= 6
    
    def test_create_production_workflow_with_custom_config(self):
        """Test production workflow with custom configuration."""
        
        config = WorkflowConfig(
            name="custom-production",
            description="Custom production workflow",
            runner="custom-runner",
            claude_code=ClaudeCodeConfig(tools=get_default_tools()[:2])
        )
        
        workflow = create_production_workflow(config)
        workflow_dict = workflow.to_dict()
        
        assert workflow_dict["name"] == "custom-production"
        assert workflow_dict["description"] == "Custom production workflow"
        assert workflow_dict["runner"] == "custom-runner"


class TestWorkflowValidation:
    """Test workflow validation and error handling."""
    
    def test_workflow_step_dependencies(self):
        """Test that workflow steps have correct dependencies."""
        
        config = WorkflowConfig.create_default()
        builder = WorkflowBuilder(config)
        workflow = builder.build_complete_workflow()
        workflow_dict = workflow.to_dict()
        
        # Create dependency map
        step_deps = {}
        for step in workflow_dict["steps"]:
            step_name = step["name"]
            depends = step.get("depends", [])
            step_deps[step_name] = depends
        
        # Validate key dependencies
        assert "parse-incident-event" not in step_deps or step_deps["parse-incident-event"] == []
        assert "get-slack-token" in step_deps and "parse-incident-event" in step_deps["get-slack-token"]
        assert "get-secrets" in step_deps and "get-slack-token" in step_deps["get-secrets"]
        assert "claude-code-investigation" in step_deps and "create-incident-channel" in step_deps["claude-code-investigation"]
    
    def test_workflow_outputs(self):
        """Test that workflow steps have required outputs."""
        
        config = WorkflowConfig.create_default()
        builder = WorkflowBuilder(config)
        workflow = builder.build_complete_workflow()
        workflow_dict = workflow.to_dict()
        
        # Check for required outputs
        step_outputs = {}
        for step in workflow_dict["steps"]:
            if "output" in step:
                step_outputs[step["name"]] = step["output"]
        
        assert "INCIDENT_DATA" in step_outputs.values()
        assert "SLACK_TOKEN" in step_outputs.values()
        assert "ALL_SECRETS" in step_outputs.values()
        assert "INVESTIGATION_ANALYSIS" in step_outputs.values()