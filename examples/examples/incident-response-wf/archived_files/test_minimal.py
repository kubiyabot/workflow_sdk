#!/usr/bin/env python3
"""
Minimal test to debug the workflow execution issue.
"""

import os
import sys
import json
from pathlib import Path

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from fixed_incident_workflow import create_fixed_incident_workflow


def test_minimal():
    """Minimal test with detailed debugging."""
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ No API key")
        return
    
    print("🔧 Creating workflow...")
    workflow = create_fixed_incident_workflow()
    workflow_dict = workflow.to_dict()
    
    print(f"✅ Workflow: {workflow_dict['name']}")
    print(f"📋 Keys: {list(workflow_dict.keys())}")
    
    # Create minimal incident
    incident = {
        "id": "TEST-001",
        "title": "Test Incident",
        "url": "https://test.com",
        "severity": "low",
        "body": "Test incident body",
        "kubiya": {"slack_channel_id": "#test"}
    }
    
    params = {"event": json.dumps(incident)}
    
    print(f"📦 Params: {list(params.keys())}")
    print(f"📄 Event size: {len(params['event'])} chars")
    
    # Try execution
    client = KubiyaClient(api_key=api_key, timeout=60)
    
    print("🚀 Executing...")
    try:
        events = list(client.execute_workflow(
            workflow_definition=workflow_dict,
            parameters=params,
            stream=True
        ))
        
        print(f"✅ Got {len(events)} events")
        for i, event in enumerate(events):
            print(f"Event {i+1}: {type(event)} - {str(event)[:100]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_minimal()