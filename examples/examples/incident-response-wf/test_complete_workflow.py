#!/usr/bin/env python3
"""
Complete end-to-end test of the incident response workflow with all fixes.
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


def run_complete_workflow_test():
    """Run the complete workflow test with all enhancements."""
    
    print("🚀 COMPLETE INCIDENT RESPONSE WORKFLOW TEST")
    print("=" * 60)
    print("🎯 Testing all fixes:")
    print("  ✅ Enhanced user resolution (email/display name)")
    print("  ✅ Real Slack channel creation")
    print("  ✅ User invitations")
    print("  ✅ Block Kit message templates")
    print("  ✅ Technical investigation")
    print("  ✅ Threaded updates")
    print("  ✅ Final summary")
    print("=" * 60)
    
    # Validate environment
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable is required")
        return 1
    
    # Create test incident
    timestamp = int(time.time())
    incident_event = {
        "id": f"E2E-TEST-{timestamp}",
        "title": "Complete End-to-End Test Incident",
        "severity": "critical",
        "description": "Testing all workflow components with real Slack integration"
    }
    
    test_params = {
        "incident_event": json.dumps(incident_event),
        "slack_users": "shaked@kubiya.ai,amit@example.com",  # Use emails for better resolution
        "create_real_channel": "true",
        "auto_assign": "true"
    }
    
    print(f"📋 Test Parameters:")
    print(f"  🆔 Incident ID: {incident_event['id']}")
    print(f"  📝 Title: {incident_event['title']}")
    print(f"  🚨 Severity: {incident_event['severity']}")
    print(f"  👥 Users: {test_params['slack_users']}")
    
    # Create workflow
    workflow = create_real_slack_incident_workflow()
    client = KubiyaClient(api_key=api_key, timeout=600)
    
    try:
        print(f"\n🚀 Starting complete workflow execution...")
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters=test_params,
            stream=True
        )
        
        print(f"📡 Processing events...")
        
        step_results = {}
        completed_steps = []
        failed_steps = []
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        step_status = step.get('status', '')
                        step_output = step.get('output', '')
                        
                        if step_status == 'completed':
                            print(f"  ✅ {step_name}")
                            completed_steps.append(step_name)
                            step_results[step_name] = step_output
                        elif step_status == 'failed':
                            error_msg = step.get('error', 'Unknown error')
                            print(f"  ❌ {step_name}: {error_msg}")
                            failed_steps.append((step_name, error_msg))
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        if success:
                            print(f"\n🎉 COMPLETE WORKFLOW TEST SUCCESSFUL!")
                        else:
                            print(f"\n❌ COMPLETE WORKFLOW TEST FAILED!")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # Detailed results analysis
        print(f"\n📊 DETAILED TEST RESULTS:")
        print(f"=" * 60)
        
        # Step 1: Incident parsing
        if 'parse-incident-event' in step_results:
            print(f"1️⃣ INCIDENT PARSING: ✅")
            incident_data = step_results['parse-incident-event']
            if incident_event['id'] in incident_data:
                print(f"   🆔 Incident ID correctly parsed")
        
        # Step 2: Slack token
        if 'setup-slack-integration' in step_results:
            print(f"2️⃣ SLACK INTEGRATION: ✅")
            token_data = step_results['setup-slack-integration']
            if 'token' in token_data:
                print(f"   🔑 Slack token retrieved successfully")
        
        # Step 3: User resolution (most important fix)
        if 'resolve-slack-users' in step_results:
            print(f"3️⃣ USER RESOLUTION: ✅")
            user_data = step_results['resolve-slack-users']
            print(f"   👥 User resolution data:")
            
            # Extract resolution details
            import re
            resolved_count_match = re.search(r'"resolved_count": (\d+)', user_data)
            user_mentions_match = re.search(r'"user_mentions": "([^"]*)"', user_data)
            
            if resolved_count_match:
                resolved_count = int(resolved_count_match.group(1))
                print(f"   📊 Users resolved: {resolved_count}")
                if resolved_count > 0:
                    print(f"   ✅ Enhanced resolution working!")
                else:
                    print(f"   ⚠️ No users resolved - may need investigation")
            
            if user_mentions_match:
                mentions = user_mentions_match.group(1)
                print(f"   💬 User mentions: {mentions}")
        
        # Step 4: War room creation
        if 'create-war-room' in step_results:
            print(f"4️⃣ WAR ROOM CREATION: ✅")
            war_room_data = step_results['create-war-room']
            
            channel_id_match = re.search(r'"channel_id": "([^"]+)"', war_room_data)
            channel_name_match = re.search(r'"channel_name": "([^"]+)"', war_room_data)
            creation_status_match = re.search(r'"creation_status": "([^"]+)"', war_room_data)
            
            if channel_id_match and channel_name_match:
                channel_id = channel_id_match.group(1)
                channel_name = channel_name_match.group(1)
                creation_status = creation_status_match.group(1) if creation_status_match else "unknown"
                
                print(f"   📱 Channel: #{channel_name} ({channel_id})")
                print(f"   🏗️ Status: {creation_status}")
                print(f"   🔗 URL: https://kubiya.slack.com/channels/{channel_id}")
                
                if creation_status in ['created', 'existing']:
                    print(f"   ✅ Real channel creation successful!")
                else:
                    print(f"   📝 Running in demo mode")
        
        # Step 5: Technical investigation
        if 'technical-investigation' in step_results:
            print(f"5️⃣ TECHNICAL INVESTIGATION: ✅")
            investigation_data = step_results['technical-investigation']
            
            confidence_match = re.search(r'"confidence_level": (\d+)', investigation_data)
            if confidence_match:
                confidence = int(confidence_match.group(1))
                print(f"   🔬 Investigation confidence: {confidence}%")
                if confidence >= 80:
                    print(f"   ✅ High confidence investigation!")
        
        # Step 6: Slack updates
        if 'update-slack-thread' in step_results:
            print(f"6️⃣ SLACK THREAD UPDATES: ✅")
            update_data = step_results['update-slack-thread']
            
            update_status_match = re.search(r'"update_status": "([^"]+)"', update_data)
            if update_status_match:
                update_status = update_status_match.group(1)
                print(f"   💬 Thread update status: {update_status}")
        
        # Step 7: Final summary
        if 'final-summary' in step_results:
            print(f"7️⃣ FINAL SUMMARY: ✅")
            summary_data = step_results['final-summary']
            
            success_score_match = re.search(r'"overall_success_score": (\d+)', summary_data)
            overall_status_match = re.search(r'"overall_status": "([^"]+)"', summary_data)
            
            if success_score_match and overall_status_match:
                success_score = int(success_score_match.group(1))
                overall_status = overall_status_match.group(1)
                print(f"   📊 Success score: {success_score}%")
                print(f"   🎯 Overall status: {overall_status}")
        
        # Summary
        print(f"\n🎯 TEST SUMMARY:")
        print(f"=" * 40)
        print(f"✅ Completed steps: {len(completed_steps)}")
        print(f"❌ Failed steps: {len(failed_steps)}")
        
        if completed_steps:
            print(f"\n✅ Successful steps:")
            for step in completed_steps:
                print(f"   • {step}")
        
        if failed_steps:
            print(f"\n❌ Failed steps:")
            for step, error in failed_steps:
                print(f"   • {step}: {error}")
        
        # Check your Slack workspace message
        if 'create-war-room' in step_results:
            war_room_data = step_results['create-war-room']
            channel_name_match = re.search(r'"channel_name": "([^"]+)"', war_room_data)
            if channel_name_match:
                channel_name = channel_name_match.group(1)
                print(f"\n👀 CHECK YOUR SLACK WORKSPACE:")
                print(f"   📱 Look for channel: #{channel_name}")
                print(f"   🎯 You should see a Block Kit incident message")
                print(f"   💬 Check for threaded investigation updates")
                print(f"   👥 Verify you were invited to the channel")
        
        return 0 if len(failed_steps) == 0 else 1
        
    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_complete_workflow_test())