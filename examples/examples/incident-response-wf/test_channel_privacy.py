#!/usr/bin/env python3
"""
Test channel privacy settings with public/private fallback.
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
from workflows.real_slack_incident_workflow import create_real_slack_incident_workflow


def test_channel_privacy_modes():
    """Test different channel privacy modes."""
    
    print("📱 SLACK CHANNEL PRIVACY TEST")
    print("=" * 40)
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY required")
        return 1
    
    # Test scenarios
    privacy_modes = [
        ("public", "Create public channel only"),
        ("private", "Create private channel only"), 
        ("auto", "Try public first, fallback to private")
    ]
    
    for privacy_mode, description in privacy_modes:
        print(f"\n🧪 Testing: {privacy_mode} mode")
        print(f"📋 Description: {description}")
        
        # Create test incident
        timestamp = int(time.time())
        incident_data = {
            "id": f"PRIVACY-TEST-{privacy_mode.upper()}-{timestamp}",
            "title": f"Channel Privacy Test - {privacy_mode.title()} Mode",
            "severity": "medium",
            "description": f"Testing {privacy_mode} channel creation with fallback"
        }
        
        test_params = {
            "incident_event": json.dumps(incident_data),
            "slack_users": "shaked@kubiya.ai",
            "create_real_channel": "true",
            "auto_assign": "true",
            "channel_privacy": privacy_mode
        }
        
        print(f"🔧 Privacy mode: {privacy_mode}")
        print(f"📋 Incident: {incident_data['id']}")
        
        # Execute workflow
        workflow = create_real_slack_incident_workflow()
        client = KubiyaClient(api_key=api_key, timeout=120)
        
        try:
            start_time = time.time()
            
            events = client.execute_workflow(
                workflow_definition=workflow.to_dict(),
                parameters=test_params,
                stream=True
            )
            
            war_room_output = ""
            for event in events:
                if isinstance(event, str) and event.strip():
                    try:
                        parsed = json.loads(event)
                        event_type = parsed.get('type', '')
                        
                        if 'step_complete' in event_type:
                            step = parsed.get('step', {})
                            step_name = step.get('name', '')
                            step_status = step.get('status', '')
                            
                            if step_name == 'create-war-room' and step_status == 'finished':
                                war_room_output = step.get('output', '')
                                # Extract creation status
                                if 'created_public' in war_room_output:
                                    print(f"  ✅ Public channel created successfully")
                                elif 'created_private' in war_room_output:
                                    print(f"  ✅ Private channel created successfully")
                                elif 'demo' in war_room_output:
                                    print(f"  📝 Demo mode (creation failed)")
                                else:
                                    print(f"  ⚠️ Unknown creation status")
                        
                        elif 'workflow_complete' in event_type:
                            duration = time.time() - start_time
                            success = parsed.get('success', False)
                            
                            if success:
                                print(f"  🎉 Completed in {duration:.1f}s")
                            else:
                                print(f"  ❌ Failed after {duration:.1f}s")
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            # Brief pause between tests
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
    
    print(f"\n📋 PRIVACY TEST SUMMARY:")
    print(f"✅ All privacy modes tested")
    print(f"🔧 Channel creation attempts made with fallback logic")
    print(f"📱 Check Slack workspace for any created channels")
    print(f"\n💡 Configuration options:")
    print(f"   • channel_privacy=public (public channels only)")
    print(f"   • channel_privacy=private (private channels only)")
    print(f"   • channel_privacy=auto (public→private fallback)")
    
    return 0


if __name__ == "__main__":
    sys.exit(test_channel_privacy_modes())