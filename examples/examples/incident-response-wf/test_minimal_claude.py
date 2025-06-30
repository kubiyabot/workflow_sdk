#!/usr/bin/env python3
"""
Minimal Claude Code test to verify basic functionality.
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step

def create_minimal_workflow():
    """Create minimal workflow with just Claude test."""
    
    workflow = (Workflow("minimal-claude-test")
                .description("Minimal Claude Code test")
                .type("chain") 
                .runner("core-testing-2"))
    
    workflow.data["params"] = {"test_message": "${test_message:Hello from Claude}"}
    
    # Simple Claude test step
    claude_step = Step("claude-test")
    claude_step.data = {
        "name": "claude-test",
        "executor": {
            "type": "tool",
            "config": {
                "timeout": 180,
                "tool_def": {
                    "name": "minimal_claude_test",
                    "description": "Minimal Claude Code test",
                    "type": "docker",
                    "image": "node:18-bullseye",
                    "content": '''#!/bin/bash
echo "🧪 MINIMAL CLAUDE CODE TEST"
echo "=========================="
echo "⏱️ $(date -u +%H:%M:%S) - Starting test"

# Install minimal packages
echo "📦 Installing curl and jq..."
apt-get update -qq && apt-get install -y curl jq 2>/dev/null
echo "✅ Basic packages installed"

# Install Claude Code CLI
echo "🧠 Installing Claude Code CLI..."
echo "⏱️ $(date -u +%H:%M:%S) - Running npm install..."

# Show progress
npm install -g @anthropic-ai/claude-code &
NPM_PID=$!

# Monitor npm installation
COUNTER=0
while kill -0 "$NPM_PID" 2>/dev/null; do
    sleep 5
    COUNTER=$((COUNTER + 5))
    echo "⏱️ npm install running... ${COUNTER}s"
    if [ $COUNTER -gt 60 ]; then
        echo "⚠️ npm taking too long, continuing..."
        break
    fi
done

wait "$NPM_PID" 2>/dev/null

if command -v claude >/dev/null 2>&1; then
    echo "✅ Claude Code CLI installed successfully"
    VERSION=$(claude --version 2>&1 || echo "unknown")
    echo "📋 Version: $VERSION"
    
    # Simple test prompt
    PROMPT="Analyze this message: $test_message. Respond with a JSON object containing: {\"analysis\": \"brief analysis\", \"status\": \"success\"}"
    
    echo "🚀 Testing Claude with simple prompt..."
    echo "📋 Prompt: $PROMPT"
    
    # Execute Claude with timeout and progress monitoring
    echo "⏱️ $(date -u +%H:%M:%S) - Starting Claude analysis..."
    
    CLAUDE_OUTPUT=$(timeout 60 claude -p "$PROMPT" --output-format json 2>&1)
    CLAUDE_EXIT_CODE=$?
    
    echo "📊 Claude completed (exit code: $CLAUDE_EXIT_CODE) at $(date -u +%H:%M:%S)"
    
    if [ $CLAUDE_EXIT_CODE -eq 0 ] && [ -n "$CLAUDE_OUTPUT" ]; then
        echo "✅ Claude test successful"
        echo "📋 Output: $CLAUDE_OUTPUT"
        RESULT="{\"status\": \"success\", \"claude_output\": $CLAUDE_OUTPUT}"
    else
        echo "⚠️ Claude test failed: $CLAUDE_OUTPUT"
        RESULT="{\"status\": \"failed\", \"error\": \"$(echo "$CLAUDE_OUTPUT" | head -c 200)\"}"
    fi
else
    echo "❌ Claude Code CLI not available"
    RESULT="{\"status\": \"cli_not_available\", \"message\": \"Claude CLI installation failed\"}"
fi

echo ""
echo "📊 FINAL RESULT:"
echo "$RESULT"

echo ""
echo "✅ Minimal test completed at $(date -u +%H:%M:%S)"'''
                },
                "args": {
                    "test_message": "${test_message}"
                }
            }
        },
        "output": "TEST_RESULT"
    }
    
    workflow.data["steps"] = [claude_step.data]
    return workflow

def test_minimal():
    """Test minimal Claude functionality."""
    
    print("🧪 MINIMAL CLAUDE CODE TEST")
    print("=" * 40)
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY required")
        return 1
    
    params = {"test_message": "Test incident analysis"}
    
    workflow = create_minimal_workflow()
    client = KubiyaClient(api_key=api_key, timeout=300)
    
    try:
        print("🚀 Executing minimal workflow...")
        
        events = client.execute_workflow(
            workflow_definition=workflow.to_dict(),
            parameters=params,
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
                        
                        print(f"📋 {step_name}: {step_status}")
                        
                        if step_status == 'finished':
                            return 0
                        else:
                            error = step.get('error', 'Unknown error')
                            print(f"❌ Error: {error}")
                            return 1
                    
                    elif 'workflow_complete' in event_type:
                        success = parsed.get('success', False)
                        print(f"🎉 Workflow: {'SUCCESS' if success else 'FAILED'}")
                        return 0 if success else 1
                        
                except json.JSONDecodeError:
                    continue
        
        print("⚠️ No completion event received")
        return 1
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    result = test_minimal()
    print(f"\n📋 Exit code: {result}")
    sys.exit(result)