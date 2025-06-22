# Kubiya Workflow SDK

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**Build Deterministic AI Workflows That Actually Work™**

[Get Started](#-quick-start) • [Documentation](https://docs.kubiya.ai) • [Examples](#-examples) • [API Reference](#-api-reference) • [Enterprise](https://kubiya.ai/enterprise)

</div>

---

## 🚀 The Future of AI is Deterministic

**Kubiya Workflow SDK** is a composable workflow stack that transforms unpredictable AI agents into reliable, production-grade automation. By combining the structure of DAGs with the intelligence of AI, we deliver deterministic workflows that actually work.

### Why We Built This

After watching teams struggle with free-wheeling agent frameworks that promise magic but deliver chaos, we took a different approach. Instead of hoping an AI will figure out the right sequence of actions, we provide the tools to **define** the right sequence – with AI filling in the intelligent parts. [Read more about our architecture →](docs/ARCHITECTURE.md)

### Core Principles

- **🎯 Deterministic Execution**: Same inputs → Same workflow → Same outputs, every time
- **🏗️ Composable Building Blocks**: Combine simple, tested components into complex workflows  
- **🔧 Run ANY Docker Container**: Not limited to Python – use any tool, any language
- **☸️ Kubernetes-Native**: Built for K8s from day zero, not retrofitted
- **🏠 Your Infrastructure**: Runs entirely on-premise with zero vendor lock-in
- **🤖 AI with Guardrails**: Intelligence where it matters, structure where it counts

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

## 🤖 AI-Powered Workflow Generation (Optional)

The SDK includes an optional ADK (Agent Development Kit) provider that uses AI to generate workflows from natural language:

```bash
# Install with ADK provider (uses Together AI by default)
pip install kubiya-workflow-sdk[adk]
```

```python
from kubiya_workflow_sdk import KubiyaClient
from kubiya_workflow_sdk.providers import get_provider

# Initialize client
client = KubiyaClient(api_key="your-api-key", org_name="your-org")

# Get ADK provider
provider = get_provider("adk", client=client)

# Generate workflow from natural language
workflow = provider.generate_workflow(
    task="Create a workflow to deploy a Docker container to Kubernetes with health checks",
    context={"namespace": "production", "image": "myapp:v1.0"}
)

# The provider generates Python code using SDK abstractions,
# compiles it, validates it, and returns the workflow as JSON
print(workflow)
```

The ADK provider:
- Generates workflows using the SDK's Python API (chain, step, etc.)
- Validates using SDK's built-in validation
- Automatically fixes compilation errors with AI refinement
- Supports Together AI (default), Google AI, and Vertex AI models
- Includes SSE and Vercel AI SDK streaming formats

See the [Provider Documentation](kubiya_workflow_sdk/providers/README.md) for more details.

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
# Returns: ["adk", "langchain", "custom"]
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
      'Authorization': `Bearer ${apiKey}`
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
};
```

The compose endpoint supports:
- **Plan Mode** (`execute: false`): Generate workflow without execution
- **Act Mode** (`execute: true`): Generate and immediately execute workflow
- **Session Continuity**: Maintain context across requests
- **Streaming**: Real-time updates via SSE or Vercel AI SDK format

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
