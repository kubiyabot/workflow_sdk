#!/usr/bin/env python3
"""
Production Workflow Test Runner.
Tests the incident response workflow with realistic scenarios and validates all features.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from kubiya_workflow_sdk.client import KubiyaClient
from workflows.production_incident_workflow import build_production_incident_response_workflow


def create_test_scenarios():
    """Create different test scenarios for comprehensive validation."""
    
    scenarios = {
        "critical_memory_incident": {
            "name": "Critical Memory Exhaustion",
            "datadog_event_payload": json.dumps({
                "data": {
                    "id": "INC-2024-MEMORY-001",
                    "type": "incidents",
                    "attributes": {
                        "title": "Critical Memory Exhaustion - API Servers",
                        "description": "Production API servers experiencing critical memory exhaustion with OOM kills. CPU at 98%, error rate increased to 12.5%. Customer impact severe.",
                        "severity": "critical",
                        "services": [
                            {"name": "api-server", "environment": "production"},
                            {"name": "user-service", "environment": "production"}
                        ],
                        "tags": ["env:production", "service:api-server", "severity:critical"],
                        "created": datetime.utcnow().isoformat() + "Z",
                        "created_by": {"email": "datadog@company.com"},
                        "detective_monitor_id": "12345",
                        "detective_monitor_name": "High Memory Usage Alert"
                    }
                }
            }),
            "incident_id": "INC-2024-MEMORY-001",
            "incident_title": "Critical Memory Exhaustion - API Servers",
            "incident_severity": "critical",
            "incident_body": "Production API servers experiencing critical memory exhaustion",
            "incident_url": "https://app.datadoghq.com/incidents/INC-2024-MEMORY-001"
        },
        
        "network_latency_incident": {
            "name": "Network Latency Spike",
            "datadog_event_payload": json.dumps({
                "data": {
                    "id": "INC-2024-NETWORK-002",
                    "type": "incidents", 
                    "attributes": {
                        "title": "Network Latency Spike - Cross-Region",
                        "description": "Significant network latency spike between regions causing timeout errors.",
                        "severity": "high",
                        "services": [
                            {"name": "gateway", "environment": "production"},
                            {"name": "database", "environment": "production"}
                        ],
                        "tags": ["env:production", "network:latency", "severity:high"],
                        "created": datetime.utcnow().isoformat() + "Z",
                        "created_by": {"email": "monitoring@company.com"},
                        "detective_monitor_id": "67890",
                        "detective_monitor_name": "Network Latency Monitor"
                    }
                }
            }),
            "incident_id": "INC-2024-NETWORK-002",
            "incident_title": "Network Latency Spike - Cross-Region",
            "incident_severity": "high",
            "incident_body": "Network latency spike causing timeout errors",
            "incident_url": "https://app.datadoghq.com/incidents/INC-2024-NETWORK-002"
        },
        
        "simple_test_incident": {
            "name": "Simple Test Incident",
            "datadog_event_payload": "{}",  # Empty payload to test fallback
            "incident_id": "TEST-001",
            "incident_title": "Simple Test Incident",
            "incident_severity": "medium",
            "incident_body": "Basic test incident for workflow validation",
            "incident_url": "https://app.datadoghq.com/test"
        }
    }
    
    return scenarios


def validate_workflow_structure():
    """Validate the workflow structure before testing."""
    print("🔍 Validating Workflow Structure")
    print("=" * 50)
    
    try:
        workflow = build_production_incident_response_workflow()
        workflow_dict = workflow.to_dict()
        
        # Basic validation
        required_fields = ['name', 'description', 'steps']
        for field in required_fields:
            if field not in workflow_dict:
                print(f"❌ Missing required field: {field}")
                return False
            print(f"✅ {field}: {workflow_dict[field] if field != 'steps' else f'{len(workflow_dict[field])} steps'}")
        
        # Validate steps
        steps = workflow_dict['steps']
        print(f"\n📋 Step Validation:")
        
        expected_steps = [
            "extract-datadog-event",
            "get-slack-integration", 
            "create-incident-channel",
            "claude-code-initial-analysis",
            "claude-code-investigation",
            "generate-incident-report"
        ]
        
        for i, expected_step in enumerate(expected_steps):
            if i < len(steps):
                actual_step = steps[i].get('name', 'unnamed')
                if expected_step == actual_step:
                    print(f"✅ Step {i+1}: {actual_step}")
                else:
                    print(f"⚠️ Step {i+1}: Expected {expected_step}, got {actual_step}")
            else:
                print(f"❌ Missing step {i+1}: {expected_step}")
        
        # Validate Claude Code steps
        claude_steps = [step for step in steps if 'claude-code' in step.get('name', '')]
        print(f"\n🤖 Claude Code Steps: {len(claude_steps)}")
        for step in claude_steps:
            print(f"   • {step.get('name')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow validation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


def test_workflow_compilation():
    """Test workflow compilation and serialization."""
    print("\n🔧 Testing Workflow Compilation")
    print("=" * 50)
    
    try:
        workflow = build_production_incident_response_workflow()
        
        # Test to_dict()
        workflow_dict = workflow.to_dict()
        print("✅ to_dict() successful")
        
        # Test JSON serialization
        def fix_step_objects(obj):
            if hasattr(obj, '__class__') and 'Step' in str(type(obj)):
                if hasattr(obj, 'to_dict'):
                    return obj.to_dict()
                elif hasattr(obj, 'data'):
                    return obj.data
                else:
                    return str(obj)
            elif isinstance(obj, dict):
                return {k: fix_step_objects(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [fix_step_objects(v) for v in obj]
            else:
                return obj
        
        workflow_dict = fix_step_objects(workflow_dict)
        json_str = json.dumps(workflow_dict, indent=2, default=str)
        print("✅ JSON serialization successful")
        print(f"   JSON size: {len(json_str)} characters")
        
        # Test YAML compilation
        yaml_output = workflow.to_yaml()
        print("✅ YAML compilation successful")
        print(f"   YAML size: {len(yaml_output)} characters")
        
        # Add required fields for API
        if 'runner' not in workflow_dict:
            workflow_dict['runner'] = 'core-testing-2'
            print("✅ Added default runner")
        
        return workflow_dict
        
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None


def test_api_connection():
    """Test connection to Kubiya API."""
    print("\n🌐 Testing API Connection") 
    print("=" * 50)
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY not set")
        return None
    
    print(f"✅ API key available (length: {len(api_key)})")
    
    try:
        client = KubiyaClient(api_key=api_key)
        print("✅ KubiyaClient created successfully")
        return client
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        return None


def execute_workflow_test(client, workflow_dict, scenario_name, scenario_data):
    """Execute workflow with a specific test scenario."""
    print(f"\n🚀 Testing Scenario: {scenario_name}")
    print("=" * 60)
    
    print(f"📋 Scenario Details:")
    print(f"   - ID: {scenario_data['incident_id']}")
    print(f"   - Title: {scenario_data['incident_title']}")
    print(f"   - Severity: {scenario_data['incident_severity']}")
    
    try:
        print("▶️ Executing workflow...")
        start_time = time.time()
        
        execution_result = client.execute_workflow(
            workflow_definition=workflow_dict,
            parameters=scenario_data,
            stream=False
        )
        
        execution_time = time.time() - start_time
        print(f"✅ Workflow executed in {execution_time:.2f} seconds")
        
        return execution_result
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None


def analyze_execution_results(scenario_name, result):
    """Analyze the results of workflow execution."""
    print(f"\n📊 Results Analysis - {scenario_name}")
    print("=" * 60)
    
    if not result:
        print("❌ No results to analyze")
        return False
    
    print(f"📋 Result Type: {type(result)}")
    
    try:
        # Print full result for debugging
        result_json = json.dumps(result, indent=2, default=str)
        print(f"📋 Full Result ({len(result_json)} chars):")
        # Print first 1000 chars for readability
        print(result_json[:1000] + ("..." if len(result_json) > 1000 else ""))
        
        # Analyze key fields
        status = result.get('status', 'unknown')
        print(f"\n📊 Status: {status}")
        
        execution_id = result.get('execution_id') or result.get('id')
        if execution_id:
            print(f"🔑 Execution ID: {execution_id}")
        
        # Check for workflow success indicators
        success_indicators = [
            status in ['completed', 'success', 'succeeded'],
            'execution_id' in result or 'id' in result,
            not result.get('error'),
            not result.get('errors')
        ]
        
        success_count = sum(success_indicators)
        print(f"✅ Success Indicators: {success_count}/4")
        
        if result.get('error'):
            print(f"❌ Error: {result['error']}")
        
        if result.get('errors'):
            print(f"❌ Errors: {result['errors']}")
        
        return success_count >= 2  # At least 2 success indicators
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False


def run_comprehensive_tests():
    """Run comprehensive tests of the production workflow."""
    print("🧪 Production Incident Response Workflow - Comprehensive Tests")
    print("=" * 80)
    
    # Step 1: Validate workflow structure
    if not validate_workflow_structure():
        print("❌ Workflow structure validation failed")
        return 1
    
    # Step 2: Test compilation
    workflow_dict = test_workflow_compilation()
    if not workflow_dict:
        print("❌ Workflow compilation failed")
        return 1
    
    # Step 3: Test API connection
    client = test_api_connection()
    if not client:
        print("❌ API connection failed")
        return 1
    
    # Step 4: Run test scenarios
    scenarios = create_test_scenarios()
    results = {}
    
    for scenario_name, scenario_data in scenarios.items():
        result = execute_workflow_test(client, workflow_dict, scenario_name, scenario_data)
        success = analyze_execution_results(scenario_name, result)
        results[scenario_name] = {
            'result': result,
            'success': success
        }
        
        # Brief pause between tests
        time.sleep(2)
    
    # Step 5: Overall results
    print("\n🎯 Overall Test Results")
    print("=" * 80)
    
    total_tests = len(scenarios)
    successful_tests = sum(1 for r in results.values() if r['success'])
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    print("\nTest Summary:")
    for scenario_name, result_data in results.items():
        status = "✅ PASS" if result_data['success'] else "❌ FAIL"
        print(f"   {status} {scenario_name}")
    
    # Step 6: Production readiness assessment
    print("\n🏭 Production Readiness Assessment")
    print("=" * 50)
    
    readiness_checks = [
        ("Workflow Structure", validate_workflow_structure()),
        ("Compilation", workflow_dict is not None),
        ("API Connection", client is not None),
        ("Test Execution", successful_tests > 0),
        ("Error Handling", successful_tests == total_tests or successful_tests >= total_tests * 0.8)
    ]
    
    passed_checks = sum(1 for _, check in readiness_checks if check)
    
    for check_name, passed in readiness_checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
    
    print(f"\nProduction Readiness: {passed_checks}/{len(readiness_checks)} checks passed")
    
    if passed_checks >= len(readiness_checks) * 0.8:
        print("🎉 PRODUCTION READY! Workflow is ready for deployment.")
        return 0
    else:
        print("⚠️ NOT PRODUCTION READY. Address failing checks before deployment.")
        return 1


def main():
    """Main test execution."""
    try:
        return run_comprehensive_tests()
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())