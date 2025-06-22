#!/usr/bin/env python3
"""
End-to-End Example: ADK Provider with Together AI

This example demonstrates the complete workflow generation and execution
pipeline using the ADK provider with Together AI models.

Prerequisites:
1. Set your Together AI API key: export TOGETHER_API_KEY=your-key
2. Set your Kubiya API key: export KUBIYA_API_KEY=your-key
3. Install dependencies: pip install kubiya-workflow-sdk[adk]
"""

import os
import asyncio
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment():
    """Check required environment variables."""
    required_vars = {
        "TOGETHER_API_KEY": "Together AI API key for model access",
        "KUBIYA_API_KEY": "Kubiya platform API key (or use mock client)"
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var}: {description}")
    
    if missing:
        print("Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nSet them with:")
        print("  export TOGETHER_API_KEY=your-together-api-key")
        print("  export KUBIYA_API_KEY=your-kubiya-api-key")
        return False
    
    return True


async def example_basic_generation():
    """Example 1: Basic workflow generation."""
    print("\n" + "="*60)
    print("Example 1: Basic Workflow Generation")
    print("="*60)
    
    from kubiya_workflow_sdk import KubiyaClient
    from kubiya_workflow_sdk.providers import get_provider
    
    # Initialize client
    client = KubiyaClient(api_key=os.getenv("KUBIYA_API_KEY"))
    
    # Create ADK provider with Together AI
    provider = get_provider("adk", client=client)
    
    # Generate a simple workflow
    task = "Create a workflow to check system health: disk space, memory, and CPU usage"
    
    print(f"Task: {task}")
    print("Generating workflow...")
    
    workflow = provider.generate_workflow(
        task=task,
        context={
            "output_format": "json",
            "alert_threshold": 80
        }
    )
    
    print(f"\nGenerated workflow: {workflow['name']}")
    print(f"Description: {workflow.get('description', 'N/A')}")
    print(f"Number of steps: {len(workflow.get('steps', []))}")
    
    # Display steps
    print("\nSteps:")
    for i, step in enumerate(workflow.get('steps', []), 1):
        print(f"  {i}. {step['name']}")
        if 'executor' in step:
            print(f"     Type: {step['executor']['type']}")
            if 'script' in step['executor']:
                print(f"     Script preview: {step['executor']['script'][:50]}...")
    
    return workflow


async def example_streaming_generation():
    """Example 2: Streaming workflow generation with real-time feedback."""
    print("\n" + "="*60)
    print("Example 2: Streaming Workflow Generation")
    print("="*60)
    
    from kubiya_workflow_sdk import KubiyaClient
    from kubiya_workflow_sdk.providers import get_provider
    
    client = KubiyaClient(api_key=os.getenv("KUBIYA_API_KEY"))
    provider = get_provider("adk", client=client)
    
    task = "Deploy a Node.js application to Kubernetes with health checks and rollback"
    
    print(f"Task: {task}")
    print("Streaming generation (SSE format)...\n")
    
    events = []
    async for event in provider.generate_workflow(
        task=task,
        stream=True,
        stream_format="sse",
        context={
            "app_name": "my-node-app",
            "namespace": "production",
            "replicas": 3
        }
    ):
        # Display streaming events
        if event.strip():
            print(f"[SSE] {event.strip()}")
            events.append(event)
    
    print(f"\nTotal events received: {len(events)}")
    
    # Try to extract workflow from events
    workflow_json = None
    for event in events:
        if "workflow" in event:
            try:
                # Parse SSE data
                if event.startswith("data: "):
                    data = json.loads(event[6:])
                    if "content" in data and "<workflow>" in data["content"]:
                        import re
                        match = re.search(r'<workflow>\s*(.*?)\s*</workflow>', 
                                        data["content"], re.DOTALL)
                        if match:
                            workflow_json = json.loads(match.group(1))
                            break
            except:
                pass
    
    if workflow_json:
        print(f"\nExtracted workflow: {workflow_json.get('name', 'Unknown')}")
    
    return events


async def example_with_platform_context():
    """Example 3: Generation with platform context discovery."""
    print("\n" + "="*60)
    print("Example 3: Workflow Generation with Platform Context")
    print("="*60)
    
    from kubiya_workflow_sdk import KubiyaClient
    from kubiya_workflow_sdk.providers import get_provider
    
    # Create a mock client if no real API key
    if not os.getenv("KUBIYA_API_KEY") or os.getenv("KUBIYA_API_KEY") == "mock":
        print("Using mock client for demonstration...")
        from unittest.mock import Mock
        client = Mock(spec=KubiyaClient)
        
        # Mock platform resources
        client.get_runners = Mock(return_value=[
            {"name": "aws-prod", "type": "kubernetes", "region": "us-east-1"},
            {"name": "azure-dev", "type": "aci", "region": "westus2"}
        ])
        client.get_integrations = Mock(return_value=[
            {"name": "github", "type": "github", "status": "active"},
            {"name": "slack", "type": "slack", "status": "active"},
            {"name": "aws", "type": "aws", "status": "active"}
        ])
        client.get_secrets_metadata = Mock(return_value=[
            {"name": "GITHUB_TOKEN", "type": "oauth"},
            {"name": "AWS_ACCESS_KEY", "type": "string"},
            {"name": "SLACK_WEBHOOK", "type": "string"}
        ])
        client.list_agents = Mock(return_value=[
            {"name": "deploy-agent", "description": "Handles deployments"},
            {"name": "monitor-agent", "description": "System monitoring"}
        ])
    else:
        client = KubiyaClient(api_key=os.getenv("KUBIYA_API_KEY"))
    
    provider = get_provider("adk", client=client)
    
    # Complex task that requires platform context
    task = """
    Create a complete CI/CD workflow that:
    1. Triggers on GitHub push to main branch
    2. Runs tests in the available runner
    3. Builds and pushes Docker image
    4. Deploys to Kubernetes 
    5. Sends Slack notification on success/failure
    Use any available integrations and secrets.
    """
    
    print(f"Task: {task}")
    print("\nThe provider will discover available platform resources...")
    
    # Generate with session for context continuity
    session_id = f"demo-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    workflow = provider.generate_workflow(
        task=task,
        session_id=session_id,
        user_id="demo-user"
    )
    
    print(f"\nGenerated workflow: {workflow['name']}")
    
    # Display discovered context usage
    workflow_str = json.dumps(workflow, indent=2)
    
    print("\nPlatform resources detected in workflow:")
    if "aws-prod" in workflow_str or "kubernetes" in workflow_str:
        print("  ✓ Kubernetes runner")
    if "GITHUB_TOKEN" in workflow_str:
        print("  ✓ GitHub integration")
    if "SLACK_WEBHOOK" in workflow_str:
        print("  ✓ Slack integration")
    if "AWS_ACCESS_KEY" in workflow_str:
        print("  ✓ AWS credentials")
    
    return workflow


async def example_refinement_loop():
    """Example 4: Workflow refinement with error correction."""
    print("\n" + "="*60)
    print("Example 4: Workflow Refinement Loop")
    print("="*60)
    
    from kubiya_workflow_sdk import KubiyaClient
    from kubiya_workflow_sdk.providers import get_provider
    
    client = KubiyaClient(api_key=os.getenv("KUBIYA_API_KEY", "mock"))
    provider = get_provider("adk", client=client)
    
    # Intentionally problematic workflow code
    workflow_code = """
from kubiya_workflow_sdk.dsl import Workflow, Step
from kubiya_workflow_sdk.dsl.executors import PythonExecutor

workflow = Workflow("broken_workflow")

# This has intentional errors
step1 = Step(
    name="step with spaces",  # Invalid: spaces in name
    executor=PythonExecutor(
        script="import requests\\nprint(data)"  # Invalid: undefined variable
    )
)
workflow.add_step(step1)

# Missing dependency
step2 = Step(
    name="dependent_step",
    executor=PythonExecutor(script="print('Done')"),
    depends_on=["nonexistent_step"]  # Invalid: references non-existent step
)
workflow.add_step(step2)
"""
    
    print("Testing workflow with intentional errors...")
    print("Code preview:")
    print(workflow_code[:200] + "...")
    
    # Validate the problematic workflow
    validation = provider.validate_workflow(workflow_code)
    
    print(f"\nValidation result: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
    if validation.get('errors'):
        print("Errors found:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if not validation['valid']:
        print("\nAttempting automatic refinement...")
        
        # Use refinement to fix errors
        refined_workflow = provider.refine_workflow(
            workflow_code=workflow_code,
            errors=validation['errors']
        )
        
        print(f"\nRefined workflow: {refined_workflow.get('name', 'Unknown')}")
        print("The refinement agent has fixed the errors!")
        
        # Show the corrected workflow
        if refined_workflow.get('steps'):
            print("\nCorrected steps:")
            for step in refined_workflow['steps']:
                print(f"  - {step['name']} (valid name without spaces)")
                if 'depends_on' in step:
                    print(f"    Dependencies: {step['depends_on']}")
    
    return refined_workflow if not validation['valid'] else None


async def example_session_continuity():
    """Example 5: Building complex workflows iteratively with session continuity."""
    print("\n" + "="*60)
    print("Example 5: Session Continuity - Iterative Workflow Building")
    print("="*60)
    
    from kubiya_workflow_sdk import KubiyaClient
    from kubiya_workflow_sdk.providers import get_provider
    
    client = KubiyaClient(api_key=os.getenv("KUBIYA_API_KEY", "mock"))
    provider = get_provider("adk", client=client)
    
    # Use consistent session and user IDs
    session_id = f"iterative-build-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    user_id = "demo-builder"
    
    print(f"Session ID: {session_id}")
    print("Building a complex workflow step by step...\n")
    
    # Step 1: Basic workflow
    print("1. Creating basic web app deployment...")
    workflow_v1 = provider.generate_workflow(
        task="Create a workflow to deploy a Python Flask web application",
        session_id=session_id,
        user_id=user_id
    )
    print(f"   Created: {workflow_v1['name']}")
    print(f"   Steps: {len(workflow_v1.get('steps', []))}")
    
    # Step 2: Add database
    print("\n2. Adding database setup to the workflow...")
    workflow_v2 = provider.generate_workflow(
        task="Add PostgreSQL database setup and migration steps to the workflow",
        session_id=session_id,
        user_id=user_id
    )
    print(f"   Updated: {workflow_v2['name']}")
    print(f"   Steps: {len(workflow_v2.get('steps', []))}")
    
    # Step 3: Add monitoring
    print("\n3. Adding monitoring and alerting...")
    workflow_v3 = provider.generate_workflow(
        task="Add Prometheus monitoring and PagerDuty alerting to the deployment",
        session_id=session_id,
        user_id=user_id
    )
    print(f"   Updated: {workflow_v3['name']}")
    print(f"   Steps: {len(workflow_v3.get('steps', []))}")
    
    # Step 4: Add rollback
    print("\n4. Adding rollback capability...")
    workflow_final = provider.generate_workflow(
        task="Add automatic rollback on health check failures with notification",
        session_id=session_id,
        user_id=user_id
    )
    
    print(f"\nFinal workflow: {workflow_final['name']}")
    print(f"Total steps: {len(workflow_final.get('steps', []))}")
    
    # Display evolution
    print("\nWorkflow evolution:")
    print(f"  Basic deployment: {len(workflow_v1.get('steps', []))} steps")
    print(f"  + Database: {len(workflow_v2.get('steps', []))} steps")
    print(f"  + Monitoring: {len(workflow_v3.get('steps', []))} steps")
    print(f"  + Rollback: {len(workflow_final.get('steps', []))} steps")
    
    return workflow_final


async def example_vercel_streaming():
    """Example 6: Vercel AI SDK format streaming."""
    print("\n" + "="*60)
    print("Example 6: Vercel AI SDK Format Streaming")
    print("="*60)
    
    from kubiya_workflow_sdk import KubiyaClient
    from kubiya_workflow_sdk.providers import get_provider
    
    client = KubiyaClient(api_key=os.getenv("KUBIYA_API_KEY", "mock"))
    provider = get_provider("adk", client=client)
    
    task = "Create a workflow for blue-green deployment with traffic shifting"
    
    print(f"Task: {task}")
    print("Streaming with Vercel AI SDK format...\n")
    
    event_types = {"text": 0, "tool_call": 0, "tool_result": 0, "finish": 0}
    
    async for event in provider.generate_workflow(
        task=task,
        stream=True,
        stream_format="vercel",
        context={
            "deployment_type": "blue-green",
            "traffic_steps": [25, 50, 75, 100]
        }
    ):
        if event.strip() and event.startswith("data: "):
            try:
                data = json.loads(event[6:])
                event_type = data.get("type", "unknown")
                event_types[event_type] = event_types.get(event_type, 0) + 1
                
                # Display different event types
                if event_type == "text":
                    print(f"[TEXT] {data.get('content', '')[:100]}...")
                elif event_type == "tool_call":
                    print(f"[TOOL_CALL] {data.get('name', 'unknown')} - {data.get('id', '')}")
                elif event_type == "tool_result":
                    print(f"[TOOL_RESULT] {data.get('name', 'unknown')} - {data.get('id', '')}")
                elif event_type == "finish":
                    print(f"[FINISH] Reason: {data.get('finishReason', 'unknown')}")
                    
            except json.JSONDecodeError:
                pass
    
    print("\nEvent summary:")
    for event_type, count in event_types.items():
        if count > 0:
            print(f"  {event_type}: {count}")
    
    return event_types


async def main():
    """Run all examples."""
    if not check_environment():
        return
    
    print("\n" + "="*60)
    print("ADK Provider End-to-End Examples with Together AI")
    print("="*60)
    
    try:
        # Make sure ADK is available
        from kubiya_workflow_sdk.providers.adk.agents import ADK_AVAILABLE
        if not ADK_AVAILABLE:
            print("\nError: Google ADK is not installed.")
            print("Install with: pip install kubiya-workflow-sdk[adk]")
            return
        
        # Run examples
        examples = [
            ("Basic Generation", example_basic_generation),
            ("Streaming Generation", example_streaming_generation),
            ("Platform Context", example_with_platform_context),
            ("Refinement Loop", example_refinement_loop),
            ("Session Continuity", example_session_continuity),
            ("Vercel AI Format", example_vercel_streaming)
        ]
        
        results = {}
        for name, example_func in examples:
            try:
                print(f"\nRunning: {name}")
                result = await example_func()
                results[name] = "✅ Success"
            except Exception as e:
                logger.error(f"Example '{name}' failed: {e}")
                results[name] = f"❌ Failed: {str(e)}"
        
        # Summary
        print("\n" + "="*60)
        print("Summary")
        print("="*60)
        for name, status in results.items():
            print(f"{name}: {status}")
        
        print("\n✅ Examples completed!")
        print("\nNext steps:")
        print("1. Try modifying the task descriptions")
        print("2. Experiment with different context parameters")
        print("3. Use different streaming formats")
        print("4. Build complex workflows iteratively")
        
    except Exception as e:
        logger.error(f"Failed to run examples: {e}")
        print("\nMake sure you have installed the ADK dependencies:")
        print("  pip install kubiya-workflow-sdk[adk]")


if __name__ == "__main__":
    asyncio.run(main()) 