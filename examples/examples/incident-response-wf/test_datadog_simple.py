#!/usr/bin/env python3
"""
Simple end-to-end test with Datadog incident - focused on results capture.
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


def test_datadog_incident_simple():
    """Simple test with clear output capture."""
    
    print("🚨 DATADOG INCIDENT - SIMPLE E2E TEST")
    print("=" * 50)
    
    # Validate environment
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY required")
        return 1
    
    # Create Datadog incident
    timestamp = int(time.time())
    incident_data = {
        "id": f"DATADOG-PROD-{timestamp}",
        "title": "Critical Memory Alert - Production API Cluster",
        "severity": "critical",
        "description": "Production API servers showing 95%+ memory usage with degraded response times",
        "source": "datadog",
        "monitor_id": "987654321",
        "affected_hosts": ["api-01.prod", "api-02.prod", "api-03.prod"],
        "error_rate": "15.2%",
        "response_time": "3.1s"
    }
    
    test_params = {
        "incident_event": json.dumps(incident_data),
        "slack_users": "shaked@kubiya.ai,oncall@company.com",
        "create_real_channel": "true",
        "auto_assign": "true"
    }
    
    print(f"📋 Incident: {incident_data['id']}")
    print(f"🚨 Severity: {incident_data['severity']}")
    print(f"👥 Teams: {test_params['slack_users']}")
    
    # Execute workflow
    workflow = create_real_slack_incident_workflow()
    client = KubiyaClient(api_key=api_key, timeout=300)
    
    try:
        print(f"\n🚀 Executing workflow...")
        start_time = time.time()
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters=test_params,
            stream=True
        )
        
        all_events = []
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    all_events.append(parsed)
                    
                    event_type = parsed.get('type', '')
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        step_status = step.get('status', '')
                        
                        if step_status == 'completed':
                            print(f"  ✅ {step_name}")
                        else:
                            print(f"  ❌ {step_name}: {step.get('error', 'Failed')}")
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        duration = time.time() - start_time
                        
                        if success:
                            print(f"\n🎉 SUCCESS! Datadog incident handled in {duration:.1f}s")
                        else:
                            print(f"\n❌ FAILED after {duration:.1f}s")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # Save detailed execution log
        log_file = Path(__file__).parent / f"datadog_execution_{timestamp}.json"
        with open(log_file, 'w') as f:
            json.dump({
                "incident": incident_data,
                "parameters": test_params,
                "events": all_events,
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)
        
        print(f"📋 Execution log: {log_file}")
        
        # Check for Slack channel creation in events
        channel_created = False
        for event in all_events:
            if event.get('type') == 'step_complete':
                step = event.get('step', {})
                if step.get('name') == 'create-war-room' and step.get('status') == 'completed':
                    output = step.get('output', '')
                    if 'channel_id' in output:
                        print(f"📱 Slack channel created! Check your workspace.")
                        channel_created = True
                        break
        
        if not channel_created:
            print(f"⚠️ No Slack channel detected in logs")
        
        print(f"\n✅ Datadog incident response test completed!")
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(test_datadog_incident_simple())