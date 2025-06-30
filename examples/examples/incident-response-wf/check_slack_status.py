#!/usr/bin/env python3
"""
Quick Slack integration status checker.
"""

import os
import sys
import json
from pathlib import Path

# Add SDK path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step


def check_slack_status():
    """Check current Slack integration status and permissions."""
    
    print("🔍 SLACK INTEGRATION STATUS CHECK")
    print("=" * 40)
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY required")
        return 1
    
    # Create simple Slack check workflow
    workflow = Workflow("slack-status-check")
    workflow.data = {
        "name": "slack-status-check",
        "description": "Check Slack integration status",
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
                "name": "check-slack-permissions",
                "executor": {
                    "type": "tool",
                    "config": {
                        "tool_def": {
                            "name": "check_slack_permissions",
                            "description": "Check Slack bot permissions and status",
                            "type": "docker",
                            "image": "curlimages/curl:latest",
                            "content": '''#!/bin/sh
echo "🔍 SLACK INTEGRATION DIAGNOSTIC"
echo "=============================="

SLACK_TOKEN=$(echo "$slack_token" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$SLACK_TOKEN" ] || [ "$SLACK_TOKEN" = "null" ]; then
    echo "❌ No Slack token available"
    echo "💡 Check Kubiya Slack integration setup"
    exit 1
fi

echo "🔑 Token found: ${SLACK_TOKEN:0:20}..."

# Test 1: Auth check
echo ""
echo "1️⃣ Testing bot authentication..."
AUTH_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/auth.test")

if echo "$AUTH_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Bot authentication successful"
    BOT_USER=$(echo "$AUTH_RESPONSE" | grep -o '"user":"[^"]*"' | cut -d'"' -f4)
    TEAM_NAME=$(echo "$AUTH_RESPONSE" | grep -o '"team":"[^"]*"' | cut -d'"' -f4)
    echo "   🤖 Bot user: $BOT_USER"
    echo "   🏢 Team: $TEAM_NAME"
else
    echo "❌ Bot authentication failed"
    echo "   Response: $AUTH_RESPONSE"
    exit 1
fi

# Test 2: Check bot permissions
echo ""
echo "2️⃣ Checking bot permissions..."
PERMS_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/auth.test")

# Try to list channels to check permissions
CHANNELS_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" "https://slack.com/api/conversations.list?limit=5")

if echo "$CHANNELS_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Bot can list channels"
    CHANNEL_COUNT=$(echo "$CHANNELS_RESPONSE" | grep -o '"name":"[^"]*"' | wc -l)
    echo "   📱 Found $CHANNEL_COUNT channels"
else
    echo "❌ Bot cannot list channels"
    echo "   Response: $CHANNELS_RESPONSE"
fi

# Test 3: Try creating a test channel
echo ""
echo "3️⃣ Testing channel creation..."
TEST_CHANNEL="test-bot-$(date +%s)"

CREATE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $SLACK_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\\"name\\":\\"$TEST_CHANNEL\\",\\"is_private\\":false}" \
    "https://slack.com/api/conversations.create")

if echo "$CREATE_RESPONSE" | grep -q '"ok":true'; then
    CHANNEL_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "✅ Channel creation successful!"
    echo "   📱 Created: #$TEST_CHANNEL"
    echo "   🆔 Channel ID: $CHANNEL_ID"
    echo "   🔗 URL: https://slack.com/channels/$CHANNEL_ID"
    
    # Clean up test channel
    ARCHIVE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\\"channel\\":\\"$CHANNEL_ID\\"}" \
        "https://slack.com/api/conversations.archive")
    
    if echo "$ARCHIVE_RESPONSE" | grep -q '"ok":true'; then
        echo "   🗑️ Test channel archived"
    fi
    
else
    echo "❌ Channel creation failed"
    ERROR=$(echo "$CREATE_RESPONSE" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
    echo "   🔍 Error: $ERROR"
    echo "   📋 Full response: $CREATE_RESPONSE"
    
    case "$ERROR" in
        "missing_scope")
            echo "   💡 Bot needs 'channels:write' permission"
            ;;
        "restricted_action")
            echo "   💡 Workspace restricts channel creation"
            ;;
        "name_taken")
            echo "   💡 Channel name already exists"
            ;;
        *)
            echo "   💡 Check bot permissions and workspace settings"
            ;;
    esac
fi

echo ""
echo "📋 SUMMARY:"
echo "=========="
echo "✅ Bot Authentication: Working"
echo "$(echo "$CHANNELS_RESPONSE" | grep -q '"ok":true' && echo "✅" || echo "❌") Channel Access: $(echo "$CHANNELS_RESPONSE" | grep -q '"ok":true' && echo "Working" || echo "Failed")"
echo "$(echo "$CREATE_RESPONSE" | grep -q '"ok":true' && echo "✅" || echo "❌") Channel Creation: $(echo "$CREATE_RESPONSE" | grep -q '"ok":true' && echo "Working" || echo "Failed")"

if echo "$CREATE_RESPONSE" | grep -q '"ok":true'; then
    echo ""
    echo "🎉 Your Slack integration is ready for incident channels!"
else
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "   1. Check bot permissions in Slack workspace"
    echo "   2. Ensure bot has 'channels:write' scope"
    echo "   3. Verify workspace allows bot channel creation"
fi'''
                        },
                        "args": {
                            "slack_token": "${SLACK_TOKEN}"
                        }
                    }
                },
                "depends": ["get-slack-token"],
                "output": "SLACK_STATUS"
            }
        ]
    }
    
    client = KubiyaClient(api_key=api_key, timeout=120)
    
    try:
        print("🚀 Running Slack diagnostic...")
        
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
                        if step.get('name') == 'check-slack-permissions':
                            output = step.get('output', '')
                            print("\n" + "="*50)
                            print("🔍 SLACK DIAGNOSTIC RESULTS:")
                            print("="*50)
                            print(output)
                            print("="*50)
                    
                    elif 'workflow_complete' in event_type:
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        return 0
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(check_slack_status())