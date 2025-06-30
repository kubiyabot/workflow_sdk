# System Architecture

```mermaid
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
```

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
