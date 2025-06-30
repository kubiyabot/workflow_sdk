"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.incident import IncidentEvent, IncidentData, KubiyaMetadata, IncidentSeverity
from models.config import WorkflowConfig, ClaudeCodeConfig, ToolDefinition, ToolType
from models.secrets import SecretsBundle, ToolCredentials
from models.analysis import InvestigationAnalysis, ToolStatus, RecommendedAction, Priority


class TestIncidentModels:
    """Test incident-related models."""
    
    def test_incident_event_creation(self):
        """Test creating a valid incident event."""
        
        event = IncidentEvent(
            id="INC-001",
            title="Test Incident",
            severity=IncidentSeverity.HIGH,
            body="Test incident description",
            kubiya=KubiyaMetadata(slack_channel_id="#test-channel")
        )
        
        assert event.id == "INC-001"
        assert event.title == "Test Incident"
        assert event.severity == IncidentSeverity.HIGH
        assert event.kubiya.slack_channel_id == "#test-channel"
    
    def test_incident_event_validation(self):
        """Test incident event validation."""
        
        # Missing required fields
        with pytest.raises(ValidationError):
            IncidentEvent(
                title="Test",
                kubiya=KubiyaMetadata(slack_channel_id="#test")
                # Missing id
            )
        
        # Empty ID
        with pytest.raises(ValidationError):
            IncidentEvent(
                id="",
                title="Test",
                kubiya=KubiyaMetadata(slack_channel_id="#test")
            )
        
        # Empty title
        with pytest.raises(ValidationError):
            IncidentEvent(
                id="INC-001",
                title="",
                kubiya=KubiyaMetadata(slack_channel_id="#test")
            )
    
    def test_incident_data_from_event(self):
        """Test creating IncidentData from IncidentEvent."""
        
        event = IncidentEvent(
            id="INC-001",
            title="Test Incident",
            severity=IncidentSeverity.CRITICAL,
            body="Test description",
            url="https://example.com/incident/1",
            kubiya=KubiyaMetadata(slack_channel_id="#incident-test"),
            source="datadog",
            tags={"team": "platform", "service": "api"}
        )
        
        incident_data = IncidentData.from_incident_event(event)
        
        assert incident_data.incident_id == "INC-001"
        assert incident_data.incident_title == "Test Incident"
        assert incident_data.incident_severity == IncidentSeverity.CRITICAL
        assert incident_data.incident_description == "Test description"
        assert incident_data.incident_url == "https://example.com/incident/1"
        assert incident_data.slack_channel_suggestion == "#incident-test"
        assert incident_data.source_system == "datadog"
        assert incident_data.tags == {"team": "platform", "service": "api"}
        assert isinstance(incident_data.parsed_at, datetime)
    
    def test_incident_slack_summary(self):
        """Test Slack summary generation."""
        
        incident_data = IncidentData(
            incident_id="INC-001",
            incident_title="Critical Database Issue",
            incident_severity=IncidentSeverity.CRITICAL,
            incident_description="Database connections exhausted",
            slack_channel_suggestion="#critical-incident"
        )
        
        summary = incident_data.to_slack_summary()
        
        assert "🔴" in summary  # Critical severity emoji
        assert "CRITICAL INCIDENT" in summary
        assert "INC-001" in summary
        assert "Critical Database Issue" in summary
        assert "Database connections exhausted" in summary


class TestConfigModels:
    """Test configuration models."""
    
    def test_tool_definition(self):
        """Test creating a tool definition."""
        
        tool = ToolDefinition(
            name="kubectl",
            type=ToolType.CLI,
            description="Kubernetes CLI",
            install_commands=["curl -LO kubectl", "chmod +x kubectl"],
            validation_commands=["kubectl version --client"],
            priority=10
        )
        
        assert tool.name == "kubectl"
        assert tool.type == ToolType.CLI
        assert len(tool.install_commands) == 2
        assert tool.priority == 10
        assert tool.enabled == True  # Default value
    
    def test_claude_code_config(self):
        """Test Claude Code configuration."""
        
        tool = ToolDefinition(
            name="test-tool",
            type=ToolType.CLI,
            description="Test tool",
            install_commands=["echo 'test'"],
            priority=1
        )
        
        config = ClaudeCodeConfig(
            base_image="ubuntu:22.04",
            tools=[tool],
            installation_timeout=300,
            investigation_timeout=600
        )
        
        assert config.base_image == "ubuntu:22.04"
        assert len(config.tools) == 1
        assert config.installation_timeout == 300
        
        # Test enabled tools
        enabled_tools = config.get_enabled_tools()
        assert len(enabled_tools) == 1
        assert enabled_tools[0].name == "test-tool"
        
        # Test get tool by name
        found_tool = config.get_tool_by_name("test-tool")
        assert found_tool is not None
        assert found_tool.name == "test-tool"
        
        # Test non-existent tool
        not_found = config.get_tool_by_name("non-existent")
        assert not_found is None
    
    def test_workflow_config_creation(self):
        """Test creating workflow configuration."""
        
        config = WorkflowConfig.create_default()
        
        assert config.name == "production-incident-response"
        assert config.runner == "core-testing-2"
        assert isinstance(config.claude_code, ClaudeCodeConfig)
        assert len(config.claude_code.tools) > 0


class TestSecretsModels:
    """Test secrets and credentials models."""
    
    def test_tool_credentials(self):
        """Test tool credentials model."""
        
        from pydantic import SecretStr
        
        creds = ToolCredentials(
            tool_name="datadog",
            api_key=SecretStr("secret-key"),
            username="user",
            server_url="https://api.datadoghq.com",
            config_data={"app_key": "app-secret"}
        )
        
        assert creds.tool_name == "datadog"
        assert creds.api_key.get_secret_value() == "secret-key"
        assert creds.username == "user"
        
        # Test environment variables generation
        env_vars = creds.get_env_vars()
        assert "DATADOG_API_KEY" in env_vars
        assert env_vars["DATADOG_API_KEY"] == "secret-key"
        assert "DATADOG_USERNAME" in env_vars
        assert env_vars["DATADOG_USERNAME"] == "user"
        assert "DATADOG_SERVER" in env_vars
        assert "DATADOG_APP_KEY" in env_vars
    
    def test_secrets_bundle(self):
        """Test secrets bundle model."""
        
        bundle = SecretsBundle.create_demo_bundle()
        
        assert bundle.slack_bot_token is not None
        assert bundle.datadog is not None
        assert bundle.github is not None
        
        # Test environment variables generation
        env_vars = bundle.get_all_env_vars()
        assert "SLACK_BOT_TOKEN" in env_vars
        assert "DATADOG_API_KEY" in env_vars
        assert "GITHUB_TOKEN" in env_vars
        
        # Test JSON-safe conversion
        json_safe = bundle.to_json_safe()
        assert "secrets_fetched_at" in json_safe
        assert "step_status" in json_safe


class TestAnalysisModels:
    """Test analysis and investigation models."""
    
    def test_recommended_action(self):
        """Test recommended action model."""
        
        action = RecommendedAction(
            action="Check pod status",
            tool="kubectl get pods",
            priority=Priority.P1,
            rationale="High error rates often correlate with pod failures"
        )
        
        assert action.action == "Check pod status"
        assert action.priority == Priority.P1
        assert action.rationale == "High error rates often correlate with pod failures"
    
    def test_investigation_analysis(self):
        """Test investigation analysis model."""
        
        analysis = InvestigationAnalysis.create_example("INC-001")
        
        assert analysis.incident_id == "INC-001"
        assert isinstance(analysis.investigation_timestamp, datetime)
        assert 0 <= analysis.confidence_score <= 1
        assert len(analysis.tools_installation) > 0
        assert len(analysis.recommended_actions) > 0
        
        # Test success rate calculation
        success_rate = analysis.success_rate
        assert 0 <= success_rate <= 1
        
        # Test critical actions filtering
        critical_actions = analysis.critical_actions
        assert all(action.priority in [Priority.P0, Priority.P1] for action in critical_actions)
        
        # Test Slack summary
        summary = analysis.to_slack_summary()
        assert "INC-001" in summary
        assert "INVESTIGATION COMPLETE" in summary
        assert str(int(analysis.confidence_score * 100)) + "%" in summary


class TestModelIntegration:
    """Test integration between models."""
    
    def test_end_to_end_data_flow(self):
        """Test complete data flow from event to analysis."""
        
        # Start with incident event
        event = IncidentEvent(
            id="FLOW-001",
            title="End-to-End Test",
            severity=IncidentSeverity.MEDIUM,
            body="Testing complete data flow",
            kubiya=KubiyaMetadata(slack_channel_id="#test-flow")
        )
        
        # Convert to incident data
        incident_data = IncidentData.from_incident_event(event)
        assert incident_data.incident_id == "FLOW-001"
        
        # Create secrets bundle
        secrets = SecretsBundle.create_demo_bundle()
        env_vars = secrets.get_all_env_vars()
        assert len(env_vars) > 0
        
        # Create analysis
        analysis = InvestigationAnalysis.create_example("FLOW-001")
        assert analysis.incident_id == "FLOW-001"
        
        # Test serialization/deserialization
        event_json = event.json()
        reconstructed_event = IncidentEvent.parse_raw(event_json)
        assert reconstructed_event.id == event.id
        assert reconstructed_event.title == event.title