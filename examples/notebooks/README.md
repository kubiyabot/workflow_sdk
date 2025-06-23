# Kubiya Workflow SDK - Example Notebooks

This directory contains comprehensive Jupyter notebooks demonstrating all features of the Kubiya Workflow SDK. Each notebook is designed to be self-contained and includes real execution examples with outputs.

## 📋 Requirements

- **Python 3.8 or higher** (3.9+ recommended)
- pip package manager
- Internet connection for API access
- Jupyter Notebook or JupyterLab

## 📚 Notebook Overview

### 00. Test Setup (`00_test_setup.ipynb`)
- Verify SDK installation
- Test API connectivity
- Check environment configuration
- Quick validation of basic functionality

### 01. Getting Started (`01_getting_started.ipynb`)
- Basic workflow creation and execution
- Working with parameters
- Error handling and retry logic
- Understanding workflow outputs
- **Key concepts**: Sequential execution, parameters, error handling

### 02. AI Workflow Generation (`02_ai_workflow_generation.ipynb`)
- Generate workflows using AI (ADK provider)
- Natural language to workflow conversion
- AI-assisted workflow optimization
- **Requirements**: `TOGETHER_API_KEY` for AI features

### 03. Agent Server Example (`03_agent_server_example.ipynb`)
- Deploy workflows as API servers
- RESTful endpoints for workflow execution
- Server configuration and deployment
- **Key concepts**: API servers, HTTP endpoints

### 04. Workflow Server (`04_workflow_server.ipynb`)
- Advanced server features with SSE streaming
- Real-time execution monitoring
- Event-driven architecture
- **Key concepts**: Server-Sent Events, streaming

### 05. Full Capabilities (`05_full_capabilities.ipynb`)
- Comprehensive SDK feature demonstration
- All executor types (shell, Python, Docker)
- Advanced workflow patterns
- **Key concepts**: Complete feature showcase

### 06. SDK End-to-End (`06_sdk_end_to_end.ipynb`)
- Production-ready workflow examples
- Integration with Kubiya platform features
- Client API usage (runners, integrations)
- **Key concepts**: Platform integration

### 07. Multi-Provider Agent (`07_multi_provider_agent.ipynb`)
- Using multiple AI providers
- Provider-specific configurations
- Agent composition patterns
- **Key concepts**: Multi-provider support

### 08. Workflow Orchestration (`08_workflow_orchestration.ipynb`)
- Parallel execution patterns
- Sub-workflows and nesting
- Advanced control flow
- **Key concepts**: Parallelism, orchestration

### 09. Tool Executors (`09_tool_executors.ipynb`)
- Custom tool creation
- Bounded services (Redis, PostgreSQL)
- Docker-based tools
- **Key concepts**: Tools, services, containers

### 10. Advanced Patterns (`10_advanced_patterns.ipynb`)
- Dynamic workflow generation
- Conditional branching
- Event-driven workflows
- **Key concepts**: Advanced patterns

### 11. Real World Examples (`11_real_world_examples.ipynb`)
- Production CI/CD pipelines
- Data processing workflows
- Infrastructure automation
- **Key concepts**: Real-world applications

## 🚀 Getting Started

### Quick Setup (Recommended)

1. **Create and activate a virtual environment**:
   ```bash
   # Create virtual environment
   python -m venv kubiya_env
   
   # Activate it
   # On macOS/Linux:
   source kubiya_env/bin/activate
   # On Windows:
   # kubiya_env\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   # Install everything from requirements.txt
   pip install -r requirements.txt
   
   # Or install individually:
   pip install kubiya-workflow-sdk jupyter python-dotenv
   ```

3. **Set up environment variables**:
   ```bash
   # Create .env file
   echo "KUBIYA_API_KEY=your-api-key" > .env
   echo "TOGETHER_API_KEY=your-together-key" >> .env  # Optional, for AI features
   ```

4. **Launch Jupyter and start with setup notebook**:
   ```bash
   jupyter notebook 00_test_setup.ipynb
   ```

### Alternative: Use the Setup Notebook

The `00_test_setup.ipynb` notebook provides a guided setup process that:
- Checks Python version compatibility
- Installs all required dependencies
- Creates .env file template
- Verifies API connectivity
- Tests workflow execution

This is recommended for first-time users or troubleshooting.

## 🔧 Configuration

### Required Environment Variables
- `KUBIYA_API_KEY`: Your Kubiya API key (get from https://app.kubiya.ai/settings/api-keys)

### Optional Environment Variables
- `TOGETHER_API_KEY`: For AI-powered workflow generation (notebook 02)

### Runner Configuration
The SDK automatically selects an appropriate runner. For advanced use cases, you can:
- Set up local Kubernetes runners for enhanced security
- Use specific runners for compliance requirements
- Configure runners with custom resources

## 📝 Key Concepts

### Workflows
- Composed of sequential or parallel steps
- Support parameters and environment variables
- Include error handling and retry logic

### Executors
- **Shell**: Run bash commands
- **Python**: Execute Python code
- **Docker**: Run containerized tools
- **Tool**: Custom tools with bounded services
- **Inline Agent**: Embedded AI agents

### Services
- Bounded services run alongside tools
- Support for databases, caches, message queues
- Automatic networking and lifecycle management

## 🎯 Examples of Real Outputs

When you run the notebooks, you'll see actual outputs like:

```
🚀 Executing workflow...
============================================================
📤 Output: 🎉 Hello from Kubiya SDK!
✅ Completed step: greeting
📤 Output: 2024-06-23 15:30:45
✅ Completed step: timestamp
📤 Output: ✅ Workflow execution complete!
✅ Completed step: complete
============================================================
✅ Workflow completed successfully!
   Steps executed: 3
   Outputs received: 3
```

## 🛠️ Troubleshooting

### Common Issues

1. **API Key Issues**:
   - Verify key at https://app.kubiya.ai/settings/api-keys
   - Check key hasn't expired
   - Ensure proper formatting in .env file

2. **Runner Issues**:
   - SDK automatically selects runners
   - For specific requirements, configure local runners
   - Check runner availability in your organization

3. **Network Issues**:
   - Ensure connectivity to api.kubiya.ai
   - Check firewall/proxy settings
   - Verify SSL/TLS configuration

### Getting Help
- Documentation: https://docs.kubiya.ai
- Support: support@kubiya.ai
- Community: https://community.kubiya.ai

## 📚 Learning Path

1. Start with **00_test_setup.ipynb** to verify installation
2. Learn basics in **01_getting_started.ipynb**
3. Explore AI features in **02_ai_workflow_generation.ipynb**
4. Build on concepts progressively through notebooks 03-10
5. Apply learning with **11_real_world_examples.ipynb**

Each notebook builds on previous concepts while introducing new features. They're designed to be run in order but can also serve as standalone references.

## 🎉 Next Steps

After completing these notebooks:
1. Build your own workflows for your use cases
2. Deploy workflows as API servers
3. Integrate with your CI/CD pipelines
4. Explore advanced patterns for complex automation

Happy automating with Kubiya! 🚀 