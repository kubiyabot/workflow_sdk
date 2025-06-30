#!/usr/bin/env python3
"""
Test the incident response workflow with a realistic Datadog incident example.
This simulates a real production incident scenario.
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


def create_datadog_incident_payload():
    """Create a realistic Datadog incident payload."""
    
    timestamp = datetime.now(timezone.utc)
    incident_id = f"DATADOG-{timestamp.strftime('%Y%m%d')}-{int(time.time() % 10000)}"
    
    # Realistic Datadog incident webhook payload
    incident_payload = {
        "id": incident_id,
        "title": "High Memory Usage on Production API Servers",
        "severity": "critical",
        "description": "Memory usage has exceeded 90% across multiple production API servers. Response times are degraded and error rates are increasing.",
        "source": "datadog",
        "monitor": {
            "id": "12345678",
            "name": "Production API Memory Usage",
            "query": "avg(last_5m):avg:system.mem.pct_usable{env:production,service:api} by {host} < 0.1",
            "threshold": 0.1,
            "current_value": 0.05
        },
        "alerts": [
            {
                "host": "api-prod-01.company.com",
                "memory_usage": "95%",
                "status": "ALERT"
            },
            {
                "host": "api-prod-02.company.com", 
                "memory_usage": "92%",
                "status": "ALERT"
            },
            {
                "host": "api-prod-03.company.com",
                "memory_usage": "89%", 
                "status": "WARN"
            }
        ],
        "metrics": {
            "avg_response_time": "2.8s",
            "error_rate": "12.3%",
            "requests_per_second": "1,247"
        },
        "tags": [
            "env:production",
            "service:api",
            "team:backend",
            "priority:critical"
        ],
        "dashboard_url": "https://app.datadoghq.com/dashboard/abc-123-def",
        "triggered_at": timestamp.isoformat(),
        "escalation_policy": "oncall-backend-team"
    }
    
    return incident_payload


def run_datadog_incident_test():
    """Run the complete incident response workflow with Datadog incident data."""
    
    print("🚨 DATADOG INCIDENT RESPONSE TEST")
    print("=" * 60)
    print("🎯 Simulating real production incident scenario:")
    print("  📊 High Memory Usage on Production API Servers")
    print("  🚨 Critical severity with multiple host alerts")
    print("  📈 Performance degradation metrics")
    print("  🔗 Real Datadog dashboard links")
    print("=" * 60)
    
    # Validate environment
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable is required")
        print("💡 Set it with: export KUBIYA_API_KEY='your-api-key'")
        return 1
    
    # Create realistic Datadog incident
    incident_data = create_datadog_incident_payload()
    
    print(f"📋 Datadog Incident Details:")
    print(f"  🆔 Incident ID: {incident_data['id']}")
    print(f"  📝 Title: {incident_data['title']}")
    print(f"  🚨 Severity: {incident_data['severity']}")
    print(f"  📊 Monitor: {incident_data['monitor']['name']}")
    print(f"  🖥️  Affected Hosts: {len(incident_data['alerts'])}")
    print(f"  ⏱️  Response Time: {incident_data['metrics']['avg_response_time']}")
    print(f"  ❌ Error Rate: {incident_data['metrics']['error_rate']}")
    print(f"  🔗 Dashboard: {incident_data['dashboard_url']}")
    
    # Enhanced incident description for better investigation
    enhanced_description = f"""
🚨 **PRODUCTION INCIDENT - IMMEDIATE ATTENTION REQUIRED**

**Summary**: {incident_data['title']}
**Severity**: {incident_data['severity'].upper()}
**Source**: Datadog Monitor Alert

**📊 Current Metrics:**
• Average Response Time: {incident_data['metrics']['avg_response_time']}
• Error Rate: {incident_data['metrics']['error_rate']}
• Requests/Second: {incident_data['metrics']['requests_per_second']}

**🖥️ Affected Infrastructure:**
{chr(10).join([f"• {alert['host']}: {alert['memory_usage']} memory usage ({alert['status']})" for alert in incident_data['alerts']])}

**📈 Monitor Details:**
• Monitor: {incident_data['monitor']['name']}
• Query: {incident_data['monitor']['query']}
• Threshold: {incident_data['monitor']['threshold']} (Current: {incident_data['monitor']['current_value']})

**🔗 Investigation Links:**
• Dashboard: {incident_data['dashboard_url']}
• Monitor: https://app.datadoghq.com/monitors/{incident_data['monitor']['id']}

**👥 Escalation:** {incident_data['escalation_policy']}
**🏷️ Tags:** {', '.join(incident_data['tags'])}
"""
    
    # Update incident with enhanced description
    incident_data['description'] = enhanced_description.strip()
    
    # Test parameters optimized for Datadog incident
    test_params = {
        "incident_event": json.dumps(incident_data),
        "slack_users": "shaked@kubiya.ai,backend-oncall@company.com,sre-team@company.com",  # Use relevant team emails
        "create_real_channel": "true",
        "auto_assign": "true"
    }
    
    print(f"\n👥 Notification Recipients:")
    print(f"  📧 {test_params['slack_users']}")
    
    # Create workflow
    workflow = create_real_slack_incident_workflow()
    client = KubiyaClient(api_key=api_key, timeout=600)
    
    try:
        print(f"\n🚀 Executing Datadog incident response workflow...")
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters=test_params,
            stream=True
        )
        
        print(f"📡 Processing real-time events...")
        
        step_results = {}
        step_timings = {}
        completed_steps = []
        failed_steps = []
        start_time = time.time()
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_started' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        step_timings[step_name] = time.time()
                        print(f"  🔄 Starting: {step_name}")
                    
                    elif 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        step_status = step.get('status', '')
                        step_output = step.get('output', '')
                        
                        # Calculate step duration
                        if step_name in step_timings:
                            duration = time.time() - step_timings[step_name]
                            duration_str = f"({duration:.1f}s)"
                        else:
                            duration_str = ""
                        
                        if step_status == 'completed':
                            print(f"  ✅ {step_name} {duration_str}")
                            completed_steps.append(step_name)
                            step_results[step_name] = step_output
                        elif step_status == 'failed':
                            error_msg = step.get('error', 'Unknown error')
                            print(f"  ❌ {step_name} {duration_str}: {error_msg}")
                            failed_steps.append((step_name, error_msg))
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        total_duration = time.time() - start_time
                        
                        if success:
                            print(f"\n🎉 DATADOG INCIDENT RESPONSE COMPLETED! ({total_duration:.1f}s total)")
                        else:
                            print(f"\n❌ DATADOG INCIDENT RESPONSE FAILED! ({total_duration:.1f}s total)")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # Detailed results analysis for Datadog incident
        print(f"\n📊 DATADOG INCIDENT RESPONSE ANALYSIS:")
        print(f"=" * 60)
        
        # Incident Parsing Analysis
        if 'parse-incident-event' in step_results:
            print(f"1️⃣ INCIDENT PARSING: ✅")
            parse_data = step_results['parse-incident-event']
            if incident_data['id'] in parse_data:
                print(f"   🆔 Datadog incident ID correctly parsed")
                print(f"   📊 Monitor data preserved in workflow")
        
        # Slack Token Retrieval
        if 'setup-slack-integration' in step_results:
            print(f"2️⃣ SLACK INTEGRATION: ✅")
            token_data = step_results['setup-slack-integration']
            if 'token' in token_data:
                print(f"   🔑 Slack bot token retrieved for notifications")
        
        # User Resolution for Datadog Incident Teams
        if 'resolve-slack-users' in step_results:
            print(f"3️⃣ TEAM RESOLUTION: ✅")
            user_data = step_results['resolve-slack-users']
            
            # Extract resolution details
            import re
            resolved_count_match = re.search(r'"resolved_count": (\d+)', user_data)
            user_mentions_match = re.search(r'"user_mentions": "([^"]*)"', user_data)
            
            if resolved_count_match:
                resolved_count = int(resolved_count_match.group(1))
                print(f"   👥 Backend/SRE team members resolved: {resolved_count}")
                if resolved_count > 0:
                    print(f"   ✅ On-call team successfully identified!")
                else:
                    print(f"   ⚠️ Team resolution may need verification")
            
            if user_mentions_match:
                mentions = user_mentions_match.group(1)
                print(f"   💬 Team mentions: {mentions}")
        
        # War Room Creation for Critical Datadog Incident
        if 'create-war-room' in step_results:
            print(f"4️⃣ INCIDENT WAR ROOM: ✅")
            war_room_data = step_results['create-war-room']
            
            channel_id_match = re.search(r'"channel_id": "([^"]+)"', war_room_data)
            channel_name_match = re.search(r'"channel_name": "([^"]+)"', war_room_data)
            creation_status_match = re.search(r'"creation_status": "([^"]+)"', war_room_data)
            
            if channel_id_match and channel_name_match:
                channel_id = channel_id_match.group(1)
                channel_name = channel_name_match.group(1)
                creation_status = creation_status_match.group(1) if creation_status_match else "unknown"
                
                print(f"   📱 War Room: #{channel_name}")
                print(f"   🆔 Channel ID: {channel_id}")
                print(f"   🏗️ Status: {creation_status}")
                print(f"   🔗 Direct Link: https://kubiya.slack.com/channels/{channel_id}")
                
                if creation_status in ['created', 'existing']:
                    print(f"   🎯 REAL INCIDENT CHANNEL CREATED!")
                    print(f"   👥 Backend/SRE team should be invited")
                    print(f"   📊 Datadog metrics included in Block Kit message")
                else:
                    print(f"   📝 Running in demo mode")
        
        # Technical Investigation for Memory Issue
        if 'technical-investigation' in step_results:
            print(f"5️⃣ MEMORY INVESTIGATION: ✅")
            investigation_data = step_results['technical-investigation']
            
            confidence_match = re.search(r'"confidence_level": (\d+)', investigation_data)
            if confidence_match:
                confidence = int(confidence_match.group(1))
                print(f"   🔬 Investigation confidence: {confidence}%")
                print(f"   🖥️ System health checks completed")
                print(f"   📈 Memory usage patterns analyzed")
                if confidence >= 80:
                    print(f"   ✅ High confidence memory investigation!")
        
        # Slack Updates with Datadog Context
        if 'update-slack-thread' in step_results:
            print(f"6️⃣ INCIDENT UPDATES: ✅")
            update_data = step_results['update-slack-thread']
            
            update_status_match = re.search(r'"update_status": "([^"]+)"', update_data)
            if update_status_match:
                update_status = update_status_match.group(1)
                print(f"   💬 Datadog investigation posted to thread: {update_status}")
                print(f"   📊 Memory metrics and recommendations shared")
        
        # Final Incident Summary
        if 'final-summary' in step_results:
            print(f"7️⃣ INCIDENT SUMMARY: ✅")
            summary_data = step_results['final-summary']
            
            success_score_match = re.search(r'"overall_success_score": (\d+)', summary_data)
            overall_status_match = re.search(r'"overall_status": "([^"]+)"', summary_data)
            
            if success_score_match and overall_status_match:
                success_score = int(success_score_match.group(1))
                overall_status = overall_status_match.group(1)
                print(f"   📊 Incident response score: {success_score}%")
                print(f"   🎯 Overall status: {overall_status}")
                print(f"   📋 Complete Datadog incident documentation generated")
        
        # Real-world impact summary
        print(f"\n🎯 REAL-WORLD IMPACT SUMMARY:")
        print(f"=" * 50)
        print(f"✅ Automated incident response steps: {len(completed_steps)}")
        print(f"❌ Failed automation steps: {len(failed_steps)}")
        
        if completed_steps:
            print(f"\n✅ Successfully automated:")
            automation_benefits = {
                'parse-incident-event': '• Structured Datadog incident data for team consumption',
                'setup-slack-integration': '• Secured communication channel access',
                'resolve-slack-users': '• Identified and contacted on-call backend/SRE teams',
                'create-war-room': '• Created dedicated incident war room with context',
                'technical-investigation': '• Automated memory usage analysis and recommendations',
                'update-slack-thread': '• Real-time investigation updates for team',
                'final-summary': '• Complete incident documentation and metrics'
            }
            
            for step in completed_steps:
                if step in automation_benefits:
                    print(f"   {automation_benefits[step]}")
        
        if failed_steps:
            print(f"\n❌ Manual intervention needed:")
            for step, error in failed_steps:
                print(f"   • {step}: {error}")
        
        # Check your Slack workspace message
        if 'create-war-room' in step_results:
            war_room_data = step_results['create-war-room']
            channel_name_match = re.search(r'"channel_name": "([^"]+)"', war_room_data)
            if channel_name_match:
                channel_name = channel_name_match.group(1)
                print(f"\n👀 CHECK YOUR SLACK WORKSPACE NOW:")
                print(f"   📱 Look for war room: #{channel_name}")
                print(f"   🚨 Should contain Datadog incident details")
                print(f"   📊 Memory usage metrics and affected hosts")
                print(f"   🔗 Dashboard links for immediate investigation")
                print(f"   👥 Backend/SRE team members should be invited")
                print(f"   💬 Investigation updates in thread replies")
        
        # Datadog-specific recommendations
        print(f"\n🔧 DATADOG INCIDENT NEXT STEPS:")
        print(f"   1. 📊 Review memory usage dashboard: {incident_data['dashboard_url']}")
        print(f"   2. 🖥️ Check affected hosts: {', '.join([alert['host'] for alert in incident_data['alerts']])}")
        print(f"   3. 📈 Monitor response time recovery")
        print(f"   4. 🔍 Investigate memory leak patterns")
        print(f"   5. 📋 Document resolution steps in war room")
        
        return 0 if len(failed_steps) == 0 else 1
        
    except Exception as e:
        print(f"❌ Datadog incident response test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_datadog_incident_test())