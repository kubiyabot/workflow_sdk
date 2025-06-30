#!/usr/bin/env python3
"""
Simple Slack channel creation debug - focusing on the API calls.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add SDK path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step


def debug_slack_simple():
    """Simple debug focusing on exact API responses."""
    
    print("🔍 SLACK CHANNEL DEBUG - SIMPLE")
    print("=" * 40)
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY required")
        return 1
    
    timestamp = int(time.time())
    
    workflow = Workflow("simple-slack-debug")
    workflow.data = {
        "name": "simple-slack-debug",
        "description": "Simple Slack debug",
        "type": "chain",
        "runner": "core-testing-2",
        "steps": [
            {
                "name": "get-token",
                "executor": {
                    "type": "kubiya",
                    "config": {
                        "url": "api/v1/integration/slack/token/1",
                        "method": "GET"
                    }
                },
                "output": "TOKEN"
            },
            {
                "name": "test-channel",
                "executor": {
                    "type": "tool",
                    "config": {
                        "tool_def": {
                            "name": "test_channel_creation",
                            "description": "Test channel creation",
                            "type": "docker",
                            "image": "curlimages/curl:latest",
                            "content": f'''#!/bin/sh
echo "🔍 Testing Slack channel creation"

TOKEN=$(echo "$token" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
CHANNEL="debug-test-{timestamp}"

echo "Token: ${{TOKEN:0:20}}..."
echo "Channel: $CHANNEL"

# Test 1: Auth
echo ""
echo "1. Testing auth..."
AUTH=$(curl -s -H "Authorization: Bearer $TOKEN" "https://slack.com/api/auth.test")
echo "Auth response: $AUTH"

# Test 2: Create channel
echo ""
echo "2. Creating channel..."
CREATE=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{{"name":"'$CHANNEL'","is_private":false}}' "https://slack.com/api/conversations.create")
echo "Create response: $CREATE"

if echo "$CREATE" | grep -q '"ok":true'; then
    CHANNEL_ID=$(echo "$CREATE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    echo "SUCCESS! Channel created: $CHANNEL_ID"
    echo "URL: https://slack.com/channels/$CHANNEL_ID"
    
    # Post message
    echo ""
    echo "3. Posting message..."
    MSG=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{{"channel":"'$CHANNEL_ID'","text":"Debug test successful!"}}' "https://slack.com/api/chat.postMessage")
    echo "Message response: $MSG"
    
    # Archive
    echo ""
    echo "4. Archiving..."
    ARCHIVE=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{{"channel":"'$CHANNEL_ID'"}}' "https://slack.com/api/conversations.archive")
    echo "Archive response: $ARCHIVE"
    
else
    ERROR=$(echo "$CREATE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "FAILED! Error: $ERROR"
    echo "Full response: $CREATE"
fi

echo ""
echo "Debug completed!"'''
                        },
                        "args": {
                            "token": "${TOKEN}"
                        }
                    }
                },
                "depends": ["get-token"],
                "output": "RESULT"
            }
        ]
    }
    
    client = KubiyaClient(api_key=api_key, timeout=120)
    
    try:
        print(f"🚀 Running simple debug...")
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters={},
            stream=True
        )
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        if step.get('name') == 'test-channel':
                            output = step.get('output', '')
                            print("\n" + "="*50)
                            print("🔍 SLACK DEBUG OUTPUT:")
                            print("="*50)
                            print(output)
                            print("="*50)
                    
                    elif 'workflow_complete' in event_type:
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        return 0
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(debug_slack_simple())