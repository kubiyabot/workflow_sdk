# ADK Provider for Kubiya Workflow SDK

The ADK (Agent Development Kit) Provider brings Google's Agent Development Kit agentic framework capabilities to the Kubiya Workflow SDK, enabling intelligent workflow generation and execution through natural language.

## Overview

The ADK Provider integrates Google's Agent Development Kit with the Kubiya platform, leveraging state-of-the-art language models through Together AI to create, validate, refine, and execute workflows. This provider transforms natural language requirements into production-ready workflows with built-in error handling and self-refinement capabilities.

### Key Features

- **Natural Language to Workflow**: Convert plain English requirements into Kubiya workflows
- **Intelligent Context Loading**: Automatically discovers and uses platform resources
- **Self-Refinement Loop**: Automatically fixes compilation errors and validates workflows
- **Streaming Support**: Real-time feedback with SSE and Vercel AI SDK formats
- **Artifact Management**: Persistent storage of workflows and execution results
- **Multi-Model Support**: Configurable AI models with Together AI as default provider
- **Production Ready**: Comprehensive error handling and validation

## Installation

Install the Kubiya Workflow SDK with ADK support:

```bash
pip install kubiya-workflow-sdk[adk]
```

Or install from source:

```bash
git clone https://github.com/kubiya-ai/workflow-sdk
cd workflow-sdk
pip install -e .[adk]
```

### Dependencies

The ADK provider requires:
- Python 3.8+
- Google ADK (`google-adk`)
- Google Generative AI (`google-generativeai`)
- LiteLLM for model provider abstraction
- Together AI Python client

## Configuration

### Environment Variables

Create a `.env` file or export these variables:

```bash
# Required: Together AI API key for model access
TOGETHER_API_KEY=your-together-api-key

# Optional: Alternative model providers
GOOGLE_API_KEY=your-google-api-key  # For Google AI models
VERTEX_PROJECT_ID=your-project-id   # For Vertex AI models
VERTEX_LOCATION=us-central1         # Vertex AI region

# Optional: Model overrides
ADK_ORCHESTRATOR_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
ADK_WORKFLOW_GENERATOR_MODEL=deepseek-ai/DeepSeek-V3
ADK_REFINEMENT_MODEL=deepseek-ai/DeepSeek-R1

# Optional: ADK configuration
ADK_MAX_REFINEMENT_ITERATIONS=3
ADK_MODEL_PROVIDER=together  # Options: together, google, vertex
```

### Programmatic Configuration

```python
from kubiya_workflow_sdk.providers.adk import ADKConfig, ModelProvider

# Custom configuration
config = ADKConfig(
    model_provider=ModelProvider.TOGETHER,
    model_overrides={
        "orchestrator": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "workflow_generator": "deepseek-ai/DeepSeek-V3"
    }
)
```

## Quick Start

### Basic Workflow Generation

```python
from kubiya_workflow_sdk import KubiyaClient
from kubiya_workflow_sdk.providers import get_provider

# Initialize client and provider
client = KubiyaClient(api_key="your-kubiya-api-key")
provider = get_provider("adk", client=client)

# Generate a workflow from natural language
workflow = provider.generate_workflow(
    task="Deploy my application to Kubernetes with health checks",
    context={"environment": "production"}
)

print(f"Generated workflow: {workflow['name']}")
print(f"Steps: {len(workflow['steps'])}")
```

### Streaming Workflow Generation

```python
import asyncio

async def stream_workflow_generation():
    # Stream generation with real-time feedback
    async for event in provider.generate_workflow(
        task="Create a CI/CD pipeline for Node.js application",
        stream=True,
        stream_format="sse"  # or "vercel" for Vercel AI SDK format
    ):
        print(event, end="", flush=True)

asyncio.run(stream_workflow_generation())
```

### Workflow Execution with Streaming

```python
async def execute_with_streaming():
    # Generate workflow first
    workflow = provider.generate_workflow(
        task="Run database backup and upload to S3"
    )
    
    # Execute with streaming output
    async for event in provider.execute_workflow(
        workflow=workflow,
        parameters={"database": "production_db"},
        stream=True
    ):
        print(event, end="", flush=True)

asyncio.run(execute_with_streaming())
```

## Advanced Usage

### Session Management and Continuity

```python
# Use session IDs for conversation continuity
session_id = "user-session-123"
user_id = "user-456"

# First request
workflow1 = provider.generate_workflow(
    task="Create a deployment workflow",
    session_id=session_id,
    user_id=user_id
)

# Follow-up request uses context from previous interaction
workflow2 = provider.generate_workflow(
    task="Add rollback capability to the previous workflow",
    session_id=session_id,
    user_id=user_id
)
```

### Custom Artifact Storage

```python
from google.adk.artifacts import GcsArtifactService

# Use Google Cloud Storage for persistent artifacts
artifact_service = GcsArtifactService(bucket_name="my-workflow-artifacts")

provider = get_provider(
    "adk",
    client=client,
    artifact_service=artifact_service
)
```

### Error Handling and Refinement

```python
# Manual workflow refinement
workflow_code = """
from kubiya_workflow_sdk.dsl import Workflow, Step
# ... workflow with errors ...
"""

# Validate workflow
validation = provider.validate_workflow(workflow_code)
if not validation["valid"]:
    # Automatically refine to fix errors
    refined_workflow = provider.refine_workflow(
        workflow_code=workflow_code,
        errors=validation["errors"]
    )
    print(f"Refined workflow: {refined_workflow['name']}")
```

### Direct Python Code Execution

```python
# Execute workflow from Python code
workflow_code = """
from kubiya_workflow_sdk.dsl import Workflow, Step
from kubiya_workflow_sdk.dsl.executors import BashExecutor

workflow = Workflow("system_check")
workflow.add_step(Step(
    name="check_disk",
    executor=BashExecutor(script="df -h")
))
"""

result = await provider.execute_workflow(
    workflow=workflow_code,
    stream=False
)
print(f"Execution result: {result}")
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────┐
│                   ADK Provider                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ Orchestrator│  │  Workflow   │  │  Compiler  │ │
│  │    Agent    │─▶│  Generator  │─▶│   Agent    │ │
│  └─────────────┘  └─────────────┘  └────────────┘ │
│         │                                    │      │
│         │         ┌─────────────┐           │      │
│         └────────▶│ Refinement  │◀──────────┘      │
│                   │    Agent    │                  │
│                   └─────────────┘                  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │            Platform Context Tools            │  │
│  │  • Runners  • Integrations  • Secrets       │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │              Artifact Storage                │  │
│  │  • Workflows  • Code  • Results  • History  │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Agent Responsibilities

1. **Orchestrator Agent**: Coordinates the workflow generation process
2. **Context Loader Agent**: Gathers platform resources and capabilities
3. **Workflow Generator Agent**: Creates workflows using Kubiya SDK
4. **Compiler Agent**: Validates and compiles workflows to JSON
5. **Refinement Agent**: Fixes errors using advanced reasoning

### Event Flow

The provider uses ADK's event system for all communications:

```python
# Example event structure
{
    "author": "WorkflowGenerator",
    "content": {"parts": [{"text": "Generated workflow code..."}]},
    "actions": {
        "artifact_delta": {"generated_workflow.py": 1},
        "state_delta": {"workflow_status": "generated"}
    }
}
```

## Best Practices

### 1. Use Descriptive Task Descriptions

```python
# ❌ Too vague
provider.generate_workflow("deploy app")

# ✅ Descriptive with context
provider.generate_workflow(
    task="Deploy Node.js application to Kubernetes with rolling updates, health checks, and automatic rollback on failure",
    context={
        "app_name": "my-api",
        "namespace": "production",
        "replicas": 3
    }
)
```

### 2. Handle Streaming Properly

```python
async def handle_streaming():
    events = []
    async for event in provider.generate_workflow(task="...", stream=True):
        events.append(event)
        # Process event in real-time
        if "error" in event:
            # Handle errors immediately
            break
    return events
```

### 3. Leverage Session Continuity

```python
# Build complex workflows iteratively
session_id = "build-session"

# Step 1: Basic workflow
base = provider.generate_workflow(
    "Create basic web server deployment",
    session_id=session_id
)

# Step 2: Add monitoring
with_monitoring = provider.generate_workflow(
    "Add Prometheus monitoring to the deployment",
    session_id=session_id
)

# Step 3: Add CI/CD
complete = provider.generate_workflow(
    "Add GitOps CI/CD pipeline with ArgoCD",
    session_id=session_id
)
```

### 4. Use Appropriate Models

Different models excel at different tasks:

- **Orchestration**: Meta-Llama 3.1 70B (default)
- **Code Generation**: DeepSeek V3 (optimized for code)
- **Refinement**: DeepSeek R1 (advanced reasoning)
- **Fast Tasks**: Gemini 2.0 Flash

### 5. Monitor Token Usage

```python
# Together AI provides usage information
config = ADKConfig(
    model_provider=ModelProvider.TOGETHER,
    log_token_usage=True  # Enable token logging
)
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure ADK dependencies are installed
   pip install kubiya-workflow-sdk[adk] --upgrade
   ```

2. **API Key Issues**
   ```python
   # Verify API key is set
   import os
   assert os.getenv("TOGETHER_API_KEY"), "Together AI API key not set"
   ```

3. **Model Availability**
   ```python
   # Check available models
   from litellm import list_models
   print(list_models(provider="together"))
   ```

4. **Streaming Interruptions**
   ```python
   # Add timeout and retry logic
   async def safe_stream(provider, task, max_retries=3):
       for attempt in range(max_retries):
           try:
               async for event in provider.generate_workflow(task, stream=True):
                   yield event
               break
           except Exception as e:
               if attempt == max_retries - 1:
                   raise
               await asyncio.sleep(2 ** attempt)
   ```

### Debug Mode

Enable detailed logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("kubiya_workflow_sdk.providers.adk")

# Or use environment variable
os.environ["ADK_DEBUG"] = "true"
```

## API Reference

### Provider Methods

#### `generate_workflow(task, context=None, stream=False, stream_format="sse", session_id=None, user_id=None, **kwargs)`

Generate a workflow from natural language description.

**Parameters:**
- `task` (str): Natural language description of the desired workflow
- `context` (dict, optional): Additional context for generation
- `stream` (bool): Enable streaming response
- `stream_format` (str): Format for streaming ("sse" or "vercel")
- `session_id` (str, optional): Session ID for conversation continuity
- `user_id` (str, optional): User ID for artifact namespacing

**Returns:**
- Without streaming: Dict containing the generated workflow
- With streaming: AsyncGenerator yielding formatted events

#### `execute_workflow(workflow, parameters=None, stream=True, stream_format="sse", user_id=None, session_id=None, **kwargs)`

Execute a workflow with optional streaming.

**Parameters:**
- `workflow` (str|dict): Workflow dict, name/ID, or Python code
- `parameters` (dict, optional): Workflow execution parameters
- `stream` (bool): Enable streaming response
- `stream_format` (str): Format for streaming
- `user_id` (str, optional): User ID for artifact storage
- `session_id` (str, optional): Session ID for continuity

**Returns:**
- Without streaming: Dict containing execution results
- With streaming: AsyncGenerator yielding execution events

#### `validate_workflow(workflow_code, context=None, **kwargs)`

Validate a workflow definition.

**Parameters:**
- `workflow_code` (str): Python code or JSON workflow definition
- `context` (dict, optional): Additional validation context

**Returns:**
- Dict with validation results: `{"valid": bool, "errors": list, "warnings": list}`

#### `refine_workflow(workflow_code, errors, context=None, user_id=None, session_id=None, **kwargs)`

Refine a workflow to fix errors.

**Parameters:**
- `workflow_code` (str): Current workflow code with errors
- `errors` (list): List of error messages to fix
- `context` (dict, optional): Additional context
- `user_id` (str, optional): User ID for artifact storage
- `session_id` (str, optional): Session ID for continuity

**Returns:**
- Dict containing the refined workflow

## Contributing

We welcome contributions to the ADK Provider! Please see our [Contributing Guide](../../../CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/kubiya-ai/workflow-sdk
cd workflow-sdk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e .[adk,dev]

# Run tests
pytest kubiya_workflow_sdk/providers/adk/tests/
```

## License

The ADK Provider is part of the Kubiya Workflow SDK and is released under the MIT License. See [LICENSE](../../../LICENSE) for details.

## Support

- **Documentation**: [https://docs.kubiya.ai/workflow-sdk](https://docs.kubiya.ai/workflow-sdk)
- **Issues**: [GitHub Issues](https://github.com/kubiya-ai/workflow-sdk/issues)
- **Discord**: [Join our community](https://discord.gg/kubiya)
- **Email**: support@kubiya.ai 