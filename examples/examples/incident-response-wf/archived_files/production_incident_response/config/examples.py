"""Configuration examples and templates."""

from ..models.config import WorkflowConfig, ClaudeCodeConfig, SlackConfig
from ..tools.registry import get_default_tools, get_minimal_tools, get_full_toolset


def create_example_config() -> WorkflowConfig:
    """Create an example configuration with default tools."""
    
    claude_config = ClaudeCodeConfig(
        base_image="ubuntu:22.04",
        tools=get_default_tools(),
        installation_timeout=600,
        investigation_timeout=1800,
        kubernetes_enabled=True
    )
    
    slack_config = SlackConfig(
        channel_prefix="inc",
        channel_suffix_length=20,
        use_blocks=True,
        notify_on_start=True,
        notify_on_completion=True,
        notify_on_error=True
    )
    
    return WorkflowConfig(
        name="production-incident-response",
        version="2.0.0",
        description="Production-grade incident response workflow with configurable Claude Code tools",
        runner="core-testing-2",
        timeout=3600,
        claude_code=claude_config,
        slack=slack_config,
        enable_datadog_enrichment=True,
        enable_github_analysis=True,
        enable_kubernetes_analysis=True,
        demo_mode=False
    )


def create_minimal_config() -> WorkflowConfig:
    """Create a minimal configuration for testing."""
    
    claude_config = ClaudeCodeConfig(
        base_image="alpine:latest",
        tools=get_minimal_tools(),
        installation_timeout=300,
        investigation_timeout=600,
        kubernetes_enabled=False
    )
    
    slack_config = SlackConfig(
        channel_prefix="test",
        use_blocks=False,
        notify_on_start=False,
        notify_on_completion=True,
        notify_on_error=True
    )
    
    return WorkflowConfig(
        name="minimal-incident-response",
        version="2.0.0-minimal",
        description="Minimal incident response workflow for testing",
        runner="core-testing-2",
        timeout=1800,
        claude_code=claude_config,
        slack=slack_config,
        enable_datadog_enrichment=False,
        enable_github_analysis=False,
        enable_kubernetes_analysis=True,
        demo_mode=True
    )


def create_full_config() -> WorkflowConfig:
    """Create a full configuration with all available tools."""
    
    claude_config = ClaudeCodeConfig(
        base_image="ubuntu:22.04",
        tools=get_full_toolset(),
        installation_timeout=900,
        investigation_timeout=2400,
        kubernetes_enabled=True
    )
    
    slack_config = SlackConfig(
        channel_prefix="incident",
        channel_suffix_length=25,
        use_blocks=True,
        update_interval=300,
        notify_on_start=True,
        notify_on_completion=True,
        notify_on_error=True
    )
    
    return WorkflowConfig(
        name="full-incident-response",
        version="2.0.0-full",
        description="Complete incident response workflow with all available tools",
        runner="core-testing-2",
        timeout=4800,
        claude_config=claude_config,
        slack=slack_config,
        enable_datadog_enrichment=True,
        enable_github_analysis=True,
        enable_kubernetes_analysis=True,
        demo_mode=False
    )


def create_kubernetes_focused_config() -> WorkflowConfig:
    """Create a configuration focused on Kubernetes incident response."""
    
    from ..tools.registry import ToolRegistry
    
    registry = ToolRegistry()
    k8s_tools = [
        registry.jq_tool(),
        registry.kubectl(),
        registry.helm(),
        registry.docker_cli()
    ]
    
    claude_config = ClaudeCodeConfig(
        base_image="ubuntu:22.04",
        tools=k8s_tools,
        kubernetes_enabled=True
    )
    
    return WorkflowConfig(
        name="k8s-incident-response",
        description="Kubernetes-focused incident response workflow",
        claude_code=claude_config,
        enable_kubernetes_analysis=True,
        enable_datadog_enrichment=False,
        enable_github_analysis=False
    )


def create_observability_focused_config() -> WorkflowConfig:
    """Create a configuration focused on observability and monitoring."""
    
    from ..tools.registry import ToolRegistry
    
    registry = ToolRegistry()
    observability_tools = [
        registry.jq_tool(),
        registry.datadog_cli(),
        registry.observe_cli(),
        registry.claude_code_cli()
    ]
    
    claude_config = ClaudeCodeConfig(
        base_image="ubuntu:22.04",
        tools=observability_tools,
        kubernetes_enabled=False
    )
    
    return WorkflowConfig(
        name="observability-incident-response",
        description="Observability-focused incident response workflow",
        claude_code=claude_config,
        enable_datadog_enrichment=True,
        enable_github_analysis=False,
        enable_kubernetes_analysis=False
    )


def create_development_config() -> WorkflowConfig:
    """Create a configuration optimized for development and testing."""
    
    claude_config = ClaudeCodeConfig(
        base_image="alpine:latest",
        tools=get_minimal_tools(),
        installation_timeout=180,
        investigation_timeout=300,
        kubernetes_enabled=False
    )
    
    slack_config = SlackConfig(
        channel_prefix="dev-test",
        use_blocks=False
    )
    
    return WorkflowConfig(
        name="development-incident-response",
        version="2.0.0-dev",
        description="Development and testing incident response workflow",
        runner="core-testing-2",
        timeout=900,
        claude_code=claude_config,
        slack=slack_config,
        enable_datadog_enrichment=False,
        enable_github_analysis=False,
        enable_kubernetes_analysis=False,
        demo_mode=True,
        demo_api_keys={
            "datadog": "demo_key",
            "github": "demo_token",
            "slack": "demo_bot_token"
        }
    )