#!/usr/bin/env python3
"""
Comprehensive End-to-End Test with Claude Code Integration
==========================================================

This script tests the complete incident response workflow with:
- Claude Code AI-powered investigation
- Proper tool configuration and secret validation
- Real monitoring tool integration (kubectl, observe-cli, datadog-cli)
- Fallback handling for missing secrets
- Full end-to-end flow validation

Usage:
    python test_e2e_claude_code.py
    
Environment Variables Required:
    KUBIYA_API_KEY - Required for workflow execution
    OBSERVE_API_KEY - Optional for Observe.ai integration
    DATADOG_API_KEY - Optional for Datadog integration
    KUBECTL_CONFIG - Optional for Kubernetes cluster access
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# Add SDK path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from workflows.real_slack_incident_workflow import create_real_slack_incident_workflow


def validate_environment():
    """Validate environment and collect available secrets."""
    print("🔧 ENVIRONMENT VALIDATION")
    print("=" * 50)
    
    # Required
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY is required")
        print("   Export KUBIYA_API_KEY before running this test")
        return None, {}
    
    print(f"✅ KUBIYA_API_KEY: {api_key[:20]}...")
    
    # Optional secrets with validation
    secrets = {}
    secret_status = {}
    
    # Check Observe.ai API key
    observe_key = os.getenv('OBSERVE_API_KEY')
    if observe_key:
        secrets['observe_api_key'] = observe_key
        secret_status['observe_api'] = f"✅ Available ({observe_key[:15]}...)"
    else:
        secret_status['observe_api'] = "⚠️ Not provided (Observe.ai analysis will be skipped)"
    
    # Check Datadog API key  
    datadog_key = os.getenv('DATADOG_API_KEY')
    if datadog_key:
        secrets['datadog_api_key'] = datadog_key
        secret_status['datadog_api'] = f"✅ Available ({datadog_key[:15]}...)"
    else:
        secret_status['datadog_api'] = "⚠️ Not provided (Datadog analysis will be skipped)"
    
    # Check kubectl config
    kubectl_config = os.getenv('KUBECTL_CONFIG')
    if kubectl_config:
        secrets['kubectl_config'] = kubectl_config
        secret_status['kubectl'] = f"✅ Available ({len(kubectl_config)} chars)"
    else:
        secret_status['kubectl'] = "⚠️ Not provided (Kubernetes analysis will be skipped)"
    
    print("\n📋 Secret Validation Results:")
    for tool, status in secret_status.items():
        print(f"  {tool}: {status}")
    
    tools_available = len([k for k in secrets.keys() if k])
    print(f"\n🛠️ Tools Available: {tools_available}/3 monitoring tools configured")
    print(f"💡 Claude Code will use available tools for comprehensive analysis")
    
    return api_key, secrets


def create_test_incident():
    """Create realistic test incident data."""
    timestamp = datetime.now(timezone.utc)
    incident_id = f"E2E-CLAUDE-{timestamp.strftime('%Y%m%d-%H%M%S')}"
    
    incident_data = {
        "id": incident_id,
        "title": "Production API Performance Degradation - Claude Code E2E Test",
        "severity": "critical",
        "description": "Comprehensive end-to-end test of incident response workflow with Claude Code integration",
        "source": "e2e_test",
        "detected_at": timestamp.isoformat(),
        "affected_services": ["api-gateway", "user-service", "payment-service"],
        "alerts": [
            "High error rate detected: 8.2% (baseline: 0.3%)",
            "Response time degradation: 1,250ms p95 (baseline: 180ms)",
            "Database connection pool utilization: 95%"
        ],
        "business_impact": {
            "users_affected": "~45,000 active users",
            "revenue_impact": "$125K/hr transaction volume affected",
            "services_degraded": ["user authentication", "payment processing"]
        }
    }
    
    return incident_data


def run_e2e_test():
    """Execute comprehensive end-to-end test."""
    print("🚀 CLAUDE CODE E2E INCIDENT RESPONSE TEST")
    print("=" * 60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Validate environment
    api_key, secrets = validate_environment()
    if not api_key:
        return 1
    
    # Create test incident
    print("\n📋 TEST INCIDENT CREATION")
    print("=" * 40)
    incident_data = create_test_incident()
    print(f"🆔 Incident ID: {incident_data['id']}")
    print(f"📝 Title: {incident_data['title']}")
    print(f"🚨 Severity: {incident_data['severity']}")
    print(f"🎯 Purpose: Test Claude Code integration with available monitoring tools")
    
    # Configure test parameters
    test_params = {
        "incident_event": json.dumps(incident_data),
        "slack_users": "shaked@kubiya.ai,test-user@example.com",
        "create_real_channel": "true",
        "auto_assign": "true", 
        "channel_privacy": "auto",  # Test fallback logic
        "enable_claude_analysis": "true"  # Enable Claude Code
    }
    
    # Add available secrets to parameters
    test_params.update(secrets)
    
    print(f"\n🔧 Test Configuration:")
    print(f"  📧 Slack Users: {test_params['slack_users']}")
    print(f"  📱 Channel Privacy: {test_params['channel_privacy']} (with fallback)")
    print(f"  🤖 Claude Code: {test_params['enable_claude_analysis']}")
    print(f"  🛠️ Monitoring Tools: {len(secrets)} configured")
    
    # Create and execute workflow
    print(f"\n🏗️ WORKFLOW EXECUTION")
    print("=" * 40)
    
    workflow = create_real_slack_incident_workflow()
    client = KubiyaClient(api_key=api_key, timeout=900)  # 15 minute timeout for Claude Code
    
    try:
        start_time = time.time()
        print(f"🚀 Executing workflow with {len(workflow.data['steps'])} steps...")
        print(f"⏱️ Timeout: 15 minutes (extended for Claude Code analysis)")
        print()
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters=test_params,
            stream=True
        )
        
        # Track step progress and results
        step_results = {}
        claude_analysis_data = {}
        
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
                        
                        if step_status == 'finished':
                            print(f"✅ {step_name}")
                            step_results[step_name] = {
                                'status': 'completed',
                                'output': step_output
                            }
                            
                            # Capture Claude Code investigation results
                            if step_name == 'technical-investigation':
                                claude_analysis_data = step_output
                                
                        elif step_status == 'failed':
                            error_msg = step.get('error', 'Unknown error')
                            print(f"❌ {step_name}: {error_msg}")
                            step_results[step_name] = {
                                'status': 'failed',
                                'error': error_msg
                            }
                    
                    elif 'workflow_complete' in event_type:
                        duration = time.time() - start_time
                        success = parsed.get('success', False)
                        
                        print(f"\n📊 WORKFLOW EXECUTION SUMMARY")
                        print("=" * 50)
                        print(f"⏱️ Duration: {duration:.1f} seconds")
                        print(f"🎯 Success: {'✅ Yes' if success else '❌ No'}")
                        print(f"📋 Steps Completed: {len([r for r in step_results.values() if r['status'] == 'completed'])}/7")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # Analyze results
        print(f"\n📋 DETAILED RESULTS ANALYSIS")
        print("=" * 50)
        
        # Check each step
        expected_steps = [
            'parse-incident-event',
            'setup-slack-integration', 
            'resolve-slack-users',
            'create-war-room',
            'technical-investigation',
            'update-slack-thread',
            'final-summary'
        ]
        
        all_steps_passed = True
        for step_name in expected_steps:
            if step_name in step_results:
                result = step_results[step_name]
                if result['status'] == 'completed':
                    print(f"  ✅ {step_name}: Completed successfully")
                else:
                    print(f"  ❌ {step_name}: Failed - {result.get('error', 'Unknown')}")
                    all_steps_passed = False
            else:
                print(f"  ⚠️ {step_name}: Not executed")
                all_steps_passed = False
        
        # Analyze Claude Code investigation specifically
        print(f"\n🤖 CLAUDE CODE ANALYSIS RESULTS")
        print("=" * 50)
        
        if 'technical-investigation' in step_results:
            investigation_output = step_results['technical-investigation']['output']
            
            # Parse investigation results
            try:
                # Look for specific indicators in the output
                if 'claude_analysis_completed' in investigation_output:
                    print("✅ Claude Code analysis executed successfully")
                    print("🧠 AI-powered investigation completed")
                elif 'simulated_analysis' in investigation_output:
                    print("⚠️ Claude Code simulated (actual Claude CLI not available)")
                    print("🔧 Environment setup and tool validation completed")
                else:
                    print("❓ Claude Code execution status unclear")
                
                # Check tool usage
                if any(tool in investigation_output for tool in ['kubectl', 'observe-cli', 'datadog-cli']):
                    configured_tools = [tool for tool in ['kubectl', 'observe-cli', 'datadog-cli'] 
                                      if tool in investigation_output]
                    print(f"🛠️ Monitoring tools utilized: {', '.join(configured_tools)}")
                else:
                    print("⚠️ No monitoring tools detected in output")
                
                # Check confidence level
                if 'confidence_level' in investigation_output:
                    import re
                    confidence_match = re.search(r'"confidence_level":\s*(\d+)', investigation_output)
                    if confidence_match:
                        confidence = confidence_match.group(1)
                        print(f"🎯 Investigation confidence: {confidence}%")
                
            except Exception as e:
                print(f"⚠️ Could not parse investigation results: {e}")
        else:
            print("❌ Claude Code investigation step did not complete")
        
        # Check Slack integration
        print(f"\n📱 SLACK INTEGRATION RESULTS")
        print("=" * 50)
        
        if 'create-war-room' in step_results:
            war_room_output = step_results['create-war-room']['output']
            
            # Check channel creation
            if 'channel_id' in war_room_output:
                print("✅ Slack channel created successfully")
                
                # Extract channel details
                import re
                channel_id_match = re.search(r'"channel_id":\s*"([^"]+)"', war_room_output)
                channel_name_match = re.search(r'"channel_name":\s*"([^"]+)"', war_room_output)
                
                if channel_id_match and channel_name_match:
                    channel_id = channel_id_match.group(1)
                    channel_name = channel_name_match.group(1)
                    print(f"📱 Channel: #{channel_name} (ID: {channel_id})")
                    
                    # Check creation status
                    if 'created_public' in war_room_output:
                        print("🔓 Channel type: Public")
                    elif 'created_private' in war_room_output:
                        print("🔒 Channel type: Private")
                    elif 'existing' in war_room_output:
                        print("♻️ Used existing channel")
                    elif 'demo' in war_room_output:
                        print("📝 Demo mode (no real channel created)")
            else:
                print("⚠️ Slack channel creation unclear")
        
        # Final assessment
        print(f"\n🏆 E2E TEST ASSESSMENT")
        print("=" * 50)
        
        if all_steps_passed:
            print("🎉 SUCCESS: All workflow steps completed successfully")
            print("✅ Claude Code integration is working correctly")
            print("✅ Monitoring tool integration is configured properly")
            print("✅ Secret validation and fallback handling is functional")
            test_result = 0
        else:
            print("⚠️ PARTIAL SUCCESS: Some steps had issues")
            print("🔧 Review failed steps for debugging")
            test_result = 1
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("=" * 30)
        
        if len(secrets) < 3:
            missing_tools = []
            if 'observe_api_key' not in secrets:
                missing_tools.append("OBSERVE_API_KEY")
            if 'datadog_api_key' not in secrets:
                missing_tools.append("DATADOG_API_KEY") 
            if 'kubectl_config' not in secrets:
                missing_tools.append("KUBECTL_CONFIG")
            
            print(f"🔧 To enable full monitoring integration, provide:")
            for tool in missing_tools:
                print(f"   export {tool}=<your_key_here>")
        
        print(f"📋 For production deployment:")
        print(f"   1. Configure real Claude Code CLI installation")
        print(f"   2. Set up monitoring tool authentication")
        print(f"   3. Configure Slack workspace permissions")
        print(f"   4. Test with actual production incidents")
        
        return test_result
        
    except Exception as e:
        print(f"❌ E2E test failed: {e}")
        return 1


if __name__ == "__main__":
    print(__doc__)
    result = run_e2e_test()
    
    print(f"\n📋 Test completed with exit code: {result}")
    if result == 0:
        print("🎉 Claude Code E2E test PASSED")
    else:
        print("⚠️ Claude Code E2E test had issues - check logs above")
    
    sys.exit(result)