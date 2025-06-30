"""
Factory functions for creating incident response workflows.

This module provides high-level factory functions that simplify the creation
of incident response workflows for different use cases and configurations.
"""

from typing import Optional, Dict, Any, List
from kubiya_workflow_sdk.dsl import Workflow

from .models import WorkflowConfig, SeverityLevel, PriorityLevel
from .builders import IncidentResponseWorkflowBuilder
from .tools import ToolFactory
from .executors import WorkflowExecutor, StreamingWorkflowExecutor


def create_incident_workflow(
    workflow_name: str = "incident-response-workflow",
    config: Optional[WorkflowConfig] = None,
    include_kubernetes: bool = True,
    include_monitoring: bool = True,
    include_slack: bool = False,
    custom_tools: Optional[List] = None
) -> Workflow:
    """
    Create a complete incident response workflow with specified components.
    
    Args:
        workflow_name: Name for the workflow
        config: Workflow configuration (uses defaults if None)
        include_kubernetes: Whether to include Kubernetes investigation
        include_monitoring: Whether to include monitoring analysis
        include_slack: Whether to include Slack notifications
        custom_tools: Custom tools to include in addition to standard ones
        
    Returns:
        Configured Workflow ready for execution
    """
    # Use provided config or create default
    if config is None:
        config = WorkflowConfig(
            workflow_name=workflow_name,
            workflow_version="1.0.0",
            timeout=3600,
            debug_mode=True
        )
    else:
        config.workflow_name = workflow_name
    
    # Create builder
    builder = IncidentResponseWorkflowBuilder(config)
    
    # Add tools based on requirements
    if include_kubernetes:
        builder.with_kubernetes_tools(
            enable_monitoring=True,
            enable_health_checks=True
        )
    
    if include_monitoring:
        builder.with_monitoring_tools(
            provider="mock",  # Use mock for demo, can be "datadog", "prometheus", etc.
            enable_alerting=False
        )
    
    if include_slack:
        builder.with_slack_tools(
            enable_threading=True,
            enable_formatting=True
        )
    
    # Add custom tools if provided
    if custom_tools:
        current_tools = builder.tools or []
        builder.with_tools(current_tools + custom_tools)
    
    # Build complete workflow
    return builder.build_complete()


def create_minimal_workflow(
    workflow_name: str = "minimal-incident-response",
    config: Optional[WorkflowConfig] = None
) -> Workflow:
    """
    Create a minimal incident response workflow for testing and quick deployment.
    
    Args:
        workflow_name: Name for the workflow
        config: Workflow configuration (uses defaults if None)
        
    Returns:
        Minimal Workflow for testing
    """
    if config is None:
        config = WorkflowConfig(
            workflow_name=workflow_name,
            timeout=1800,  # 30 minutes
            debug_mode=True,
            retry_limit=2
        )
    else:
        config.workflow_name = workflow_name
    
    builder = IncidentResponseWorkflowBuilder(config)
    return builder.build_minimal()


def create_kubernetes_focused_workflow(
    workflow_name: str = "k8s-incident-response",
    config: Optional[WorkflowConfig] = None,
    enable_monitoring: bool = True,
    enable_health_checks: bool = True
) -> Workflow:
    """
    Create a Kubernetes-focused incident response workflow.
    
    Args:
        workflow_name: Name for the workflow
        config: Workflow configuration
        enable_monitoring: Enable cluster monitoring features
        enable_health_checks: Enable comprehensive health checks
        
    Returns:
        Kubernetes-focused Workflow
    """
    if config is None:
        config = WorkflowConfig(
            workflow_name=workflow_name,
            timeout=2400,  # 40 minutes
            debug_mode=True
        )
    else:
        config.workflow_name = workflow_name
    
    builder = (IncidentResponseWorkflowBuilder(config)
               .with_kubernetes_tools(
                   enable_monitoring=enable_monitoring,
                   enable_health_checks=enable_health_checks
               ))
    
    return builder.build_kubernetes_focused()


def create_monitoring_focused_workflow(
    workflow_name: str = "monitoring-incident-response",
    config: Optional[WorkflowConfig] = None,
    provider: str = "mock",
    enable_alerting: bool = False
) -> Workflow:
    """
    Create a monitoring-focused incident response workflow.
    
    Args:
        workflow_name: Name for the workflow
        config: Workflow configuration
        provider: Monitoring provider ("mock", "datadog", "prometheus")
        enable_alerting: Enable alerting features
        
    Returns:
        Monitoring-focused Workflow
    """
    if config is None:
        config = WorkflowConfig(
            workflow_name=workflow_name,
            timeout=2400,  # 40 minutes
            debug_mode=True
        )
    else:
        config.workflow_name = workflow_name
    
    builder = (IncidentResponseWorkflowBuilder(config)
               .with_monitoring_tools(
                   provider=provider,
                   enable_alerting=enable_alerting
               ))
    
    return builder.build_monitoring_focused()


def create_production_workflow(
    workflow_name: str = "production-incident-response",
    severity_level: SeverityLevel = SeverityLevel.HIGH,
    timeout_minutes: int = 120,
    enable_all_integrations: bool = True
) -> Workflow:
    """
    Create a production-ready incident response workflow with all features.
    
    Args:
        workflow_name: Name for the workflow
        severity_level: Default severity level for production incidents
        timeout_minutes: Workflow timeout in minutes
        enable_all_integrations: Enable all available integrations
        
    Returns:
        Production-ready Workflow
    """
    config = WorkflowConfig(
        workflow_name=workflow_name,
        workflow_version="1.0.0-prod",
        timeout=timeout_minutes * 60,
        retry_limit=3,
        debug_mode=False,  # Disable debug in production
        log_level="info",
        llm_model="gpt-4o",  # Use more capable model for production
        llm_temperature=0.1
    )
    
    if enable_all_integrations:
        return create_incident_workflow(
            workflow_name=workflow_name,
            config=config,
            include_kubernetes=True,
            include_monitoring=True,
            include_slack=True
        )
    else:
        return create_incident_workflow(
            workflow_name=workflow_name,
            config=config,
            include_kubernetes=True,
            include_monitoring=True,
            include_slack=False
        )


def create_development_workflow(
    workflow_name: str = "dev-incident-response"
) -> Workflow:
    """
    Create a development/testing incident response workflow.
    
    Args:
        workflow_name: Name for the workflow
        
    Returns:
        Development-optimized Workflow
    """
    config = WorkflowConfig(
        workflow_name=workflow_name,
        workflow_version="1.0.0-dev",
        timeout=1800,  # 30 minutes
        retry_limit=1,  # Fail fast in development
        debug_mode=True,
        log_level="debug",
        llm_model="gpt-4o-mini",  # Faster model for development
        llm_temperature=0.2
    )
    
    return create_minimal_workflow(workflow_name, config)


class WorkflowFactory:
    """
    Comprehensive factory class for creating incident response workflows
    with various configurations and presets.
    """
    
    @staticmethod
    def create_for_severity(severity: SeverityLevel) -> Workflow:
        """Create workflow optimized for specific severity level."""
        if severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
            return create_production_workflow(
                workflow_name=f"{severity.value}-incident-response",
                severity_level=severity,
                timeout_minutes=180,  # 3 hours for critical/high
                enable_all_integrations=True
            )
        else:
            return create_incident_workflow(
                workflow_name=f"{severity.value}-incident-response",
                include_kubernetes=True,
                include_monitoring=True,
                include_slack=False
            )
    
    @staticmethod
    def create_for_platform(platform: str) -> Workflow:
        """Create workflow optimized for specific platform."""
        platform_lower = platform.lower()
        
        if "kubernetes" in platform_lower or "k8s" in platform_lower:
            return create_kubernetes_focused_workflow()
        elif "monitoring" in platform_lower or "datadog" in platform_lower:
            return create_monitoring_focused_workflow(provider="datadog")
        elif "prometheus" in platform_lower:
            return create_monitoring_focused_workflow(provider="prometheus")
        else:
            return create_incident_workflow()
    
    @staticmethod
    def create_for_environment(environment: str) -> Workflow:
        """Create workflow optimized for specific environment."""
        env_lower = environment.lower()
        
        if env_lower in ["production", "prod"]:
            return create_production_workflow()
        elif env_lower in ["development", "dev", "test"]:
            return create_development_workflow()
        elif env_lower in ["staging", "stage"]:
            config = WorkflowConfig(
                workflow_name="staging-incident-response",
                timeout=2400,  # 40 minutes
                debug_mode=True,
                retry_limit=2
            )
            return create_incident_workflow(config=config)
        else:
            return create_incident_workflow()
    
    @staticmethod
    def get_available_workflows() -> Dict[str, Dict[str, Any]]:
        """Get information about all available workflow types."""
        return {
            "complete": {
                "description": "Full incident response workflow with all features",
                "components": ["validation", "ai_analysis", "kubernetes", "monitoring", "aggregation", "reporting"],
                "use_case": "Production incidents requiring comprehensive investigation"
            },
            "minimal": {
                "description": "Basic incident response workflow for testing",
                "components": ["validation", "ai_analysis", "reporting"],
                "use_case": "Quick testing and development"
            },
            "kubernetes_focused": {
                "description": "Kubernetes cluster investigation workflow",
                "components": ["validation", "ai_analysis", "kubernetes", "reporting"],
                "use_case": "Container orchestration platform issues"
            },
            "monitoring_focused": {
                "description": "Performance and metrics analysis workflow",
                "components": ["validation", "ai_analysis", "monitoring", "reporting"],
                "use_case": "Performance degradation and metrics anomalies"
            },
            "production": {
                "description": "Production-ready workflow with all integrations",
                "components": ["validation", "ai_analysis", "kubernetes", "monitoring", "slack", "aggregation", "reporting"],
                "use_case": "Critical production incidents"
            },
            "development": {
                "description": "Development and testing optimized workflow",
                "components": ["validation", "ai_analysis", "reporting"],
                "use_case": "Development environment testing and validation"
            }
        }


# Convenience functions for common use cases
def quick_incident_workflow() -> Workflow:
    """Create a quick incident response workflow for immediate use."""
    return create_minimal_workflow("quick-incident-response")


def enterprise_incident_workflow() -> Workflow:
    """Create an enterprise-grade incident response workflow."""
    return create_production_workflow(
        "enterprise-incident-response",
        severity_level=SeverityLevel.CRITICAL,
        timeout_minutes=240,  # 4 hours
        enable_all_integrations=True
    )


def demo_incident_workflow() -> Workflow:
    """Create a demo incident response workflow for presentations."""
    config = WorkflowConfig(
        workflow_name="demo-incident-response",
        timeout=900,  # 15 minutes
        debug_mode=True,
        retry_limit=1,
        llm_model="gpt-4o-mini"
    )
    
    return create_incident_workflow(
        config=config,
        include_kubernetes=True,
        include_monitoring=True,
        include_slack=False
    )