#!/usr/bin/env python3
"""
CLI tool to generate and deploy incident response workflows easily.
Usage: python generate_workflow.py [options]
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

# Add SDK path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from workflows.real_slack_incident_workflow import create_real_slack_incident_workflow


def deploy_workflow(api_key, workflow_params=None, test_mode=False):
    """Deploy the incident response workflow."""
    
    print("🚀 KUBIYA INCIDENT RESPONSE WORKFLOW GENERATOR")
    print("=" * 60)
    
    # Default parameters
    default_params = {
        "incident_event": json.dumps({
            "id": f"PROD-{datetime.now().strftime('%Y%m%d')}-001",
            "title": "Production System Alert",
            "severity": "critical",
            "description": "Automated incident detected"
        }),
        "slack_users": "shaked@kubiya.ai,amit@example.com",
        "create_real_channel": "true",
        "auto_assign": "true"
    }
    
    # Override with user params
    if workflow_params:
        default_params.update(workflow_params)
    
    print(f"📋 Workflow Parameters:")
    for key, value in default_params.items():
        if key == "incident_event":
            incident_data = json.loads(value)
            print(f"  🆔 Incident ID: {incident_data['id']}")
            print(f"  📝 Title: {incident_data['title']}")
            print(f"  🚨 Severity: {incident_data['severity']}")
        else:
            print(f"  {key}: {value}")
    
    # Create workflow
    print(f"\n🔧 Creating workflow definition...")
    workflow = create_real_slack_incident_workflow()
    
    print(f"✅ Workflow created with {len(workflow.data['steps'])} steps:")
    step_names = [step['name'] for step in workflow.data['steps']]
    for i, name in enumerate(step_names, 1):
        print(f"  {i}. {name}")
    
    if test_mode:
        print(f"\n🧪 TEST MODE - Workflow definition ready")
        return workflow.to_dict()
    
    # Deploy workflow
    print(f"\n🚚 Deploying workflow...")
    client = KubiyaClient(api_key=api_key, timeout=600)
    
    try:
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters=default_params,
            stream=True
        )
        
        print(f"📡 Processing workflow execution...")
        
        step_outputs = {}
        workflow_success = False
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        step_status = step.get('status', '')
                        
                        if step_status == 'completed':
                            print(f"  ✅ {step_name}")
                            step_outputs[step_name] = step.get('output', '')
                        elif step_status == 'failed':
                            print(f"  ❌ {step_name}: {step.get('error', 'Unknown error')}")
                    
                    elif 'workflow_complete' in event_type:
                        workflow_success = parsed.get('success', False)
                        if workflow_success:
                            print(f"\n🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
                        else:
                            print(f"\n❌ WORKFLOW FAILED!")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # Print results summary
        print(f"\n📊 DEPLOYMENT SUMMARY:")
        print(f"=" * 50)
        
        if 'create-war-room' in step_outputs:
            war_room_data = step_outputs['create-war-room']
            if 'channel_id' in war_room_data and 'channel_name' in war_room_data:
                import re
                channel_id_match = re.search(r'"channel_id": "([^"]+)"', war_room_data)
                channel_name_match = re.search(r'"channel_name": "([^"]+)"', war_room_data)
                
                if channel_id_match and channel_name_match:
                    channel_id = channel_id_match.group(1)
                    channel_name = channel_name_match.group(1)
                    print(f"📱 Slack Channel Created:")
                    print(f"   Name: #{channel_name}")
                    print(f"   ID: {channel_id}")
                    print(f"   URL: https://kubiya.slack.com/channels/{channel_id}")
        
        if 'resolve-slack-users' in step_outputs:
            user_data = step_outputs['resolve-slack-users']
            if 'resolved_count' in user_data:
                count_match = re.search(r'"resolved_count": (\d+)', user_data)
                if count_match:
                    resolved_count = count_match.group(1)
                    print(f"👥 Users Resolved: {resolved_count}")
        
        if 'technical-investigation' in step_outputs:
            investigation_data = step_outputs['technical-investigation']
            if 'confidence_level' in investigation_data:
                confidence_match = re.search(r'"confidence_level": (\d+)', investigation_data)
                if confidence_match:
                    confidence = confidence_match.group(1)
                    print(f"🔬 Investigation Confidence: {confidence}%")
        
        return workflow_success
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False


def interactive_mode():
    """Interactive mode to configure and deploy workflow."""
    
    print("🔧 INTERACTIVE WORKFLOW CONFIGURATION")
    print("=" * 50)
    
    # Get API key
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        api_key = input("🔑 Enter your Kubiya API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            return False
    
    # Configure incident
    print(f"\n📋 Configure Incident Details:")
    incident_id = input(f"🆔 Incident ID [PROD-{datetime.now().strftime('%Y%m%d')}-001]: ").strip()
    if not incident_id:
        incident_id = f"PROD-{datetime.now().strftime('%Y%m%d')}-001"
    
    incident_title = input("📝 Incident Title [Production System Alert]: ").strip()
    if not incident_title:
        incident_title = "Production System Alert"
    
    severity = input("🚨 Severity (critical/high/medium/low) [critical]: ").strip().lower()
    if severity not in ['critical', 'high', 'medium', 'low']:
        severity = 'critical'
    
    # Configure Slack users
    print(f"\n👥 Configure Slack Notifications:")
    slack_users = input("📧 Slack users (emails, comma-separated) [shaked@kubiya.ai]: ").strip()
    if not slack_users:
        slack_users = "shaked@kubiya.ai"
    
    # Build parameters
    incident_event = json.dumps({
        "id": incident_id,
        "title": incident_title,
        "severity": severity,
        "description": f"Incident requiring immediate attention"
    })
    
    params = {
        "incident_event": incident_event,
        "slack_users": slack_users,
        "create_real_channel": "true",
        "auto_assign": "true"
    }
    
    # Confirm deployment
    print(f"\n📋 Review Configuration:")
    print(f"  🆔 Incident: {incident_id}")
    print(f"  📝 Title: {incident_title}")
    print(f"  🚨 Severity: {severity}")
    print(f"  👥 Users: {slack_users}")
    
    confirm = input(f"\n🚀 Deploy workflow? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Deployment cancelled")
        return False
    
    # Deploy
    return deploy_workflow(api_key, params)


def main():
    """Main CLI function."""
    
    parser = argparse.ArgumentParser(
        description="Generate and deploy Kubiya incident response workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python generate_workflow.py --interactive
  
  # Quick deploy with defaults
  python generate_workflow.py --deploy
  
  # Custom incident
  python generate_workflow.py --deploy --incident-id "PROD-20240630-002" --severity high --users "user1@company.com,user2@company.com"
  
  # Test mode (generate only)
  python generate_workflow.py --test
        """
    )
    
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive configuration mode')
    parser.add_argument('--deploy', '-d', action='store_true',
                       help='Deploy workflow with current/default settings')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Test mode - generate workflow definition only')
    
    parser.add_argument('--incident-id', help='Custom incident ID')
    parser.add_argument('--incident-title', help='Custom incident title')
    parser.add_argument('--severity', choices=['critical', 'high', 'medium', 'low'],
                       default='critical', help='Incident severity')
    parser.add_argument('--users', help='Comma-separated list of user emails')
    parser.add_argument('--channel-privacy', choices=['public', 'private', 'auto'],
                       default='auto', help='Channel privacy: public, private, or auto (fallback)')
    
    parser.add_argument('--api-key', help='Kubiya API key (or set KUBIYA_API_KEY env var)')
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive:
        return 0 if interactive_mode() else 1
    
    # Get API key
    api_key = args.api_key or os.getenv('KUBIYA_API_KEY')
    if not api_key and not args.test:
        print("❌ API key required. Set KUBIYA_API_KEY env var or use --api-key")
        return 1
    
    # Build parameters
    params = {}
    if args.incident_id or args.incident_title or args.severity != 'critical':
        incident_event = {
            "id": args.incident_id or f"PROD-{datetime.now().strftime('%Y%m%d')}-001",
            "title": args.incident_title or "Production System Alert",
            "severity": args.severity,
            "description": "Custom incident via CLI"
        }
        params["incident_event"] = json.dumps(incident_event)
    
    if args.users:
        params["slack_users"] = args.users
    
    if args.channel_privacy:
        params["channel_privacy"] = args.channel_privacy
    
    # Deploy or test
    if args.test:
        print("🧪 TEST MODE - Generating workflow...")
        workflow_def = deploy_workflow(None, params, test_mode=True)
        print(f"\n📄 Workflow definition generated successfully!")
        print(f"📊 Steps: {len(workflow_def.get('steps', []))}")
        return 0
    elif args.deploy:
        success = deploy_workflow(api_key, params)
        return 0 if success else 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())