#!/usr/bin/env python3
"""
Debug Slack channel creation with detailed API response analysis.
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


def debug_slack_channel_creation():
    """Debug Slack channel creation with detailed logging."""
    
    print("🔍 SLACK CHANNEL CREATION DEBUG")
    print("=" * 50)
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY required")
        return 1
    
    # Create a focused debug workflow
    timestamp = int(time.time())
    test_channel_name = f"debug-test-{timestamp}"
    
    workflow = Workflow("debug-slack-channel")
    workflow.data = {
        "name": "debug-slack-channel",
        "description": "Debug Slack channel creation",
        "type": "chain",
        "runner": "core-testing-2",
        "steps": [
            {
                "name": "get-slack-token",
                "executor": {
                    "type": "kubiya",
                    "config": {
                        "url": "api/v1/integration/slack/token/1",
                        "method": "GET"
                    }
                },
                "output": "SLACK_TOKEN"
            },
            {
                "name": "debug-channel-creation",
                "executor": {
                    "type": "tool",
                    "config": {
                        "tool_def": {
                            "name": "debug_slack_channel_creation",
                            "description": "Debug Slack channel creation with detailed API analysis",
                            "type": "docker",
                            "image": "curlimages/curl:latest",
                            "content": f'''#!/bin/sh
echo "🔍 SLACK CHANNEL CREATION DEBUG"
echo "==============================="

SLACK_TOKEN=$(echo "$slack_token" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
CHANNEL_NAME="{test_channel_name}"

echo "🔑 Token: ${{SLACK_TOKEN:0:20}}..."
echo "📱 Channel name: $CHANNEL_NAME"

if [ -z "$SLACK_TOKEN" ] || [ "$SLACK_TOKEN" = "null" ]; then
    echo "❌ No Slack token available"
    exit 1
fi

# Step 1: Test auth and get bot info
echo ""
echo "1️⃣ Testing bot authentication..."
AUTH_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/auth.test")
echo "📋 Auth response: $AUTH_RESPONSE"

if echo "$AUTH_RESPONSE" | grep -q '"ok":true'; then
    BOT_USER=$(echo "$AUTH_RESPONSE" | grep -o '"user":"[^"]*"' | cut -d'"' -f4)
    BOT_USER_ID=$(echo "$AUTH_RESPONSE" | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
    TEAM_NAME=$(echo "$AUTH_RESPONSE" | grep -o '"team":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Bot authenticated successfully"
    echo "   🤖 Bot user: $BOT_USER (ID: $BOT_USER_ID)"
    echo "   🏢 Team: $TEAM_NAME"
else
    echo "❌ Bot authentication failed"
    exit 1
fi

# Step 2: Check bot permissions with detailed scope info
echo ""
echo "2️⃣ Checking bot token scopes..."
SCOPES_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/auth.test")
# Note: auth.test doesn't return scopes, but we can infer from API calls

# Step 3: Test conversations.list to check basic permissions
echo ""
echo "3️⃣ Testing conversations.list permission..."
LIST_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/conversations.list?limit=5")
echo "📋 List response: ${{LIST_RESPONSE:0:200}}..."

if echo "$LIST_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Bot can list conversations"
    CHANNEL_COUNT=$(echo "$LIST_RESPONSE" | grep -o '"name":"[^"]*"' | wc -l)
    echo "   📱 Found $CHANNEL_COUNT channels"
else
    echo "❌ Bot cannot list conversations"
    LIST_ERROR=$(echo "$LIST_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "   🔍 Error: $LIST_ERROR"
fi

# Step 4: Try creating public channel
echo ""
echo "4️⃣ Attempting to create PUBLIC channel..."
echo "   📱 Channel name: $CHANNEL_NAME"
echo "   🔒 Private: false"
echo "   📡 API endpoint: https://slack.com/api/conversations.create"

CREATE_PUBLIC_RESPONSE=$(curl -s -X POST \\
    -H "Authorization: Bearer $SLACK_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d "{\\\\"name\\\\":\\\\"$CHANNEL_NAME\\\\",\\\\"is_private\\\\":false}" \\
    "https://slack.com/api/conversations.create")

echo "📋 Public channel response: $CREATE_PUBLIC_RESPONSE"

if echo "$CREATE_PUBLIC_RESPONSE" | grep -q '"ok":true'; then
    PUBLIC_CHANNEL_ID=$(echo "$CREATE_PUBLIC_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "✅ PUBLIC channel created successfully!"
    echo "   🆔 Channel ID: $PUBLIC_CHANNEL_ID"
    echo "   📱 Channel name: $CHANNEL_NAME"
    echo "   🔗 URL: https://slack.com/channels/$PUBLIC_CHANNEL_ID"
    
    # Test posting a message
    echo ""
    echo "5️⃣ Testing message posting to public channel..."
    MSG_RESPONSE=$(curl -s -X POST \\
        -H "Authorization: Bearer $SLACK_TOKEN" \\
        -H "Content-Type: application/json" \\
        -d "{\\\\"channel\\\\":\\\\"$PUBLIC_CHANNEL_ID\\\\",\\\\"text\\\\":\\\\"🧪 Debug test - public channel created successfully!\\\\"}" \\
        "https://slack.com/api/chat.postMessage")
    
    if echo "$MSG_RESPONSE" | grep -q '"ok":true'; then
        echo "✅ Message posted to public channel"
    else
        echo "❌ Message posting failed"
        echo "   Response: $MSG_RESPONSE"
    fi
    
    # Archive test channel
    echo ""
    echo "6️⃣ Cleaning up public test channel..."
    ARCHIVE_RESPONSE=$(curl -s -X POST \\
        -H "Authorization: Bearer $SLACK_TOKEN" \\
        -H "Content-Type: application/json" \\
        -d "{\\\\"channel\\\\":\\\\"$PUBLIC_CHANNEL_ID\\\\"}" \\
        "https://slack.com/api/conversations.archive")
    
    if echo "$ARCHIVE_RESPONSE" | grep -q '"ok":true'; then
        echo "✅ Public test channel archived"
    else
        echo "⚠️ Could not archive test channel"
    fi
    
else
    PUBLIC_ERROR=$(echo "$CREATE_PUBLIC_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "❌ PUBLIC channel creation failed!"
    echo "   🔍 Error: $PUBLIC_ERROR"
    echo "   📋 Full response: $CREATE_PUBLIC_RESPONSE"
    
    # Try private channel as fallback
    echo ""
    echo "4️⃣b Attempting to create PRIVATE channel as fallback..."
    
    PRIVATE_CHANNEL_NAME="$CHANNEL_NAME-priv"
    CREATE_PRIVATE_RESPONSE=$(curl -s -X POST \\
        -H "Authorization: Bearer $SLACK_TOKEN" \\
        -H "Content-Type: application/json" \\
        -d "{\\\\"name\\\\":\\\\"$PRIVATE_CHANNEL_NAME\\\\",\\\\"is_private\\\\":true}" \\
        "https://slack.com/api/conversations.create")
    
    echo "📋 Private channel response: $CREATE_PRIVATE_RESPONSE"
    
    if echo "$CREATE_PRIVATE_RESPONSE" | grep -q '"ok":true'; then
        PRIVATE_CHANNEL_ID=$(echo "$CREATE_PRIVATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo "✅ PRIVATE channel created successfully!"
        echo "   🆔 Channel ID: $PRIVATE_CHANNEL_ID"
        echo "   📱 Channel name: $PRIVATE_CHANNEL_NAME"
    else
        PRIVATE_ERROR=$(echo "$CREATE_PRIVATE_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo "❌ PRIVATE channel creation also failed!"
        echo "   🔍 Error: $PRIVATE_ERROR"
    fi
fi

echo ""
echo "🎯 DEBUG SUMMARY:"
echo "================="
echo "• Bot authentication: $(echo "$AUTH_RESPONSE" | grep -q '"ok":true' && echo "✅ Success" || echo "❌ Failed")"
echo "• List conversations: $(echo "$LIST_RESPONSE" | grep -q '"ok":true' && echo "✅ Success" || echo "❌ Failed")"
echo "• Create public channel: $(echo "$CREATE_PUBLIC_RESPONSE" | grep -q '"ok":true' && echo "✅ Success" || echo "❌ Failed ($PUBLIC_ERROR)")"
echo "• Create private channel: $(echo "$CREATE_PRIVATE_RESPONSE" | grep -q '"ok":true' && echo "✅ Success" || echo "❌ Failed ($PRIVATE_ERROR)")"

echo ""
echo "💡 TROUBLESHOOTING:"
if ! echo "$CREATE_PUBLIC_RESPONSE" | grep -q '"ok":true' && ! echo "$CREATE_PRIVATE_RESPONSE" | grep -q '"ok":true'; then
    echo "❌ Channel creation completely failed"
    echo "   🔍 Check bot scopes: needs 'channels:manage' for public, 'groups:write' for private"
    echo "   🔍 Check workspace permissions: admin may restrict channel creation"
    echo "   🔍 Verify bot is properly installed in workspace"
else
    echo "✅ At least one channel type works - incident response will succeed!"
fi

echo ""
echo "✅ Slack channel creation debug completed!"'''
                        },
                        "args": {
                            "slack_token": "${SLACK_TOKEN}"
                        }
                    }
                },
                "depends": ["get-slack-token"],
                "output": "DEBUG_RESULTS"
            }
        ]
    }
    
    client = KubiyaClient(api_key=api_key, timeout=180)
    
    try:
        print(f"🚀 Running Slack channel debug...")
        print(f"📱 Test channel name: {test_channel_name}")
        
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
                        if step.get('name') == 'debug-channel-creation':
                            output = step.get('output', '')
                            print("\n" + "="*60)
                            print("🔍 SLACK CHANNEL DEBUG RESULTS:")
                            print("="*60)
                            print(output)
                            print("="*60)
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        if success:
                            print(f"\n✅ Debug completed successfully!")
                        else:
                            print(f"\n❌ Debug failed!")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        return 0
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(debug_slack_channel_creation())