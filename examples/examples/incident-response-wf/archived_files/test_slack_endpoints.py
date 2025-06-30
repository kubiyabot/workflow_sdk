#!/usr/bin/env python3
"""
Test different Slack API endpoints to find the working one.
"""

import os
import json
from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step

def test_slack_endpoints():
    """Test different Slack API endpoints to find the working one."""
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY not set")
        return
    
    client = KubiyaClient(api_key=api_key)
    
    endpoints_to_test = [
        "api/v1/integration/slack/token",
        "api/v1/integration/slack/token/1", 
        "api/v2/integration/slack/token",
        "api/v1/integrations/slack/token",
        "integration/slack/token",
        "integrations/slack/token"
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n🧪 Testing endpoint: {endpoint}")
        
        # Create simple test workflow
        workflow = Workflow(f"test-slack-{endpoint.replace('/', '-')}")
        workflow.data = {
            "name": f"test-slack-{endpoint.replace('/', '-')}",
            "description": f"Test Slack endpoint {endpoint}",
            "type": "chain",
            "runner": "core-testing-2",
            "steps": [
                {
                    "name": "test-slack-token",
                    "executor": {
                        "type": "kubiya",
                        "config": {
                            "url": endpoint,
                            "method": "GET"
                        }
                    },
                    "output": "SLACK_TOKEN"
                },
                {
                    "name": "print-result",
                    "executor": {
                        "type": "tool",
                        "config": {
                            "tool_def": {
                                "name": "print_slack_result",
                                "description": "Print the Slack token result",
                                "type": "docker",
                                "image": "alpine:latest",
                                "content": '''#!/bin/sh
echo "📋 Slack Token Test Result:"
echo "Endpoint: ''' + endpoint + '''"
echo "Response: $slack_token"
if echo "$slack_token" | grep -q "token"; then
    echo "✅ SUCCESS: Token found!"
else
    echo "❌ FAILED: No token in response"
fi'''
                            },
                            "args": {
                                "slack_token": "${SLACK_TOKEN}"
                            }
                        }
                    },
                    "depends": ["test-slack-token"],
                    "output": "RESULT"
                }
            ]
        }
        
        try:
            # Execute workflow
            events = client.execute_workflow(
                workflow_definition=workflow.to_dict(),
                parameters={},
                stream=True
            )
            
            # Process events quickly
            success = False
            error_msg = ""
            
            for event in events:
                if isinstance(event, str) and event.strip():
                    try:
                        parsed = json.loads(event)
                        event_type = parsed.get('type', '')
                        
                        if 'workflow_complete' in event_type:
                            if parsed.get('success', False):
                                print(f"   ✅ Endpoint works!")
                                success = True
                            else:
                                print(f"   ❌ Workflow failed")
                            break
                        elif 'step_complete' in event_type:
                            step = parsed.get('step', {})
                            if step.get('status') == 'failed':
                                error_msg = step.get('error', 'Unknown error')
                                print(f"   ❌ Step failed: {error_msg}")
                                break
                            elif step.get('name') == 'print-result':
                                output = step.get('output', '')
                                if 'SUCCESS' in output:
                                    print(f"   ✅ Token endpoint found!")
                                    success = True
                    except json.JSONDecodeError:
                        continue
            
            if success:
                print(f"🎉 WORKING ENDPOINT FOUND: {endpoint}")
                return endpoint
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print(f"\n❌ No working Slack endpoints found")
    return None

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pathlib import Path
    
    working_endpoint = test_slack_endpoints()
    if working_endpoint:
        print(f"\n🎯 Use this endpoint in your workflow: {working_endpoint}")
    else:
        print(f"\n💡 You may need to:")
        print(f"   • Set up Slack integration in Kubiya first")
        print(f"   • Check if the integration ID is different")
        print(f"   • Verify API permissions")