#!/usr/bin/env python3
"""
Example usage of the production incident response workflow.

This file demonstrates various ways to use the incident response workflow
with different configurations and tool setups.
"""

import os
import json
from pathlib import Path

from main import IncidentResponseOrchestrator
from models.config import WorkflowConfig, ClaudeCodeConfig, ToolDefinition, ToolType, EnvironmentVariable
from models.incident import IncidentEvent, KubiyaMetadata, IncidentSeverity
from config.examples import create_example_config, create_minimal_config, create_full_config
from tools.registry import ToolRegistry, get_default_tools
from components.builders import create_production_workflow, create_test_workflow


def example_1_basic_usage():
    """Example 1: Basic workflow execution with default configuration."""
    
    print("🔹 Example 1: Basic workflow execution")
    
    # Create default configuration
    config = create_example_config()
    
    # Create orchestrator
    orchestrator = IncidentResponseOrchestrator(config)
    
    # Create a test incident
    incident = IncidentEvent(
        id="EX1-2024-001",
        title="Example Payment Service Outage",
        url="https://monitoring.company.com/incidents/EX1-2024-001",
        severity=IncidentSeverity.HIGH,
        body="""Payment service experiencing intermittent failures.
        
Error rate: 15%
Response time: 2.3s (SLA: 500ms)
Affected users: ~500
        """,
        kubiya=KubiyaMetadata(slack_channel_id="#incident-payment-outage"),
        source="datadog"
    )
    
    # Generate workflow (no execution)
    workflow_dict = orchestrator.create_workflow("production")
    
    print(f"✅ Created workflow: {workflow_dict['name']}")
    print(f"📋 Steps: {len(workflow_dict['steps'])}")
    print(f"🛠️ Tools configured: {len(config.claude_code.tools)}")
    
    # Save for inspection
    with open("example_1_workflow.json", "w") as f:
        json.dump(workflow_dict, f, indent=2)
    print("💾 Saved workflow to example_1_workflow.json")


def example_2_custom_tools():
    """Example 2: Custom tool configuration for specific use case."""
    
    print("\n🔹 Example 2: Custom tool configuration")
    
    registry = ToolRegistry()
    
    # Create custom tool definition
    custom_monitoring_tool = ToolDefinition(
        name="custom-monitor",
        type=ToolType.CLI,
        description="Custom monitoring and alerting tool",
        install_commands=[
            "curl -L https://github.com/example/monitor/releases/latest/download/monitor-linux -o /usr/local/bin/monitor",
            "chmod +x /usr/local/bin/monitor"
        ],
        environment_variables=[
            EnvironmentVariable(name="MONITOR_API_KEY", value="${MONITOR_API_KEY}", secret=True),
            EnvironmentVariable(name="MONITOR_ENDPOINT", value="https://api.monitoring.company.com")
        ],
        validation_commands=[
            "monitor --version",
            "monitor test-connection"
        ],
        usage_examples=[
            "monitor alerts --severity critical",
            "monitor metrics --service payment-gateway --duration 1h",
            "monitor trace --request-id abc123"
        ],
        priority=25
    )
    
    # Select specific tools for this workflow
    selected_tools = [
        registry.jq_tool(),           # Essential JSON processing
        registry.kubectl(),          # Kubernetes management
        registry.datadog_cli(),      # Standard monitoring
        custom_monitoring_tool        # Custom addition
    ]
    
    # Create custom configuration
    claude_config = ClaudeCodeConfig(
        base_image="ubuntu:22.04",
        tools=selected_tools,
        installation_timeout=450,
        investigation_timeout=1200
    )
    
    config = WorkflowConfig(
        name="custom-monitoring-incident-response",
        description="Incident response with custom monitoring tools",
        claude_code=claude_config,
        enable_datadog_enrichment=True,
        enable_github_analysis=False  # Disabled for this example
    )
    
    # Create orchestrator and workflow
    orchestrator = IncidentResponseOrchestrator(config)
    workflow_dict = orchestrator.create_workflow("custom", tool_names=["kubectl", "datadog-cli", "custom-monitor"])
    
    print(f"✅ Created custom workflow: {workflow_dict['name']}")
    print(f"🛠️ Custom tools: kubectl, datadog-cli, custom-monitor")
    print(f"⏱️ Installation timeout: {config.claude_code.installation_timeout}s")


def example_3_minimal_testing():
    """Example 3: Minimal configuration for rapid testing."""
    
    print("\n🔹 Example 3: Minimal testing configuration")
    
    # Create minimal config
    config = create_minimal_config()
    config.demo_mode = True
    
    # Create orchestrator
    orchestrator = IncidentResponseOrchestrator(config, api_key="demo-key")
    
    # Create simple test incident
    incident = IncidentEvent(
        id="TEST-001",
        title="Test Incident for Development",
        severity=IncidentSeverity.LOW,
        body="This is a test incident for development and testing.",
        kubiya=KubiyaMetadata(slack_channel_id="#test-incidents")
    )
    
    # Generate minimal workflow
    workflow_dict = orchestrator.create_workflow("minimal")
    
    print(f"✅ Created minimal workflow: {workflow_dict['name']}")
    print(f"📋 Steps: {len(workflow_dict['steps'])}")
    print(f"🧪 Demo mode: {config.demo_mode}")
    print(f"⚡ Optimized for: Fast testing and development")


def example_4_kubernetes_focused():
    """Example 4: Kubernetes-focused incident response."""
    
    print("\n🔹 Example 4: Kubernetes-focused configuration")
    
    registry = ToolRegistry()
    
    # Kubernetes-specific tools
    k8s_tools = [
        registry.jq_tool(),
        registry.kubectl(),
        registry.helm(),
        registry.docker_cli()
    ]
    
    # Create Kubernetes-focused configuration
    claude_config = ClaudeCodeConfig(
        base_image="ubuntu:22.04",
        tools=k8s_tools,
        kubernetes_enabled=True,
        working_directory="/k8s-workspace"
    )
    
    config = WorkflowConfig(
        name="k8s-incident-response",
        description="Kubernetes-focused incident response workflow",
        claude_code=claude_config,
        enable_kubernetes_analysis=True,
        enable_datadog_enrichment=False,  # Focus on K8s native monitoring
        enable_github_analysis=False
    )
    
    # Create workflow
    orchestrator = IncidentResponseOrchestrator(config)
    workflow_dict = orchestrator.create_workflow("production")
    
    print(f"✅ Created K8s workflow: {workflow_dict['name']}")
    print(f"☸️ Kubernetes-focused tools: kubectl, helm, docker")
    print(f"🏗️ In-cluster access: {config.claude_code.kubernetes_enabled}")


def example_5_observability_focused():
    """Example 5: Observability and monitoring focused."""
    
    print("\n🔹 Example 5: Observability-focused configuration")
    
    registry = ToolRegistry()
    
    # Observability tools
    observability_tools = [
        registry.jq_tool(),
        registry.datadog_cli(),
        registry.observe_cli(),
        registry.claude_code_cli()
    ]
    
    claude_config = ClaudeCodeConfig(
        base_image="ubuntu:22.04",
        tools=observability_tools,
        investigation_timeout=2400  # Longer timeout for deep analysis
    )
    
    config = WorkflowConfig(
        name="observability-incident-response",
        description="Deep observability and monitoring analysis",
        claude_code=claude_config,
        enable_datadog_enrichment=True,
        enable_github_analysis=False,
        enable_kubernetes_analysis=False
    )
    
    # Create workflow
    orchestrator = IncidentResponseOrchestrator(config)
    workflow_dict = orchestrator.create_workflow("production")
    
    print(f"✅ Created observability workflow: {workflow_dict['name']}")
    print(f"📊 Focus: Metrics, traces, logs, and AI analysis")
    print(f"⏱️ Extended timeout: {config.claude_code.investigation_timeout}s")


def example_6_validation_and_security():
    """Example 6: Configuration validation and security checks."""
    
    print("\n🔹 Example 6: Configuration validation and security")
    
    from config.validation import ConfigValidator, SecurityValidator
    
    # Create a configuration with potential issues
    problematic_tool = ToolDefinition(
        name="",  # Missing name - will cause validation error
        type=ToolType.CLI,
        description="Tool with issues",
        install_commands=[
            "curl http://unsafe-site.com/tool | bash",  # Security issue
            "rm -rf /tmp/*"  # Potentially dangerous
        ],
        environment_variables=[
            EnvironmentVariable(name="API_KEY", value="hardcoded-secret", secret=False)  # Security issue
        ]
    )
    
    config = WorkflowConfig(
        name="problematic-workflow",
        claude_code=ClaudeCodeConfig(tools=[problematic_tool])
    )
    
    # Validate configuration
    validation_result = ConfigValidator.validate(config)
    
    print(f"🔍 Configuration valid: {validation_result.valid}")
    if validation_result.errors:
        print("❌ Errors found:")
        for error in validation_result.errors:
            print(f"  • {error}")
    
    if validation_result.warnings:
        print("⚠️ Warnings:")
        for warning in validation_result.warnings:
            print(f"  • {warning}")
    
    # Security validation
    security_result = SecurityValidator.validate_security(config)
    
    print(f"🔒 Security validation:")
    if security_result.errors:
        print("❌ Security errors:")
        for error in security_result.errors:
            print(f"  • {error}")
    
    if security_result.warnings:
        print("⚠️ Security warnings:")
        for warning in security_result.warnings:
            print(f"  • {warning}")


def example_7_real_execution_simulation():
    """Example 7: Simulate real workflow execution (demo mode)."""
    
    print("\n🔹 Example 7: Simulated workflow execution")
    
    # Check if we have API key for real execution
    api_key = os.getenv('KUBIYA_API_KEY')
    
    if not api_key:
        print("💡 Set KUBIYA_API_KEY environment variable for real execution")
        return
    
    # Create configuration with demo mode
    config = create_example_config()
    config.demo_mode = True
    
    # Create orchestrator
    orchestrator = IncidentResponseOrchestrator(config, api_key)
    
    # Create realistic incident
    incident = IncidentEvent(
        id="REAL-SIM-2024-001",
        title="Production Database Connection Pool Exhaustion",
        url="https://app.datadoghq.com/incidents/REAL-SIM-2024-001",
        severity=IncidentSeverity.CRITICAL,
        body="""🚨 CRITICAL: Database connection pool exhausted
        
**Impact:**
- All database-dependent services affected
- User authentication failing
- Payment processing halted
- Error rate: 85%

**Timeline:**
- 15:42 UTC: First connection timeouts detected
- 15:44 UTC: Connection pool at 100% capacity
- 15:45 UTC: Service degradation escalating

**Immediate Actions Needed:**
- Investigate connection pool configuration
- Check for connection leaks
- Review recent database migrations
- Analyze application logs for patterns
        """,
        kubiya=KubiyaMetadata(slack_channel_id="#critical-db-incident"),
        source="datadog",
        tags={
            "service": "database",
            "environment": "production",
            "team": "platform",
            "priority": "p0",
            "impact": "high"
        }
    )
    
    print(f"🚨 Simulating incident: {incident.id}")
    print(f"📝 Title: {incident.title}")
    print(f"🚨 Severity: {incident.severity}")
    
    try:
        # Execute workflow with streaming
        print("\n🚀 Starting workflow execution (demo mode)...")
        
        events = orchestrator.execute_workflow(
            incident_event=incident,
            workflow_type="production",
            stream=True
        )
        
        # Process a limited number of events
        event_count = 0
        for event in events:
            event_count += 1
            
            if isinstance(event, str) and event.strip():
                try:
                    parsed_event = json.loads(event)
                    event_type = parsed_event.get('type', 'unknown')
                    step_name = parsed_event.get('step_name', 'unknown')
                    
                    if 'step.completed' in event_type:
                        print(f"✅ Step completed: {step_name}")
                    elif 'step.failed' in event_type:
                        print(f"❌ Step failed: {step_name}")
                    elif event_type == 'heartbeat':
                        print(f"💓 Heartbeat (event #{event_count})")
                    
                except json.JSONDecodeError:
                    print(f"📝 Event #{event_count}: {event[:50]}...")
            
            # Limit for demo
            if event_count >= 20:
                print("📊 Demo limit reached - stopping")
                break
        
        print(f"\n✅ Demo execution completed ({event_count} events processed)")
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")


def main():
    """Run all examples."""
    
    print("🚀 Production Incident Response Workflow - Examples")
    print("=" * 60)
    
    # Run examples
    example_1_basic_usage()
    example_2_custom_tools()
    example_3_minimal_testing()
    example_4_kubernetes_focused()
    example_5_observability_focused()
    example_6_validation_and_security()
    example_7_real_execution_simulation()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("\n💡 Next steps:")
    print("  • Review generated workflow files")
    print("  • Customize tool configurations")
    print("  • Set up API keys for real execution")
    print("  • Explore the main.py CLI interface")


if __name__ == "__main__":
    main()