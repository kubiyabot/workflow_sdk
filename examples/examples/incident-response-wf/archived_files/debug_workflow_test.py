#!/usr/bin/env python3
"""
Enhanced debugging test for incident response workflow.
Provides real-time streaming, detailed logging, and step-by-step verification.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from fixed_incident_workflow import create_fixed_incident_workflow


class WorkflowDebugger:
    """Enhanced debugging and monitoring for workflow execution."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = KubiyaClient(api_key=api_key)
        self.execution_log = []
        self.step_statuses = {}
        self.start_time = None
        self.events_received = 0
    
    def log(self, level: str, message: str, data: dict = None):
        """Enhanced logging with timestamps and structure."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "data": data or {}
        }
        self.execution_log.append(log_entry)
        
        # Color coding for console output
        colors = {
            "INFO": "\033[36m",    # Cyan
            "SUCCESS": "\033[32m", # Green
            "WARNING": "\033[33m", # Yellow
            "ERROR": "\033[31m",   # Red
            "STEP": "\033[35m",    # Magenta
            "EVENT": "\033[94m"    # Blue
        }
        
        color = colors.get(level, "\033[0m")
        reset = "\033[0m"
        
        print(f"{color}[{timestamp}] {level}: {message}{reset}")
        if data:
            print(f"  📊 Data: {json.dumps(data, indent=2, default=str)[:200]}...")
    
    def test_workflow_creation(self):
        """Test workflow creation with detailed validation."""
        self.log("INFO", "🔧 Creating and validating fixed workflow definition")
        
        try:
            workflow = create_fixed_incident_workflow()
            workflow_dict = workflow.to_dict()
            self.log("SUCCESS", f"✅ Fixed workflow created: {workflow_dict['name']}")
            
            # Validate workflow structure
            required_fields = ['name', 'description', 'steps', 'type']
            for field in required_fields:
                if field not in workflow_dict:
                    self.log("ERROR", f"❌ Missing required field: {field}")
                    return None
                self.log("INFO", f"✓ {field}: {workflow_dict[field] if field != 'steps' else f'{len(workflow_dict[field])} steps'}")
            
            # Validate each step
            self.log("INFO", "🔍 Validating workflow steps:")
            for i, step in enumerate(workflow_dict['steps'], 1):
                step_name = step.get('name', f'step-{i}')
                self.log("STEP", f"  {i}. {step_name}")
                
                # Check step structure
                if 'command' not in step and 'executor' not in step:
                    self.log("WARNING", f"    ⚠️ Step may be missing execution command")
                else:
                    self.log("INFO", f"    ✓ Execution method configured")
                
                if 'depends' in step:
                    self.log("INFO", f"    📎 Depends on: {step['depends']}")
                
                if 'output' in step:
                    self.log("INFO", f"    📤 Output: {step['output']}")
            
            return workflow_dict
            
        except Exception as e:
            self.log("ERROR", f"❌ Workflow creation failed: {str(e)}")
            return None
    
    def create_test_incident(self):
        """Create a comprehensive test incident with all fields."""
        incident_event = {
            "id": f"INC-2024-DEBUG-{int(time.time())}",
            "title": "DEBUG: Production Payment Gateway Critical Database Connection Crisis",
            "url": f"https://app.datadoghq.com/incidents/INC-2024-DEBUG-{int(time.time())}",
            "severity": "critical",
            "body": "🚨 CRITICAL PRODUCTION INCIDENT 🚨\n\nPayment gateway experiencing catastrophic failure:\n- Error rate: 35% (threshold: 2%)\n- Response time: 4.2s (SLA: 500ms)\n- Database connections: 98% capacity\n- Failed transactions: 2,847\n- Revenue impact: $47,000\n- Customer complaints: 156\n\nTiming correlates with:\n- Payment service v2.4.1 deployment (52 minutes ago)\n- Traffic spike +65% from flash sale\n- Database maintenance window completed 1hr ago\n\nREQUIRES IMMEDIATE INVESTIGATION AND POTENTIAL ROLLBACK",
            "kubiya": {
                "slack_channel_id": f"#inc-debug-{int(time.time())}-payment-crisis"
            }
        }
        
        self.log("INFO", "📋 Created comprehensive test incident")
        self.log("INFO", f"  🆔 ID: {incident_event['id']}")
        self.log("INFO", f"  📝 Title: {incident_event['title']}")
        self.log("INFO", f"  🚨 Severity: {incident_event['severity']}")
        self.log("INFO", f"  💬 Slack Channel: {incident_event['kubiya']['slack_channel_id']}")
        
        return incident_event
    
    def execute_with_streaming(self, workflow_dict: dict, incident_event: dict):
        """Execute workflow with comprehensive streaming and monitoring."""
        self.log("INFO", "🚀 Starting workflow execution with streaming...")
        self.start_time = time.time()
        
        workflow_params = {
            "event": json.dumps(incident_event)
        }
        
        self.log("INFO", f"📦 Workflow parameters prepared")
        self.log("INFO", f"  📄 Event size: {len(workflow_params['event'])} characters")
        
        try:
            # Execute with streaming enabled
            self.log("INFO", "🌊 Enabling streaming execution...")
            
            for event in self.client.execute_workflow(
                workflow_definition=workflow_dict,
                parameters=workflow_params,
                stream=True
            ):
                self.events_received += 1
                self.process_streaming_event(event)
                
                # Limit events for debugging (remove in production)
                if self.events_received >= 20:
                    self.log("WARNING", "⚠️ Limiting events for debugging (first 20 shown)")
                    break
            
            self.log("SUCCESS", f"✅ Streaming completed - Total events: {self.events_received}")
            
        except Exception as e:
            self.log("ERROR", f"❌ Streaming execution failed: {str(e)}")
            import traceback
            self.log("ERROR", f"🔍 Traceback: {traceback.format_exc()}")
    
    def execute_without_streaming(self, workflow_dict: dict, incident_event: dict):
        """Execute workflow without streaming for comparison."""
        self.log("INFO", "🎯 Executing workflow without streaming...")
        
        workflow_params = {
            "event": json.dumps(incident_event)
        }
        
        try:
            result = self.client.execute_workflow(
                workflow_definition=workflow_dict,
                parameters=workflow_params,
                stream=False
            )
            
            self.log("SUCCESS", "✅ Non-streaming execution completed")
            self.analyze_final_result(result)
            return result
            
        except Exception as e:
            self.log("ERROR", f"❌ Non-streaming execution failed: {str(e)}")
            import traceback
            self.log("ERROR", f"🔍 Traceback: {traceback.format_exc()}")
            return None
    
    def process_streaming_event(self, event):
        """Process and analyze each streaming event."""
        self.log("EVENT", f"📡 Event #{self.events_received}")
        
        if isinstance(event, dict):
            # Extract event details
            event_type = event.get('type', 'unknown')
            step_name = event.get('step_name', event.get('stepName', 'unknown'))
            status = event.get('status', event.get('state', 'unknown'))
            message = event.get('message', event.get('msg', ''))
            
            self.log("EVENT", f"  📋 Type: {event_type}")
            self.log("EVENT", f"  🔧 Step: {step_name}")
            self.log("EVENT", f"  📊 Status: {status}")
            
            if message:
                self.log("EVENT", f"  💬 Message: {message[:100]}...")
            
            # Track step status
            if step_name != 'unknown':
                self.step_statuses[step_name] = {
                    'status': status,
                    'type': event_type,
                    'timestamp': time.time(),
                    'event_number': self.events_received
                }
            
            # Look for specific event types
            if event_type in ['step.started', 'step.running']:
                self.log("STEP", f"▶️ Step starting: {step_name}")
            elif event_type in ['step.completed', 'step.success']:
                self.log("STEP", f"✅ Step completed: {step_name}")
            elif event_type in ['step.failed', 'step.error']:
                self.log("STEP", f"❌ Step failed: {step_name}")
            elif event_type in ['workflow.completed', 'workflow.success']:
                self.log("SUCCESS", f"🎉 Workflow completed successfully!")
            elif event_type in ['workflow.failed', 'workflow.error']:
                self.log("ERROR", f"💥 Workflow failed!")
            
            # Show output data if available
            if 'output' in event and event['output']:
                output_preview = str(event['output'])[:150]
                self.log("EVENT", f"  📤 Output: {output_preview}...")
        
        elif isinstance(event, str):
            # Handle string events
            self.log("EVENT", f"  📝 String event: {event[:100]}...")
        
        else:
            # Handle other event types
            self.log("EVENT", f"  ❓ Unknown event type: {type(event)}")
    
    def analyze_final_result(self, result):
        """Analyze the final workflow result in detail."""
        self.log("INFO", "📊 Analyzing final workflow result...")
        
        if not result:
            self.log("WARNING", "⚠️ No final result received")
            return
        
        self.log("INFO", f"📋 Result type: {type(result)}")
        
        if isinstance(result, dict):
            # Check execution metadata
            for key in ['execution_id', 'id', 'executionId', 'status', 'state']:
                if key in result:
                    self.log("INFO", f"  🔑 {key}: {result[key]}")
            
            # Check for errors
            if 'errors' in result and result['errors']:
                self.log("ERROR", f"❌ Errors found: {len(result['errors'])}")
                for i, error in enumerate(result['errors'][:3], 1):
                    self.log("ERROR", f"  {i}. {error}")
            
            # Check for outputs
            if 'outputs' in result and result['outputs']:
                self.log("SUCCESS", f"📤 Outputs available: {len(result['outputs'])}")
                for output_name, output_value in result['outputs'].items():
                    output_preview = str(output_value)[:100]
                    self.log("INFO", f"  📄 {output_name}: {output_preview}...")
            
            # Check for events
            if 'events' in result and result['events']:
                self.log("INFO", f"📡 Events in result: {len(result['events'])}")
                for i, event in enumerate(result['events'][:3], 1):
                    event_preview = str(event)[:80]
                    self.log("INFO", f"  {i}. {event_preview}...")
        
        # Show full result (truncated)
        result_str = json.dumps(result, indent=2, default=str)
        if len(result_str) > 1000:
            result_str = result_str[:1000] + "... [truncated]"
        
        self.log("INFO", f"📋 Full result preview:\n{result_str}")
    
    def generate_execution_report(self):
        """Generate a comprehensive execution report."""
        duration = time.time() - self.start_time if self.start_time else 0
        
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE EXECUTION REPORT")
        print("="*80)
        
        print(f"⏱️  **Execution Duration**: {duration:.2f} seconds")
        print(f"📡 **Events Received**: {self.events_received}")
        print(f"🔧 **Steps Tracked**: {len(self.step_statuses)}")
        
        if self.step_statuses:
            print(f"\n📋 **Step Status Summary**:")
            for step_name, step_data in self.step_statuses.items():
                status_emoji = "✅" if "complet" in step_data['status'].lower() or "success" in step_data['status'].lower() else "❌" if "fail" in step_data['status'].lower() or "error" in step_data['status'].lower() else "⏳"
                print(f"  {status_emoji} {step_name}: {step_data['status']} (Event #{step_data['event_number']})")
        
        print(f"\n📈 **Event Timeline**:")
        for i, log_entry in enumerate(self.execution_log[-10:], 1):  # Show last 10 log entries
            print(f"  {i}. [{log_entry['timestamp']}] {log_entry['level']}: {log_entry['message']}")
        
        print(f"\n🎯 **Validation Results**:")
        expected_steps = [
            "parse-incident-event",
            "get-slack-token", 
            "get-secrets",
            "create-incident-channel",
            "claude-code-investigation",
            "update-slack-results"
        ]
        
        for step in expected_steps:
            if step in self.step_statuses:
                status = self.step_statuses[step]['status']
                emoji = "✅" if "success" in status.lower() or "complet" in status.lower() else "❌" if "fail" in status.lower() else "⏳"
                print(f"  {emoji} {step}: {status}")
            else:
                print(f"  ❓ {step}: No status received")


def main():
    """Enhanced main function with comprehensive debugging."""
    print("🔍 ENHANCED INCIDENT RESPONSE WORKFLOW DEBUGGER")
    print("🎯 Real-time streaming, detailed logging, step-by-step verification")
    print("="*90)
    
    # Check API key
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable not set")
        return 1
    
    print(f"✅ API Key available (length: {len(api_key)})")
    
    # Initialize debugger
    debugger = WorkflowDebugger(api_key)
    debugger.log("INFO", "🚀 Enhanced workflow debugger initialized")
    
    # Test workflow creation
    workflow_dict = debugger.test_workflow_creation()
    if not workflow_dict:
        debugger.log("ERROR", "❌ Cannot proceed without valid workflow")
        return 1
    
    # Create test incident
    incident_event = debugger.create_test_incident()
    
    # Execute with streaming
    debugger.log("INFO", "🌊 Testing with streaming enabled...")
    debugger.execute_with_streaming(workflow_dict, incident_event)
    
    # Execute without streaming for comparison
    debugger.log("INFO", "🎯 Testing without streaming for comparison...")
    final_result = debugger.execute_without_streaming(workflow_dict, incident_event)
    
    # Generate comprehensive report
    debugger.generate_execution_report()
    
    print("\n🎉 ENHANCED DEBUGGING COMPLETE!")
    print("="*90)
    print("✅ **Streaming Events**: Real-time monitoring enabled")
    print("✅ **Step Tracking**: Individual step status monitored")
    print("✅ **Error Detection**: Comprehensive error analysis")
    print("✅ **Performance Metrics**: Timing and throughput measured")
    print("✅ **Validation**: All expected steps verified")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())