#!/usr/bin/env python3
"""
Demo script for the Claude Code Incident Response Workflow.
Shows how to build, compile, and execute the workflow with different scenarios.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.incident_response_workflow import build_incident_response_workflow


def demo_datadog_cpu_spike():
    """Demo scenario: Datadog CPU spike incident."""
    print("🚨 Demo Scenario: Datadog CPU Spike")
    print("-" * 40)
    
    workflow = build_incident_response_workflow()
    
    # Set parameters for CPU spike scenario
    workflow.set_params({
        "incident_id": "INC-2024-CPU-001",
        "incident_title": "Critical CPU spike detected across production cluster",
        "incident_severity": "critical",
        "incident_body": "Datadog monitoring detected CPU usage above 95% across multiple production nodes. API response times have increased by 400%. This appears to be related to a memory leak in the user-service deployment that started after the 2:30 PM release.",
        "incident_url": "https://datadog.example.com/alerts/cpu-spike-prod",
        "checkpoint_dir": "/tmp/incident-cpu-001"
    })
    
    compiled = workflow.compile()
    
    print(f"📋 Workflow: {compiled['name']}")
    print(f"🎯 Scenario: CPU performance degradation")
    print(f"🔧 Steps: {len(compiled['workflow']['steps'])}")
    print(f"🤖 Claude Code Steps: {count_claude_code_steps(compiled)}")
    
    return compiled


def demo_kubernetes_deployment_failure():
    """Demo scenario: Kubernetes deployment failure."""
    print("🚨 Demo Scenario: Kubernetes Deployment Failure")
    print("-" * 40)
    
    workflow = build_incident_response_workflow()
    
    # Set parameters for deployment failure scenario
    workflow.set_params({
        "incident_id": "INC-2024-K8S-002", 
        "incident_title": "Payment service deployment failing with ImagePullBackOff",
        "incident_severity": "high",
        "incident_body": "The payment-service deployment is stuck in ImagePullBackOff state after attempting to deploy v2.1.3. Pods are failing to start and customers cannot complete transactions. The issue started 15 minutes ago during our regular deployment window.",
        "incident_url": "https://argocd.example.com/applications/payment-service",
        "checkpoint_dir": "/tmp/incident-k8s-002"
    })
    
    compiled = workflow.compile()
    
    print(f"📋 Workflow: {compiled['name']}")
    print(f"🎯 Scenario: Kubernetes deployment issue")
    print(f"🔧 Steps: {len(compiled['workflow']['steps'])}")
    print(f"🤖 Claude Code Steps: {count_claude_code_steps(compiled)}")
    
    return compiled


def demo_network_connectivity_issue():
    """Demo scenario: Network connectivity issue."""
    print("🚨 Demo Scenario: Network Connectivity Issue")
    print("-" * 40)
    
    workflow = build_incident_response_workflow()
    
    # Set parameters for network issue scenario
    workflow.set_params({
        "incident_id": "INC-2024-NET-003",
        "incident_title": "Intermittent connection timeouts to external payment gateway",
        "incident_severity": "medium",
        "incident_body": "Users are experiencing intermittent timeouts when processing payments through the Stripe gateway. Error rate has increased to 15% over the last hour. Network monitoring shows packet loss on the egress path to external services.",
        "incident_url": "https://observe.example.com/network/egress-monitoring",
        "checkpoint_dir": "/tmp/incident-net-003"
    })
    
    compiled = workflow.compile()
    
    print(f"📋 Workflow: {compiled['name']}")
    print(f"🎯 Scenario: Network connectivity degradation")
    print(f"🔧 Steps: {len(compiled['workflow']['steps'])}")
    print(f"🤖 Claude Code Steps: {count_claude_code_steps(compiled)}")
    
    return compiled


def count_claude_code_steps(compiled_workflow):
    """Count the number of Claude Code (inline_agent) steps."""
    count = 0
    for step in compiled_workflow["workflow"]["steps"]:
        if step.get("executor", {}).get("type") == "inline_agent":
            count += 1
    return count


def analyze_workflow_features(compiled_workflow):
    """Analyze and display workflow features."""
    print("\n🔍 Workflow Analysis:")
    print("-" * 30)
    
    steps = compiled_workflow["workflow"]["steps"]
    
    # Count step types
    step_types = {}
    claude_code_tools = set()
    
    for step in steps:
        executor_type = step.get("executor", {}).get("type", "unknown")
        step_types[executor_type] = step_types.get(executor_type, 0) + 1
        
        # Collect Claude Code tools
        if executor_type == "inline_agent":
            agent_tools = step.get("executor", {}).get("config", {}).get("agent", {}).get("tools", [])
            for tool in agent_tools:
                claude_code_tools.add(tool.get("name", "unnamed"))
    
    print(f"📊 Step Types:")
    for step_type, count in step_types.items():
        print(f"   {step_type}: {count}")
    
    print(f"\n🛠️  Claude Code Tools ({len(claude_code_tools)}):")
    for tool in sorted(claude_code_tools):
        print(f"   - {tool}")
    
    # Check for key features
    features = []
    
    if any("slack" in step["name"] for step in steps):
        features.append("✅ Slack Integration")
    
    if any("kubernetes" in step["name"] for step in steps):
        features.append("✅ Kubernetes Investigation")
        
    if any("datadog" in step["name"] for step in steps):
        features.append("✅ Datadog Monitoring")
    
    if any("checkpoint" in step.get("description", "").lower() for step in steps):
        features.append("✅ Checkpoint System")
    
    if step_types.get("inline_agent", 0) > 0:
        features.append("✅ Claude Code AI Agents")
    
    print(f"\n🎯 Key Features:")
    for feature in features:
        print(f"   {feature}")


def save_demo_scenarios():
    """Save all demo scenarios to JSON files."""
    print("\n💾 Saving Demo Scenarios...")
    
    scenarios = [
        ("cpu_spike", demo_datadog_cpu_spike),
        ("deployment_failure", demo_kubernetes_deployment_failure),
        ("network_issue", demo_network_connectivity_issue)
    ]
    
    examples_dir = Path(__file__).parent
    examples_dir.mkdir(exist_ok=True)
    
    for scenario_name, scenario_func in scenarios:
        compiled = scenario_func()
        
        # Save compiled workflow
        output_file = examples_dir / f"scenario_{scenario_name}.json"
        with open(output_file, "w") as f:
            json.dump(compiled, f, indent=2)
        
        print(f"   📄 {scenario_name}: {output_file}")
    
    print("✅ All scenarios saved!")


def main():
    """Main demo function."""
    print("🚀 Claude Code Incident Response Workflow Demo")
    print("=" * 60)
    print(f"⏰ Generated: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)
    
    # Run demo scenarios
    scenarios = [
        demo_datadog_cpu_spike,
        demo_kubernetes_deployment_failure, 
        demo_network_connectivity_issue
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] ", end="")
        compiled = scenario()
        analyze_workflow_features(compiled)
        print()
    
    # Save scenarios
    save_demo_scenarios()
    
    print("🎉 Demo completed! Key highlights:")
    print("   🤖 Claude Code acts as AI agent in investigation steps")
    print("   🔧 Each step uses Docker tools with CLI interfaces")
    print("   📊 Kubernetes, Datadog, and Slack integrations")
    print("   ⚡ Automatic incident analysis and response planning") 
    print("   💾 Checkpoint system for workflow resilience")
    print("   📋 End-to-end incident reporting")
    
    print(f"\n📂 Files generated in: {Path(__file__).parent}")
    print("   - scenario_*.json: Compiled workflows for each scenario")
    print("   - Use these files to deploy workflows to Kubiya")


if __name__ == "__main__":
    main()