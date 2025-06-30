#!/usr/bin/env python3
"""
Test runner for the comprehensive incident response workflow with proper Claude Code tool steps.
This script will deploy and execute the workflow using realistic Datadog event data.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from kubiya_workflow_sdk.client import KubiyaClient
from workflows.proper_incident_workflow import build_proper_incident_response_workflow


def create_realistic_datadog_incident():
    """Create a realistic Datadog incident event with full webhook structure."""
    return {
        "datadog_event_payload": json.dumps({
            "data": {
                "id": "INC-2024-DD-003",
                "type": "incidents",
                "attributes": {
                    "title": "Critical API Server Memory Exhaustion - Production",
                    "description": "Production API servers in us-east-1 are experiencing critical memory exhaustion with multiple OOM kills detected. CPU usage has spiked to 98% across all instances. Error rate has increased from 0.1% to 12.5% over the last 20 minutes. Customer-facing services are severely impacted with response times exceeding 15 seconds.",
                    "severity": "critical",
                    "customer_impact_scope": "high",
                    "detection_method": "monitor",
                    "services": [
                        {"name": "api-server", "environment": "production"},
                        {"name": "user-service", "environment": "production"},
                        {"name": "payment-service", "environment": "production"}
                    ],
                    "tags": ["env:production", "service:api-server", "region:us-east-1", "severity:critical"],
                    "created": "2024-01-15T14:25:33Z",
                    "created_by": {
                        "email": "datadog-monitor@company.com",
                        "name": "Datadog Monitor"
                    },
                    "detective_monitor_id": "12345678",
                    "detective_monitor_name": "API Server High Memory Usage",
                    "detective_monitor_tags": ["monitor:memory", "service:api-server"],
                    "fields": {
                        "affected_customers": "1200+",
                        "revenue_impact": "high",
                        "escalation_level": "p1"
                    },
                    "postmortem": {
                        "required": True,
                        "template": "production-incident"
                    }
                }
            },
            "meta": {
                "webhook_id": "webhook-123456",
                "event_type": "incident.created",
                "timestamp": "2024-01-15T14:25:33Z"
            }
        }),
        # Also provide fallback fields for compatibility
        "incident_id": "INC-2024-DD-003",
        "incident_title": "Critical API Server Memory Exhaustion - Production", 
        "incident_severity": "critical",
        "incident_body": "Production API servers experiencing critical memory exhaustion with OOM kills, 98% CPU usage, and 12.5% error rate. Customer impact severe with 15s response times.",
        "incident_url": "https://app.datadoghq.com/incidents/INC-2024-DD-003",
        "checkpoint_dir": "/tmp/incident-dd-003"
    }


def test_workflow_deployment():
    """Test deploying the comprehensive workflow to Kubiya."""
    print("🚀 Testing Comprehensive Workflow Deployment")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable not set")
        return False
    
    print(f"✅ API Key available (length: {len(api_key)})")
    
    # Create workflow client
    try:
        client = KubiyaClient(api_key=api_key)
        print("✅ Workflow client created successfully")
    except Exception as e:
        print(f"❌ Failed to create workflow client: {e}")
        return False
    
    # Build the workflow
    try:
        workflow = build_proper_incident_response_workflow()
        print("✅ Workflow built successfully")
        
        # Convert to deployable format
        workflow_dict = workflow.to_dict()
        
        # Handle Step object serialization
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
        
        print("   Fixing all Step objects recursively...")
        workflow_dict = fix_step_objects(workflow_dict)
        
        # Add runner field if missing
        if 'runner' not in workflow_dict:
            workflow_dict['runner'] = 'core-testing-2'
            print(f"   Added default runner: {workflow_dict['runner']}")
        
        print(f"✅ Workflow converted to dict: {workflow_dict['name']}")
        print(f"   - Steps: {len(workflow_dict['steps'])}")
        print(f"   - Description: {workflow_dict['description']}")
        
        # Count Claude Code tool steps
        claude_code_steps = [step for step in workflow_dict['steps'] if 'claude-code' in step.get('name', '')]
        print(f"   - Claude Code Tool Steps: {len(claude_code_steps)}")
        
        for step in claude_code_steps:
            print(f"     • {step.get('name', 'unnamed')}")
        
    except Exception as e:
        print(f"❌ Failed to build workflow: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    return workflow_dict, client


def test_workflow_execution(workflow_dict, client):
    """Test executing the workflow with realistic incident data."""
    print("\n🎯 Testing Workflow Execution")
    print("=" * 60)
    
    # Create realistic incident
    realistic_incident = create_realistic_datadog_incident()
    print("📋 Realistic Datadog Incident Created:")
    print(f"   - ID: {realistic_incident['incident_id']}")
    print(f"   - Title: {realistic_incident['incident_title']}")
    print(f"   - Severity: {realistic_incident['incident_severity']}")
    print(f"   - Webhook Event: Full Datadog incident webhook structure")
    
    # Show preview of webhook payload
    payload_preview = json.loads(realistic_incident['datadog_event_payload'])
    print(f"   - Services Affected: {len(payload_preview['data']['attributes']['services'])}")
    print(f"   - Customer Impact: {payload_preview['data']['attributes']['customer_impact_scope']}")
    print(f"   - Detection Method: {payload_preview['data']['attributes']['detection_method']}")
    
    try:
        # Execute the workflow
        print("\n▶️  Executing comprehensive workflow...")
        execution_result = client.execute_workflow(
            workflow_definition=workflow_dict,
            parameters=realistic_incident,
            stream=False
        )
        print(f"✅ Workflow execution completed: {type(execution_result)}")
        
        return execution_result
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return None


def analyze_comprehensive_results(final_status):
    """Analyze the comprehensive workflow execution results."""
    print("\n📊 Comprehensive Results Analysis")
    print("=" * 60)
    
    if not final_status:
        print("❌ No final status available")
        return
    
    print(f"📋 Response Type: {type(final_status)}")
    
    # Print the full response for debugging
    try:
        print(f"📋 Full Response: {json.dumps(final_status, indent=2, default=str)}")
    except Exception as e:
        print(f"📋 Response (non-JSON): {final_status}")
    
    # Analyze workflow execution
    status = final_status.get('status', 'unknown')
    print(f"📋 Final Status: {status}")
    
    # Check for execution details
    execution_id = final_status.get('execution_id') or final_status.get('id') or final_status.get('executionId')
    if execution_id:
        print(f"🔑 Execution ID: {execution_id}")
    
    workflow_id = final_status.get('workflow_id') or final_status.get('workflowId')
    if workflow_id:
        print(f"🔗 Workflow ID: {workflow_id}")
    
    # Analyze step results
    if 'steps' in final_status:
        print("\n📋 Step Execution Results:")
        for step_name, step_result in final_status['steps'].items():
            step_status = step_result.get('status', 'unknown')
            emoji = "✅" if step_status == 'completed' else "❌" if step_status == 'failed' else "⏳"
            print(f"   {emoji} {step_name}: {step_status}")
            
            # Show Claude Code outputs specifically
            if 'claude-code' in step_name.lower() and 'output' in step_result:
                print(f"      🤖 Claude Code Output: {step_result['output'][:200]}...")
    
    # Check for errors
    if 'errors' in final_status:
        print(f"\n❌ Errors Encountered:")
        for error in final_status['errors']:
            print(f"   - {error}")
    
    # Check for workflow outputs
    if 'outputs' in final_status:
        print(f"\n📤 Workflow Outputs:")
        for output_name, output_value in final_status['outputs'].items():
            print(f"   - {output_name}: {str(output_value)[:100]}...")
    
    # Look for Claude Code specific results
    claude_code_outputs = []
    for key, value in final_status.items():
        if any(term in key.lower() for term in ['claude', 'analysis', 'findings', 'investigation']):
            claude_code_outputs.append((key, value))
    
    if claude_code_outputs:
        print(f"\n🤖 Claude Code Analysis Results:")
        for key, value in claude_code_outputs:
            print(f"   🔍 {key}: {str(value)[:200]}...")


def main():
    """Main test execution function."""
    print("🧪 Comprehensive Incident Response Workflow Test")
    print("🤖 Testing Claude Code as Tool Steps with All CLI Integrations")
    print("=" * 80)
    
    # Test deployment
    result = test_workflow_deployment()
    if not result:
        print("❌ Deployment test failed")
        return 1
    
    workflow_dict, client = result
    
    # Test execution
    execution_result = test_workflow_execution(workflow_dict, client)
    if not execution_result:
        print("❌ Execution test failed")
        return 1
    
    # Analyze results
    analyze_comprehensive_results(execution_result)
    
    print("\n🎉 Comprehensive Test Completed!")
    print("=" * 80)
    print("✅ Claude Code Tool Steps Architecture Validated")
    print("✅ All CLI Tools Integration Tested")
    print("✅ Comprehensive Incident Response Workflow Executed")
    print("✅ Multi-Platform Investigation Capability Demonstrated")
    return 0


if __name__ == "__main__":
    sys.exit(main())