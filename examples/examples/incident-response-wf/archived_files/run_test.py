#!/usr/bin/env python3
"""
Test runner for the incident response workflow with fake Datadog incident.
This script will deploy and execute the workflow using the SDK.
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
from workflows.simple_incident_workflow import build_simple_incident_response_workflow


def create_fake_datadog_incident():
    """Create a realistic fake Datadog incident event."""
    return {
        "incident_id": "INC-2024-DD-001",
        "incident_title": "High CPU usage detected on production API servers",
        "incident_severity": "critical",
        "incident_body": "Datadog monitoring has detected CPU usage above 95% on multiple production API servers (api-server-1, api-server-2, api-server-3) in the us-east-1 region. This started 15 minutes ago and is affecting user response times. Current metrics show: CPU: 97%, Memory: 78%, Response time: 2.5s (normal: 200ms). Error rate has increased to 8.3% from baseline of 0.1%.",
        "incident_url": "https://app.datadoghq.com/incident/12345",
        "checkpoint_dir": "/tmp/incident-dd-001"
    }


def test_workflow_deployment():
    """Test deploying the workflow to Kubiya."""
    print("🚀 Testing Workflow Deployment")
    print("=" * 50)
    
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
        workflow = build_simple_incident_response_workflow()
        print("✅ Workflow built successfully")
        
        # Convert to deployable format
        workflow_dict = workflow.to_dict()
        
        # Convert Step objects to dictionaries
        if 'steps' in workflow_dict:
            serialized_steps = []
            for i, step in enumerate(workflow_dict['steps']):
                print(f"   Processing step {i}: {type(step)}")
                if hasattr(step, 'to_dict'):
                    serialized_step = step.to_dict()
                    print(f"     Serialized via to_dict(): {type(serialized_step)}")
                    serialized_steps.append(serialized_step)
                elif hasattr(step, 'data'):
                    serialized_step = step.data
                    print(f"     Using .data: {type(serialized_step)}")
                    serialized_steps.append(serialized_step)
                else:
                    print(f"     Using as-is: {type(step)}")
                    serialized_steps.append(step)
            workflow_dict['steps'] = serialized_steps
            
        # Deep scan and fix Step objects
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
        
        # Clean up fields that might be causing validation issues
        if 'params' in workflow_dict:
            # Move params to parameters if needed
            if 'parameters' not in workflow_dict:
                workflow_dict['parameters'] = workflow_dict['params']
            del workflow_dict['params']
            print("   Moved 'params' to 'parameters'")
        
        # Remove 'type' field if it exists at workflow level (might conflict with step types)
        if 'type' in workflow_dict:
            workflow_dict['workflow_type'] = workflow_dict['type']
            del workflow_dict['type']
            print("   Renamed 'type' to 'workflow_type'")
        
        print(f"   Final workflow keys: {list(workflow_dict.keys())}")
        
        print(f"✅ Workflow converted to dict: {workflow_dict['name']}")
        print(f"   - Steps: {len(workflow_dict['steps'])}")
        print(f"   - Description: {workflow_dict['description']}")
        
    except Exception as e:
        print(f"❌ Failed to build workflow: {e}")
        return False
    
    return workflow_dict, client


def test_workflow_execution(workflow_dict, client):
    """Test executing the workflow with fake incident data."""
    print("\n🎯 Testing Workflow Execution")
    print("=" * 50)
    
    # Create fake incident
    fake_incident = create_fake_datadog_incident()
    print("📋 Fake Datadog Incident Created:")
    print(f"   - ID: {fake_incident['incident_id']}")
    print(f"   - Title: {fake_incident['incident_title']}")
    print(f"   - Severity: {fake_incident['incident_severity']}")
    print(f"   - URL: {fake_incident['incident_url']}")
    
    # Update workflow with incident parameters
    workflow_dict['params'] = fake_incident
    
    try:
        # Execute the workflow directly (no separate deployment needed)
        print("\n▶️  Executing workflow...")
        execution_result = client.execute_workflow(
            workflow_definition=workflow_dict,
            parameters=fake_incident,
            stream=False  # Get final result, not streaming
        )
        print(f"✅ Workflow execution completed: {type(execution_result)}")
        
        return execution_result
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return None


def monitor_execution(client, execution_id):
    """Monitor the workflow execution progress."""
    print(f"\n👀 Monitoring Execution: {execution_id}")
    print("=" * 50)
    
    max_attempts = 30  # 5 minutes with 10-second intervals
    attempt = 0
    
    while attempt < max_attempts:
        try:
            status = client.get_execution_status(execution_id)
            print(f"🔄 Attempt {attempt + 1}: Status = {status.get('status', 'unknown')}")
            
            if status.get('status') in ['completed', 'failed', 'cancelled']:
                print(f"🏁 Final status: {status.get('status')}")
                return status
                
        except Exception as e:
            print(f"⚠️  Error checking status: {e}")
        
        attempt += 1
        time.sleep(10)
    
    print("⏰ Monitoring timeout reached")
    return None


def analyze_results(final_status):
    """Analyze the workflow execution results."""
    print("\n📊 Results Analysis")
    print("=" * 50)
    
    if not final_status:
        print("❌ No final status available")
        return
    
    print(f"📋 Raw Response Type: {type(final_status)}")
    
    # Print the full response for debugging
    import json
    try:
        print(f"📋 Full Response: {json.dumps(final_status, indent=2, default=str)}")
    except Exception as e:
        print(f"📋 Response (non-JSON): {final_status}")
    
    status = final_status.get('status', 'unknown')
    print(f"📋 Final Status: {status}")
    
    # Check for execution ID
    execution_id = final_status.get('execution_id') or final_status.get('id') or final_status.get('executionId')
    if execution_id:
        print(f"🔑 Execution ID: {execution_id}")
    
    # Check for workflow ID
    workflow_id = final_status.get('workflow_id') or final_status.get('workflowId')
    if workflow_id:
        print(f"🔗 Workflow ID: {workflow_id}")
    
    # Check for step results
    if 'steps' in final_status:
        print("\n📋 Step Results:")
        for step_name, step_result in final_status['steps'].items():
            step_status = step_result.get('status', 'unknown')
            emoji = "✅" if step_status == 'completed' else "❌" if step_status == 'failed' else "⏳"
            print(f"   {emoji} {step_name}: {step_status}")
            
            # Show Claude Code outputs
            if 'output' in step_result and 'claude' in step_name.lower():
                print(f"      🤖 Claude Output: {step_result['output'][:200]}...")
    
    # Check for errors
    if 'errors' in final_status:
        print(f"\n❌ Errors encountered:")
        for error in final_status['errors']:
            print(f"   - {error}")
    
    # Check for outputs
    if 'outputs' in final_status:
        print(f"\n📤 Workflow Outputs:")
        for output_name, output_value in final_status['outputs'].items():
            print(f"   - {output_name}: {str(output_value)[:100]}...")
    
    # Check for any message or result field
    if 'message' in final_status:
        print(f"\n📝 Message: {final_status['message']}")
    
    if 'result' in final_status:
        print(f"\n📊 Result: {final_status['result']}")
        
    # Look for any Claude Code related fields
    for key, value in final_status.items():
        if 'claude' in key.lower() or 'agent' in key.lower() or 'analysis' in key.lower():
            print(f"\n🤖 {key}: {str(value)[:300]}...")


def main():
    """Main test execution function."""
    print("🧪 Incident Response Workflow Live Test")
    print("🤖 Testing Claude Code Integration with Real Execution")
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
    
    # Analyze results directly (since we got the final result)
    analyze_results(execution_result)
    
    print("\n🎉 Test completed!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())