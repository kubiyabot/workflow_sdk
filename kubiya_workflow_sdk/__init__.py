"""
Kubiya Workflow SDK

A production-grade SDK for building and executing workflows on the Kubiya platform.

Quick Start:
-----------
    from kubiya_workflow_sdk import workflow, step

    # Define a workflow
    @workflow("data-pipeline", "1.0.0")
    def my_pipeline():
        return (
            step("extract", "Extract data")
            .shell("python extract.py")
            >> step("transform", "Transform data")
            .python(lambda data: process(data))
            >> step("load", "Load to database")
            .docker("postgres:latest", "psql -c 'INSERT...'")
        )
    
    # Execute the workflow
    from kubiya_workflow_sdk import execute_workflow
    result = execute_workflow(my_pipeline(), params={"date": "2024-01-01"})

Tool Execution:
--------------
    from kubiya_workflow_sdk.tools import tool, execute_tool
    
    @tool(name="data_processor", requirements=["pandas"])
    def process_data(file_path: str):
        import pandas as pd
        df = pd.read_csv(file_path)
        return {"rows": len(df)}
    
    # Execute tool directly
    result = execute_tool("data_processor", tool_def=process_data.as_tool())
"""

from .__version__ import __version__, __author__, __email__, __license__

# Core functionality
from .core import (
    # Types
    ExecutorType,
    StepStatus,
    WorkflowStatus,
    RetryPolicy,
    ExecutionResult,
    WorkflowMetadata,
    ToolDefinition,
    ServiceSpec,
    Volume,
    
    # Exceptions
    KubiyaSDKError,
    WorkflowError,
    WorkflowValidationError,
    WorkflowExecutionError,
    ClientError,
    AuthenticationError,
    ToolError,
    ToolExecutionError,
)

# Enhanced execution with logging and validation
from .execution import (
    # Execution modes
    ExecutionMode,
    LogLevel,
    
    # Enhanced execution functions
    execute_workflow_with_logging,
    execute_workflow_logged,
    execute_workflow_events,
    execute_workflow_raw,
    
    # Validation
    validate_workflow_definition,
)

# DSL - Primary interface
from .dsl import (
    # Workflow creation
    workflow,
    step,
    
    # Executors
    python_executor,
    shell_executor,
    docker_executor,
    tool_executor,
    inline_agent_executor,
    
    # Control flow
    when,
    retry_policy,
    continue_on,
    
    # Examples
    examples,
)

# Client functionality (legacy/raw interface)
from .client import (
    KubiyaClient,
    execute_workflow,
)

# Tool framework
from .tools import (
    # Decorators
    tool,
    shell_tool,
    docker_tool,
    
    # Execution
    execute_tool,
    ToolExecutor,
    
    # Templates
    DockerToolTemplate,
    AuthenticatedToolTemplate,
    CLIToolTemplate,
)

# Server (optional)
try:
    from .server import WorkflowServer, create_server
except ImportError:
    WorkflowServer = None
    create_server = None

# MCP Protocol (optional)
try:
    from .mcp import KubiyaWorkflowServer as MCPServer
except ImportError:
    MCPServer = None


# Main exports
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    
    # Core types
    "ExecutorType",
    "StepStatus",
    "WorkflowStatus",
    "RetryPolicy",
    "ExecutionResult",
    "WorkflowMetadata",
    "ToolDefinition",
    "ServiceSpec",
    "Volume",
    
    # Exceptions
    "KubiyaSDKError",
    "WorkflowError",
    "WorkflowValidationError",
    "WorkflowExecutionError",
    "ClientError",
    "AuthenticationError",
    "ToolError",
    "ToolExecutionError",
    
    # Enhanced execution
    "ExecutionMode",
    "LogLevel",
    "execute_workflow_with_logging",
    "execute_workflow_logged",
    "execute_workflow_events",
    "execute_workflow_raw",
    "validate_workflow_definition",
    
    # DSL
    "workflow",
    "step",
    "python_executor",
    "shell_executor",
    "docker_executor",
    "tool_executor",
    "inline_agent_executor",
    "when",
    "retry_policy",
    "continue_on",
    "examples",
    
    # Client (legacy)
    "KubiyaClient",
    "execute_workflow",
    
    # Tools
    "tool",
    "shell_tool",
    "docker_tool",
    "execute_tool",
    "ToolExecutor",
    "DockerToolTemplate",
    "AuthenticatedToolTemplate",
    "CLIToolTemplate",
    
    # Server (optional)
    "WorkflowServer",
    "create_server",
    
    # MCP (optional)
    "MCPServer",
]


def get_version_info() -> dict:
    """Get detailed version information."""
    return {
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "has_server": WorkflowServer is not None,
        "has_mcp": MCPServer is not None,
    } 