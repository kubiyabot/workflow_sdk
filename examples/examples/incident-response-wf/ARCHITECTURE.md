# 🏗️ Architecture Documentation

## Overview

The Kubiya Incident Response Workflow is built on a microservices architecture using containerized execution, event-driven processing, and declarative workflow definitions.

## System Architecture

```mermaid
graph TB
    subgraph "User Interface"
        CLI[CLI Generator]
        Interactive[Interactive Mode]
        Production[Production Deployer]
    end
    
    subgraph "Workflow Definition Layer"
        DSL[Python DSL]
        Compiler[DSL Compiler]
        DAG[Workflow DAG]
    end
    
    subgraph "Execution Layer"
        Engine[Kubiya Engine]
        Runner[core-testing-2]
        Scheduler[Step Scheduler]
    end
    
    subgraph "Container Runtime"
        Alpine[Alpine Containers]
        Curl[Curl Containers] 
        Tools[Tool Containers]
    end
    
    subgraph "External Integrations"
        Slack[Slack API]
        Kubiya[Kubiya Platform]
        Docker[Docker Registry]
    end
    
    CLI --> DSL
    Interactive --> DSL
    Production --> DSL
    DSL --> Compiler
    Compiler --> DAG
    DAG --> Engine
    Engine --> Runner
    Runner --> Scheduler
    Scheduler --> Alpine
    Scheduler --> Curl
    Scheduler --> Tools
    Alpine --> Slack
    Curl --> Slack
    Tools --> Kubiya
    Engine --> Docker
```

## DSL to DAG Compilation Process

### 1. DSL Definition
```python
# Human-readable workflow definition
workflow = (Workflow("incident-response-production")
            .description("Production incident response")
            .type("chain")
            .runner("core-testing-2"))

step = Step("parse-incident-event")
step.data = {
    "name": "parse-incident-event",
    "executor": {
        "type": "tool",
        "config": {
            "tool_def": {
                "name": "parse_incident_event_production",
                "type": "docker",
                "image": "alpine:latest",
                "content": "#!/bin/sh\necho 'Parsing incident...'"
            }
        }
    },
    "output": "INCIDENT_DATA"
}

workflow.data["steps"] = [step.data]
```

### 2. Compilation to JSON DAG
```json
{
  "name": "incident-response-production",
  "description": "Production incident response with real Slack integration and Block Kit",
  "type": "chain",
  "runner": "core-testing-2",
  "params": {
    "incident_event": "${incident_event}",
    "slack_users": "${slack_users:shaked@kubiya.ai,amit@example.com}",
    "create_real_channel": "${create_real_channel:true}"
  },
  "steps": [
    {
      "name": "parse-incident-event",
      "executor": {
        "type": "tool",
        "config": {
          "tool_def": {
            "name": "parse_incident_event_production",
            "description": "Parse incident event with user resolution",
            "type": "docker",
            "image": "alpine:latest",
            "content": "#!/bin/sh\necho 'Parsing incident...'"
          },
          "args": {
            "incident_event": "${incident_event}",
            "slack_users": "${slack_users}"
          }
        }
      },
      "output": "INCIDENT_DATA",
      "depends": []
    }
  ]
}
```

### 3. DAG Execution Graph
```mermaid
graph LR
    subgraph "Step Dependencies"
        A[parse-incident-event] --> B[setup-slack-integration]
        B --> C[resolve-slack-users]
        C --> D[create-war-room]
        D --> E[technical-investigation]
        E --> F[update-slack-thread]
        F --> G[final-summary]
    end
    
    subgraph "Data Flow"
        A --> INCIDENT_DATA
        B --> SLACK_TOKEN
        C --> USER_RESOLUTION
        D --> WAR_ROOM
        E --> INVESTIGATION
        F --> SLACK_UPDATE
        G --> FINAL_SUMMARY
    end
    
    INCIDENT_DATA --> B
    SLACK_TOKEN --> C
    USER_RESOLUTION --> D
    WAR_ROOM --> E
    INVESTIGATION --> F
    SLACK_UPDATE --> G
```

## Container Strategy

### Base Images
- **alpine:latest**: Minimal Linux distribution (5MB)
- **curlimages/curl:latest**: Specialized for HTTP operations
- **Custom images**: Built on Alpine for specific tools

### Container Lifecycle
```mermaid
sequenceDiagram
    participant Engine as Kubiya Engine
    participant Scheduler as Step Scheduler
    participant Container as Docker Container
    participant Registry as Docker Registry
    
    Engine->>Scheduler: Execute Step
    Scheduler->>Registry: Pull Image
    Registry-->>Scheduler: Image Ready
    Scheduler->>Container: Start Container
    Container->>Container: Execute Script
    Container->>Container: Generate Output
    Container-->>Scheduler: Return Results
    Scheduler->>Container: Cleanup
    Scheduler-->>Engine: Step Complete
```

### Security Model
- **Isolated Execution**: Each step runs in fresh container
- **No Persistence**: Containers are ephemeral
- **Limited Network**: Only required external connections
- **Read-only Filesystem**: Prevents modification attacks
- **Resource Limits**: CPU/memory constraints

## Event-Driven Processing

### Workflow Events
```mermaid
sequenceDiagram
    participant Client as CLI Client
    participant Engine as Kubiya Engine
    participant Step as Step Executor
    participant Slack as Slack API
    
    Client->>Engine: execute_workflow()
    Engine-->>Client: workflow_started
    
    loop For Each Step
        Engine->>Step: execute_step()
        Step-->>Engine: step_started
        Step->>Step: Container Execution
        Step-->>Engine: step_progress
        Step->>Slack: API Calls
        Slack-->>Step: API Response
        Step-->>Engine: step_complete
        Engine-->>Client: step_complete
    end
    
    Engine-->>Client: workflow_complete
```

### Event Types
- `workflow_started`: Workflow execution begins
- `step_started`: Individual step begins
- `step_progress`: Step execution updates
- `step_complete`: Step finishes (success/failure)
- `workflow_complete`: All steps finished

## Data Flow Architecture

### Parameter Injection
```bash
# Environment variables are injected into containers
export incident_event='{"id":"PROD-001","title":"Database Issue"}'
export slack_users="user1@company.com,user2@company.com"

# Container receives these as environment variables
#!/bin/sh
INCIDENT_ID=$(echo "$incident_event" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
USERS_INPUT=$(echo "$slack_users")
```

### Output Chaining
```json
{
  "step_1_output": "INCIDENT_DATA",
  "step_2_input": "${INCIDENT_DATA}",
  "step_2_output": "SLACK_TOKEN",
  "step_3_input": "${INCIDENT_DATA},${SLACK_TOKEN}"
}
```

### JSON Processing
```bash
# Extract specific fields from JSON output
CHANNEL_ID=$(echo "$war_room" | grep -o '"channel_id":"[^"]*"' | cut -d'"' -f4)
USER_IDS=$(echo "$user_resolution" | grep -o '"user_ids":"[^"]*"' | cut -d'"' -f4)

# Generate structured output
echo "{
  \"channel_id\": \"$CHANNEL_ID\",
  \"users_invited\": \"$USER_IDS\",
  \"status\": \"completed\"
}"
```

## Scalability Considerations

### Horizontal Scaling
- **Stateless Execution**: No shared state between workflows
- **Container Isolation**: Independent scaling per step type
- **Event Streaming**: Asynchronous processing

### Performance Optimizations
- **Image Caching**: Pre-pulled base images
- **Parallel Steps**: Independent steps run concurrently
- **Resource Pooling**: Reused container infrastructure

### Monitoring Integration
- **Execution Metrics**: Step timing, success rates
- **Resource Usage**: CPU, memory, network per step
- **Error Tracking**: Failed steps, retry logic

## Extension Points

### Custom Executors
```python
# Add new executor types
{
  "type": "custom_integration",
  "config": {
    "service": "datadog",
    "action": "create_incident",
    "parameters": {...}
  }
}
```

### Tool Registry
```python
# Reusable tool definitions
tool_registry = {
    "kubectl": {
        "image": "bitnami/kubectl:latest",
        "content": "#!/bin/bash\nkubectl get pods"
    },
    "aws_cli": {
        "image": "amazon/aws-cli:latest", 
        "content": "#!/bin/bash\naws ec2 describe-instances"
    }
}
```

### Plugin System
- **Pre-step Hooks**: Authentication, validation
- **Post-step Processing**: Logging, notifications
- **Error Handlers**: Retry logic, fallback actions

This architecture ensures reliable, scalable, and secure incident response automation while maintaining flexibility for customization and extension.