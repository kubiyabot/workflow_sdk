#!/usr/bin/env python3
"""
Minimal test to understand the expected workflow format.
"""

import os
import sys
import json
from pathlib import Path

# Add the workflow_sdk to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient


def test_minimal_workflow():
    """Test with a minimal workflow to understand the expected format."""
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY not set")
        return
    
    client = KubiyaClient(api_key=api_key)
    
    # Try the most minimal workflow possible
    minimal_workflow = {
        "name": "minimal-test",
        "description": "Minimal test workflow",
        "runner": "core-testing-2",
        "steps": [
            {
                "name": "echo-step",
                "command": "echo 'Hello from Kubiya!'"
            }
        ]
    }
    
    print("🧪 Testing minimal workflow:")
    print(json.dumps(minimal_workflow, indent=2))
    
    try:
        print("🚀 Submitting workflow execution...")
        result = client.execute_workflow(
            workflow_definition=minimal_workflow,
            stream=False
        )
        print("🎯 Got immediate response (workflow submitted)")
        
        print("✅ Minimal workflow executed successfully!")
        print(f"📋 Result: {json.dumps(result, indent=2, default=str)}")
        
    except Exception as e:
        print(f"❌ Minimal workflow failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


def test_claude_code_minimal():
    """Test minimal Claude Code integration."""
    
    api_key = os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ KUBIYA_API_KEY not set")
        return
    
    client = KubiyaClient(api_key=api_key)
    
    # Minimal Claude Code workflow
    claude_workflow = {
        "name": "claude-minimal-test",
        "description": "Minimal Claude Code test",
        "runner": "core-testing-2",
        "steps": [
            {
                "name": "claude-analysis",
                "executor": {
                    "type": "inline_agent",
                    "config": {
                        "message": "Analyze this test incident: High CPU usage on server. Provide a brief JSON response with category and urgency.",
                        "agent": {
                            "name": "test-analyzer",
                            "ai_instructions": "You are a simple test analyst. Provide brief JSON responses.",
                            "runners": ["core-testing-2"],
                            "llm_model": "gpt-4o-mini",
                            "is_debug_mode": True
                        }
                    }
                }
            }
        ]
    }
    
    print("\n🤖 Testing minimal Claude Code workflow:")
    print(json.dumps(claude_workflow, indent=2))
    
    try:
        result = client.execute_workflow(
            workflow_definition=claude_workflow,
            stream=False
        )
        
        print("✅ Claude Code workflow executed successfully!")
        print(f"📋 Result: {json.dumps(result, indent=2, default=str)}")
        
    except Exception as e:
        print(f"❌ Claude Code workflow failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    print("🧪 Minimal Workflow Tests")
    print("=" * 50)
    
    test_minimal_workflow()
    test_claude_code_minimal()
    
    print("\n🎉 Tests completed!")