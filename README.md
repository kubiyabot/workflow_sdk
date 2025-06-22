# Kubiya Workflow SDK

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**Build Deterministic AI Workflows That Actually Work™**

[Get Started](#-quick-start) • [Documentation](https://docs.kubiya.ai) • [Examples](#-examples) • [API Reference](#-api-reference) • [Enterprise](https://kubiya.ai/enterprise)

</div>

---

## 🚀 The Future of AI is Deterministic

**Kubiya Workflow SDK** is a serverless workflow platform that transforms unpredictable AI agents into reliable, production-grade automation. Every workflow step runs as an independent Docker container, giving you the power to run ANY software while maintaining deterministic execution.

### Why We Built This

After watching teams struggle with free-wheeling agent frameworks that promise magic but deliver chaos, we took a different approach. Instead of hoping an AI will figure out the right sequence of actions, we provide the tools to **define** the right sequence – with AI filling in the intelligent parts. [Read more about our architecture →](docs/ARCHITECTURE.md)

### Core Principles

- **🐳 Serverless Containers**: Every step runs in its own Docker container - use ANY language, tool, or software
- **🎯 Deterministic Execution**: Same inputs → Same workflow → Same outputs, every time
- **🏗️ Stateless Architecture**: Each execution starts fresh with zero state pollution
- **🚀 Infinite Scale**: From 1 to 1,000,000 executions without infrastructure changes
- **🏠 Your Infrastructure**: Runs entirely on-premise with zero vendor lock-in
- **🤖 ADK Orchestration**: Powered by ADK (Agent Development Kit) for intelligent workflow orchestration

## ✨ Key Features

### 🎯 Stateless & Serverless Orchestration
```yaml
# Workflows are pure schemas - no hidden state
name: incident-response
steps:
  - name: detect
    executor: docker
    image: monitoring:latest
  - name: analyze  
    executor: inline_agent
    depends: [detect]
  - name: remediate
    executor: shell
    depends: [analyze]
```

- **Fully Stateless**: Each execution starts fresh, no drift or side effects
- **Serverless Agents**: Spin up just-in-time containers only when needed
- **Schema-Driven**: Workflows are data, not code – version control friendly

### 🔌 Universal Integration

```python
# Via Kubiya API
client.execute_workflow("deploy-app", params={"version": "2.0"})

# Via MCP Server (works with ANY agent system)
mcp_client.call_tool("kubiya_workflow", workflow="deploy-app")

# Direct in your code
result = workflow.run(params={"env": "production"})
```

- **API-First**: RESTful API with SSE streaming
- **MCP Compatible**: Integrate with Claude, ChatGPT, any MCP client
- **SDK Support**: Python, with more languages coming
- **Agent Agnostic**: Works with LangChain, AutoGPT, or custom agents

### 🏭 Production-Grade Infrastructure
- **Any Docker Container**: Run Python, Go, Rust, bash – anything
- **Kubernetes-Native**: Built for K8s, not adapted to it
- **Multi-Cluster**: Span workflows across any environment
- **Zero Changes Required**: Deploy to your existing stack

## 📦 Installation

```bash
# Basic installation
pip install kubiya-workflow-sdk

# With all features (includes server and ADK provider)
pip install kubiya-workflow-sdk[all]

# For development
pip install kubiya-workflow-sdk[dev]

# Just the ADK provider for AI workflow generation
pip install kubiya-workflow-sdk[adk]
```

### 🐳 Docker Installation

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t kubiya-sdk-server .
docker run -p 8000:8000 \
  -e KUBIYA_API_KEY=$KUBIYA_API_KEY \
  -e TOGETHER_API_KEY=$TOGETHER_API_KEY \
  kubiya-sdk-server
```

## 🤖 AI-Powered Workflow Generation with ADK

### The Power of ADK Orchestration

Kubiya SDK is powered by **ADK (Agent Development Kit)**, our intelligent orchestration provider that enables AI-powered workflow generation and execution. ADK brings multi-agent intelligence to your workflows while maintaining the deterministic, containerized execution model.

### 🐳 Every Step Runs in Docker

**This is not just another Python framework** - Kubiya executes every workflow step as a serverless Docker container:

```python
# This workflow can use ANY language or tool
workflow = KubiyaWorkflow.from_prompt(
    """
    Create a data pipeline that:
    1. Extracts data using Python pandas
    2. Transforms with Node.js 
    3. Runs statistical analysis in R
    4. Loads to database using Go
    5. Sends notification via Ruby script
    """,
    runner="kubiya-hosted"
)

# Each step runs in its own container with the right runtime
# No need to pre-install anything!
```

### Generate Workflows from Natural Language

Simply describe what you want in plain English, and ADK will generate production-ready workflows:

```python
from kubiya_workflow_sdk.providers import get_provider
import asyncio

async def generate_backup_workflow():
    # Initialize AI provider
    adk = get_provider("adk")
    
    # Describe your task in natural language
    result = await adk.compose(
        task="""
        Create a workflow that:
        1. Backs up all PostgreSQL databases
        2. Compresses the backups
        3. Uploads to S3 with encryption
        4. Sends a Slack notification when complete
        5. Cleans up backups older than 30 days
        """,
        mode="plan"  # Generate only (use "act" to also execute)
    )
    
    # Get the generated workflow
    workflow = result["workflow"]
    print(f"Generated: {workflow['name']}")
    print(f"Steps: {len(workflow['steps'])}")

asyncio.run(generate_backup_workflow())
```

### Real-Time Streaming

Watch the AI generate and execute workflows in real-time:

```python
async def deploy_with_ai():
    adk = get_provider("adk")
    
    # Stream generation and execution
    async for event in adk.compose(
        task="Deploy my Node.js app to Kubernetes with zero downtime",
        mode="act",  # Generate AND execute
        stream=True,
        parameters={
            "app_name": "my-app",
            "image": "myapp:v2.0",
            "namespace": "production"
        }
    ):
        print(event)  # Real-time updates

asyncio.run(deploy_with_ai())
```

### REST API with Compose Endpoint

The SDK server includes AI workflow generation via REST API:

```bash
# Generate a workflow from natural language
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "adk",
    "task": "Create a CI/CD pipeline that runs tests, builds Docker image, and deploys to staging",
    "mode": "plan"
  }'

# Generate and execute with streaming
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Accept: text/event-stream" \
  -d '{
    "provider": "adk",
    "task": "Check system health and restart unhealthy services",
    "mode": "act",
    "stream": true
  }'
```

[Learn more about AI-powered workflows →](docs/kubiya/providers/adk/getting-started.mdx)

## 🎯 Quick Start

### 1. Define Your Workflow

```python
from kubiya_workflow_sdk.dsl import workflow, step

# Create a deterministic AI workflow
wf = (
    workflow("automated-deployment")
    .description("Zero-touch deployment with rollback capabilities")
    .params(
        VERSION="${VERSION}",
        ENVIRONMENT="staging",
        ROLLBACK_ENABLED="true"
    )
    
    # AI-powered analysis step
    .step("analyze-risk")
    .inline_agent(
        message="Analyze deployment risk for version ${VERSION}",
        agent_name="deployment-analyzer",
        ai_instructions="You are a deployment risk analyst. Evaluate changes and provide structured risk assessment.",
        runners=["production-runner"]
    )
    .output("RISK_ANALYSIS")
    
    # Conditional deployment based on risk
    .step("deploy")
    .shell("kubectl apply -f deployment.yaml")
    .preconditions(
        {"condition": "${RISK_ANALYSIS.risk_level}", "expected": "re:(low|medium)"}
    )
    .retry(limit=3, interval_sec=60)
    
    # Automated validation
    .step("validate")
    .tool_def(
        name="health-checker",
        type="docker",
        image="kubiya/health-check:latest",
        content="#!/bin/sh\ncurl -f http://app/health || exit 1",
        args=[{"name": "endpoint", "type": "string"}]
    )
    .args(endpoint="${APP_ENDPOINT}")
)
```

### 2. Test Locally

```python
from kubiya_workflow_sdk.testing_v2 import WorkflowTest

# Test with deterministic mocks
test = WorkflowTest(wf)
test.mock_step("analyze-risk", output={"risk_level": "low"})
test.mock_step("deploy", output={"status": "success"})

result = test.run(params={"VERSION": "v2.1.0"})
test.assert_success()
```

### 3. Execute via API

```bash
# Validate workflow
kubiya validate workflow.py

# Execute workflow
kubiya run workflow.py --params VERSION=v1.0.0 ENVIRONMENT=production

# View execution results
kubiya list --status completed --limit 10
```

## 🏗️ Architecture

### Workflow Composition

```python
# Compose workflows like microservices
main_workflow = (
    workflow("platform-automation")
    .sub_workflow("provision", "infrastructure/provision.yaml")
    .sub_workflow("deploy", "apps/deploy.yaml")
    .sub_workflow("monitor", "observability/setup.yaml")
)
```

### Tool Ecosystem

Define reusable, containerized tools inline with steps:

```python
# Tool definition is part of step configuration
.step("notify")
.tool_def(
    name="slack-notifier",
    type="docker",
    image="kubiya/slack:latest",
    content="""#!/bin/sh
curl -X POST $SLACK_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{"text": "'$message'"}'
""",
    args=[
        {"name": "message", "type": "string"},
        {"name": "SLACK_WEBHOOK", "type": "string", "secret": True}
    ]
)
.args(message="Deployment complete!")
```

### AI Agent Integration

```python
# Deterministic AI with structured outputs
.step("intelligent-analysis")
.inline_agent(
    message="Analyze system metrics and provide recommendations",
    agent_name="sre-assistant",
    ai_instructions="""You are an SRE expert. Analyze metrics and provide:
    1. Current system health (healthy|degraded|critical)
    2. Root cause analysis
    3. Recommended actions
    Output as structured JSON.""",
    runners=["default"],  # Required parameter
    llm_model="gpt-4"
)
.output("ANALYSIS")
```

## 🔐 Security & Compliance

### Policy Enforcement

```yaml
# policy.yaml
apiVersion: kubiya.ai/v1
kind: Policy
metadata:
  name: production-safeguards
spec:
  rules:
    - name: require-approval
      match:
        environment: production
      require:
        approval: 
          roles: ["sre-lead", "platform-team"]
    
    - name: working-hours-only
      match:
        environment: production
      require:
        schedule:
          days: ["mon", "tue", "wed", "thu", "fri"]
          hours: ["09:00-17:00"]
```

### Audit Trail

Every workflow execution is fully auditable:

```json
{
  "workflow_id": "automated-deployment",
  "execution_id": "exec-123456",
  "timestamp": "2024-01-15T10:30:00Z",
  "user": "john.doe@company.com",
  "parameters": {
    "VERSION": "v2.1.0",
    "ENVIRONMENT": "production"
  },
  "steps": [
    {
      "name": "analyze-risk",
      "status": "success",
      "duration": "2.3s",
      "output": {"risk_level": "low"}
    }
  ],
  "policies_evaluated": ["production-safeguards"],
  "approvals": [
    {
      "approver": "jane.smith@company.com",
      "timestamp": "2024-01-15T10:25:00Z"
    }
  ]
}
```

## 📊 Examples

### Infrastructure Automation

```python
# Deterministic infrastructure provisioning
infra_workflow = (
    workflow("provision-k8s-cluster")
    .params(
        CLUSTER_NAME="prod-cluster-01",
        NODE_COUNT="5",
        REGION="us-east-1"
    )
    
    # Validate prerequisites
    .step("validate", "terraform validate")
    
    # Plan with approval gate
    .step("plan", "terraform plan -out=tfplan")
    .output("PLAN_OUTPUT")
    
    # Apply with safety checks
    .step("apply", "terraform apply tfplan")
    .preconditions(
        {"condition": "${PLAN_OUTPUT.changes.destroy}", "expected": "0"}
    )
    
    # Configure with deterministic outcomes
    .step("configure")
    .inline_agent(
        message="Configure cluster with security best practices",
        agent_name="k8s-configurator",
        ai_instructions="Apply CIS benchmarks and company security policies",
        runners=["kubernetes-runner"]
    )
)
```

### Incident Response

```python
# Automated, deterministic incident response
incident_workflow = (
    workflow("incident-response")
    .params(
        INCIDENT_ID="${INCIDENT_ID}",
        SEVERITY="${SEVERITY}"
    )
    
    # AI-powered triage
    .step("triage")
    .inline_agent(
        message="Analyze incident ${INCIDENT_ID} and determine response plan",
        agent_name="incident-analyzer",
        ai_instructions="You are an incident commander. Provide structured response plan.",
        runners=["incident-response-runner"]
    )
    .output("RESPONSE_PLAN")
    
    # Execute response plan
    .parallel_steps(
        "execute-response",
        items="${RESPONSE_PLAN.actions}",
        command="kubiya execute-action --action=${ITEM}"
    )
    
    # Verify resolution
    .step("verify", "python verify_resolution.py")
    .retry(limit=5, interval_sec=60)
)
```

## 🛠️ Advanced Features

### Parallel Execution

```python
# Process multiple items with controlled concurrency
.parallel_steps(
    "process-regions",
    items=["us-east-1", "eu-west-1", "ap-south-1"],
    command="deploy-to-region.sh ${ITEM}",
    max_concurrent=2
)
```

### Conditional Logic

```python
# Complex conditional execution
.step("conditional-deploy")
.shell("./deploy.sh")
.preconditions(
    {"condition": "${ENVIRONMENT}", "expected": "production"},
    {"condition": "${RISK_SCORE}", "expected": "re:[0-5]"},  # Regex match
    {"condition": "`date +%u`", "expected": "re:[1-5]"}     # Weekdays only
)
```

### Error Handling

```python
# Sophisticated error handling
.step("critical-operation")
.shell("./critical-task.sh")
.retry(
    limit=3,
    interval_sec=60,
    exponential_base=2.0,  # Exponential backoff multiplier
    exit_codes=[1, 2]  # Retry only on specific errors
)
.continue_on(failure=True)
```

## 🌐 SDK Server with AI Capabilities

The Kubiya SDK includes a production-ready REST API server with AI-powered workflow generation:

### Starting the Server

```bash
# Start with default settings
kubiya-server

# Or with custom configuration
kubiya-server --host 0.0.0.0 --port 8000 --reload

# Using Docker
docker-compose up -d
```

### REST API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### List Available Providers
```bash
curl http://localhost:8000/api/v1/providers
# Returns: ["adk"]  # Currently ADK is the only supported orchestration provider
```

#### AI-Powered Workflow Generation (ADK Provider)

Generate workflows from natural language using the `/compose` endpoint:

```bash
# Plan mode - Generate workflow only
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "adk",
    "task": "Create a workflow to backup PostgreSQL databases to S3 with encryption",
    "mode": "plan"
  }'

# Act mode - Generate AND execute workflow
curl -X POST http://localhost:8000/api/v1/compose \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "provider": "adk",
    "task": "Check system health and send alerts if any issues",
    "mode": "act",
    "stream": true
  }'
```

#### Direct Workflow Execution

```bash
# Execute a workflow directly
curl -X POST http://localhost:8000/api/v1/workflows/execute \
  -H "Authorization: Bearer $KUBIYA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "health-check",
      "steps": [
        {"name": "check_cpu", "command": "top -bn1 | grep Cpu"},
        {"name": "check_memory", "command": "free -h"},
        {"name": "check_disk", "command": "df -h"}
      ]
    },
    "stream": true
  }'
```

### Streaming Support

The server supports Server-Sent Events (SSE) for real-time updates:

```javascript
// JavaScript/TypeScript client example
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/compose?' + 
  new URLSearchParams({
    provider: 'adk',
    task: 'Deploy my application',
    mode: 'act',
    stream: 'true'
  }),
  {
    headers: {
      'Authorization': 'Bearer ' + KUBIYA_API_KEY
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data);
};
```

[Full API documentation →](https://docs.kubiya.ai/api-reference)

## 🐳 Serverless Container Architecture

### Every Step is a Docker Container

Unlike traditional workflow engines that run Python scripts in a shared environment, Kubiya executes every workflow step as an independent, serverless Docker container. This revolutionary approach gives you:

#### **Complete Software Freedom**

```python
# Example: Multi-language data pipeline
workflow = (
    workflow("data-processing-pipeline")
    
    # Step 1: Extract with Python
    .step("extract")
    .docker(
        image="python:3.11",
        packages=["pandas", "requests", "boto3"],
        code="""
        import pandas as pd
        import requests
        
        # Use ANY Python library
        data = pd.read_csv('s3://bucket/data.csv')
        processed = data.transform(...)
        save_artifact('extracted.parquet', processed)
        """
    )
    
    # Step 2: Transform with Node.js
    .step("transform")
    .docker(
        image="node:20",
        packages=["lodash", "moment", "csv-parser"],
        code="""
        const _ = require('lodash');
        const data = loadArtifact('extracted.parquet');
        
        // Use ANY npm package
        const transformed = _.chain(data)
            .filter(...)
            .groupBy(...)
            .value();
        
        saveArtifact('transformed.json', transformed);
        """
    )
    
    # Step 3: Analyze with R
    .step("analyze")
    .docker(
        image="r-base:latest",
        code="""
        library(ggplot2)
        library(forecast)
        
        # Use ANY R package
        data <- read_json('transformed.json')
        model <- auto.arima(data$values)
        forecast <- predict(model, n.ahead=30)
        
        save_artifact('forecast.rds', forecast)
        """
    )
    
    # Step 4: Load with Go for performance
    .step("load")
    .docker(
        image="golang:1.21",
        code="""
        package main
        
        import (
            "database/sql"
            _ "github.com/lib/pq"
        )
        
        func main() {
            // High-performance database operations
            db, _ := sql.Open("postgres", connStr)
            // Bulk insert with Go's concurrency
        }
        """
    )
)
```

#### **True Statelessness**

Each execution starts completely fresh:
- No leftover files from previous runs
- No environment pollution
- No dependency conflicts
- Perfect reproducibility

#### **Infinite Scalability**

The serverless model means:
- No pre-provisioned compute
- Scale from 0 to 1000s of concurrent executions
- Pay only for what you use
- No infrastructure management

### Real-World Use Cases

#### **Multi-Tool DevOps Pipeline**

```python
workflow = (
    workflow("complete-deployment")
    
    # Terraform for infrastructure
    .step("provision")
    .docker(
        image="hashicorp/terraform:latest",
        code="terraform apply -auto-approve"
    )
    
    # Ansible for configuration
    .step("configure")
    .docker(
        image="ansible/ansible:latest",
        code="ansible-playbook -i inventory site.yml"
    )
    
    # Docker for building
    .step("build")
    .docker(
        image="docker:dind",
        code="docker build -t myapp:latest ."
    )
    
    # Kubernetes for deployment
    .step("deploy")
    .docker(
        image="bitnami/kubectl:latest",
        code="kubectl rollout restart deployment/myapp"
    )
)
```

#### **Data Science Pipeline**

```python
workflow = (
    workflow("ml-pipeline")
    
    # Jupyter notebook execution
    .step("train-model")
    .docker(
        image="jupyter/tensorflow-notebook",
        code="papermill train.ipynb output.ipynb -p epochs 100"
    )
    
    # Model validation with custom image
    .step("validate")
    .docker(
        image="myorg/ml-validator:latest",
        code="python validate_model.py --model output/model.h5"
    )
)
```

### Container Management

#### **Resource Control**

```python
.step("heavy-compute")
.docker(
    image="python:3.11",
    resources={
        "cpu": "4",
        "memory": "16Gi",
        "gpu": "1"  # For ML workloads
    },
    code="# Resource-intensive operations"
)
```

#### **Custom Images**

```python
# Use your own Docker images
.step("proprietary-tool")
.docker(
    image="myregistry.com/my-tool:v2.1",
    registry_auth={
        "username": "${REGISTRY_USER}",
        "password": "${REGISTRY_PASS}"
    },
    code="./run-analysis.sh"
)
```

#### **Volume Mounts**

```python
# Share data between steps efficiently
.step("process")
.docker(
    image="processor:latest",
    volumes=[
        {"host": "/data", "container": "/input", "mode": "ro"},
        {"host": "/output", "container": "/output", "mode": "rw"}
    ],
    code="process --input /input --output /output"
)
```

### Security Benefits

- **Complete Isolation**: Each container runs in its own namespace
- **No Cross-Contamination**: Steps can't affect each other
- **Controlled Access**: Fine-grained permissions per container
- **Audit Trail**: Every container execution is logged
- **Secrets Management**: Secure injection of credentials

## 📈 Monitoring & Observability

### Built-in Metrics

- Workflow execution duration
- Step success/failure rates
- Resource utilization
- API latency percentiles

### Integration with Observability Platforms

```python
# Steps are automatically monitored
.step("monitored-step")
.shell("./process.sh")
.output("METRICS")  # Capture output for monitoring
```

## 🚀 Getting to Production

### 1. Development
```bash
# Create new workflow
kubiya init my-workflow --template basic

# Validate workflow
kubiya validate my-workflow.py

# Test locally with dry run
kubiya run my-workflow.py --dry-run
```

### 2. Testing
```bash
# Execute with test parameters
kubiya run my-workflow.py --params ENV=staging --params DRY_RUN=true

# Export workflow definition
kubiya export my-workflow.py --format yaml > workflow.yaml
```

### 3. Production
```bash
# Execute in production
kubiya run my-workflow.py --params ENV=production

# View execution history
kubiya list --status completed --limit 20

# Visualize workflow
kubiya visualize my-workflow.py --format mermaid
```

## 📚 Documentation

### 🚀 Getting Started
- [Welcome & Overview](docs/kubiya/getting-started/welcome.mdx) - Introduction to Kubiya Workflow SDK
- [Installation Guide](docs/kubiya/getting-started/installation.mdx) - Install and configure the SDK
- [Quickstart Tutorial](docs/kubiya/getting-started/quickstart.mdx) - Build your first workflow in 5 minutes
- [Core Concepts](docs/kubiya/getting-started/concepts.mdx) - Understand workflows, steps, and execution

### 🏗️ Architecture & Design
- [Architecture Overview](docs/ARCHITECTURE.md) - System architecture and components
- [Provider System](docs/kubiya/providers/overview.mdx) - Extensible AI provider framework
- [Server Architecture](docs/kubiya/servers/overview.mdx) - REST API and SSE streaming

### 🤖 AI-Powered Workflows (ADK Provider)
- [ADK Getting Started](docs/kubiya/providers/adk/getting-started.mdx) - Generate workflows with AI
- [ADK Configuration](docs/kubiya/providers/adk/configuration.mdx) - Model selection and settings
- [ADK Examples](docs/kubiya/providers/adk/examples.mdx) - Real-world AI workflow examples

### 📖 Tutorials & Examples
- [Interactive Notebooks](examples/notebooks/) - Jupyter notebooks for hands-on learning
  - [Getting Started Notebook](examples/notebooks/01_getting_started.ipynb)
  - [AI Workflow Generation](examples/notebooks/02_ai_workflow_generation.ipynb)
- [Example Workflows](examples/) - Production-ready workflow templates
- [Testing Guide](docs/kubiya/workflows/testing.mdx) - Test and debug workflows

### 🚢 Deployment & Operations
- [Docker Deployment](docs/kubiya/deployment/docker.mdx) - Containerized deployment
- [Kubernetes Guide](docs/kubiya/deployment/kubernetes.mdx) - Production K8s deployment
- [Getting Started Guide](docs/GETTING_STARTED.md) - End-to-end setup instructions

### 📡 API & SDK Reference
- [Client API](docs/kubiya/api-reference/client.mdx) - Python client reference
- [Workflow API](docs/kubiya/api-reference/workflow.mdx) - Workflow object reference
- [REST API](docs/kubiya/servers/endpoints.mdx) - Server REST endpoints
- [Streaming API](docs/kubiya/servers/sse-streaming.mdx) - Real-time SSE events

## 🤝 Enterprise Support

Get enterprise-grade support and features:

- 24/7 SLA-backed support
- Custom executor development
- Private registry hosting
- Compliance certifications (SOC2, ISO 27001)
- Professional services

[Contact Sales](https://kubiya.ai/contact-sales)

## 🎯 Why Kubiya Over Multi-Agent Systems?

| Multi-Agent Chaos | Kubiya DAG Workflows |
|-------------------|---------------------|
| ❌ Unpredictable execution paths | ✅ Deterministic, same path every time |
| ❌ "Garbage accumulates" in long chains | ✅ Clean execution with isolated steps |
| ❌ Hard to debug AI decisions | ✅ Clear DAG shows exact execution flow |
| ❌ Complex programming with LangGraph | ✅ Simple DSL, compose in hours not months |
| ❌ Vendor lock-in to agent frameworks | ✅ Runs on YOUR infrastructure |
| ❌ Limited to Python/LLM tools | ✅ Run ANY Docker container |

### The Bottom Line

We built Kubiya because **deterministic workflows beat chaotic agents** for real-world automation:

- **Flexibility**: Integrate with any agent system via API or MCP
- **Determinism**: DAG structure guarantees predictable execution
- **Stateless**: Pure schemas, no hidden state or drift
- **Serverless**: Just-in-time container execution
- **Kubernetes-Native**: Built for K8s from day zero

Transform months of fragile agent development into hours of reliable automation.

## 📄 License

MIT - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Stop hoping AI agents will work. Start shipping workflows that do.**

[Read Architecture](docs/ARCHITECTURE.md) • [Get Started](#-quick-start) • [Deploy to K8s](docs/DEPLOYMENT.md)

</div> 
