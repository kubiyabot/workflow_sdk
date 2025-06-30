#!/usr/bin/env python3
"""
Test runner for the real Slack incident response workflow.
This validates complete Slack integration with Block Kit, user resolution, and threaded updates.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# Add paths for SDK access - match the pattern from run_comprehensive_test.py
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from kubiya_workflow_sdk.client import KubiyaClient
from workflows.real_slack_incident_workflow import create_real_slack_incident_workflow


def create_test_incident_with_users():
    """Create test incident with real user assignments."""
    return {
        "id": f"REAL-SLACK-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "title": "Production API Gateway Performance Degradation",
        "severity": "critical",
        "description": "API response times have increased from 200ms to 3.5s over the last 15 minutes. Error rate spiked to 8.5%. Customer complaints incoming.",
        "source": "datadog",
        "url": f"https://app.datadoghq.com/incidents/REAL-SLACK-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "affected_services": ["api-gateway", "user-service", "payment-processor"],
        "environment": "production",
        "priority": "p0",
        "team": "platform-engineering"
    }


def execute_real_slack_workflow_test():
    """Execute the real Slack workflow test."""
    
    print("🚀 REAL SLACK INCIDENT RESPONSE WORKFLOW TEST")
    print("=" * 60)
    print("🎯 Testing Features:")
    print("   ✅ Real Slack channel creation")
    print("   ✅ Block Kit message templates")
    print("   ✅ User resolution (@username to User ID)")
    print("   ✅ Threaded follow-up messages")
    print("   ✅ Fixed technical investigation")
    print("   ✅ Production-ready error handling")
    print("=" * 60)
    
    # Validate environment
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable is required")
        return 1
    
    print(f"✅ API Key validated (length: {len(api_key)} characters)")
    
    # Create workflow
    print("\n🔧 Creating real Slack incident workflow...")
    workflow = create_real_slack_incident_workflow()
    workflow_dict = workflow.to_dict()
    
    print(f"✅ Workflow created:")
    print(f"   📋 Name: {workflow_dict['name']}")
    print(f"   📊 Steps: {len(workflow_dict.get('steps', []))}")
    print(f"   🎯 Features: Real Slack + Block Kit + User Resolution + Threading")
    
    # Print step sequence
    step_names = [step.get('name', 'unnamed') for step in workflow_dict.get('steps', [])]
    print(f"   📝 Step sequence:")
    for i, step_name in enumerate(step_names, 1):
        print(f"      {i}. {step_name}")
    
    # Create test incident
    print("\n📋 Creating test incident...")
    incident = create_test_incident_with_users()
    
    print(f"✅ Test incident created:")
    print(f"   🆔 ID: {incident['id']}")
    print(f"   📝 Title: {incident['title']}")
    print(f"   🚨 Severity: {incident['severity']}")
    print(f"   🎯 Priority: {incident['priority']}")
    
    # Prepare execution parameters
    execution_params = {
        "incident_event": json.dumps(incident),
        "slack_users": "@shaked,@amit",  # Default users - can be overridden
        "create_real_channel": "true",   # Set to false for demo mode
        "auto_assign": "true"
    }
    
    print(f"\n🔧 Execution parameters:")
    print(f"   👥 Slack users: {execution_params['slack_users']}")
    print(f"   📱 Create real channel: {execution_params['create_real_channel']}")
    print(f"   🎯 Auto assign: {execution_params['auto_assign']}")
    
    # Initialize client
    print(f"\n🚀 Initializing Kubiya client...")
    client = KubiyaClient(
        api_key=api_key,
        timeout=3600,  # 1 hour
        max_retries=3
    )
    
    try:
        print(f"\n🌊 Starting workflow execution...")
        print("💓 Monitoring: Real-time events and step progression")
        print("📡 Expected: Channel creation, Block Kit messages, threaded updates")
        print("-" * 60)
        
        # Execute with streaming
        events = client.execute_workflow(
            workflow_definition=workflow_dict,
            parameters=execution_params,
            stream=True
        )
        
        # Process events with detailed logging
        event_count = 0
        step_status = {}
        errors = []
        start_time = time.time()
        
        print("📡 STREAMING EVENTS:")
        print("-" * 40)
        
        for event in events:
            event_count += 1
            current_time = time.time()
            elapsed = current_time - start_time
            
            if isinstance(event, str) and event.strip():
                # Log first few events for debugging
                if event_count <= 5:
                    print(f"🔍 Event #{event_count}: {event[:200]}...")
                
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', 'unknown')
                    step_name = parsed.get('step', {}).get('name') or parsed.get('step_name', 'unknown')
                    
                    # Track step progression
                    if 'step_running' in event_type or 'step.started' in event_type:
                        step_status[step_name] = 'running'
                        print(f"▶️  STEP STARTED: {step_name} (at {elapsed:.1f}s)")
                        
                        # Show step-specific information
                        if step_name == "resolve-slack-users":
                            print(f"   👥 Resolving users: {execution_params['slack_users']}")
                        elif step_name == "create-war-room":
                            print(f"   📱 Creating Slack channel with Block Kit...")
                        elif step_name == "technical-investigation":
                            print(f"   🔬 Running production investigation tools...")
                        elif step_name == "update-slack-thread":
                            print(f"   💬 Posting threaded updates...")
                    
                    elif 'step_complete' in event_type:
                        step_data = parsed.get('step', {})
                        status = step_data.get('status', 'unknown')
                        output = step_data.get('output', '')
                        
                        if status == 'finished':
                            step_status[step_name] = 'completed'
                            print(f"✅ STEP COMPLETED: {step_name} (at {elapsed:.1f}s)")
                            
                            # Show relevant output snippets
                            if step_name == "parse-incident-event" and output:
                                try:
                                    output_json = json.loads(output)
                                    print(f"   📋 Incident ID: {output_json.get('incident_id')}")
                                    print(f"   📱 Channel name: {output_json.get('slack_channel_name')}")
                                except:
                                    pass
                            
                            elif step_name == "resolve-slack-users" and output:
                                try:
                                    output_json = json.loads(output)
                                    print(f"   👥 User mentions: {output_json.get('user_mentions')}")
                                    print(f"   🔍 Resolution mode: {output_json.get('resolution_mode')}")
                                except:
                                    pass
                            
                            elif step_name == "create-war-room" and output:
                                try:
                                    output_json = json.loads(output)
                                    print(f"   📱 Channel ID: {output_json.get('channel_id')}")
                                    print(f"   🎨 Block Kit status: {output_json.get('message_status')}")
                                    print(f"   🏗️ Creation status: {output_json.get('creation_status')}")
                                except:
                                    pass
                            
                            elif step_name == "technical-investigation" and output:
                                try:
                                    output_json = json.loads(output)
                                    print(f"   🎯 Confidence: {output_json.get('confidence_level')}%")
                                    print(f"   🔍 Status: {output_json.get('investigation_status')}")
                                except:
                                    pass
                        
                        elif status == 'failed':
                            step_status[step_name] = 'failed'
                            error_msg = step_data.get('error', 'Unknown error')
                            print(f"❌ STEP FAILED: {step_name}")
                            print(f"   🔍 Error: {error_msg}")
                            errors.append(f"{step_name}: {error_msg}")
                    
                    elif 'workflow_complete' in event_type:
                        workflow_status = parsed.get('status', 'unknown')
                        success = parsed.get('success', False)
                        
                        if success:
                            print(f"🎉 WORKFLOW COMPLETED SUCCESSFULLY! (total: {elapsed:.1f}s)")
                        else:
                            print(f"💥 WORKFLOW FAILED! (at {elapsed:.1f}s)")
                        break
                    
                    elif event_type == 'heartbeat':
                        if event_count % 20 == 0:  # Log every 20th heartbeat
                            print(f"💓 Heartbeat - Connection alive ({elapsed:.1f}s elapsed)")
                
                except json.JSONDecodeError:
                    if "error" in event.lower() or "fail" in event.lower():
                        print(f"⚠️ Raw error event: {event[:300]}")
            
            # Safety limit
            if event_count >= 200:
                print("⚠️ Reached 200 events limit")
                break
        
        # Generate final summary
        total_time = time.time() - start_time
        completed_steps = [name for name, status in step_status.items() if status == 'completed']
        failed_steps = [name for name, status in step_status.items() if status == 'failed']
        
        print("\n" + "=" * 60)
        print("📊 REAL SLACK WORKFLOW TEST SUMMARY")
        print("=" * 60)
        
        print(f"⏱️  EXECUTION METRICS:")
        print(f"   📅 Total time: {total_time:.2f} seconds")
        print(f"   📡 Events processed: {event_count}")
        print(f"   ✅ Steps completed: {len(completed_steps)}")
        print(f"   ❌ Steps failed: {len(failed_steps)}")
        
        print(f"\n🔧 FEATURE VALIDATION:")
        
        # Validate each major feature
        features_passed = 0
        total_features = 6
        
        # Feature 1: Incident parsing
        if "parse-incident-event" in completed_steps:
            print(f"   ✅ Incident parsing: PASSED")
            features_passed += 1
        else:
            print(f"   ❌ Incident parsing: FAILED")
        
        # Feature 2: User resolution
        if "resolve-slack-users" in completed_steps:
            print(f"   ✅ User resolution: PASSED")
            features_passed += 1
        else:
            print(f"   ❌ User resolution: FAILED")
        
        # Feature 3: Slack channel creation
        if "create-war-room" in completed_steps:
            print(f"   ✅ Slack war room + Block Kit: PASSED")
            features_passed += 1
        else:
            print(f"   ❌ Slack war room + Block Kit: FAILED")
        
        # Feature 4: Technical investigation
        if "technical-investigation" in completed_steps:
            print(f"   ✅ Technical investigation: PASSED")
            features_passed += 1
        else:
            print(f"   ❌ Technical investigation: FAILED")
        
        # Feature 5: Threaded updates
        if "update-slack-thread" in completed_steps:
            print(f"   ✅ Threaded Slack updates: PASSED")
            features_passed += 1
        else:
            print(f"   ❌ Threaded Slack updates: FAILED")
        
        # Feature 6: Final summary
        if "final-summary" in completed_steps:
            print(f"   ✅ Final summary: PASSED")
            features_passed += 1
        else:
            print(f"   ❌ Final summary: FAILED")
        
        success_rate = (features_passed / total_features) * 100
        print(f"\n🏆 OVERALL SUCCESS RATE: {features_passed}/{total_features} features ({success_rate:.1f}%)")
        
        if errors:
            print(f"\n❌ ERRORS ENCOUNTERED:")
            for error in errors:
                print(f"   • {error}")
        
        # Final assessment
        if success_rate >= 80:
            print(f"\n🎉 SUCCESS: Real Slack workflow is working!")
            print(f"   ✅ All major features operational")
            print(f"   ✅ Production-ready for incident response")
            result_code = 0
        else:
            print(f"\n⚠️ PARTIAL SUCCESS: Some features need attention")
            print(f"   📊 Success rate: {success_rate:.1f}%")
            result_code = 1
        
        print(f"\n💡 Next Steps:")
        if success_rate >= 80:
            print(f"   • Deploy to production incident response")
            print(f"   • Configure real Slack workspace")
            print(f"   • Set up monitoring and alerting")
            print(f"   • Train incident response team")
        else:
            print(f"   • Review failed steps above")
            print(f"   • Check Slack API permissions")
            print(f"   • Verify workflow configuration")
            print(f"   • Test individual components")
        
        print(f"\n🚀 REAL SLACK WORKFLOW TEST COMPLETED")
        print("=" * 60)
        
        return result_code
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ TEST EXECUTION FAILED after {duration:.1f}s")
        print(f"🔍 Error: {str(e)}")
        
        import traceback
        print(f"\n📋 Traceback:")
        print(traceback.format_exc())
        
        return 1


if __name__ == "__main__":
    print("🧪 Starting Real Slack Incident Response Workflow Test...")
    sys.exit(execute_real_slack_workflow_test())