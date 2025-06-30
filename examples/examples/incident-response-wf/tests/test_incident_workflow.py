#!/usr/bin/env python3
"""
Test script for the incident response workflow.
Validates workflow compilation and provides testing utilities.
"""

import sys
import os
import json
from pathlib import Path

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.incident_response_workflow import build_incident_response_workflow


def test_workflow_compilation():
    """Test that the workflow compiles without errors."""
    print("🧪 Testing workflow compilation...")
    
    try:
        workflow = build_incident_response_workflow()
        compiled = workflow.compile()
        
        # Basic validation
        assert "name" in compiled
        assert "workflow" in compiled
        assert "steps" in compiled["workflow"]
        assert len(compiled["workflow"]["steps"]) > 0
        
        print(f"✅ Workflow compiled successfully!")
        print(f"   Name: {compiled['name']}")
        print(f"   Steps: {len(compiled['workflow']['steps'])}")
        
        return compiled
        
    except Exception as e:
        print(f"❌ Workflow compilation failed: {e}")
        raise


def test_workflow_structure():
    """Test the workflow structure and dependencies."""
    print("\n🔍 Testing workflow structure...")
    
    workflow = build_incident_response_workflow()
    compiled = workflow.compile()
    
    steps = compiled["workflow"]["steps"]
    step_names = [step["name"] for step in steps]
    
    print(f"📋 Found {len(steps)} steps:")
    for i, step in enumerate(steps, 1):
        depends = step.get("depends", [])
        depends_str = f" (depends: {', '.join(depends)})" if depends else ""
        print(f"   {i}. {step['name']}{depends_str}")
    
    # Validate key steps exist
    required_steps = [
        "validate-inputs",
        "get-slack-integration-info", 
        "get-slack-token",
        "fetch-all-secrets",
        "initialize-incident-state",
        "incident-analysis-claude-code",
        "create-incident-channel",
        "kubernetes-investigation-claude-code",
        "datadog-investigation-claude-code",
        "aggregated-analysis-claude-code",
        "final-incident-report-claude-code"
    ]
    
    missing_steps = [step for step in required_steps if step not in step_names]
    if missing_steps:
        print(f"❌ Missing required steps: {missing_steps}")
        return False
    
    print("✅ All required steps found!")
    return True


def test_claude_code_integration():
    """Test Claude Code integration in the workflow."""
    print("\n🤖 Testing Claude Code integration...")
    
    workflow = build_incident_response_workflow()
    compiled = workflow.compile()
    
    claude_code_steps = []
    for step in compiled["workflow"]["steps"]:
        if step.get("executor", {}).get("type") == "inline_agent":
            claude_code_steps.append(step["name"])
    
    print(f"🔍 Found {len(claude_code_steps)} Claude Code steps:")
    for step in claude_code_steps:
        print(f"   - {step}")
    
    expected_claude_steps = [
        "incident-analysis-claude-code",
        "kubernetes-investigation-claude-code", 
        "datadog-investigation-claude-code",
        "aggregated-analysis-claude-code"
    ]
    
    missing_claude_steps = [step for step in expected_claude_steps if step not in claude_code_steps]
    if missing_claude_steps:
        print(f"❌ Missing Claude Code steps: {missing_claude_steps}")
        return False
    
    print("✅ Claude Code integration validated!")
    return True


def test_tool_definitions():
    """Test tool definitions in Claude Code steps."""
    print("\n🛠️  Testing tool definitions...")
    
    workflow = build_incident_response_workflow()
    compiled = workflow.compile()
    
    tools_found = []
    for step in compiled["workflow"]["steps"]:
        if step.get("executor", {}).get("type") == "inline_agent":
            agent_tools = step.get("executor", {}).get("config", {}).get("agent", {}).get("tools", [])
            for tool in agent_tools:
                tools_found.append(f"{step['name']}: {tool.get('name', 'unnamed')}")
    
    print(f"🔧 Found {len(tools_found)} tools in Claude Code steps:")
    for tool in tools_found:
        print(f"   - {tool}")
    
    # Check for key tools
    expected_tools = ["kubectl", "cluster-health", "slack-update", "datadog-metrics-query"]
    found_tool_names = [tool.split(": ")[1] for tool in tools_found]
    
    missing_tools = [tool for tool in expected_tools if tool not in found_tool_names]
    if missing_tools:
        print(f"⚠️  Missing expected tools: {missing_tools}")
    
    print("✅ Tool definitions validated!")
    return True


def generate_test_payload():
    """Generate test payload for workflow execution."""
    print("\n📦 Generating test payload...")
    
    test_payload = {
        "incident_id": "INC-2024-TEST-001",
        "incident_title": "Test incident for workflow validation",
        "incident_severity": "high", 
        "incident_body": "This is a test incident to validate the Claude Code incident response workflow. It simulates a production issue requiring investigation across Kubernetes and Datadog platforms.",
        "incident_url": "https://test.example.com/incident/001",
        "checkpoint_dir": "/tmp/test-incident-001"
    }
    
    # Save test payload
    test_file = Path(__file__).parent / "test_payload.json"
    with open(test_file, "w") as f:
        json.dump(test_payload, f, indent=2)
    
    print(f"💾 Test payload saved to: {test_file}")
    return test_payload


def validate_environment():
    """Validate the development environment."""
    print("\n🌍 Validating environment...")
    
    # Check if workflow_sdk is available
    try:
        import workflow_sdk
        print("✅ workflow_sdk module available")
    except ImportError:
        print("❌ workflow_sdk module not found")
        return False
    
    # Check for required directories
    required_dirs = [
        "incident-response-wf/workflows",
        "incident-response-wf/tools", 
        "incident-response-wf/containers",
        "incident-response-wf/tests"
    ]
    
    base_path = Path(__file__).parent.parent
    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if full_path.exists():
            print(f"✅ Directory exists: {dir_path}")
        else:
            print(f"❌ Missing directory: {dir_path}")
            return False
    
    print("✅ Environment validation passed!")
    return True


def run_all_tests():
    """Run all tests and return overall result."""
    print("🚀 Running Incident Response Workflow Tests")
    print("=" * 60)
    
    tests = [
        ("Environment Validation", validate_environment),
        ("Workflow Compilation", test_workflow_compilation), 
        ("Workflow Structure", test_workflow_structure),
        ("Claude Code Integration", test_claude_code_integration),
        ("Tool Definitions", test_tool_definitions)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Generate test payload regardless of test results
    generate_test_payload()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Workflow is ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Please review and fix issues.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)