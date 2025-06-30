#!/usr/bin/env python3
"""
Simple test for Claude Code investigation step only.
"""

import os
import sys
import json
from pathlib import Path

# Add SDK path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step

def create_simple_investigation_workflow():
    """Create a simple workflow with just the investigation step."""
    
    workflow = (Workflow("simple-claude-investigation")
                .description("Simple Claude Code investigation test")
                .type("chain")
                .runner("core-testing-2"))
    
    # Parameters
    workflow.data["params"] = {
        "incident_id": "${incident_id:TEST-001}",
        "incident_title": "${incident_title:Test Incident}",
        "incident_severity": "${incident_severity:high}",
        "enable_claude_analysis": "${enable_claude_analysis:true}"
    }
    
    # Simple investigation step
    investigation_step = Step("claude-investigation")
    investigation_step.data = {
        "name": "claude-investigation",
        "executor": {
            "type": "tool",
            "config": {
                "tool_def": {
                    "name": "simple_claude_investigation",
                    "description": "Simple Claude Code investigation test",
                    "type": "docker",
                    "image": "node:18-bullseye",
                    "content": '''#!/bin/bash
echo "🧪 SIMPLE CLAUDE CODE INVESTIGATION TEST"
echo "========================================"

# Install basic packages
apt-get update -qq && apt-get install -y curl jq

# Install Claude Code CLI
echo "🧠 Installing Claude Code CLI..."
NPM_OUTPUT=$(npm install -g @anthropic-ai/claude-code 2>&1)
if command -v claude >/dev/null 2>&1; then
    echo "✅ Claude Code CLI installed successfully"
    CLAUDE_VERSION=$(claude --version 2>&1 || echo "unknown")
    echo "📋 Version: $CLAUDE_VERSION"
    CLAUDE_AVAILABLE=true
else
    echo "⚠️ Claude Code CLI installation failed"
    echo "📋 NPM output: $NPM_OUTPUT"
    CLAUDE_AVAILABLE=false
fi

# Simple investigation prompt
PROMPT="You are investigating incident $incident_id: $incident_title (severity: $incident_severity). 
Provide a brief JSON analysis with:
- executive_summary: Brief findings
- recommendations: 2-3 action items
- confidence_level: 0-100"

echo ""
echo "📋 Investigation Details:"
echo "  🆔 ID: $incident_id"
echo "  📝 Title: $incident_title"  
echo "  🚨 Severity: $incident_severity"
echo "  🤖 Claude Analysis: $enable_claude_analysis"

if [ "$CLAUDE_AVAILABLE" = "true" ] && [ "$enable_claude_analysis" = "true" ]; then
    echo ""
    echo "🚀 Executing Claude Code investigation..."
    echo "📋 Prompt: $(echo "$PROMPT" | wc -c) characters"
    
    CLAUDE_OUTPUT=$(timeout 60 claude -p "$PROMPT" --output-format json 2>&1)
    CLAUDE_EXIT_CODE=$?
    
    echo "📊 Claude execution completed (exit code: $CLAUDE_EXIT_CODE)"
    
    if [ $CLAUDE_EXIT_CODE -eq 0 ] && [ -n "$CLAUDE_OUTPUT" ]; then
        echo "✅ Claude analysis successful"
        echo "📋 Output: $CLAUDE_OUTPUT"
        INVESTIGATION_STATUS="success"
    else
        echo "⚠️ Claude analysis failed"
        echo "📋 Error: $CLAUDE_OUTPUT"
        INVESTIGATION_STATUS="failed"
    fi
else
    echo "💭 Using simulated analysis..."
    CLAUDE_OUTPUT='{
  "executive_summary": "Simulated incident analysis for testing purposes",
  "recommendations": [
    "Monitor system metrics closely",
    "Check application logs for errors",
    "Scale resources if needed"
  ],
  "confidence_level": 85
}'
    INVESTIGATION_STATUS="simulated"
fi

# Output results
echo ""
echo "📊 INVESTIGATION RESULTS:"
echo "========================"
cat << EOF
{
  "incident_id": "$incident_id",
  "investigation_status": "$INVESTIGATION_STATUS",
  "claude_analysis": $CLAUDE_OUTPUT,
  "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "step_status": "completed"
}
EOF

echo ""
echo "✅ Simple Claude investigation completed"'''
                },
                "args": {
                    "incident_id": "${incident_id}",
                    "incident_title": "${incident_title}",
                    "incident_severity": "${incident_severity}",
                    "enable_claude_analysis": "${enable_claude_analysis}"
                }
            }
        },
        "output": "INVESTIGATION_RESULT"
    }
    
    workflow.data["steps"] = [investigation_step.data]
    return workflow

def test_simple_investigation():
    """Test the simple investigation workflow."""
    
    print("🧪 SIMPLE CLAUDE CODE INVESTIGATION TEST")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY environment variable required")
        return 1
    
    # Test parameters
    test_params = {
        "incident_id": "SIMPLE-TEST-001",
        "incident_title": "Simple Claude Code Test",
        "incident_severity": "medium",
        "enable_claude_analysis": "true"
    }
    
    print(f"📋 Test Parameters:")
    for key, value in test_params.items():
        print(f"  {key}: {value}")
    
    # Create and execute workflow
    workflow = create_simple_investigation_workflow()
    client = KubiyaClient(api_key=api_key, timeout=120)
    
    try:
        print(f"\n🚀 Executing simple investigation workflow...")
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters=test_params,
            stream=True
        )
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        step_name = step.get('name', '')
                        step_status = step.get('status', '')
                        
                        if step_status == 'finished':
                            print(f"✅ {step_name}: Completed")
                        else:
                            print(f"❌ {step_name}: {step_status}")
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        print(f"\n🎉 Workflow: {'SUCCESS' if success else 'FAILED'}")
                        return 0 if success else 1
                        
                except json.JSONDecodeError:
                    continue
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    result = test_simple_investigation()
    sys.exit(result)