#!/usr/bin/env python3
"""
Generate workflow diagrams and documentation.
"""

import json
from pathlib import Path


def generate_mermaid_diagram():
    """Generate Mermaid workflow diagram."""
    
    mermaid = """```mermaid
graph TD
    Start([🚨 Incident Triggered]) --> A[📋 Parse Incident Event]
    A --> B[🔑 Setup Slack Integration]
    B --> C[👥 Resolve Slack Users]
    C --> D[🏗️ Create War Room]
    D --> E[🔬 Technical Investigation]
    E --> F[💬 Update Slack Thread]
    F --> G[📊 Final Summary]
    G --> End([✅ Response Complete])
    
    %% Step Details
    A --> A1[Extract Incident ID]
    A --> A2[Generate Channel Name]
    A --> A3[Validate Severity]
    
    C --> C1[Search by Email]
    C --> C2[Search by Display Name]
    C --> C3[Search by Username]
    C --> C4[Fuzzy Real Name Search]
    
    D --> D1[Create Slack Channel]
    D --> D2[Invite Users]
    D --> D3[Post Block Kit Message]
    
    E --> E1[System Information]
    E --> E2[Network Connectivity]
    E --> E3[Service Health Checks]
    E --> E4[Generate Recommendations]
    
    %% Container Information
    A -.->|alpine:latest| ContainerA[🐳 Alpine Container]
    C -.->|curlimages/curl:latest| ContainerC[🐳 Curl Container]
    D -.->|curlimages/curl:latest| ContainerD[🐳 Curl Container]
    E -.->|alpine:latest| ContainerE[🐳 Alpine Container]
    F -.->|curlimages/curl:latest| ContainerF[🐳 Curl Container]
    G -.->|alpine:latest| ContainerG[🐳 Alpine Container]
    
    %% Data Flow
    A -->|INCIDENT_DATA| B
    B -->|SLACK_TOKEN| C
    C -->|USER_RESOLUTION| D
    D -->|WAR_ROOM| E
    E -->|INVESTIGATION| F
    F -->|SLACK_UPDATE| G
    
    %% Styling
    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef parseStep fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef slackStep fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef investigationStep fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef containerStep fill:#f5f5f5,stroke:#424242,stroke-width:1px,stroke-dasharray: 5 5
    
    class Start,End startEnd
    class A,A1,A2,A3 parseStep
    class B,C,C1,C2,C3,C4,D,D1,D2,D3,F slackStep
    class E,E1,E2,E3,E4,G investigationStep
    class ContainerA,ContainerC,ContainerD,ContainerE,ContainerF,ContainerG containerStep
```"""
    
    return mermaid


def generate_architecture_diagram():
    """Generate system architecture diagram."""
    
    architecture = """```mermaid
graph TB
    subgraph "🖥️ User Interface Layer"
        CLI[🔧 CLI Generator<br/>generate_workflow.py]
        Interactive[🤝 Interactive Mode<br/>--interactive]
        Production[🏭 Production Deployer<br/>deploy_production.py]
        Testing[🧪 Testing Suite<br/>test_complete_workflow.py]
    end
    
    subgraph "📝 Workflow Definition Layer"
        DSL[🐍 Python DSL<br/>real_slack_incident_workflow.py]
        Compiler[⚙️ DSL Compiler<br/>to_dict()]
        DAG[📊 Workflow DAG<br/>JSON Definition]
    end
    
    subgraph "🚀 Execution Layer"
        Engine[🎯 Kubiya Engine<br/>Workflow Orchestrator]
        Runner[🏃 Runner: core-testing-2<br/>Execution Environment]
        Scheduler[📅 Step Scheduler<br/>Dependency Resolution]
    end
    
    subgraph "🐳 Container Runtime Layer"
        Alpine[🏔️ Alpine Containers<br/>Lightweight Execution]
        Curl[🌐 Curl Containers<br/>HTTP Operations]
        Tools[🔨 Tool Containers<br/>Specialized Tasks]
    end
    
    subgraph "🔌 External Integrations"
        SlackAPI[💬 Slack API<br/>channels, users, messages]
        KubiyaAPI[🎛️ Kubiya Platform<br/>integrations, tokens]
        DockerRegistry[📦 Docker Registry<br/>Container Images]
    end
    
    subgraph "💾 Data Flow"
        Params[📥 Input Parameters<br/>incident_event, slack_users]
        StepData[🔄 Step Data<br/>INCIDENT_DATA → SLACK_TOKEN]
        Output[📤 Final Output<br/>Channel Info, Summary]
    end
    
    %% Connections
    CLI --> DSL
    Interactive --> DSL
    Production --> DSL
    Testing --> DSL
    
    DSL --> Compiler
    Compiler --> DAG
    DAG --> Engine
    
    Engine --> Runner
    Runner --> Scheduler
    
    Scheduler --> Alpine
    Scheduler --> Curl
    Scheduler --> Tools
    
    Alpine --> SlackAPI
    Curl --> SlackAPI
    Tools --> KubiyaAPI
    
    Engine --> DockerRegistry
    
    Params --> Engine
    Engine --> StepData
    StepData --> Output
    
    %% Styling
    classDef uiLayer fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef defLayer fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef execLayer fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef containerLayer fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef integrationLayer fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef dataLayer fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    
    class CLI,Interactive,Production,Testing uiLayer
    class DSL,Compiler,DAG defLayer
    class Engine,Runner,Scheduler execLayer
    class Alpine,Curl,Tools containerLayer
    class SlackAPI,KubiyaAPI,DockerRegistry integrationLayer
    class Params,StepData,Output dataLayer
```"""
    
    return architecture


def generate_data_flow_diagram():
    """Generate data flow diagram."""
    
    data_flow = """```mermaid
sequenceDiagram
    participant U as 👤 User
    participant CLI as 🔧 CLI Tool
    participant E as 🎯 Kubiya Engine
    participant C1 as 🐳 Parse Container
    participant C2 as 🐳 Slack Setup
    participant C3 as 🐳 User Resolution
    participant C4 as 🐳 War Room Creation
    participant C5 as 🐳 Investigation
    participant C6 as 🐳 Thread Update
    participant C7 as 🐳 Final Summary
    participant S as 💬 Slack API
    
    U->>CLI: Execute Workflow
    CLI->>E: Submit DAG + Parameters
    E-->>CLI: workflow_started
    
    Note over E: Step 1: Parse Incident Event
    E->>C1: incident_event, slack_users
    C1->>C1: Extract ID, Title, Severity
    C1->>C1: Generate Channel Name
    C1-->>E: INCIDENT_DATA
    E-->>CLI: step_complete(parse-incident-event)
    
    Note over E: Step 2: Setup Slack Integration
    E->>C2: Kubiya API Call
    C2->>E: Get Slack Token
    C2-->>E: SLACK_TOKEN
    E-->>CLI: step_complete(setup-slack-integration)
    
    Note over E: Step 3: Resolve Slack Users
    E->>C3: INCIDENT_DATA + SLACK_TOKEN
    C3->>S: GET /api/users.list
    S-->>C3: Users JSON
    C3->>C3: Email → User ID Resolution
    C3-->>E: USER_RESOLUTION
    E-->>CLI: step_complete(resolve-slack-users)
    
    Note over E: Step 4: Create War Room
    E->>C4: INCIDENT_DATA + SLACK_TOKEN + USER_RESOLUTION
    C4->>S: POST /api/conversations.create
    S-->>C4: Channel Created
    C4->>S: POST /api/conversations.invite
    S-->>C4: Users Invited
    C4->>S: POST /api/chat.postMessage (Block Kit)
    S-->>C4: Message Posted
    C4-->>E: WAR_ROOM
    E-->>CLI: step_complete(create-war-room)
    
    Note over E: Step 5: Technical Investigation
    E->>C5: INCIDENT_DATA + WAR_ROOM
    C5->>C5: System Analysis
    C5->>C5: Generate Recommendations
    C5-->>E: INVESTIGATION
    E-->>CLI: step_complete(technical-investigation)
    
    Note over E: Step 6: Update Slack Thread
    E->>C6: SLACK_TOKEN + WAR_ROOM + INVESTIGATION
    C6->>S: POST /api/chat.postMessage (threaded)
    S-->>C6: Thread Updated
    C6-->>E: SLACK_UPDATE
    E-->>CLI: step_complete(update-slack-thread)
    
    Note over E: Step 7: Final Summary
    E->>C7: All Previous Outputs
    C7->>C7: Generate Success Metrics
    C7->>C7: Calculate Overall Status
    C7-->>E: FINAL_SUMMARY
    E-->>CLI: step_complete(final-summary)
    
    E-->>CLI: workflow_complete(success=true)
    CLI-->>U: 🎉 Incident Response Complete!
```"""
    
    return data_flow


def generate_container_execution_diagram():
    """Generate container execution flow."""
    
    container_flow = """```mermaid
graph LR
    subgraph "📦 Container Lifecycle"
        A[🏗️ Image Pull] --> B[🚀 Container Start]
        B --> C[📥 Environment Injection]
        C --> D[🔧 Script Execution]
        D --> E[📤 Output Generation]
        E --> F[🧹 Container Cleanup]
    end
    
    subgraph "🔒 Security Model"
        G[👤 Non-root User]
        H[📂 Read-only Filesystem]
        I[🌐 Limited Network]
        J[⏱️ Resource Limits]
        K[🔄 Ephemeral Storage]
    end
    
    subgraph "🏔️ Alpine Containers"
        A1[parse-incident-event<br/>5MB Alpine]
        A2[technical-investigation<br/>Built-in Tools Only]
        A3[final-summary<br/>JSON Processing]
    end
    
    subgraph "🌐 Curl Containers"
        C1[resolve-slack-users<br/>API Operations]
        C2[create-war-room<br/>Slack Channel Creation]
        C3[update-slack-thread<br/>Message Posting]
    end
    
    A --> A1
    A --> A2
    A --> A3
    A --> C1
    A --> C2
    A --> C3
    
    B --> G
    B --> H
    B --> I
    B --> J
    B --> K
    
    classDef alpine fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef curl fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef security fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef lifecycle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class A,B,C,D,E,F lifecycle
    class G,H,I,J,K security
    class A1,A2,A3 alpine
    class C1,C2,C3 curl
```"""
    
    return container_flow


def save_diagrams():
    """Save all diagrams to markdown files."""
    
    diagrams_dir = Path(__file__).parent / "docs"
    diagrams_dir.mkdir(exist_ok=True)
    
    # Workflow diagram
    workflow_diagram = f"""# Workflow Execution Flow

{generate_mermaid_diagram()}

## Workflow Steps

1. **Parse Incident Event** - Validates and structures incident data
2. **Setup Slack Integration** - Retrieves Slack API token
3. **Resolve Slack Users** - Converts emails to Slack user IDs
4. **Create War Room** - Creates channel with Block Kit message
5. **Technical Investigation** - Automated system analysis
6. **Update Slack Thread** - Posts investigation as threaded reply
7. **Final Summary** - Comprehensive incident report

## Container Strategy

Each step runs in isolated containers:
- **Alpine containers**: Lightweight system operations
- **Curl containers**: HTTP/API operations
- **Ephemeral execution**: No persistent state
- **Security isolation**: Limited permissions and network access
"""

    with open(diagrams_dir / "workflow_diagram.md", 'w') as f:
        f.write(workflow_diagram)
    
    # Architecture diagram
    architecture_doc = f"""# System Architecture

{generate_architecture_diagram()}

## Architecture Layers

### User Interface Layer
- **CLI Generator**: Command-line workflow generation
- **Interactive Mode**: Guided workflow configuration
- **Production Deployer**: Automated production setup
- **Testing Suite**: Comprehensive validation tools

### Workflow Definition Layer
- **Python DSL**: Human-readable workflow definitions
- **DSL Compiler**: Converts Python to executable JSON
- **Workflow DAG**: Dependency-resolved execution graph

### Execution Layer
- **Kubiya Engine**: Workflow orchestration and scheduling
- **Runner Environment**: Isolated execution context
- **Step Scheduler**: Dependency resolution and parallel execution

### Container Runtime Layer
- **Alpine Containers**: Minimal Linux environments
- **Curl Containers**: HTTP operation specialists
- **Tool Containers**: Custom execution environments

### External Integrations
- **Slack API**: Real-time communication platform
- **Kubiya Platform**: Integration and token management
- **Docker Registry**: Container image distribution
"""

    with open(diagrams_dir / "architecture_diagram.md", 'w') as f:
        f.write(architecture_doc)
    
    # Data flow diagram
    data_flow_doc = f"""# Data Flow and Execution Sequence

{generate_data_flow_diagram()}

## Execution Flow

The workflow follows a strict sequence of operations:

1. **User Initiation**: User triggers workflow via CLI
2. **Parameter Injection**: Environment variables passed to containers
3. **Sequential Execution**: Each step depends on previous outputs
4. **API Integration**: Real-time Slack API operations
5. **Result Aggregation**: Comprehensive final summary

## Data Transformation

- **Input**: Raw incident JSON + user emails
- **Processing**: Multi-step enrichment and validation
- **Output**: Structured incident response with metrics

## Error Handling

- **Container Failures**: Isolated impact, detailed logging
- **API Errors**: Graceful degradation with fallbacks
- **Validation Errors**: Clear error messages and guidance
"""

    with open(diagrams_dir / "data_flow_diagram.md", 'w') as f:
        f.write(data_flow_doc)
    
    # Container execution diagram
    container_doc = f"""# Container Execution Model

{generate_container_execution_diagram()}

## Container Lifecycle

Each workflow step executes in an isolated container:

1. **Image Pull**: Base images cached for performance
2. **Container Start**: Fresh environment for each execution
3. **Environment Injection**: Parameters passed as environment variables
4. **Script Execution**: Shell scripts with embedded logic
5. **Output Generation**: Structured JSON responses
6. **Container Cleanup**: Automatic cleanup after execution

## Security Model

- **Non-root Execution**: Containers run as non-privileged users
- **Read-only Filesystem**: Prevents unauthorized modifications
- **Limited Network Access**: Only required external connections
- **Resource Limits**: CPU and memory constraints
- **Ephemeral Storage**: No persistent data storage

## Image Strategy

- **Alpine Linux**: Minimal 5MB base images
- **Specialized Images**: curl, kubectl, aws-cli as needed
- **No External Dependencies**: Self-contained execution
- **Version Pinning**: Specific image versions for reproducibility
"""

    with open(diagrams_dir / "container_execution.md", 'w') as f:
        f.write(container_doc)
    
    print("✅ Diagrams generated successfully!")
    print(f"📁 Documentation saved to: {diagrams_dir}")
    print("📋 Generated files:")
    print("   • workflow_diagram.md")
    print("   • architecture_diagram.md") 
    print("   • data_flow_diagram.md")
    print("   • container_execution.md")


if __name__ == "__main__":
    save_diagrams()