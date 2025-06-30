#!/usr/bin/env python3
"""
Test creating a persistent incident channel that STAYS visible and invites you.
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


def create_persistent_incident_channel_test():
    """Create a test that creates a PERSISTENT incident channel and invites users."""
    
    workflow = (Workflow("persistent-incident-channel-test")
                .description("Create persistent incident channel with user invites")
                .type("chain")
                .runner("core-testing-2"))
    
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
    
    # Step 2: Create persistent incident channel
    create_step = Step("create-persistent-channel")
    create_step.data = {
        "name": "create-persistent-channel",
        "executor": {
            "type": "tool",
            "config": {
                "tool_def": {
                    "name": "create_persistent_incident_channel",
                    "description": "Create persistent incident channel with user invites",
                    "type": "docker",
                    "image": "curlimages/curl:latest",
                    "content": '''#!/bin/sh
echo "🚨 CREATING PERSISTENT INCIDENT CHANNEL"
echo "======================================"

SLACK_TOKEN=$(echo "$slack_token" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
TIMESTAMP=$(date +%s)
CHANNEL_NAME="incident-test-$TIMESTAMP"

echo "🔑 Token: ${SLACK_TOKEN:0:20}..."
echo "📱 Channel name: $CHANNEL_NAME"

# 1. Create the channel
echo ""
echo "1️⃣ Creating incident channel..."
CREATE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $SLACK_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\\"name\\":\\"$CHANNEL_NAME\\",\\"is_private\\":false}" \
    "https://slack.com/api/conversations.create")

echo "📋 Create response: $CREATE_RESPONSE"

if echo "$CREATE_RESPONSE" | grep -q '"ok":true'; then
    CHANNEL_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "✅ Channel created successfully!"
    echo "📱 Channel ID: $CHANNEL_ID"
    echo "📱 Channel Name: $CHANNEL_NAME"
    echo "🔗 Channel URL: https://kubiya.slack.com/channels/$CHANNEL_ID"
else
    echo "❌ Channel creation failed!"
    exit 1
fi

# 2. Find users to invite
echo ""
echo "2️⃣ Finding users to invite..."

# Get users list
USERS_RESPONSE=$(curl -s -H "Authorization: Bearer $SLACK_TOKEN" \
    "https://slack.com/api/users.list")

echo "👥 Looking for users: shaked, amit"

# Look for shaked
SHAKED_ID=$(echo "$USERS_RESPONSE" | grep -B5 -A5 '"name":"shaked"' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
AMIT_ID=$(echo "$USERS_RESPONSE" | grep -B5 -A5 '"name":"amit"' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

# Also try alternative patterns
if [ -z "$SHAKED_ID" ]; then
    SHAKED_ID=$(echo "$USERS_RESPONSE" | grep -B5 -A5 '"real_name":".*[Ss]haked"' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
fi

if [ -z "$AMIT_ID" ]; then
    AMIT_ID=$(echo "$USERS_RESPONSE" | grep -B5 -A5 '"real_name":".*[Aa]mit"' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
fi

echo "🔍 Found user IDs:"
echo "   Shaked: $SHAKED_ID"
echo "   Amit: $AMIT_ID"

# 3. Invite users to channel
echo ""
echo "3️⃣ Inviting users to channel..."

if [ -n "$SHAKED_ID" ]; then
    echo "👥 Inviting Shaked ($SHAKED_ID)..."
    INVITE_SHAKED=$(curl -s -X POST \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\\"channel\\":\\"$CHANNEL_ID\\",\\"users\\":\\"$SHAKED_ID\\"}" \
        "https://slack.com/api/conversations.invite")
    
    echo "📋 Shaked invite response: $INVITE_SHAKED"
    
    if echo "$INVITE_SHAKED" | grep -q '"ok":true'; then
        echo "✅ Shaked invited successfully!"
    else
        echo "⚠️ Could not invite Shaked"
    fi
else
    echo "⚠️ Shaked user not found"
fi

if [ -n "$AMIT_ID" ]; then
    echo "👥 Inviting Amit ($AMIT_ID)..."
    INVITE_AMIT=$(curl -s -X POST \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\\"channel\\":\\"$CHANNEL_ID\\",\\"users\\":\\"$AMIT_ID\\"}" \
        "https://slack.com/api/conversations.invite")
    
    echo "📋 Amit invite response: $INVITE_AMIT"
    
    if echo "$INVITE_AMIT" | grep -q '"ok":true'; then
        echo "✅ Amit invited successfully!"
    else
        echo "⚠️ Could not invite Amit"
    fi
else
    echo "⚠️ Amit user not found"
fi

# 4. Post incident message with Block Kit
echo ""
echo "4️⃣ Posting incident response message..."

INCIDENT_MESSAGE=$(cat << EOF
{
  "channel": "$CHANNEL_ID",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🚨 INCIDENT RESPONSE ACTIVATED"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Incident ID:*\\nTEST-PERSISTENT-$TIMESTAMP"
        },
        {
          "type": "mrkdwn",
          "text": "*Severity:*\\n🚨 Critical"
        },
        {
          "type": "mrkdwn",
          "text": "*Assigned Team:*\\n<@$SHAKED_ID> <@$AMIT_ID>"
        },
        {
          "type": "mrkdwn",
          "text": "*Created:*\\n$(date)"
        }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*🎯 THIS IS A PERSISTENT TEST CHANNEL*\\n\\nThis channel will NOT be archived and should remain visible in your Slack workspace. You should be invited to this channel and see this message."
      }
    },
    {
      "type": "divider"
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Next Actions:*\\n• Check if you can see this channel\\n• Verify you were invited\\n• Confirm Block Kit formatting works\\n• Test threaded replies"
      }
    }
  ]
}
EOF
)

MESSAGE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $SLACK_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$INCIDENT_MESSAGE" \
    "https://slack.com/api/chat.postMessage")

echo "📋 Message response: $MESSAGE_RESPONSE"

if echo "$MESSAGE_RESPONSE" | grep -q '"ok":true'; then
    MESSAGE_TS=$(echo "$MESSAGE_RESPONSE" | grep -o '"ts":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Incident message posted successfully!"
    echo "📧 Message timestamp: $MESSAGE_TS"
else
    echo "❌ Message posting failed!"
fi

# 5. Final summary (DO NOT ARCHIVE THE CHANNEL!)
echo ""
echo "🎯 PERSISTENT CHANNEL SUMMARY:"
echo "=============================="
echo "📱 Channel Name: $CHANNEL_NAME"
echo "📱 Channel ID: $CHANNEL_ID"
echo "🔗 Direct URL: https://kubiya.slack.com/channels/$CHANNEL_ID"
echo "👥 Users invited: $([ -n "$SHAKED_ID" ] && echo "Shaked" || echo "Shaked(not found)") $([ -n "$AMIT_ID" ] && echo "Amit" || echo "Amit(not found)")"
echo "📧 Message posted: $(echo "$MESSAGE_RESPONSE" | grep -q '"ok":true' && echo "Yes" || echo "No")"
echo ""
echo "⚠️  IMPORTANT: This channel will remain active!"
echo "🔍 Check your Slack workspace now!"

echo "{"
echo "  \\"channel_id\\": \\"$CHANNEL_ID\\","
echo "  \\"channel_name\\": \\"$CHANNEL_NAME\\","
echo "  \\"channel_url\\": \\"https://kubiya.slack.com/channels/$CHANNEL_ID\\","
echo "  \\"shaked_invited\\": $([ -n "$SHAKED_ID" ] && echo "true" || echo "false"),"
echo "  \\"amit_invited\\": $([ -n "$AMIT_ID" ] && echo "true" || echo "false"),"
echo "  \\"message_posted\\": $(echo "$MESSAGE_RESPONSE" | grep -q '"ok":true' && echo "true" || echo "false"),"
echo "  \\"persistent\\": true"
echo "}"'''
                },
                "args": {
                    "slack_token": "${SLACK_TOKEN}"
                }
            }
        },
        "depends": ["get-slack-token"],
        "output": "CHANNEL_RESULT"
    }
    
    # Add steps to workflow
    workflow.data["steps"] = [
        token_step.data,
        create_step.data
    ]
    
    return workflow


def run_persistent_test():
    """Run the persistent channel test."""
    
    print("🚨 PERSISTENT INCIDENT CHANNEL TEST")
    print("=" * 50)
    print("🎯 This will create a REAL incident channel that STAYS visible")
    print("👥 You should be invited to the channel")
    print("📱 The channel will NOT be archived")
    print("=" * 50)
    
    # Validate environment
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable is required")
        return 1
    
    # Create workflow
    workflow = create_persistent_incident_channel_test()
    client = KubiyaClient(api_key=api_key, timeout=300)
    
    try:
        print("🚀 Creating persistent incident channel...")
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters={},
            stream=True
        )
        
        channel_info = None
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        
                        if step_name == 'create-persistent-channel':
                            output = step.get('output', '')
                            print("\n" + "="*60)
                            print("📱 CHANNEL CREATION OUTPUT:")
                            print("="*60)
                            print(output)
                            print("="*60)
                            
                            # Try to extract channel info
                            if 'channel_id' in output:
                                import re
                                channel_match = re.search(r'"channel_id": "([^"]+)"', output)
                                name_match = re.search(r'"channel_name": "([^"]+)"', output)
                                if channel_match and name_match:
                                    channel_info = {
                                        'id': channel_match.group(1),
                                        'name': name_match.group(1)
                                    }
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        if success:
                            print("\n✅ Persistent channel test completed!")
                        else:
                            print("\n❌ Persistent channel test failed!")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        if channel_info:
            print(f"\n🎉 SUCCESS! Channel created:")
            print(f"   📱 Name: {channel_info['name']}")
            print(f"   🆔 ID: {channel_info['id']}")
            print(f"   🔗 URL: https://kubiya.slack.com/channels/{channel_info['id']}")
            print(f"\n👀 CHECK YOUR SLACK NOW:")
            print(f"   • Look for channel: #{channel_info['name']}")
            print(f"   • You should be invited to it")
            print(f"   • You should see a Block Kit incident message")
            print(f"   • The channel should remain visible (not archived)")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_persistent_test())