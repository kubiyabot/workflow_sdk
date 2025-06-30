#!/usr/bin/env python3
"""
Super simple workflow test to isolate the validation issue.
"""

import os
import sys
import json
from pathlib import Path

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step


def create_super_simple_workflow():
    """Create the simplest possible workflow."""
    workflow = (Workflow("test-simple-workflow")
                .description("Super simple test workflow")
                .type("chain")
                .runner("core-testing-2"))
    
    # Just one simple step
    step1 = (Step("hello-world")
             .docker("alpine:latest", content="""#!/bin/sh
echo "Hello World from step 1"
echo '{"message": "hello", "status": "complete"}'
""")
             .output("HELLO_OUTPUT"))
    
    # Add step to workflow
    workflow.data["steps"] = [step1.to_dict()]
    
    return workflow


def test_super_simple():
    """Test the super simple workflow."""
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ No API key")
        return
    
    print("🔧 Creating super simple workflow...")
    workflow = create_super_simple_workflow()
    workflow_dict = workflow.to_dict()
    
    print(f"✅ Workflow: {workflow_dict['name']}")
    print(f"📋 Keys: {list(workflow_dict.keys())}")
    print(f"📝 Steps: {len(workflow_dict['steps'])}")
    
    # Minimal parameters
    params = {"message": "test"}
    
    print(f"📦 Params: {params}")
    
    # Try execution
    client = KubiyaClient(api_key=api_key, timeout=60)
    
    print("🚀 Executing super simple workflow...")
    try:
        events = list(client.execute_workflow(
            workflow_definition=workflow_dict,
            parameters=params,
            stream=True
        ))
        
        print(f"✅ Got {len(events)} events")
        for i, event in enumerate(events):
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    if 'error' in parsed:
                        print(f"❌ Event {i+1}: {parsed['error']}")
                    else:
                        print(f"📡 Event {i+1}: {parsed.get('details', {}).get('errorType', 'success')}")
                except:
                    print(f"📝 Event {i+1}: {event[:50]}...")
            else:
                print(f"📋 Event {i+1}: {type(event)}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_super_simple()