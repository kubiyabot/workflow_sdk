#!/usr/bin/env python3
"""
Debug script to check Slack integration and test real channel creation.
"""

import os
import json
import requests

def debug_kubiya_slack_integration():
    """Debug the Kubiya Slack integration setup."""
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY not set")
        return
    
    print("🔍 Debugging Kubiya Slack Integration")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 1. Check Slack integrations
    print("1️⃣ Checking Slack integrations...")
    try:
        response = requests.get("https://api.kubiya.ai/api/v2/integrations/slack", headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Response received")
            print(f"   📋 Data: {json.dumps(data, indent=2)}")
            
            if isinstance(data, list) and len(data) > 0:
                integration = data[0]
                integration_uuid = integration.get('uuid')
                print(f"   🆔 Integration UUID: {integration_uuid}")
                
                # 2. Try to get token
                if integration_uuid:
                    print(f"\n2️⃣ Getting Slack token for UUID: {integration_uuid}")
                    token_url = f"https://api.kubiya.ai/api/v1/integration/slack/token/{integration_uuid}"
                    token_response = requests.get(token_url, headers=headers)
                    print(f"   Status: {token_response.status_code}")
                    
                    if token_response.status_code == 200:
                        token_data = token_response.json()
                        print(f"   ✅ Token response: {json.dumps(token_data, indent=2)}")
                        
                        slack_token = token_data.get('token')
                        if slack_token:
                            print(f"   🔑 Slack Token: {slack_token[:20]}...")
                            
                            # 3. Test Slack API
                            print(f"\n3️⃣ Testing Slack API with token...")
                            test_slack_api(slack_token)
                        else:
                            print(f"   ❌ No token in response")
                    else:
                        print(f"   ❌ Token request failed: {token_response.text}")
            else:
                print(f"   ⚠️ No integrations found or empty response")
        else:
            print(f"   ❌ Failed: {response.text}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_slack_api(token):
    """Test Slack API with the token."""
    
    slack_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test auth
    print("   🔍 Testing Slack auth...")
    try:
        auth_response = requests.get("https://slack.com/api/auth.test", headers=slack_headers)
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            if auth_data.get('ok'):
                print(f"   ✅ Auth successful!")
                print(f"   👤 User: {auth_data.get('user')}")
                print(f"   🏢 Team: {auth_data.get('team')}")
                print(f"   🤖 Bot: {auth_data.get('bot_id')}")
                
                # Test creating a channel
                print(f"\n   🏗️ Testing channel creation...")
                test_channel_creation(token)
            else:
                print(f"   ❌ Auth failed: {auth_data}")
        else:
            print(f"   ❌ Auth request failed: {auth_response.text}")
    except Exception as e:
        print(f"   ❌ Auth error: {e}")

def test_channel_creation(token):
    """Test creating a Slack channel."""
    
    slack_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Create test channel
    channel_name = f"test-incident-{int(time.time())}"
    create_data = {
        "name": channel_name,
        "is_private": False
    }
    
    try:
        create_response = requests.post(
            "https://slack.com/api/conversations.create",
            headers=slack_headers,
            json=create_data
        )
        
        if create_response.status_code == 200:
            create_result = create_response.json()
            if create_result.get('ok'):
                channel_id = create_result.get('channel', {}).get('id')
                print(f"   ✅ Channel created: {channel_id}")
                print(f"   📱 Channel name: {channel_name}")
                
                # Test posting a message
                print(f"   📨 Testing message posting...")
                test_message_posting(token, channel_id)
                
                # Clean up - archive the test channel
                print(f"   🗑️ Cleaning up test channel...")
                cleanup_channel(token, channel_id)
                
            else:
                print(f"   ❌ Channel creation failed: {create_result}")
        else:
            print(f"   ❌ Create request failed: {create_response.text}")
    except Exception as e:
        print(f"   ❌ Channel creation error: {e}")

def test_message_posting(token, channel_id):
    """Test posting a Block Kit message to the channel."""
    
    slack_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    message_data = {
        "channel": channel_id,
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🧪 TEST INCIDENT RESPONSE"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Test Message:* This is a test of the incident response workflow Block Kit integration!"
                }
            }
        ]
    }
    
    try:
        msg_response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=slack_headers,
            json=message_data
        )
        
        if msg_response.status_code == 200:
            msg_result = msg_response.json()
            if msg_result.get('ok'):
                print(f"   ✅ Message posted successfully!")
            else:
                print(f"   ❌ Message posting failed: {msg_result}")
        else:
            print(f"   ❌ Message request failed: {msg_response.text}")
    except Exception as e:
        print(f"   ❌ Message posting error: {e}")

def cleanup_channel(token, channel_id):
    """Archive the test channel."""
    
    slack_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        archive_response = requests.post(
            "https://slack.com/api/conversations.archive",
            headers=slack_headers,
            json={"channel": channel_id}
        )
        
        if archive_response.status_code == 200:
            archive_result = archive_response.json()
            if archive_result.get('ok'):
                print(f"   ✅ Test channel archived")
            else:
                print(f"   ⚠️ Archive failed: {archive_result}")
    except Exception as e:
        print(f"   ⚠️ Archive error: {e}")

if __name__ == "__main__":
    import time
    debug_kubiya_slack_integration()