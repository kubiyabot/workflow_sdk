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
from ..client import StreamingKubiyaClient
from ..runner import WorkflowRunner
from ..stream_parser import KubiyaStreamParser
from ..validation import validate_workflow


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
        self.kubiya_client = StreamingKubiyaClient(
            api_token=api_token,
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
                    if hasattr(item, '_flow_metadata'):
                        workflow_func = item
                        break
                
                if not workflow_func:
                    return {
                        'success': False,
                        'error': 'No workflow found in code. Use @workflow or @flow decorator.'
                    }
                
                # Create workflow instance
                workflow_instance = workflow_func()
                
                # Store it
                self.workflows[name] = workflow_instance
                
                # Validate
                validation = validate_workflow(workflow_instance.to_dict())
                
                return {
                    'success': True,
                    'workflow': {
                        'name': name,
                        'description': description or workflow_instance.description,
                        'steps': len(workflow_instance.steps),
                        'params': list(workflow_instance.params.keys())
                    },
                    'validation': {
                        'valid': validation.valid,
                        'errors': validation.errors,
                        'warnings': validation.warnings
                    }
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
                    'error': f'Workflow "{name}" not found'
                }
            
            workflow = self.workflows[name]
            execution_id = f"exec-{name}-{datetime.now().timestamp()}"
            
            try:
                if self.kubiya_client:
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
                        result = await self.kubiya_client.execute_workflow_async(
                            workflow=workflow.to_dict(),
                            params=params
                        )
                        
                        self.executions[execution_id] = result
                        
                        return {
                            'success': True,
                            'execution_id': execution_id,
                            'status': result.status.value,
                            'outputs': result.outputs,
                            'duration': result.duration_seconds
                        }
                else:
                    # Local mock execution
                    runner = WorkflowRunner()
                    result = await runner.run_async(workflow, params=params)
                    
                    self.executions[execution_id] = result
                    
                    return {
                        'success': True,
                        'execution_id': execution_id,
                        'status': 'completed',
                        'outputs': result.get('outputs', {}),
                        'mocked': True
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'execution_id': execution_id,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        @self.tool(description="Get workflow execution status and results")
        async def get_execution(execution_id: str) -> Dict[str, Any]:
            """Get execution status and results."""
            if execution_id not in self.executions:
                return {
                    'success': False,
                    'error': f'Execution "{execution_id}" not found'
                }
            
            execution = self.executions[execution_id]
            
            return {
                'success': True,
                'execution_id': execution_id,
                'status': execution.get('status', 'unknown'),
                'outputs': execution.get('outputs', {}),
                'errors': execution.get('errors', []),
                'duration': execution.get('duration_seconds')
            }
        
        @self.tool(description="List all defined workflows")
        async def list_workflows() -> Dict[str, Any]:
            """List all workflows defined in this session."""
            workflows = []
            for name, wf in self.workflows.items():
                workflows.append({
                    'name': name,
                    'description': wf.description,
                    'steps': len(wf.steps),
                    'params': list(wf._context.params.keys()) if wf._context else []
                })
            
            return {
                'success': True,
                'count': len(workflows),
                'workflows': workflows
            }
        
        @self.tool(description="Export workflow as YAML or JSON")
        async def export_workflow(name: str, format: str = "yaml") -> Dict[str, Any]:
            """Export workflow definition."""
            if name not in self.workflows:
                return {
                    'success': False,
                    'error': f'Workflow "{name}" not found'
                }
            
            workflow = self.workflows[name]
            
            try:
                if format == "yaml":
                    content = workflow.to_yaml()
                elif format == "json":
                    content = workflow.to_json()
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
    
    async def _stream_execution(self, execution_id: str, workflow: flow_decorator, 
                              params: Optional[Dict[str, Any]]):
        """Stream workflow execution events."""
        try:
            events = []
            parser = KubiyaStreamParser()
            
            async for event in self.kubiya_client.execute_workflow_stream(
                workflow=workflow.to_dict(),
                params=params
            ):
                events.append(event)
                parsed = parser.parse_event(json.dumps(event))
                
                # Store intermediate state
                self.executions[execution_id] = {
                    'status': 'running',
                    'events': events,
                    'current_step': parsed.step_name if hasattr(parsed, 'step_name') else None
                }
            
            # Final state
            self.executions[execution_id]['status'] = 'completed'
            
        except Exception as e:
            self.executions[execution_id] = {
                'status': 'failed',
                'error': str(e),
                'events': events
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
                        name=step.data.get('name'),
                        type=step.data.get('executor', {}).get('type', 'unknown'),
                        description=step.data.get('description', ''),
                        depends_on=step.data.get('depends', [])
                    )
                    for step in workflow.steps
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
                        description=wf.description,
                        version=wf.version,
                        params=list(wf.params.keys())
                    )
                    for name, wf in mcp.workflows.items()
                ]
            
            def resolve_workflow(self, info, name):
                mcp = info.context['mcp']
                if name in mcp.workflows:
                    wf = mcp.workflows[name]
                    return WorkflowType(
                        name=name,
                        description=wf.description,
                        version=wf.version,
                        params=list(wf.params.keys())
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
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        
        # Call the tool handler
        if asyncio.iscoroutinefunction(tool.handler):
            return await tool.handler(**arguments)
        else:
            return tool.handler(**arguments)
    
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
            # Run with stdio transport (standard MCP)
            asyncio.run(self._run_stdio())
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    
    async def _run_stdio(self):
        """Run server with stdio transport."""
        # This would implement the full MCP stdio protocol
        # For now, we'll provide a simple REPL for testing
        print(f"🚀 {self.name} running on stdio transport")
        print("Available tools:")
        for tool in self.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
        
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, input, "\n> ")
                if line.lower() in ['exit', 'quit']:
                    break
                    
                # Simple command parser
                parts = line.split(' ', 1)
                if len(parts) < 1:
                    continue
                    
                cmd = parts[0]
                args = json.loads(parts[1]) if len(parts) > 1 else {}
                
                if cmd == "list":
                    print(json.dumps(self.list_tools(), indent=2))
                elif cmd in self.tools:
                    result = await self.call_tool(cmd, args)
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Unknown command: {cmd}")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")


class KubiyaMCP(FastMCP):
    """
    Enhanced MCP server with Kubiya-specific features.
    
    Adds workflow management, validation, and execution capabilities.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Kubiya-specific tools
        self._register_kubiya_tools()
    
    def _register_kubiya_tools(self):
        """Register additional Kubiya-specific tools."""
        
        @self.tool(description="Validate workflow syntax and structure")
        async def validate_workflow_code(code: str) -> Dict[str, Any]:
            """Validate workflow Python code without executing."""
            try:
                # Parse without executing
                compile(code, '<string>', 'exec')
                
                # Check for workflow decorator
                if '@workflow' not in code and '@flow' not in code:
                    return {
                        'success': False,
                        'error': 'No @workflow or @flow decorator found'
                    }
                
                # Check for basic structure
                issues = []
                if 'step(' not in code:
                    issues.append('No steps defined')
                
                return {
                    'success': len(issues) == 0,
                    'valid': len(issues) == 0,
                    'issues': issues
                }
                
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f'Syntax error: {e}',
                    'line': e.lineno,
                    'offset': e.offset
                }


def create_mcp_server(name: str = "Kubiya MCP Server", 
                     workflows: Optional[List[Union[flow_decorator, Callable]]] = None,
                     **kwargs) -> KubiyaMCP:
    """
    Create a Kubiya MCP server.
    
    Args:
        name: Server name
        workflows: List of workflows to register
        **kwargs: Additional server configuration
        
    Returns:
        Configured MCP server instance
    """
    server = KubiyaMCP(name, **kwargs)
    
    # Register provided workflows
    if workflows:
        for wf in workflows:
            if callable(wf) and hasattr(wf, '_flow_metadata'):
                # It's a workflow function
                instance = wf()
                server.workflows[instance.name] = instance
            elif isinstance(wf, flow_decorator):
                # It's a workflow instance
                server.workflows[wf.name] = wf
    
    return server


# Export for convenience
__all__ = ['FastMCP', 'KubiyaMCP', 'create_mcp_server'] 