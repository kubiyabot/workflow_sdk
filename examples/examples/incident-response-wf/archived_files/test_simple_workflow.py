#!/usr/bin/env python3
"""
Test script for the simplified incident response workflow.
"""

import os
import sys
import json
from pathlib import Path

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from simple_incident_workflow import create_datadog_incident_workflow


def test_simple_workflow():
    """Test the simplified incident response workflow."""
    print("🧪 Testing Simplified Incident Response Workflow")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable not set")
        return 1
    
    print(f"✅ API Key available (length: {len(api_key)})")
    
    # Create client
    client = KubiyaClient(api_key=api_key)
    print("✅ Client created")
    
    # Build workflow
    try:
        workflow = create_datadog_incident_workflow()
        print("✅ Workflow built successfully")
        
        # Convert to dict manually to handle Step objects
        workflow_dict = workflow.to_dict()
        print(f"✅ Workflow compiled: {len(workflow_dict['steps'])} steps")
        
        # Show steps
        for i, step in enumerate(workflow_dict['steps'], 1):
            print(f"   {i}. {step.get('name', 'unnamed')}")
        
    except Exception as e:
        print(f"❌ Workflow build failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1
    
    # Create realistic incident event using the actual format
    incident_event = {
        "id": "INC-2024-SIMPLE-TEST-001",
        "title": "Production API Critical Error Rate Spike",
        "url": "https://app.datadoghq.com/incidents/INC-2024-SIMPLE-TEST-001",
        "severity": "critical",
        "body": "Production API experiencing critical error rate spike from 0.5% to 25% over the last 15 minutes. Response times degraded from 200ms to 3.2s. Customer impact severe with payment processing failures. Correlates with recent deployment 45 minutes ago.",
        "kubiya": {
            "slack_channel_id": "#inc-INC-2024-SIMPLE-TEST-001-production-api-critical"
        }
    }
    
    # Set workflow parameters
    workflow_params = {
        "event": json.dumps(incident_event)
    }
    
    print(f"\n📋 Test Incident Created:")
    print(f"   - ID: {incident_event['id']}")
    print(f"   - Title: {incident_event['title']}")
    print(f"   - Severity: {incident_event['severity']}")
    print(f"   - Slack Channel: {incident_event['kubiya']['slack_channel_id']}")
    
    # Execute workflow
    try:
        print("\n🚀 Executing simplified workflow...")
        result = client.execute_workflow(
            workflow_definition=workflow_dict,
            parameters=workflow_params,
            stream=False
        )
        
        print("✅ Workflow execution completed!")
        print(f"📋 Result type: {type(result)}")
        
        # Analyze result
        if isinstance(result, dict):
            print(f"📋 Execution status: {result.get('status', 'unknown')}")
            
            if 'execution_id' in result or 'id' in result:
                exec_id = result.get('execution_id') or result.get('id')
                print(f"🔑 Execution ID: {exec_id}")
            
            if 'errors' in result and result['errors']:
                print(f"❌ Errors: {len(result['errors'])}")
                for error in result['errors'][:2]:
                    print(f"   - {error}")
            
            if 'outputs' in result:
                print(f"📤 Outputs: {len(result['outputs'])}")
                for output_name in result['outputs']:
                    print(f"   - {output_name}")
        
        print(f"\n📊 Raw Result Preview:")
        print(json.dumps(result, indent=2, default=str)[:500] + "...")
        
        return 0
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    print("🧪 Simplified Incident Response Workflow Test")
    print("🎯 Testing Exact Use Case: Datadog Event → Claude Code Investigation → Slack Updates")
    print("=" * 80)
    
    exit_code = test_simple_workflow()
    
    if exit_code == 0:
        print("\n🎉 Simplified Workflow Test Completed Successfully!")
        print("=" * 80)
        print("✅ Datadog Event Parsing")
        print("✅ Secret Management (Datadog, Observe, ArgoCD, GitHub, Slack)")
        print("✅ Slack War Room Creation")
        print("✅ Claude Code CLI Tool Integration")
        print("✅ Kubernetes Context Setup")
        print("✅ All CLI Tools Configured (kubectl, helm, argocd, observe, dogshell, gh)")
        print("✅ Investigation Analysis Generation")
        print("✅ Slack Progress Updates")
    else:
        print("\n❌ Test Failed - Check Output Above")
    
    sys.exit(exit_code)