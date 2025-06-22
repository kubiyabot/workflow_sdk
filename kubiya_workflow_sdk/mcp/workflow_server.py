"""
Kubiya Workflow MCP Server - Modern implementation using FastMCP patterns.

Provides LLMs with instant feedback workflow creation, validation, and execution
capabilities through the Model Context Protocol.
"""

import asyncio
import json
import traceback
import tempfile
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

# FastMCP is optional - we provide a fallback
try:
    from fastmcp import FastMCP
    HAS_FASTMCP = True
    
    # Also try to import Context for type hints
    try:
        from fastmcp import Context
    except ImportError:
        # Create a dummy Context class for type hints
        class Context:
            async def info(self, message: str): pass
            async def error(self, message: str): pass
            async def report_progress(self, current: int, total: int): pass
except ImportError:
    # Fallback to basic implementation
    HAS_FASTMCP = False
    # Create dummy classes
    class FastMCP:
        def __init__(self, *args, **kwargs):
            self.tools = {}
            
        def tool(self, func):
            return func
    
    class Context:
        async def info(self, message: str): pass
        async def error(self, message: str): pass
        async def report_progress(self, current: int, total: int): pass
    
from ..dsl import workflow, step
from ..client import KubiyaClient
from ..execution import validate_workflow_definition, execute_workflow_events, ExecutionMode, LogLevel


@dataclass
class ExecutionState:
    """Tracks workflow execution state."""
    execution_id: str
    status: str
    workflow_name: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class KubiyaWorkflowServer:
    """
    Modern MCP server for Kubiya Workflow SDK.
    
    Features:
    - Instant workflow validation and feedback
    - Support for both JSON and Python workflow definitions
    - Real-time execution streaming
    - Multiple transport protocols (stdio, HTTP, SSE)
    - Production-ready error handling
    """
    
    def __init__(
        self,
        name: str = "Kubiya Workflow Server",
        api_token: Optional[str] = None,
        base_url: str = "https://api.kubiya.ai"
    ):
        self.name = name
        self.api_token = api_token or os.getenv('KUBIYA_API_KEY')
        self.base_url = base_url
        
        # State management
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.executions: Dict[str, ExecutionState] = {}
        
        # Initialize Kubiya client
        self.kubiya_client = KubiyaClient(
            api_key=self.api_token,
            base_url=base_url
        ) if self.api_token else None
        
        # Initialize FastMCP if available
        self.mcp = FastMCP(name, dependencies=["kubiya-workflow-sdk"]) if HAS_FASTMCP else None
        
        if self.mcp:
            self._register_tools()
    
    def _register_tools(self):
        """Register workflow tools with FastMCP."""
        
        @self.mcp.tool
        async def create_workflow_from_python(
            name: str,
            code: str,
            description: str = "",
            validate_only: bool = False,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Create a workflow from Python code with instant feedback.
            
            Args:
                name: Unique workflow name
                code: Python code defining the workflow using @workflow decorator
                description: Optional workflow description
                validate_only: If True, only validate without storing
            
            Returns:
                Validation results and workflow definition
            """
            if ctx:
                await ctx.info(f"Creating workflow '{name}' from Python code")
            
            try:
                # Create safe execution environment
                exec_globals = {
                    'workflow': workflow,
                    'step': step,
                    '__name__': '__main__',
                    '__builtins__': __builtins__
                }
                
                # Execute the code
                exec(code, exec_globals)
                
                # Find workflow function
                workflow_func = None
                for item in exec_globals.values():
                    if callable(item) and hasattr(item, '_workflow_metadata'):
                        workflow_func = item
                        break
                
                if not workflow_func:
                    return {
                        'success': False,
                        'error': 'No @workflow decorated function found in code',
                        'suggestions': [
                            'Add @workflow decorator to your function',
                            'Example: @workflow\ndef my_workflow():\n    return ...'
                        ]
                    }
                
                # Create workflow instance
                workflow_instance = workflow_func()
                workflow_dict = workflow_instance.to_dict()
                
                # Validate workflow
                errors = validate_workflow_definition(workflow_dict)
                
                result = {
                    'success': len(errors) == 0,
                    'name': name,
                    'description': description or workflow_dict.get('description', ''),
                    'validation': {
                        'valid': len(errors) == 0,
                        'errors': errors,
                        'warnings': []
                    },
                    'workflow': {
                        'steps': len(workflow_dict.get('steps', [])),
                        'parameters': list(workflow_dict.get('params', {}).keys())
                    }
                }
                
                # Store if valid and not validation-only
                if len(errors) == 0 and not validate_only:
                    self.workflows[name] = workflow_dict
                    if ctx:
                        await ctx.info(f"Workflow '{name}' created successfully")
                
                return result
                
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f'Python syntax error: {str(e)}',
                    'line': e.lineno,
                    'suggestions': [
                        'Check Python syntax',
                        'Ensure proper indentation',
                        'Verify all imports are available'
                    ]
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'suggestions': [
                        'Check workflow definition syntax',
                        'Ensure all required parameters are provided',
                        'Verify step configurations are valid'
                    ]
                }
        
        @self.mcp.tool
        async def create_workflow_from_json(
            name: str,
            workflow_json: Union[str, Dict[str, Any]],
            description: str = "",
            validate_only: bool = False,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Create a workflow from JSON definition with instant feedback.
            
            Args:
                name: Unique workflow name
                workflow_json: JSON workflow definition (string or dict)
                description: Optional workflow description
                validate_only: If True, only validate without storing
            
            Returns:
                Validation results and workflow definition
            """
            if ctx:
                await ctx.info(f"Creating workflow '{name}' from JSON")
            
            try:
                # Parse JSON if string
                if isinstance(workflow_json, str):
                    workflow_dict = json.loads(workflow_json)
                else:
                    workflow_dict = workflow_json
                
                # Add metadata
                if description:
                    workflow_dict['description'] = description
                
                # Validate workflow
                errors = validate_workflow_definition(workflow_dict)
                
                result = {
                    'success': len(errors) == 0,
                    'name': name,
                    'description': description,
                    'validation': {
                        'valid': len(errors) == 0,
                        'errors': errors,
                        'warnings': []
                    },
                    'workflow': {
                        'steps': len(workflow_dict.get('steps', [])),
                        'parameters': list(workflow_dict.get('params', {}).keys())
                    }
                }
                
                # Store if valid and not validation-only
                if len(errors) == 0 and not validate_only:
                    self.workflows[name] = workflow_dict
                    if ctx:
                        await ctx.info(f"Workflow '{name}' created successfully")
                
                return result
                
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f'JSON parsing error: {str(e)}',
                    'suggestions': [
                        'Check JSON syntax',
                        'Ensure all quotes are properly closed',
                        'Verify JSON structure is valid'
                    ]
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        @self.mcp.tool
        async def execute_workflow_streaming(
            name: str,
            parameters: Optional[Dict[str, Any]] = None,
            mode: str = "EVENTS",
            log_level: str = "NORMAL",
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Execute a workflow with real-time streaming feedback.
            
            Args:
                name: Workflow name to execute
                parameters: Workflow parameters
                mode: Execution mode (RAW, LOGGING, EVENTS)
                log_level: Log level (MINIMAL, NORMAL, VERBOSE, DEBUG)
            
            Returns:
                Execution ID and streaming information
            """
            if name not in self.workflows:
                return {
                    'success': False,
                    'error': f'Workflow "{name}" not found',
                    'available_workflows': list(self.workflows.keys())
                }
            
            if not self.api_token:
                return {
                    'success': False,
                    'error': 'API token required for workflow execution',
                    'help': 'Set KUBIYA_API_KEY environment variable or pass api_token to server'
                }
            
            # Create execution ID
            execution_id = f"exec-{name}-{int(datetime.now().timestamp())}"
            
            # Initialize execution state
            execution_state = ExecutionState(
                execution_id=execution_id,
                status='starting',
                workflow_name=name
            )
            self.executions[execution_id] = execution_state
            
            if ctx:
                await ctx.info(f"Starting execution of workflow '{name}'")
                await ctx.report_progress(0, 100)
            
            try:
                # Get execution mode and log level
                exec_mode = getattr(ExecutionMode, mode.upper(), ExecutionMode.EVENTS)
                log_lvl = getattr(LogLevel, log_level.upper(), LogLevel.NORMAL)
                
                # Start async execution
                asyncio.create_task(
                    self._execute_workflow_async(
                        execution_id, 
                        self.workflows[name], 
                        parameters or {}, 
                        exec_mode, 
                        log_lvl,
                        ctx
                    )
                )
                
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'status': 'running',
                    'workflow': name,
                    'mode': mode,
                    'stream_available': True
                }
                
            except Exception as e:
                execution_state.status = 'failed'
                execution_state.errors.append(str(e))
                
                return {
                    'success': False,
                    'execution_id': execution_id,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        @self.mcp.tool
        async def get_execution_status(
            execution_id: str,
            include_events: bool = False,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Get workflow execution status and results.
            
            Args:
                execution_id: Execution ID to query
                include_events: Whether to include execution events
            
            Returns:
                Execution status and results
            """
            if execution_id not in self.executions:
                return {
                    'success': False,
                    'error': f'Execution "{execution_id}" not found',
                    'available_executions': list(self.executions.keys())
                }
            
            execution = self.executions[execution_id]
            
            result = {
                'success': True,
                'execution_id': execution_id,
                'status': execution.status,
                'workflow': execution.workflow_name,
                'outputs': execution.outputs,
                'errors': execution.errors,
                'created_at': execution.created_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
            }
            
            if include_events:
                result['events'] = execution.events
            
            return result
        
        @self.mcp.tool
        async def list_workflows(ctx: Context = None) -> Dict[str, Any]:
            """
            List all available workflows.
            
            Returns:
                List of workflow definitions
            """
            workflows = []
            for name, workflow_def in self.workflows.items():
                # Re-validate
                errors = validate_workflow_definition(workflow_def)
                workflows.append({
                    'name': name,
                    'description': workflow_def.get('description', ''),
                    'steps': len(workflow_def.get('steps', [])),
                    'parameters': list(workflow_def.get('params', {}).keys()),
                    'valid': len(errors) == 0,
                    'validation_errors': errors if errors else None
                })
            
            return {
                'success': True,
                'count': len(workflows),
                'workflows': workflows
            }
        
        @self.mcp.tool
        async def validate_workflow_definition(
            workflow_data: Union[str, Dict[str, Any]],
            source_type: str = "auto",
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Validate a workflow definition without creating it.
            
            Args:
                workflow_data: Workflow definition (JSON string, dict, or Python code)
                source_type: Source type (json, python, auto)
            
            Returns:
                Validation results with detailed feedback
            """
            if ctx:
                await ctx.info("Validating workflow definition")
            
            try:
                # Auto-detect source type if not specified
                if source_type == "auto":
                    if isinstance(workflow_data, str):
                        # Try to detect if it's Python code or JSON
                        stripped = workflow_data.strip()
                        if stripped.startswith('{') or stripped.startswith('['):
                            source_type = "json"
                        elif '@workflow' in workflow_data or 'def ' in workflow_data:
                            source_type = "python"
                        else:
                            source_type = "json"  # Default assumption
                    else:
                        source_type = "json"
                
                if source_type == "python":
                    # Use the Python workflow creation tool for validation
                    return await create_workflow_from_python(
                        name="__validation_temp__",
                        code=workflow_data,
                        validate_only=True,
                        ctx=ctx
                    )
                else:
                    # Use the JSON workflow creation tool for validation
                    return await create_workflow_from_json(
                        name="__validation_temp__",
                        workflow_json=workflow_data,
                        validate_only=True,
                        ctx=ctx
                    )
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        @self.mcp.tool
        async def get_workflow_definition(
            name: str,
            format: str = "json",
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Get a workflow definition in specified format.
            
            Args:
                name: Workflow name
                format: Output format (json, yaml)
            
            Returns:
                Workflow definition
            """
            if name not in self.workflows:
                return {
                    'success': False,
                    'error': f'Workflow "{name}" not found',
                    'available_workflows': list(self.workflows.keys())
                }
            
            workflow_def = self.workflows[name]
            
            try:
                if format.lower() == "yaml":
                    try:
                        import yaml
                        content = yaml.dump(workflow_def, default_flow_style=False)
                    except ImportError:
                        return {
                            'success': False,
                            'error': 'PyYAML not installed. Use JSON format or install: pip install pyyaml'
                        }
                else:
                    content = json.dumps(workflow_def, indent=2)
                
                return {
                    'success': True,
                    'name': name,
                    'format': format,
                    'content': content,
                    'definition': workflow_def
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    async def _execute_workflow_async(
        self,
        execution_id: str,
        workflow_def: Dict[str, Any],
        parameters: Dict[str, Any],
        mode: ExecutionMode,
        log_level: LogLevel,
        ctx: Optional[Context] = None
    ):
        """Execute workflow asynchronously and update state."""
        execution = self.executions[execution_id]
        
        try:
            execution.status = 'running'
            
            if ctx:
                await ctx.info(f"Executing workflow with {len(workflow_def.get('steps', []))} steps")
            
            # Execute using the SDK's execution module (convert sync to async)
            events_processed = 0
            for event in execute_workflow_events(
                workflow_definition=workflow_def,
                api_key=self.api_token,
                parameters=parameters
            ):
                # Store event
                execution.events.append(event)
                events_processed += 1
                
                # Update progress if context available
                if ctx and event.get('type') == 'step_progress':
                    progress = event.get('progress', {})
                    current = progress.get('current', 0)
                    total = progress.get('total', 100)
                    await ctx.report_progress(current, total)
                
                # Update status based on event type
                if event.get('type') == 'workflow_completed':
                    execution.status = 'completed'
                    execution.outputs = event.get('outputs', {})
                    execution.completed_at = datetime.now()
                elif event.get('type') == 'workflow_failed':
                    execution.status = 'failed'
                    execution.errors.append(event.get('error', 'Unknown error'))
                    execution.completed_at = datetime.now()
                elif event.get('type') == 'execution_failed':
                    execution.status = 'failed'
                    execution.errors.append(event.get('error', 'Execution failed'))
                    execution.completed_at = datetime.now()
                    break
                elif 'error' in event:
                    execution.errors.append(event['error'])
                
                # Allow other async tasks to run
                if events_processed % 10 == 0:
                    await asyncio.sleep(0)
            
            # Ensure we have a final status
            if execution.status == 'running':
                execution.status = 'completed'
                execution.completed_at = datetime.now()
            
            if ctx:
                await ctx.info(f"Workflow execution completed with status: {execution.status}")
                
        except Exception as e:
            execution.status = 'failed'
            execution.errors.append(str(e))
            execution.completed_at = datetime.now()
            
            if ctx:
                await ctx.error(f"Workflow execution failed: {str(e)}")
    
    def run(
        self,
        transport: str = "stdio",
        host: str = "127.0.0.1",
        port: int = 8000,
        **kwargs
    ):
        """
        Run the MCP server with specified transport.
        
        Args:
            transport: Transport type (stdio, sse, streamable-http)
            host: Host address for HTTP transports
            port: Port for HTTP transports
        """
        if not HAS_FASTMCP:
            print("⚠️  Warning: FastMCP not available")
            print("   Limited functionality without FastMCP")
            print("   Install with: pip install fastmcp")
            return
        
        # Check if API token is available for workflow execution
        if not self.api_token:
            print("⚠️  Warning: No API token configured")
            print("   Workflow creation and validation will work")
            print("   But workflow execution requires KUBIYA_API_KEY")
            print("   Set KUBIYA_API_KEY environment variable to enable execution")
        
        # Configure and run FastMCP server
        if hasattr(self.mcp, 'run'):
            if transport == "stdio":
                self.mcp.run(transport="stdio")
            elif transport == "sse":
                self.mcp.run(transport="sse", host=host, port=port)
            elif transport == "streamable-http":
                self.mcp.run(transport="streamable-http", host=host, port=port)
            else:
                raise ValueError(f"Unsupported transport: {transport}")
        else:
            print("MCP server not properly initialized")


def create_workflow_server(
    name: str = "Kubiya Workflow Server",
    api_token: Optional[str] = None,
    base_url: str = "https://api.kubiya.ai"
) -> KubiyaWorkflowServer:
    """
    Create a new Kubiya Workflow MCP server.
    
    Args:
        name: Server name
        api_token: Kubiya API token
        base_url: Kubiya API base URL
    
    Returns:
        Configured server instance
    """
    return KubiyaWorkflowServer(
        name=name,
        api_token=api_token,
        base_url=base_url
    )


# Convenience alias for backwards compatibility
WorkflowMCPServer = KubiyaWorkflowServer 