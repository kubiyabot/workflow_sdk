# Kubiya Workflow SDK Providers

The Kubiya Workflow SDK provides a powerful provider architecture that allows agentic frameworks to generate intelligent workflows using the SDK's Python API.

## Overview

Providers extend the Kubiya SDK with capabilities to:
- Generate workflows using AI agents and the SDK's fluent API
- Validate workflows using SDK's built-in validation
- Refine workflows based on errors
- Stream responses in SSE or Vercel AI SDK format

## Available Providers

### ADK Provider

The ADK (Agent Development Kit) provider uses Google's ADK framework with Together AI models to intelligently generate Kubiya workflows.

#### Features

- **SDK-Based Generation**: Generates Python code using the Kubiya SDK's fluent API
- **Intelligent Compilation**: Executes the Python code and validates using SDK
- **Error Refinement**: Automatically fixes compilation and validation errors
- **Multiple Model Support**: Together AI (default), Google AI, Vertex AI
- **Streaming Support**: SSE and Vercel AI SDK formats
- **Platform Integration**: Loads runners, integrations, and secrets from Kubiya

#### Installation

```bash
pip install kubiya-workflow-sdk[adk]
```

#### Usage

```python
from kubiya_workflow_sdk import KubiyaClient
from kubiya_workflow_sdk.providers import get_provider

# Initialize client
client = KubiyaClient(api_key="your-api-key", org_name="your-org")

# Get ADK provider
provider = get_provider("adk", client=client)

# Generate a workflow
result = provider.generate_workflow(
    task="Create a workflow to deploy a container to Kubernetes",
    context={"namespace": "production"}
)

# The result is a workflow dictionary (JSON)
print(result)
```

#### How It Works

1. **Context Loading**: The provider first loads platform context (runners, integrations, secrets)
2. **Code Generation**: AI agents generate Python code using the SDK's fluent API:
   ```python
   from kubiya_workflow_sdk.dsl import chain
   
   workflow = (
       chain("deploy-container")
       .description("Deploy container to Kubernetes")
       .runner("default-runner")
       .step("deploy", "kubectl apply -f deployment.yaml")
   )
   ```
3. **Compilation**: The Python code is executed to create a Workflow object
4. **Validation**: The workflow is validated using `workflow.validate()`
5. **Refinement**: If errors occur, the refinement agent fixes them
6. **Output**: The final workflow is returned as JSON

#### Configuration

Configure the ADK provider with environment variables:

```bash
# Model provider (default: together_ai)
export ADK_MODEL_PROVIDER=together_ai
export TOGETHER_API_KEY=your-key

# Or use Google AI
export ADK_MODEL_PROVIDER=google_ai
export GOOGLE_API_KEY=your-key

# Other options
export ADK_ENABLE_DEBUG=true
export ADK_MAX_REFINEMENT_ITERATIONS=5
```

Or programmatically:

```python
from kubiya_workflow_sdk.providers.adk import ADKConfig

config = ADKConfig(
    model_provider="together_ai",
    enable_streaming=True,
    max_refinement_iterations=5
)

provider = get_provider("adk", client=client, config=config)
```

#### Streaming Responses

Enable streaming for real-time feedback:

```python
# SSE format
response = provider.generate_workflow(
    task="Deploy app",
    stream=True,
    stream_format="sse"
)

for event in response:
    print(event)  # SSE formatted events

# Vercel AI SDK format
response = provider.generate_workflow(
    task="Deploy app", 
    stream=True,
    stream_format="vercel"
)
```

## Creating Custom Providers

To create a custom provider, extend the `BaseProvider` class:

```python
from kubiya_workflow_sdk.providers.base import BaseProvider

class MyProvider(BaseProvider):
    def generate_workflow(self, task, context=None, **kwargs):
        # Your implementation
        pass
    
    def validate_workflow(self, workflow_code, context=None, **kwargs):
        # Your implementation
        pass
    
    def refine_workflow(self, workflow_code, errors, context=None, **kwargs):
        # Your implementation
        pass
```

Register your provider:

```python
from kubiya_workflow_sdk.providers import register_provider

register_provider("my_provider", MyProvider)
```

## Examples

### Basic Workflow Generation

```python
# Generate a simple backup workflow
workflow = provider.generate_workflow(
    "Create a daily database backup workflow"
)

# Generated workflow (JSON):
# {
#   "name": "daily-db-backup",
#   "description": "Daily database backup workflow",
#   "schedule": "0 2 * * *",
#   "steps": [
#     {
#       "name": "backup",
#       "command": "pg_dump -h localhost -d mydb > backup.sql"
#     }
#   ]
# }
```

### Complex Multi-Step Workflow

```python
# Generate a complex deployment workflow
workflow = provider.generate_workflow(
    """Create a workflow to:
    1. Run tests
    2. Build Docker image
    3. Push to registry
    4. Deploy to Kubernetes
    """,
    context={
        "image": "myapp:latest",
        "registry": "docker.io/myorg"
    }
)
```

### Workflow Validation

```python
# Validate existing workflow code
validation = provider.validate_workflow(
    workflow_code='''
    from kubiya_workflow_sdk.dsl import chain
    
    workflow = chain("test")
    .step("echo", "echo hello")
    '''
)

if not validation["valid"]:
    print("Errors:", validation["errors"])
```

### Error Refinement

```python
# Fix workflow with errors
refined = provider.refine_workflow(
    workflow_code=broken_code,
    errors=["Missing runner specification"],
    context={"available_runners": ["default-runner"]}
)
```

## Best Practices

1. **Always provide context**: Include relevant context about available resources
2. **Use specific task descriptions**: Be clear about workflow requirements
3. **Handle streaming appropriately**: Use async iteration for streaming responses
4. **Validate before deployment**: Always validate generated workflows
5. **Monitor refinement**: Track refinement iterations to avoid infinite loops

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
2. **API key issues**: Check environment variables are set correctly
3. **Model timeouts**: Increase timeout settings for complex workflows
4. **Validation failures**: Review platform context and available resources

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export ADK_ENABLE_DEBUG=true
```

## API Reference

See the [API documentation](../api/providers.md) for detailed reference. 