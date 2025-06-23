"""Base classes and utilities for ADK agents."""

import os
import json
import logging
import sys
from typing import Dict, Any, Optional, List, Union, Set
from datetime import datetime
import uuid
from dataclasses import dataclass

# Fix AsyncIterator import for Python 3.9
if sys.version_info >= (3, 9):
    from collections.abc import AsyncIterator
else:
    from typing import AsyncIterator

# Type stubs for ADK components
try:
    from google.adk.agents import LlmAgent, BaseAgent, Agent
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
    from google.adk.events.event import Event
    from google.adk.events.event_actions import EventActions
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.adk.sessions import Session
    from google.adk.tools import FunctionTool
    from google.genai import types
    from google.genai.types import GenerateContentConfig
    ADK_AVAILABLE = True
except ImportError:
    # Create stub classes for type hints
    class LlmAgent:
        pass
    class BaseAgent:
        pass
    class CallbackContext:
        pass
    class InvocationContext:
        pass
    class Event:
        pass
    class EventActions:
        pass
    class LlmRequest:
        pass
    class LlmResponse:
        pass
    class Session:
        pass
    class InMemoryArtifactService:
        pass
    class FunctionTool:
        pass
    class types:
        class Part:
            @staticmethod
            def from_bytes(data, mime_type):
                pass
        class Content:
            pass
    class GenerateContentConfig:
        pass
    ADK_AVAILABLE = False

from ..config import ADKConfig

logger = logging.getLogger(__name__)


def _get_model_for_agent(config: ADKConfig, agent_role: str) -> Any:
    """Get the model configuration for a specific agent role."""
    model_name = config.get_model_for_role(agent_role)
    
    # Wrap all models with LiteLlm for universal compatibility
    try:
        from google.adk.models.lite_llm import LiteLlm
        logger.debug(f"Wrapping model '{model_name}' with LiteLlm for agent role '{agent_role}'")
        return LiteLlm(model=model_name)
    except ImportError:
        logger.warning(f"LiteLlm not available, using model name directly: {model_name}")
        return model_name


def _get_default_generate_config() -> Any:
    """Get default GenerateContentConfig for agents."""
    if ADK_AVAILABLE:
        # Create a default config with basic settings
        return GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_modalities=["TEXT"]  # This is what was missing!
        )
    return None


def get_docker_registry_context() -> str:
    """Get Docker registry configuration from environment variables."""
    registries = os.environ.get("DOCKER_REGISTRIES", "hub.docker.com").split(",")
    registries = [r.strip() for r in registries if r.strip()]
    
    registry_context = f"""
Docker Container Configuration:
- Trusted registries: {', '.join(registries)}
- Default registry: {registries[0] if registries else 'hub.docker.com'}
- All Docker images must be from these trusted registries
- Prefer official images when available (e.g., python:3.9-alpine, node:18-alpine, ubuntu:22.04)
"""
    
    # Add specific image recommendations
    recommendations = {
        "python": "python:3.9-alpine, python:3.11-slim",
        "node": "node:18-alpine, node:20-alpine", 
        "kubectl": "bitnami/kubectl:latest, kubiya/kubectl-light:latest",
        "aws": "amazon/aws-cli:latest, amazon/aws-cli:2.x.x",
        "terraform": "hashicorp/terraform:latest, hashicorp/terraform:1.6",
        "ansible": "ansible/ansible-runner:latest",
        "curl": "curlimages/curl:latest, appropriate/curl:latest",
        "git": "alpine/git:latest, bitnami/git:latest",
        "jq": "stedolan/jq:latest, ghcr.io/jqlang/jq:latest",
        "database": "postgres:15-alpine, mysql:8.0, mongo:7.0, redis:7-alpine"
    }
    
    registry_context += "\nRecommended Docker images by use case:\n"
    for use_case, images in recommendations.items():
        registry_context += f"- {use_case}: {images}\n"
    
    return registry_context


def get_dsl_context() -> str:
    """Get comprehensive DSL context for workflow generation."""
    return """
# Kubiya Workflow SDK DSL Guide

The Kubiya SDK provides a powerful, chainable DSL for creating workflows. Here's how to use it effectively:

## Core Concepts

1. **Workflows**: Container for steps with configuration
   ```python
   from kubiya_workflow_sdk import Workflow
   
   wf = Workflow("my-workflow")
       .description("Process data files")
       .runner("my-runner")  # Specify the runner
       .env(LOG_LEVEL="info")  # Environment variables
       .params(DATE="${{ctx.param('date')}}")  # Parameters with dynamic values
   ```

2. **Steps**: Individual units of work
   - Basic command: `wf.step("name", "echo hello")`
   - With tool: `wf.step("name").tool("kubectl", namespace="default")`
   - With Docker: See Docker tools section below

3. **Tool Steps**: The most powerful feature for complex operations
   
   Tool steps execute in Docker containers and can:
   - Run any script/program in an isolated environment
   - Mount files and secrets securely
   - Connect to bounded services (databases, caches, etc.)
   - Return structured output

## Docker-Based Tool Steps

Tool steps are the recommended way to execute complex operations:

```python
# Method 1: Inline tool definition
wf.step("process-data")
  .tool_def(
      name="data-processor",
      type="docker",
      image="python:3.9-alpine",
      content='''#!/bin/sh
set -e
pip install pandas numpy
python << 'EOF'
import pandas as pd
import json
# Your Python code here
print(json.dumps({"status": "success"}))
EOF
''',
      args=[
          {"name": "input_file", "type": "string", "required": True},
          {"name": "output_format", "type": "string", "default": "csv"}
      ]
  )
  .args(input_file="data.csv", output_format="json")
  .output("PROCESS_RESULT")

# Method 2: Using pre-registered tools
wf.step("deploy")
  .tool("kubectl", command="apply -f deployment.yaml", namespace="production")
```

## Bounded Services

Tools can include bounded services (databases, caches, message queues) that run alongside the main container:

```python
wf.step("test-api")
  .tool_def(
      name="api-tester",
      type="docker", 
      image="python:3.9-alpine",
      content='''#!/bin/sh
# Wait for database
for i in $(seq 1 30); do
    if nc -z database 5432; then
        echo "Database is ready"
        break
    fi
    sleep 1
done

# Run tests
pip install psycopg2-binary requests
python test_api.py
''',
      args=[],
      with_services=[
          {
              "name": "database",
              "image": "postgres:15-alpine",
              "exposed_ports": [5432],
              "env": {
                  "POSTGRES_DB": "testdb",
                  "POSTGRES_USER": "testuser",
                  "POSTGRES_PASSWORD": "testpass"
              }
          },
          {
              "name": "redis",
              "image": "redis:7-alpine", 
              "exposed_ports": [6379]
          }
      ]
  )
```

Services are accessible by their name as hostname within the tool container.

## Integration Patterns

### Kubernetes Integration
```python
wf.step("get-pods")
  .tool_def(
      name="k8s-reader",
      type="docker",
      image="bitnami/kubectl:latest",
      content='''#!/bin/sh
kubectl get pods -o json | jq '.items[] | {name: .metadata.name, status: .status.phase}'
''',
      args=[{"name": "namespace", "type": "string", "default": "default"}],
      with_files=[
          {"source": "/var/run/secrets/kubernetes.io/serviceaccount/token", "destination": "/tmp/token"},
          {"source": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt", "destination": "/tmp/ca.crt"}
      ]
  )
  .args(namespace="{{ctx.param('namespace')}}")
```

### AWS Integration
```python
wf.step("list-s3")
  .tool_def(
      name="aws-s3-lister",
      type="docker",
      image="amazon/aws-cli:latest",
      content="aws s3 ls s3://{{bucket_name}}/",
      args=[{"name": "bucket_name", "type": "string", "required": True}],
      env=["AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
  )
```

## Best Practices

1. **Always use set -e in shell scripts** to exit on errors
2. **Output JSON for structured data** that can be captured with .output()
3. **Use alpine-based images** when possible for smaller size
4. **Pin image versions** for reproducibility (e.g., python:3.9-alpine not python:alpine)
5. **Use bounded services** instead of external dependencies when possible
6. **Validate inputs** in your scripts before processing
7. **Handle errors gracefully** and provide meaningful error messages

## Dynamic Values and Context

Use template variables for dynamic values:
- `{{ctx.param('name')}}` - Workflow parameters
- `{{ctx.env('KEY')}}` - Environment variables  
- `{{steps.step_name.output}}` - Output from previous steps
- `{{ctx.secrets('secret_name')}}` - Secret values

## Workflow Compilation

After building the workflow with the DSL, compile it to JSON:

```python
# Build workflow
wf = Workflow("my-workflow")
    .description("My workflow")
    .step("step1", "echo hello")
    .step("step2", "echo world")

# Compile to JSON
workflow_json = wf.to_json()
```

The JSON format is what gets submitted to the Kubiya platform for execution.
"""


@dataclass
class MissingContext:
    """Track missing context during workflow generation."""
    missing_resources: Set[str]
    missing_capabilities: Set[str]


@dataclass
class WorkflowGenerationResult:
    """Result of workflow generation."""
    success: bool
    workflow_code: Optional[str] = None
    workflow_json: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None
    missing_context: Optional[MissingContext] = None


@dataclass
class WorkflowExecutionResult:
    """Result of workflow execution."""
    success: bool
    execution_id: Optional[str] = None
    outputs: Dict[str, Any] = None
    errors: List[str] = None
    logs: List[str] = None
    duration_seconds: Optional[float] = None


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    valid: bool
    meets_requirements: bool
    missing_requirements: List[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    suggestions: List[str] = None 