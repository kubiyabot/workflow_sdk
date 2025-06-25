# Kubiya MCP Server

A production-ready MCP (Model Context Protocol) server for Kubiya workflows with intelligent DSL generation, real-time execution streaming, and Docker-focused automation.

## Features

- **Smart DSL Generation**: Context-aware workflow compilation with runner and integration suggestions
- **Real-time Execution**: Stream workflow execution events as they happen
- **Docker-First**: Extensive Docker image recommendations and templates
- **Authentication**: Built-in support for API keys via headers, parameters, or environment
- **Rich Context**: Access to runners, integrations, and best practices
- **Developer-Friendly**: Comprehensive examples and workflow patterns

## Installation

```bash
pip install kubiya-workflow-sdk
```

## Quick Start

### 1. Set up authentication

```bash
export KUBIYA_API_KEY="your-api-key-here"
```

### 2. Run the server

```bash
# Standard MCP stdio mode
python -m kubiya_workflow_sdk.mcp.server

# HTTP mode for web deployments
python -m kubiya_workflow_sdk.mcp.server --transport http --port 8000

# With custom configuration
python -m kubiya_workflow_sdk.mcp.server \
  --name "My Workflow Server" \
  --runner "my-custom-runner" \
  --base-url "https://api.kubiya.ai"
```

### 3. Connect with a client

```python
from fastmcp import Client
import asyncio

async def main():
    # Connect to the server
    async with Client("http://localhost:8000") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Compile a workflow
        result = await client.call_tool(
            "compile_workflow",
            dsl_code="""
from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("hello-docker")
wf.description("Hello world with Docker")
wf.step("greet").docker(
    image="python:3.11-slim",
    script='print("Hello from Docker!")'
)
"""
        )
        print(f"Compilation: {result}")

asyncio.run(main())
```

## Available Tools

### compile_workflow
Compile DSL code into a workflow JSON manifest with validation and suggestions.

```python
result = await client.call_tool(
    "compile_workflow",
    dsl_code="...",
    name="optional-override",
    description="optional-description",
    runner="specific-runner",
    prefer_docker=True
)
```

### execute_workflow
Execute a workflow with real-time streaming of events.

```python
# Execute from DSL
async for event in client.call_tool_stream(
    "execute_workflow",
    workflow_input="... DSL code ...",
    params={"key": "value"},
    stream_format="vercel"  # or "raw"
):
    print(event)

# Execute from compiled manifest
async for event in client.call_tool_stream(
    "execute_workflow",
    workflow_input=compiled_manifest,
    params={"key": "value"}
):
    print(event)
```

### get_workflow_runners
Get available runners with capabilities and recommendations.

```python
runners = await client.call_tool(
    "get_workflow_runners",
    refresh=True
)
print(f"Available runners: {runners['runners']}")
print(f"Docker-enabled: {runners['recommendations']['docker_workflows']}")
```

### get_integrations
Get available integrations and Docker image suggestions.

```python
integrations = await client.call_tool(
    "get_integrations",
    category="python",  # optional filter
    refresh=True
)
print(f"Python Docker images: {integrations['docker_images']['python']}")
```

## Workflow DSL Examples

### Simple Shell Workflow
```python
from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("simple-task")
wf.description("A simple shell workflow")
wf.step("hello", "echo 'Hello, World!'")
wf.step("date", "date")
```

### Docker-Based Data Processing
```python
wf = Workflow("data-processor")
wf.description("Process CSV data with pandas")
wf.params(
    csv_url={"required": True, "description": "URL of CSV file"},
    output_format={"default": "json", "description": "json or csv"}
)

# Download data
wf.step("download").docker(
    image="alpine/curl",
    command="curl -L -o data.csv {{csv_url}}"
)

# Process with pandas
wf.step("process").docker(
    image="jupyter/scipy-notebook:latest",
    script='''
import pandas as pd

df = pd.read_csv("data.csv")
result = df.describe()

if "{{output_format}}" == "json":
    print(result.to_json())
else:
    print(result.to_csv())
'''
).depends_on("download")
```

### Parallel Processing
```python
wf = Workflow("parallel-tasks")
wf.description("Run tasks in parallel")

with wf.parallel_steps():
    wf.step("task1").docker(
        image="python:3.11-slim",
        command="python -c 'print(\"Task 1\")'"
    )
    wf.step("task2").docker(
        image="node:20-slim",
        command="node -e 'console.log(\"Task 2\")'"
    )
    wf.step("task3", "echo 'Task 3'")

wf.step("combine", "echo 'All tasks complete'")
```

### Error Handling
```python
wf = Workflow("resilient-workflow")
wf.description("Workflow with error handling")

# Retry on failure
wf.step("api-call", "curl https://api.example.com").retry(
    max_attempts=3,
    delay_seconds=5
)

# Continue on failure
wf.step("optional", "might-fail").continue_on("failure")

# Conditional error handling
wf.step("on-error", "send-alert.sh").condition("{{api-call.status}} == 'failed'")

# Always run cleanup
wf.step("cleanup", "rm -f temp/*").continue_on("any")
```

## Authentication

The server supports multiple authentication methods:

1. **Environment Variable** (recommended for development):
   ```bash
   export KUBIYA_API_KEY="your-key"
   ```

2. **HTTP Headers** (for web deployments):
   ```
   Authorization: Bearer your-key
   Authorization: UserKey your-key
   ```

3. **Tool Parameters** (for per-request auth):
   ```python
   await client.call_tool(
       "execute_workflow",
       workflow_input="...",
       api_key="your-key"
   )
   ```

## Docker Image Recommendations

The server provides intelligent Docker image suggestions:

- **Python**: `python:3.11-slim`, `jupyter/scipy-notebook`
- **Node.js**: `node:20-slim`, `node:20-alpine`
- **Data Science**: `tensorflow/tensorflow`, `pytorch/pytorch`
- **Cloud CLIs**: `amazon/aws-cli`, `google/cloud-sdk`
- **Databases**: `postgres:15-alpine`, `mysql:8.0`, `mongo:7.0`

## Resources and Prompts

The server includes built-in resources and prompts:

### Resources
- `workflow://examples/hello-world`
- `workflow://examples/docker-python`
- `workflow://examples/parallel-processing`
- `workflow://examples/ci-cd-pipeline`
- `workflow://examples/data-pipeline`
- `workflow://templates/docker-commands`
- `workflow://templates/patterns`
- `workflow://best-practices`
- `workflow://docker-images`

### Prompts
- `workflow_dsl_guide` - Generate DSL guide for a task
- `docker_workflow_examples` - Get Docker examples by use case
- `workflow_patterns` - Common workflow patterns

## Best Practices

1. **Use Docker for Complex Tasks**: Better isolation and reproducibility
2. **Meaningful Names**: Use kebab-case for workflows, descriptive step names
3. **Error Handling**: Add retry logic and cleanup steps
4. **Parameters**: Provide defaults and descriptions
5. **Security**: Never hardcode secrets, use parameters
6. **Performance**: Run independent steps in parallel

## Development

### Running Tests
```bash
pytest tests/mcp/
```

### Debug Mode
```bash
export KUBIYA_LOG_LEVEL=DEBUG
python -m kubiya_workflow_sdk.mcp.server
```

## Architecture

The server is built with:
- **FastMCP**: MCP protocol implementation
- **Context Managers**: Runner and integration awareness
- **Streaming Support**: Real-time execution events
- **Authentication**: Flexible auth methods
- **Caching**: Efficient client management

## Contributing

Contributions are welcome! Please see the main project's contributing guidelines.

## License

See the main project LICENSE file. 