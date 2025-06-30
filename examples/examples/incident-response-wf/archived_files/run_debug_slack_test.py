#!/usr/bin/env python3
"""
Debug test with detailed Slack API output to see exactly what's happening.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# Add paths for SDK access
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step


def create_debug_slack_workflow():
    """Create a debug workflow that shows detailed Slack API responses."""
    
    workflow = (Workflow("debug-slack-channel-creation")
                .description("Debug Slack channel creation with detailed API responses")
                .type("chain")
                .runner("core-testing-2"))
    
    # Parameters
    workflow.data["params"] = {
        "test_channel_name": "debug-incident-test",
        "test_users": "@shaked,@amit"
    }
    
    # Step 1: Get Slack token
    token_step = Step("get-slack-token")
    token_step.data = {
        "name": "get-slack-token",
        "executor": {
            "type": "kubiya",
            "config": {
                "url": "api/v1/integration/slack/token/1",
                "method": "GET"
            }
        },
        "output": "SLACK_TOKEN"
    }
    
    # Step 2: Debug Slack API calls
    debug_step = Step("debug-slack-api")
    debug_step.data = {
        "name": "debug-slack-api",
        "executor": {
            "type": "tool",
            "config": {
                "tool_def": {
                    "name": "debug_slack_channel_creation",
                    "description": "Debug Slack channel creation with full API responses",
                    "type": "docker",
                    "image": "curlimages/curl:latest",
                    "content": '''#!/bin/sh
echo "🔍 DEBUG: Slack Channel Creation Test"
echo "===================================="

# Extract token
SLACK_TOKEN=$(echo "$slack_token" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
echo "🔑 Token preview: ${SLACK_TOKEN:0:20}..."

if [ -z "$SLACK_TOKEN" ] || [ "$SLACK_TOKEN" = "null" ]; then
    echo "❌ No Slack token available"
    exit 1
fi

# Test 1: Auth test
echo ""
echo "1️⃣ Testing Slack Authentication:"
AUTH_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" \
    "https://slack.com/api/auth.test")

echo "📋 Auth Response:"
echo "$AUTH_RESPONSE"

if echo "$AUTH_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Auth successful!"
    USER_NAME=$(echo "$AUTH_RESPONSE" | grep -o '"user":"[^"]*"' | cut -d'"' -f4)
    TEAM_NAME=$(echo "$AUTH_RESPONSE" | grep -o '"team":"[^"]*"' | cut -d'"' -f4)
    echo "👤 Bot User: $USER_NAME"
    echo "🏢 Team: $TEAM_NAME"
else
    echo "❌ Auth failed!"
    exit 1
fi

# Test 2: List existing channels
echo ""
echo "2️⃣ Listing existing channels:"
CHANNELS_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" \
    "https://slack.com/api/conversations.list?limit=20")

echo "📋 Channels Response:"
echo "$CHANNELS_RESPONSE" | head -c 500
echo "..."

# Test 3: Try to create a test channel
CHANNEL_NAME="debug-test-$(date +%s)"
echo ""
echo "3️⃣ Creating test channel: $CHANNEL_NAME"

CREATE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $SLACK_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\\"name\\":\\"$CHANNEL_NAME\\",\\"is_private\\":false}" \
    "https://slack.com/api/conversations.create")

echo "📋 Create Response:"
echo "$CREATE_RESPONSE"

if echo "$CREATE_RESPONSE" | grep -q '"ok":true'; then
    CHANNEL_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "✅ Channel created successfully!"
    echo "📱 Channel ID: $CHANNEL_ID"
    echo "📱 Channel Name: $CHANNEL_NAME"
    
    # Test 4: Post a message
    echo ""
    echo "4️⃣ Posting test message:"
    
    MESSAGE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\\"channel\\":\\"$CHANNEL_ID\\",\\"text\\":\\"🧪 Debug test message from incident response workflow!\\"}" \
        "https://slack.com/api/chat.postMessage")
    
    echo "📋 Message Response:"
    echo "$MESSAGE_RESPONSE"
    
    if echo "$MESSAGE_RESPONSE" | grep -q '"ok":true'; then
        echo "✅ Message posted successfully!"
    else
        echo "❌ Message posting failed!"
    fi
    
    # Test 5: Archive the test channel
    echo ""
    echo "5️⃣ Cleaning up test channel:"
    
    ARCHIVE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\\"channel\\":\\"$CHANNEL_ID\\"}" \
        "https://slack.com/api/conversations.archive")
    
    echo "📋 Archive Response:"
    echo "$ARCHIVE_RESPONSE"
    
    if echo "$ARCHIVE_RESPONSE" | grep -q '"ok":true'; then
        echo "✅ Test channel archived successfully!"
    else
        echo "⚠️ Could not archive test channel"
    fi
    
else
    echo "❌ Channel creation failed!"
    ERROR_MSG=$(echo "$CREATE_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "🔍 Error: $ERROR_MSG"
fi

echo ""
echo "🎯 DEBUG SUMMARY:"
echo "==============="
echo "• Slack token: $([ -n "$SLACK_TOKEN" ] && echo "Available" || echo "Missing")"
echo "• Auth test: $(echo "$AUTH_RESPONSE" | grep -q '"ok":true' && echo "✅ Passed" || echo "❌ Failed")"
echo "• Channel creation: $(echo "$CREATE_RESPONSE" | grep -q '"ok":true' && echo "✅ Success" || echo "❌ Failed")"

echo ""
echo "✅ Slack API debug completed!"'''
                },
                "args": {
                    "slack_token": "${SLACK_TOKEN}",
                    "test_channel_name": "${test_channel_name}",
                    "test_users": "${test_users}"
                }
            }
        },
        "depends": ["get-slack-token"],
        "output": "DEBUG_RESULTS"
    }
    
    # Add steps to workflow
    workflow.data["steps"] = [
        token_step.data,
        debug_step.data
    ]
    
    return workflow


def run_debug_test():
    """Run the debug test to see what's happening with Slack."""
    
    print("🔍 SLACK API DEBUG TEST")
    print("=" * 40)
    print("🎯 This will test actual Slack channel creation")
    print("📱 Check your Slack workspace for a debug channel")
    print("=" * 40)
    
    # Validate environment
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable is required")
        return 1
    
    # Create workflow
    workflow = create_debug_slack_workflow()
    client = KubiyaClient(api_key=api_key, timeout=300)
    
    try:
        print("🚀 Starting debug workflow...")
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters={
                "test_channel_name": f"debug-test-{int(time.time())}",
                "test_users": "@shaked,@amit"
            },
            stream=True
        )
        
        print("📡 Processing events...")
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        
                        if step_name == 'debug-slack-api':
                            output = step.get('output', '')
                            print("\n" + "="*50)
                            print("🔍 SLACK API DEBUG OUTPUT:")
                            print("="*50)
                            print(output)
                            print("="*50)
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        if success:
                            print("\n✅ Debug test completed successfully!")
                        else:
                            print("\n❌ Debug test failed!")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        print("\n💡 Check your Slack workspace:")
        print("   • Look for a channel named 'debug-test-XXXXXXX'")
        print("   • Check if it was created and then archived")
        print("   • Look for a test message in the channel")
        
        return 0
        
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_debug_test())