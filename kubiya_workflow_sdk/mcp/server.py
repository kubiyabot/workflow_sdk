"""
MCP Server implementation for Kubiya Workflows.

Provides tools for:
- Defining workflows from inline Python code
- Executing workflows with parameters
- Querying workflows via GraphQL
- Managing workflow lifecycle
"""

import asyncio
import json
import sys
import traceback
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
import inspect
import textwrap
from datetime import datetime

try:
    import graphene
    from graphql import graphql
    HAS_GRAPHQL = True
except ImportError:
    HAS_GRAPHQL = False
    
from ..dsl import workflow as flow_decorator, step
from ..client import KubiyaClient
from ..execution import validate_workflow_definition, execute_workflow_events, ExecutionMode, LogLevel


@dataclass
class Tool:
    """MCP Tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    

@dataclass
class MCPResponse:
    """Standard MCP response format."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ValidationResult:
    """Simple validation result container."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        self.valid = len(errors) == 0
        self.warnings = []  # Could be extended in future


class FastMCP:
    """
    FastMCP-compatible server for Kubiya workflows.
    
    Example:
        mcp = FastMCP("Kubiya Workflow Server")
        
        @mcp.tool
        def create_workflow(name: str, code: str) -> Dict[str, Any]:
            '''Create a workflow from Python code'''
            return mcp.define_workflow_from_code(name, code)
    """
    
    def __init__(self, name: str = "Kubiya MCP Server", 
                 api_token: Optional[str] = None,
                 base_url: str = "https://api.kubiya.ai"):
        self.name = name
        self.api_token = api_token
        self.base_url = base_url
        self.tools: Dict[str, Tool] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.executions: Dict[str, Any] = {}
        
        # Initialize Kubiya client
        self.kubiya_client = KubiyaClient(
            api_key=api_token,
            base_url=base_url
        ) if api_token else None
        
        # Register built-in tools
        self._register_builtin_tools()
        
        # Setup GraphQL if available
        if HAS_GRAPHQL:
            self._setup_graphql()
    
    def tool(self, func: Optional[Callable] = None, *, 
             name: Optional[str] = None,
             description: Optional[str] = None) -> Callable:
        """Decorator to register a tool with the MCP server."""
        def decorator(f: Callable) -> Callable:
            tool_name = name or f.__name__
            tool_desc = description or f.__doc__ or f"Tool: {tool_name}"
            
            # Extract parameters from function signature
            sig = inspect.signature(f)
            params = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                param_type = str(param.annotation) if param.annotation != param.empty else 'Any'
                params[param_name] = {
                    'type': param_type,
                    'required': param.default == param.empty,
                    'default': None if param.default == param.empty else param.default
                }
            
            self.tools[tool_name] = Tool(
                name=tool_name,
                description=tool_desc,
                parameters=params,
                handler=f
            )
            
            return f
            
        if func is None:
            return decorator
        return decorator(func)
    
    def _register_builtin_tools(self):
        """Register built-in Kubiya workflow tools."""
        
        @self.tool(description="Define a workflow from inline Python code")
        async def define_workflow(name: str, code: str, description: str = "") -> Dict[str, Any]:
            """
            Define a new workflow from Python code.
            
            Args:
                name: Workflow name
                code: Python code defining the workflow
                description: Optional workflow description
                
            Returns:
                Workflow definition and validation status
            """
            try:
                # Create a safe execution environment
                exec_globals = {
                    'workflow': flow_decorator,
                    'flow': flow_decorator,
                    'step': step,
                    '__name__': '__main__'
                }
                
                # Execute the code
                exec(code, exec_globals)
                
                # Find the workflow function
                workflow_func = None
                for item in exec_globals.values():
                    if hasattr(item, '_workflow_metadata'):
                        workflow_func = item
                        break
                
                if not workflow_func:
                    return {
                        'success': False,
                        'error': 'No workflow found in code. Use @workflow decorator.',
                        'suggestions': [
                            'Ensure your function has @workflow decorator',
                            'Example: @workflow\ndef my_workflow():\n    return ...'
                        ]
                    }
                
                # Create workflow instance
                workflow_instance = workflow_func()
                workflow_dict = workflow_instance.to_dict()
                
                # Validate using SDK validation
                errors = validate_workflow_definition(workflow_dict)
                validation = ValidationResult(errors)
                
                # Only store if valid
                if validation.valid:
                    self.workflows[name] = workflow_dict
                
                return {
                    'success': validation.valid,
                    'workflow': {
                        'name': name,
                        'description': description or workflow_dict.get('description', ''),
                        'steps': len(workflow_dict.get('steps', [])),
                        'params': list(workflow_dict.get('params', {}).keys())
                    },
                    'validation': {
                        'valid': validation.valid,
                        'errors': validation.errors,
                        'warnings': validation.warnings
                    }
                }
                
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f'Python syntax error: {str(e)}',
                    'line': e.lineno,
                    'offset': e.offset,
                    'suggestions': [
                        'Check Python syntax',
                        'Ensure proper indentation',
                        'Verify all parentheses and quotes are closed'
                    ]
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        @self.tool(description="Execute a workflow with parameters")
        async def execute_workflow(name: str, params: Optional[Dict[str, Any]] = None,
                                 stream: bool = True) -> Dict[str, Any]:
            """
            Execute a defined workflow.
            
            Args:
                name: Workflow name
                params: Workflow parameters
                stream: Whether to stream execution events
                
            Returns:
                Execution ID and initial status
            """
            if name not in self.workflows:
                return {
                    'success': False,
                    'error': f'Workflow "{name}" not found',
                    'available_workflows': list(self.workflows.keys())
                }
            
            if not self.kubiya_client:
                return {
                    'success': False,
                    'error': 'No API token configured. Set KUBIYA_API_KEY environment variable to enable execution.',
                    'help': 'Export your API key: export KUBIYA_API_KEY="your-api-key"'
                }
            
            workflow = self.workflows[name]
            execution_id = f"exec-{name}-{int(datetime.now().timestamp())}"
            
            try:
                # Execute via Kubiya API
                if stream:
                    # Start streaming execution
                    asyncio.create_task(
                        self._stream_execution(execution_id, workflow, params)
                    )
                    
                    return {
                        'success': True,
                        'execution_id': execution_id,
                        'status': 'running',
                        'stream_endpoint': f'/executions/{execution_id}/stream'
                    }
                else:
                    # Synchronous execution
                    result = self.kubiya_client.execute_workflow(
                        workflow_definition=workflow,
                        params=params
                    )
                    
                    self.executions[execution_id] = {
                        'status': 'completed',
                        'result': result,
                        'completed_at': datetime.now().isoformat()
                    }
                    
                    return {
                        'success': True,
                        'execution_id': execution_id,
                        'status': 'completed',
                        'result': result
                    }
                    
            except Exception as e:
                error_msg = str(e)
                self.executions[execution_id] = {
                    'status': 'failed',
                    'error': error_msg,
                    'completed_at': datetime.now().isoformat()
                }
                
                return {
                    'success': False,
                    'execution_id': execution_id,
                    'error': error_msg,
                    'traceback': traceback.format_exc()
                }
        
        @self.tool(description="Get workflow execution status and results")
        async def get_execution(execution_id: str) -> Dict[str, Any]:
            """Get execution status and results."""
            if execution_id not in self.executions:
                return {
                    'success': False,
                    'error': f'Execution "{execution_id}" not found',
                    'available_executions': list(self.executions.keys())[-10:]  # Last 10
                }
            
            execution = self.executions[execution_id]
            
            return {
                'success': True,
                'execution_id': execution_id,
                'status': execution.get('status', 'unknown'),
                'result': execution.get('result'),
                'outputs': execution.get('outputs', {}),
                'errors': execution.get('errors', []),
                'duration': execution.get('duration_seconds'),
                'events_count': len(execution.get('events', [])),
                'completed_at': execution.get('completed_at')
            }
        
        @self.tool(description="List all defined workflows")
        async def list_workflows() -> Dict[str, Any]:
            """List all workflows defined in this session."""
            workflows = []
            for name, wf in self.workflows.items():
                # Re-validate to ensure still valid
                errors = validate_workflow_definition(wf)
                workflows.append({
                    'name': name,
                    'description': wf.get('description', ''),
                    'steps': len(wf.get('steps', [])),
                    'params': list(wf.get('params', {}).keys()),
                    'valid': len(errors) == 0,
                    'validation_errors': errors if errors else None
                })
            
            return {
                'success': True,
                'count': len(workflows),
                'workflows': workflows
            }
        
        @self.tool(description="Validate a workflow definition")
        async def validate_workflow(workflow_def: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
            """Validate workflow structure without storing it."""
            try:
                # Parse if string
                if isinstance(workflow_def, str):
                    workflow_def = json.loads(workflow_def)
                
                # Validate
                errors = validate_workflow_definition(workflow_def)
                
                return {
                    'success': len(errors) == 0,
                    'valid': len(errors) == 0,
                    'errors': errors,
                    'workflow_summary': {
                        'steps': len(workflow_def.get('steps', [])),
                        'has_name': bool(workflow_def.get('name')),
                        'has_description': bool(workflow_def.get('description')),
                        'parameters': list(workflow_def.get('params', {}).keys())
                    }
                }
                
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'valid': False,
                    'errors': [f'JSON parsing error: {str(e)}']
                }
            except Exception as e:
                return {
                    'success': False,
                    'valid': False,
                    'errors': [str(e)]
                }
        
        @self.tool(description="Export workflow as YAML or JSON")
        async def export_workflow(name: str, format: str = "yaml") -> Dict[str, Any]:
            """Export workflow definition."""
            if name not in self.workflows:
                return {
                    'success': False,
                    'error': f'Workflow "{name}" not found',
                    'available_workflows': list(self.workflows.keys())
                }
            
            workflow = self.workflows[name]
            
            try:
                if format.lower() == "json":
                    content = json.dumps(workflow, indent=2)
                elif format.lower() == "yaml":
                    # Simple YAML representation
                    try:
                        import yaml
                        content = yaml.dump(workflow, default_flow_style=False)
                    except ImportError:
                        return {
                            'success': False,
                            'error': 'PyYAML not installed. Use JSON format or install: pip install pyyaml'
                        }
                else:
                    return {
                        'success': False,
                        'error': f'Unknown format: {format}. Use "yaml" or "json".'
                    }
                
                return {
                    'success': True,
                    'format': format,
                    'content': content
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
        if HAS_GRAPHQL:
            @self.tool(description="Query workflows using GraphQL")
            async def graphql_query(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                """
                Execute GraphQL query against workflows.
                
                Example queries:
                    { workflows { name description steps { name type } } }
                    { workflow(name: "deploy") { params executions { status } } }
                """
                try:
                    result = await graphql(
                        self.graphql_schema,
                        query,
                        variable_values=variables,
                        context_value={'mcp': self}
                    )
                    
                    if result.errors:
                        return {
                            'success': False,
                            'errors': [str(e) for e in result.errors]
                        }
                    
                    return {
                        'success': True,
                        'data': result.data
                    }
                    
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e)
                    }
    
    async def _stream_execution(self, execution_id: str, workflow: Dict[str, Any], 
                              params: Optional[Dict[str, Any]]):
        """Stream workflow execution events."""
        try:
            events = []
            self.executions[execution_id] = {
                'status': 'running',
                'events': events,
                'started_at': datetime.now().isoformat()
            }
            
            # Convert sync generator to async
            def sync_events():
                for event in execute_workflow_events(
                    workflow_definition=workflow,
                    api_key=self.api_token,
                    parameters=params
                ):
                    yield event
            
            # Process events
            for event in sync_events():
                events.append(event)
                
                # Update execution state based on event
                if 'step' in event:
                    self.executions[execution_id]['current_step'] = event['step'].get('name')
                elif 'error' in event:
                    self.executions[execution_id]['status'] = 'failed'
                    self.executions[execution_id]['errors'] = self.executions[execution_id].get('errors', [])
                    self.executions[execution_id]['errors'].append(event['error'])
                elif event.get('type') == 'workflow_completed':
                    self.executions[execution_id]['status'] = 'completed'
                    self.executions[execution_id]['outputs'] = event.get('outputs', {})
                
                # Allow other tasks to run
                await asyncio.sleep(0)
            
            # Mark as completed if not already marked
            if self.executions[execution_id]['status'] == 'running':
                self.executions[execution_id]['status'] = 'completed'
            
            self.executions[execution_id]['completed_at'] = datetime.now().isoformat()
            
        except Exception as e:
            self.executions[execution_id] = {
                'status': 'failed',
                'error': str(e),
                'events': events if 'events' in locals() else [],
                'completed_at': datetime.now().isoformat()
            }
    
    def _setup_graphql(self):
        """Setup GraphQL schema for workflow queries."""
        
        class StepType(graphene.ObjectType):
            name = graphene.String()
            type = graphene.String()
            description = graphene.String()
            depends_on = graphene.List(graphene.String)
            
        class WorkflowType(graphene.ObjectType):
            name = graphene.String()
            description = graphene.String()
            version = graphene.String()
            steps = graphene.List(StepType)
            params = graphene.List(graphene.String)
            
            def resolve_steps(self, info):
                mcp = info.context['mcp']
                workflow = mcp.workflows.get(self.name)
                if not workflow:
                    return []
                
                return [
                    StepType(
                        name=step.get('name'),
                        type=step.get('executor', {}).get('type', 'unknown'),
                        description=step.get('description', ''),
                        depends_on=step.get('depends', []) if isinstance(step.get('depends'), list) else [step.get('depends')] if step.get('depends') else []
                    )
                    for step in workflow.get('steps', [])
                ]
        
        class ExecutionType(graphene.ObjectType):
            execution_id = graphene.String()
            status = graphene.String()
            outputs = graphene.JSONString()
            errors = graphene.List(graphene.String)
            
        class Query(graphene.ObjectType):
            workflows = graphene.List(WorkflowType)
            workflow = graphene.Field(WorkflowType, name=graphene.String(required=True))
            executions = graphene.List(ExecutionType)
            execution = graphene.Field(ExecutionType, id=graphene.String(required=True))
            
            def resolve_workflows(self, info):
                mcp = info.context['mcp']
                return [
                    WorkflowType(
                        name=name,
                        description=wf.get('description', ''),
                        version=wf.get('version', '1.0.0'),
                        params=list(wf.get('params', {}).keys())
                    )
                    for name, wf in mcp.workflows.items()
                ]
            
            def resolve_workflow(self, info, name):
                mcp = info.context['mcp']
                if name in mcp.workflows:
                    wf = mcp.workflows[name]
                    return WorkflowType(
                        name=name,
                        description=wf.get('description', ''),
                        version=wf.get('version', '1.0.0'),
                        params=list(wf.get('params', {}).keys())
                    )
                return None
            
            def resolve_executions(self, info):
                mcp = info.context['mcp']
                return [
                    ExecutionType(
                        execution_id=exec_id,
                        status=exec_data.get('status'),
                        outputs=exec_data.get('outputs', {}),
                        errors=exec_data.get('errors', [])
                    )
                    for exec_id, exec_data in mcp.executions.items()
                ]
            
            def resolve_execution(self, info, id):
                mcp = info.context['mcp']
                if id in mcp.executions:
                    exec_data = mcp.executions[id]
                    return ExecutionType(
                        execution_id=id,
                        status=exec_data.get('status'),
                        outputs=exec_data.get('outputs', {}),
                        errors=exec_data.get('errors', [])
                    )
                return None
        
        self.graphql_schema = graphene.Schema(query=Query)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a registered tool."""
        if tool_name not in self.tools:
            return {
                'success': False,
                'error': f'Tool "{tool_name}" not found',
                'available_tools': list(self.tools.keys())
            }
        
        tool = self.tools[tool_name]
        try:
            result = await tool.handler(**arguments)
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.parameters
            }
            for tool in self.tools.values()
        ]
    
    def run(self, transport: str = "stdio"):
        """Run the MCP server."""
        if transport == "stdio":
            asyncio.run(self._run_stdio())
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    
    async def _run_stdio(self):
        """Run MCP server over stdio."""
        print(f"🚀 {self.name} started (stdio transport)")
        
        if not self.api_token:
            print("⚠️  Warning: No API token configured")
            print("   Set KUBIYA_API_KEY environment variable to enable workflow execution")
            print()
        
        print("Available tools:")
        for tool in self.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
        print("\nWaiting for commands...")
        
        while True:
            try:
                # Read command from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                # Parse JSON command
                try:
                    command = json.loads(line.strip())
                except json.JSONDecodeError:
                    print(json.dumps({
                        'error': 'Invalid JSON command'
                    }))
                    continue
                
                # Handle command
                if command.get('type') == 'tool':
                    tool_name = command.get('tool')
                    arguments = command.get('arguments', {})
                    result = await self.call_tool(tool_name, arguments)
                    print(json.dumps(result))
                elif command.get('type') == 'list':
                    print(json.dumps({
                        'tools': self.list_tools()
                    }))
                else:
                    print(json.dumps({
                        'error': f'Unknown command type: {command.get("type")}'
                    }))
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(json.dumps({
                    'error': str(e)
                }))


class KubiyaMCP(FastMCP):
    """
    Extended MCP server with additional Kubiya-specific tools.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._register_kubiya_tools()
    
    def _register_kubiya_tools(self):
        """Register additional Kubiya-specific tools."""
        
        @self.tool(description="Validate workflow syntax and structure")
        async def validate_workflow_code(code: str) -> Dict[str, Any]:
            """Validate workflow code without creating it."""
            try:
                # Create a safe execution environment
                exec_globals = {
                    'workflow': flow_decorator,
                    'step': step,
                    '__name__': '__main__'
                }
                
                # Execute the code
                exec(code, exec_globals)
                
                # Find the workflow function
                workflow_func = None
                for item in exec_globals.values():
                    if hasattr(item, '_workflow_metadata'):
                        workflow_func = item
                        break
                
                if not workflow_func:
                    return {
                        'success': False,
                        'error': 'No workflow found in code'
                    }
                
                # Create workflow instance and validate
                workflow_instance = workflow_func()
                workflow_dict = workflow_instance.to_dict()
                errors = validate_workflow_definition(workflow_dict)
                
                return {
                    'success': len(errors) == 0,
                    'errors': errors,
                    'workflow_summary': {
                        'steps': len(workflow_dict.get('steps', [])),
                        'params': list(workflow_dict.get('params', {}).keys())
                    }
                }
                
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f'Syntax error: {str(e)}',
                    'line': e.lineno,
                    'offset': e.offset
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }


def create_mcp_server(name: str = "Kubiya MCP Server", 
                     workflows: Optional[List[Union[flow_decorator, Callable]]] = None,
                     **kwargs) -> KubiyaMCP:
    """
    Create and configure a Kubiya MCP server.
    
    Args:
        name: Server name
        workflows: Optional list of workflow functions to pre-register
        **kwargs: Additional arguments passed to KubiyaMCP
        
    Returns:
        Configured MCP server instance
    """
    server = KubiyaMCP(name, **kwargs)
    
    # Pre-register workflows if provided
    if workflows:
        for wf in workflows:
            if hasattr(wf, '_workflow_metadata'):
                # It's a workflow-decorated function
                wf_instance = wf()
                workflow_dict = wf_instance.to_dict()
                
                # Validate before storing
                errors = validate_workflow_definition(workflow_dict)
                if not errors:
                    server.workflows[wf.__name__] = workflow_dict
                else:
                    print(f"Warning: Workflow '{wf.__name__}' has validation errors: {errors}")
    
    return server


# Convenience alias
MCPServer = KubiyaMCP 