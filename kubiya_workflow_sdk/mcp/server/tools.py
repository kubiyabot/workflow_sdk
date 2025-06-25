"""MCP Tools for workflow compilation and execution."""

import asyncio
import json
import logging
import traceback
import os
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

from kubiya_workflow_sdk.dsl import Workflow
from kubiya_workflow_sdk.execution import validate_workflow_definition
from kubiya_workflow_sdk.client import StreamingKubiyaClient

logger = logging.getLogger(__name__)


def register_tools(mcp, server):
    """Register all MCP tools with the server."""
    
    @mcp.tool()
    async def compile_workflow(
        dsl_code: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        runner: Optional[str] = None,
        prefer_docker: bool = True,
        provide_missing_secrets: Optional[Union[str, Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Compile Kubiya DSL code into a workflow JSON manifest.
        
        This tool validates the DSL and produces a workflow that can be executed.
        It provides intelligent feedback about runners, Docker images, secrets, and best practices.
        
        Args:
            dsl_code: Python code using Kubiya DSL (NO decorators, just simple DSL)
            name: Optional workflow name (overrides name in code)
            description: Optional workflow description
            runner: Specific runner to use (validates availability)
            prefer_docker: Prefer Docker-based steps when possible
            provide_missing_secrets: Dict of secret_name -> secret_value for missing secrets
            
        Returns:
            Compilation result with manifest, validation, and suggestions
            
        Example DSL:
            ```python
            from kubiya_workflow_sdk.dsl import Workflow
            
            wf = Workflow("data-processor")
            wf.description("Process CSV data with pandas")
            
            # Add parameters
            wf.params(
                input_file={"default": "data.csv"},
                output_file={"default": "results.json"}
            )
            
            # Add environment variables (including secrets)
            wf.env(
                AWS_ACCESS_KEY_ID="{{secret:AWS_ACCESS_KEY_ID}}",
                AWS_SECRET_ACCESS_KEY="{{secret:AWS_SECRET_ACCESS_KEY}}"
            )
            
            # Using Docker for better isolation
            wf.step("process").docker(
                image="python:3.11-slim",
                content="python -c 'import pandas; print(pandas.__version__)'"
            )
            
            # Add files to the workflow
            wf.with_files({
                "config.json": '{"key": "value"}',
                "script.py": open("local_script.py").read()
            })
            ```
        """
        try:
            # Parse provide_missing_secrets if it's a JSON string
            if isinstance(provide_missing_secrets, str):
                try:
                    provide_missing_secrets = json.loads(provide_missing_secrets)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "errors": [f"Invalid JSON in provide_missing_secrets: {str(e)}"],
                        "provide_missing_secrets_received": provide_missing_secrets
                    }
            
            # Refresh context if needed
            if not server.workflow_context.runners:
                await server.refresh_context()
            
            # Create execution namespace
            exec_globals = {
                "Workflow": Workflow,
                "__builtins__": __builtins__,
            }
            
            # Execute the DSL code
            exec(dsl_code, exec_globals)
            
            # Find the workflow object
            workflow_obj = None
            for var_name, var_value in exec_globals.items():
                if isinstance(var_value, Workflow):
                    workflow_obj = var_value
                    break
            
            if not workflow_obj:
                return {
                    "success": False,
                    "errors": ["No Workflow object found. Create one with: wf = Workflow('name')"],
                    "suggestions": [
                        "from kubiya_workflow_sdk.dsl import Workflow",
                        "wf = Workflow('my-workflow')",
                        "wf.description('What this workflow does')",
                        "wf.step('step1', 'echo Hello')"
                    ],
                    "docker_tips": server.integration_context.get_docker_suggestions("general")
                }
            
            # Get the workflow definition
            workflow_def = workflow_obj.to_dict()
            
            # Auto-convert complex steps to Docker if prefer_docker is True
            if prefer_docker:
                workflow_def = _convert_complex_steps_to_docker(workflow_def, server)
            
            # Override fields if provided
            if name:
                workflow_def["name"] = name
            if description:
                workflow_def["description"] = description
            
            # Handle runner
            if runner:
                # Validate runner
                valid, message = server.workflow_context.validate_runner(runner)
                if not valid:
                    return {
                        "success": False,
                        "errors": [message],
                        "available_runners": [r.name for r in server.workflow_context.get_available_runners()],
                        "docker_runners": [r.name for r in server.workflow_context.get_docker_runners()]
                    }
                workflow_def["runner"] = runner
            else:
                # Use default runner
                workflow_def["runner"] = server.workflow_context.default_runner
            
            # Analyze secrets usage
            secrets_analysis = _analyze_secrets(workflow_def, server, provide_missing_secrets)
            
            # Handle missing secrets
            if secrets_analysis["missing"] and not provide_missing_secrets:
                # Add parameters for missing secrets
                if "params" not in workflow_def:
                    workflow_def["params"] = {}
                
                for secret in secrets_analysis["missing"]:
                    param_name = secret.lower().replace('_', '-')
                    if param_name not in workflow_def["params"]:
                        workflow_def["params"][param_name] = {
                            "description": f"Value for secret {secret}",
                            "required": True,
                            "secret": True  # Mark as sensitive
                        }
                
                # Add environment mapping
                if "env" not in workflow_def:
                    workflow_def["env"] = {}
                
                env_mapping = server.secrets_context.generate_env_mapping()
                workflow_def["env"].update(env_mapping)
            
            # If missing secrets are provided, add them as env vars
            elif provide_missing_secrets:
                if "env" not in workflow_def:
                    workflow_def["env"] = {}
                
                for secret_name, secret_value in provide_missing_secrets.items():
                    workflow_def["env"][secret_name] = secret_value
            
            # Validate the workflow
            validation_errors = validate_workflow_definition(workflow_def)
            
            # Analyze workflow for suggestions
            suggestions = _analyze_workflow(workflow_def, server, prefer_docker)
            
            if validation_errors:
                return {
                    "success": False,
                    "manifest": workflow_def,
                    "errors": validation_errors,
                    "suggestions": suggestions,
                    "workflow_name": workflow_def.get("name", "unnamed"),
                    "steps_count": len(workflow_def.get("steps", [])),
                    "secrets": secrets_analysis
                }
            
            # Success response with rich context
            return {
                "success": True,
                "manifest": workflow_def,
                "errors": [],
                "workflow_name": workflow_def.get("name", "unnamed"),
                "description": workflow_def.get("description", ""),
                "runner": workflow_def.get("runner"),
                "steps_count": len(workflow_def.get("steps", [])),
                "parameters": list(workflow_def.get("params", {}).keys()),
                "environment_vars": list(workflow_def.get("env", {}).keys()),
                "secrets": secrets_analysis,
                "steps": [
                    {
                        "name": step.get("name", f"step-{i}"),
                        "type": _get_step_type(step),
                        "description": _get_step_description(step)
                    }
                    for i, step in enumerate(workflow_def.get("steps", []))
                ],
                "suggestions": suggestions,
                "docker_images_used": _get_docker_images(workflow_def),
                "files_included": list(workflow_def.get("files", {}).keys()) if "files" in workflow_def else [],
                "estimated_duration": _estimate_duration(workflow_def)
            }
            
        except SyntaxError as e:
            return {
                "success": False,
                "errors": [f"Syntax error at line {e.lineno}: {str(e)}"],
                "line_number": e.lineno,
                "suggestions": [
                    "Check indentation (use 4 spaces)",
                    "Verify all quotes are closed",
                    "Ensure parentheses and brackets match"
                ]
            }
        except Exception as e:
            logger.error(f"Error compiling workflow: {e}", exc_info=True)
            return {
                "success": False,
                "errors": [str(e)],
                "traceback": traceback.format_exc(),
                "suggestions": ["Check the DSL syntax", "Ensure all required imports are present"]
            }
    
    @mcp.tool()
    async def execute_workflow(
        workflow_input: Union[str, Dict[str, Any]],
        params: Optional[Union[str, Dict[str, Any]]] = None,
        api_key: Optional[str] = None,
        runner: Optional[str] = None,
        dry_run: bool = False,
        stream_format: str = "vercel",
    ) -> Dict[str, Any]:
        """
        Execute a workflow with real-time streaming of execution events.
        
        Accepts either DSL code or a compiled JSON manifest. Provides detailed
        execution feedback with step-by-step progress.
        
        Args:
            workflow_input: DSL code (string) or compiled manifest (dict)
            params: Workflow parameters/inputs (including secret values)
            api_key: Kubiya API key (optional, uses env/headers if not provided)
            runner: Override runner (validates before execution)
            dry_run: Validate without executing
            stream_format: Event format - "vercel" for Vercel AI SDK or "raw" for standard
            
        Returns:
            Execution result with all events
        """
        try:
            # Parse params if it's a JSON string
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "type": "validation_error",
                        "error": f"Invalid JSON in params: {str(e)}",
                        "params_received": params
                    }
            
            # Get authenticated client
            client = server.get_client(api_key)
            
            # Compile if needed
            workflow_def = None
            if isinstance(workflow_input, str):
                # Compile DSL first
                compile_result = await compile_workflow(
                    dsl_code=workflow_input,
                    runner=runner,
                    prefer_docker=True
                )
                
                if not compile_result["success"]:
                    return {
                        "success": False,
                        "type": "compilation_error",
                        "error": "Compilation failed",
                        "details": compile_result["errors"],
                        "suggestions": compile_result.get("suggestions", [])
                    }
                
                workflow_def = compile_result["manifest"]
            else:
                workflow_def = workflow_input
            
            # Validate runner if specified
            if runner:
                workflow_def["runner"] = runner
                valid, message = server.workflow_context.validate_runner(runner)
                if not valid:
                    return {
                        "success": False,
                        "type": "validation_error", 
                        "error": message,
                        "available_runners": [r.name for r in server.workflow_context.get_available_runners()]
                    }
            
            # Dry run - just validate
            if dry_run:
                validation_errors = validate_workflow_definition(workflow_def)
                return {
                    "success": len(validation_errors) == 0,
                    "type": "validation_result",
                    "valid": len(validation_errors) == 0,
                    "errors": validation_errors,
                    "workflow": workflow_def.get("name"),
                    "steps": len(workflow_def.get("steps", [])),
                    "runner": workflow_def.get("runner")
                }
            
            # Execute with streaming - collect all events
            events = []
            event_count = 0
            start_time = datetime.now()
            
            # Add initial event
            events.append({
                "type": "workflow_start",
                "workflow": workflow_def.get("name"),
                "runner": workflow_def.get("runner"),
                "timestamp": start_time.isoformat(),
                "parameters": params
            })
            
            try:
                # Use the streaming client to execute
                streaming_client = StreamingKubiyaClient(
                    api_key=client.api_key,
                    base_url=client.base_url,
                    runner=workflow_def.get("runner", client.runner),
                    timeout=client.timeout,
                    org_name=client.org_name
                )
                
                # Stream execution and collect events
                async for event in streaming_client.execute_workflow_stream(workflow_def, params):
                    event_count += 1
                    
                    # Enhance events with additional context
                    if isinstance(event, dict):
                        event["event_number"] = event_count
                        
                        # Add step context if available
                        if event.get("type") == "step_running":
                            step_name = event.get("step", {}).get("name")
                            if step_name:
                                # Find step definition
                                for step in workflow_def.get("steps", []):
                                    if step.get("name") == step_name:
                                        event["step_type"] = _get_step_type(step)
                                        event["uses_docker"] = "executor" in step and step["executor"].get("type") == "docker"
                                        break
                    
                    events.append(event)
                
                # Add completion event
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                events.append({
                    "type": "workflow_complete",
                    "duration": duration,
                    "events": event_count,
                    "timestamp": end_time.isoformat(),
                    "success": True
                })
                
                # Return all events
                return {
                    "success": True,
                    "type": "execution_result",
                    "workflow": workflow_def.get("name"),
                    "runner": workflow_def.get("runner"),
                    "duration": duration,
                    "event_count": event_count,
                    "events": events,
                    "summary": {
                        "total_steps": len(workflow_def.get("steps", [])),
                        "executed_steps": sum(1 for e in events if e.get("type") == "step_complete"),
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    }
                }
                
            except Exception as e:
                # Handle execution errors
                logger.error(f"Workflow execution failed: {e}", exc_info=True)
                
                # Add error event
                events.append({
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "success": False,
                    "type": "execution_error",
                    "error": str(e),
                    "workflow": workflow_def.get("name"),
                    "runner": workflow_def.get("runner"),
                    "events": events,
                    "duration": (datetime.now() - start_time).total_seconds()
                }
                
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            error_msg = str(e)
            
            if "API key" in error_msg:
                error_msg = "Authentication failed. Please provide a valid API key."
            
            return {
                "success": False,
                "type": "error",
                "error": error_msg,
                "traceback": traceback.format_exc() if logger.isEnabledFor(logging.DEBUG) else None
            }
    
    @mcp.tool()
    async def get_workflow_runners(
        api_key: Optional[str] = None,
        refresh: bool = False,
        include_health: bool = True,
        component_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get available workflow runners with health status.
        
        Returns detailed information about each runner including capabilities,
        Docker support, health status, and component versions.
        
        Args:
            api_key: Optional API key (uses env/headers if not provided)
            refresh: Force refresh from API
            include_health: Include health status information
            component_filter: Filter by component (e.g., "agent-manager", "tool-manager")
            
        Returns:
            Runner information with health status and recommendations
        """
        try:
            # Refresh if needed or requested
            if refresh or not server.workflow_context.runners:
                await server.refresh_context(api_key)
            
            # Get runners based on filter
            if component_filter:
                runners = server.workflow_context.get_runners_by_component(component_filter)
            else:
                runners = server.workflow_context.get_available_runners()
            
            docker_runners = server.workflow_context.get_docker_runners()
            
            # Build runner details with health info
            runner_details = []
            for r in runners:
                runner_info = {
                    "name": r.name,
                    "type": r.type,
                    "status": r.status,
                    "docker_enabled": r.docker_enabled,
                    "is_healthy": r.is_healthy,
                    "health_status": r.health_status,
                    "meets_requirements": r.meets_requirements,
                    "components": {
                        name: {
                            "version": info.get("version", "unknown"),
                            "status": info.get("status", "unknown")
                        }
                        for name, info in r.component_versions.items()
                    },
                    "last_health_check": r.last_health_check.isoformat() if r.last_health_check else None
                }
                
                # Add health information if available
                if include_health:
                    runner_info.update({
                        "health_status": r.health_status,
                        "is_healthy": r.is_healthy,
                        "meets_requirements": r.meets_requirements,
                        "components": {
                            name: {
                                "version": info.get("version", "unknown"),
                                "status": info.get("status", "unknown")
                            }
                            for name, info in r.component_versions.items()
                        },
                        "last_health_check": r.last_health_check.isoformat() if r.last_health_check else None
                    })
                
                runner_details.append(runner_info)
            
            # Get component requirements
            component_reqs = server.workflow_context.component_requirements
            
            return {
                "success": True,
                "runners": runner_details,
                "default_runner": server.workflow_context.default_runner,
                "total_count": len(runners),
                "healthy_count": sum(1 for r in runners if r.is_healthy),
                "docker_enabled_count": len(docker_runners),
                "component_requirements": component_reqs,
                "recommendations": {
                    "docker_workflows": [r.name for r in docker_runners[:3]],
                    "general_purpose": server.workflow_context.default_runner,
                    "by_component": {
                        "agent-manager": [
                            r.name for r in runners 
                            if r.has_component("agent-manager")
                        ][:3],
                        "tool-manager": [
                            r.name for r in runners 
                            if r.has_component("tool-manager")
                        ][:3]
                    },
                    "tips": [
                        "Check health_status to ensure runner availability",
                        "Runners must meet component version requirements",
                        f"Default runner '{server.workflow_context.default_runner}' works for most cases"
                    ]
                },
                "health_summary": {
                    "check_enabled": os.getenv("KUBIYA_CHECK_RUNNER_HEALTH", "true").lower() == "true",
                    "unhealthy_runners": [
                        r.name for r in server.workflow_context.runners.values() 
                        if not r.is_healthy
                    ],
                    "filtered_by_requirements": [
                        r.name for r in server.workflow_context.runners.values()
                        if r.is_healthy and not r.meets_requirements
                    ]
                },
                "last_updated": server.workflow_context.last_updated.isoformat() if server.workflow_context.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get runners: {e}")
            return {
                "success": False,
                "error": str(e),
                "runners": [],
                "default_runner": server.workflow_context.default_runner,
                "tips": [
                    "Check API key configuration", 
                    "Ensure network connectivity",
                    "Set KUBIYA_CHECK_RUNNER_HEALTH=false to skip health checks"
                ]
            }
    
    @mcp.tool()
    async def get_integrations(
        api_key: Optional[str] = None,
        category: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Get available integrations and Docker images for workflows.
        
        Provides integration details and Docker image recommendations
        for different types of tasks.
        
        Args:
            api_key: Optional API key
            category: Filter by category (python, nodejs, cloud_cli, etc)
            refresh: Force refresh from API
            
        Returns:
            Integration details with Docker recommendations
        """
        try:
            # Refresh if needed
            if refresh or not server.integration_context.integrations:
                await server.refresh_context(api_key)
            
            integrations = list(server.integration_context.integrations.values())
            
            # Filter by category if specified
            if category:
                integrations = [
                    i for i in integrations 
                    if category.lower() in i.type.lower() or category.lower() in i.description.lower()
                ]
            
            # Get Docker image suggestions
            docker_suggestions = {}
            for cat, images in server.integration_context.docker_images.items():
                if not category or category.lower() in cat.lower():
                    docker_suggestions[cat] = images
            
            return {
                "success": True,
                "integrations": [
                    {
                        "name": i.name,
                        "type": i.type,
                        "description": i.description,
                        "docker_based": i.is_docker_based,
                        "docker_image": i.docker_image,
                        "commands": i.commands,
                        "environment_vars": i.environment_vars,
                        "required_secrets": i.required_secrets
                    }
                    for i in integrations
                ],
                "docker_images": docker_suggestions,
                "total_count": len(integrations),
                "docker_based_count": sum(1 for i in integrations if i.is_docker_based),
                "categories": list(server.integration_context.docker_images.keys()),
                "recommendations": _get_integration_recommendations(category, server),
                "last_updated": server.integration_context.last_updated.isoformat() if server.integration_context.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get integrations: {e}")
            return {
                "success": False,
                "error": str(e),
                "integrations": [],
                "docker_images": server.integration_context.docker_images,
                "tips": ["Docker images are categorized by use case", "Use specific images for better performance"]
            }
    
    @mcp.tool()
    async def get_workflow_secrets(
        api_key: Optional[str] = None,
        pattern: Optional[str] = None,
        task_type: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Get available secrets for workflow development.
        
        Returns secret names (not values) and provides suggestions for
        commonly needed secrets based on the task type.
        
        Args:
            api_key: Optional API key
            pattern: Filter secrets by pattern (e.g., "AWS_*", "*_TOKEN")
            task_type: Task type for suggestions (aws, database, api, etc)
            refresh: Force refresh from API
            
        Returns:
            Secret information with usage guidance
        """
        try:
            # Refresh if needed
            if refresh or not server.secrets_context.secrets:
                await server.refresh_context(api_key)
            
            secrets = list(server.secrets_context.secrets.values())
            
            # Filter by pattern if specified
            if pattern:
                secrets = [s for s in secrets if s.matches_pattern(pattern)]
            
            # Get task-specific suggestions
            suggestions = {}
            if task_type:
                suggestions = server.secrets_context.get_secret_suggestions(task_type)
            
            return {
                "success": True,
                "secrets": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "type": s.type,
                        "tags": s.tags
                    }
                    for s in secrets
                ],
                "total_count": len(secrets),
                "suggestions": suggestions,
                "usage_examples": {
                    "in_commands": "echo {{secret:SECRET_NAME}}",
                    "as_env_var": "wf.env(MY_VAR='{{secret:SECRET_NAME}}')",
                    "for_missing": "Pass as parameter: wf.params(secret_name={'required': True, 'secret': True})"
                },
                "dsl_examples": [
                    {
                        "name": "AWS credentials",
                        "code": '''wf.env(
    AWS_ACCESS_KEY_ID="{{secret:AWS_ACCESS_KEY_ID}}",
    AWS_SECRET_ACCESS_KEY="{{secret:AWS_SECRET_ACCESS_KEY}}",
    AWS_REGION="{{secret:AWS_REGION}}"
)'''
                    },
                    {
                        "name": "Database connection",
                        "code": '''wf.env(DATABASE_URL="{{secret:DATABASE_URL}}")
# Or individual components
wf.env(
    DB_HOST="{{secret:DB_HOST}}",
    DB_USER="{{secret:DB_USER}}",
    DB_PASSWORD="{{secret:DB_PASSWORD}}"
)'''
                    }
                ],
                "last_updated": server.secrets_context.last_updated.isoformat() if server.secrets_context.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get secrets: {e}")
            return {
                "success": False,
                "error": str(e),
                "secrets": [],
                "tips": [
                    "Secrets are stored securely in Kubiya",
                    "Use parameters for secrets not in the vault",
                    "Mark sensitive parameters with 'secret': True"
                ]
            }


# Helper functions
def _get_step_type(step: Dict[str, Any]) -> str:
    """Determine the type of a workflow step."""
    if "executor" in step:
        return step["executor"].get("type", "unknown")
    elif "command" in step:
        return "shell"
    elif "script" in step:
        return "script"
    elif "run" in step:
        return "workflow"
    else:
        return "unknown"


def _get_step_description(step: Dict[str, Any]) -> str:
    """Generate a description for a step."""
    step_type = _get_step_type(step)
    
    if step_type == "docker":
        image = step.get("executor", {}).get("config", {}).get("image", "unknown")
        return f"Docker step using {image}"
    elif step_type == "shell":
        cmd = step.get("command", "")[:50]
        return f"Shell command: {cmd}..."
    elif step_type == "script":
        return "Script execution"
    else:
        return f"{step_type} step"


def _get_docker_images(workflow_def: Dict[str, Any]) -> List[str]:
    """Extract all Docker images used in a workflow."""
    images = []
    for step in workflow_def.get("steps", []):
        if step.get("executor", {}).get("type") == "docker":
            image = step["executor"].get("config", {}).get("image")
            if image and image not in images:
                images.append(image)
    return images


def _estimate_duration(workflow_def: Dict[str, Any]) -> str:
    """Estimate workflow duration based on steps."""
    step_count = len(workflow_def.get("steps", []))
    docker_steps = sum(1 for s in workflow_def.get("steps", []) if _get_step_type(s) == "docker")
    
    # Basic estimation
    base_time = step_count * 5  # 5 seconds per step
    docker_time = docker_steps * 10  # Extra time for Docker
    
    total_seconds = base_time + docker_time
    
    if total_seconds < 60:
        return f"{total_seconds} seconds"
    else:
        return f"{total_seconds // 60} minutes"


def _analyze_workflow(workflow_def: Dict[str, Any], server, prefer_docker: bool) -> List[str]:
    """Analyze workflow and provide suggestions."""
    suggestions = []
    
    # Check for Docker usage
    docker_steps = [s for s in workflow_def.get("steps", []) if _get_step_type(s) == "docker"]
    shell_steps = [s for s in workflow_def.get("steps", []) if _get_step_type(s) == "shell"]
    script_steps = [s for s in workflow_def.get("steps", []) if _get_step_type(s) == "script"]
    
    # Analyze each step for complexity
    for step in workflow_def.get("steps", []):
        step_name = step.get("name", "unnamed")
        step_type = _get_step_type(step)
        
        # Check if step is complex and should use Docker
        if step_type == "shell" or step_type == "script":
            command = step.get("command", "") or step.get("script", "")
            
            # Indicators of complex steps that should use Docker
            complex_indicators = [
                # Package management
                ("pip install" in command, "python:3.11-slim", "Python package installation"),
                ("npm install" in command, "node:20-slim", "Node.js package installation"),
                ("apt-get" in command, "ubuntu:22.04", "System package installation"),
                ("yum install" in command, "centos:8", "System package installation"),
                ("gem install" in command, "ruby:3.2-slim", "Ruby gem installation"),
                
                # Language execution
                ("python" in command and "import" in command, "python:3.11-slim", "Python script execution"),
                ("node" in command or "nodejs" in command, "node:20-slim", "Node.js execution"),
                ("go run" in command, "golang:1.21-alpine", "Go execution"),
                ("java" in command, "openjdk:17-slim", "Java execution"),
                ("ruby" in command, "ruby:3.2-slim", "Ruby execution"),
                
                # Data processing
                ("pandas" in command, "jupyter/scipy-notebook:latest", "Data processing with pandas"),
                ("numpy" in command, "jupyter/scipy-notebook:latest", "Scientific computing"),
                ("tensorflow" in command, "tensorflow/tensorflow:latest", "Machine learning"),
                ("scikit" in command, "jupyter/scipy-notebook:latest", "Machine learning"),
                
                # Database operations
                ("psql" in command, "postgres:15-alpine", "PostgreSQL operations"),
                ("mysql" in command, "mysql:8.0", "MySQL operations"),
                ("mongosh" in command or "mongo" in command, "mongo:7.0", "MongoDB operations"),
                ("redis-cli" in command, "redis:7-alpine", "Redis operations"),
                
                # Cloud CLI tools
                ("aws" in command, "amazon/aws-cli:latest", "AWS CLI operations"),
                ("gcloud" in command, "google/cloud-sdk:latest", "Google Cloud operations"),
                ("az" in command, "mcr.microsoft.com/azure-cli:latest", "Azure CLI operations"),
                
                # File operations
                ("curl" in command and ("http" in command or "ftp" in command), "curlimages/curl:latest", "HTTP/FTP operations"),
                ("wget" in command, "alpine:latest", "File download"),
                ("jq" in command, "stedolan/jq:latest", "JSON processing"),
                
                # Build tools
                ("docker build" in command, "docker:24-dind", "Docker operations"),
                ("make" in command, "gcc:latest", "Build operations"),
                ("gradle" in command, "gradle:8-jdk17", "Gradle build"),
                ("maven" in command or "mvn" in command, "maven:3.9-openjdk-17", "Maven build"),
            ]
            
            for indicator, suggested_image, operation_type in complex_indicators:
                if indicator:
                    suggestions.append(
                        f"Step '{step_name}': Consider using Docker with image '{suggested_image}' for {operation_type}"
                    )
                    break
            else:
                # Check for multi-line scripts or complex shell operations
                if "\n" in command and len(command.splitlines()) > 3:
                    suggestions.append(
                        f"Step '{step_name}': Multi-line script detected. Consider using Docker for better isolation"
                    )
                elif any(op in command for op in ["&&", "||", "|", ";", ">"]):
                    suggestions.append(
                        f"Step '{step_name}': Complex shell operations detected. Consider using Docker for consistency"
                    )
    
    # General Docker suggestions
    if prefer_docker and shell_steps and not docker_steps:
        suggestions.append("Consider using Docker steps for better isolation and reproducibility")
        suggestions.append("Docker ensures consistent environments across different runners")
    
    # Check runner selection
    runner = workflow_def.get("runner")
    if runner and runner in server.workflow_context.runners:
        runner_info = server.workflow_context.runners[runner]
        if docker_steps and not runner_info.supports_docker():
            suggestions.append(f"Runner '{runner}' may not support Docker. Consider using a Docker-enabled runner.")
    
    # Parameter suggestions
    if not workflow_def.get("params"):
        suggestions.append("Consider adding parameters for flexibility: wf.params(key={'default': 'value'})")
    
    # Error handling
    has_error_handling = any(
        s.get("continueOn", {}).get("failure") or s.get("retryPolicy")
        for s in workflow_def.get("steps", [])
    )
    if not has_error_handling:
        suggestions.append("Consider adding error handling with retry policies or continue_on conditions")
    
    # File handling
    if not workflow_def.get("files"):
        suggestions.append("Use wf.with_files() to include configuration files or scripts in the workflow")
    
    return suggestions


def _analyze_secrets(workflow_def: Dict[str, Any], server, provide_missing_secrets: Optional[Dict[str, str]]) -> Dict[str, Any]:
    """Analyze secrets usage in the workflow."""
    analysis = {
        "used": [],
        "available": [],
        "missing": [],
        "suggestions": []
    }
    
    # Find all secret references in the workflow
    secret_refs = set()
    
    # Check environment variables
    for key, value in workflow_def.get("env", {}).items():
        if isinstance(value, str) and "{{secret:" in value:
            # Extract secret name
            import re
            matches = re.findall(r'\{\{secret:([^}]+)\}\}', value)
            secret_refs.update(matches)
    
    # Check step commands
    for step in workflow_def.get("steps", []):
        cmd = step.get("command", "") or step.get("run", "")
        if isinstance(cmd, str) and "{{secret:" in cmd:
            import re
            matches = re.findall(r'\{\{secret:([^}]+)\}\}', cmd)
            secret_refs.update(matches)
    
    # Analyze each secret reference
    for secret_name in secret_refs:
        analysis["used"].append(secret_name)
        
        if server.secrets_context.has_secret(secret_name):
            analysis["available"].append(secret_name)
        else:
            analysis["missing"].append(secret_name)
            server.secrets_context.mark_required(secret_name)
    
    # Add suggestions based on workflow content
    workflow_content = json.dumps(workflow_def).lower()
    
    if "aws" in workflow_content or "s3" in workflow_content:
        aws_suggestions = server.secrets_context.get_secret_suggestions("aws")
        analysis["suggestions"].extend(aws_suggestions.get("commonly_needed", []))
    
    if "database" in workflow_content or "postgres" in workflow_content or "mysql" in workflow_content:
        db_suggestions = server.secrets_context.get_secret_suggestions("database")
        analysis["suggestions"].extend(db_suggestions.get("commonly_needed", []))
    
    # Remove duplicates
    analysis["suggestions"] = list(set(analysis["suggestions"]) - set(analysis["used"]))
    
    return analysis


def _get_integration_recommendations(category: Optional[str], server) -> Dict[str, Any]:
    """Get integration recommendations based on category."""
    recommendations = {
        "tips": [],
        "docker_images": [],
        "examples": []
    }
    
    if not category:
        recommendations["tips"] = [
            "Use category parameter to filter integrations",
            "Docker-based integrations provide better isolation",
            "Check required_secrets for authentication needs"
        ]
        return recommendations
    
    # Category-specific recommendations
    category_lower = category.lower()
    
    if "python" in category_lower:
        recommendations["docker_images"] = server.integration_context.docker_images.get("python", [])[:3]
        recommendations["tips"] = [
            "Use slim images for smaller size",
            "Install dependencies in Dockerfile for caching",
            "Consider jupyter/scipy-notebook for data science"
        ]
        recommendations["examples"] = [
            "python:3.11-slim for lightweight apps",
            "python:3.11 for full Python environment"
        ]
    
    elif "cloud" in category_lower:
        recommendations["docker_images"] = server.integration_context.docker_images.get("cloud_cli", [])[:3]
        recommendations["tips"] = [
            "Mount credentials as files or use environment variables",
            "Use official cloud provider images",
            "Consider multi-cloud tools for flexibility"
        ]
    
    elif "data" in category_lower:
        recommendations["docker_images"] = server.integration_context.docker_images.get("data_processing", [])[:3]
        recommendations["tips"] = [
            "Use specialized images for data tools",
            "Mount data volumes for large datasets",
            "Consider Apache Spark for big data"
        ]
    
    return recommendations


def _convert_complex_steps_to_docker(workflow_def: Dict[str, Any], server) -> Dict[str, Any]:
    """Convert complex shell/script steps to Docker steps automatically."""
    modified_steps = []
    
    for step in workflow_def.get("steps", []):
        step_copy = step.copy()
        step_type = _get_step_type(step)
        
        # Only convert shell or script steps
        if step_type in ["shell", "script"]:
            command = step.get("command", "") or step.get("script", "")
            
            # Determine if this step should be converted to Docker
            should_convert = False
            suggested_image = "ubuntu:22.04"  # Default image
            
            # Check for complex operations
            complex_patterns = [
                # Package management
                ("pip install", "python:3.11-slim"),
                ("pip3 install", "python:3.11-slim"),
                ("npm install", "node:20-slim"),
                ("npm ci", "node:20-slim"),
                ("yarn install", "node:20-slim"),
                ("apt-get", "ubuntu:22.04"),
                ("apt install", "ubuntu:22.04"),
                ("yum install", "centos:8"),
                ("apk add", "alpine:latest"),
                ("gem install", "ruby:3.2-slim"),
                ("cargo install", "rust:latest"),
                
                # Python execution
                ("python3", "python:3.11-slim"),
                ("python -m", "python:3.11-slim"),
                ("import ", "python:3.11-slim"),  # Python script
                
                # Node.js execution
                ("node ", "node:20-slim"),
                ("npm run", "node:20-slim"),
                ("yarn run", "node:20-slim"),
                ("npx ", "node:20-slim"),
                
                # Other languages
                ("go run", "golang:1.21-alpine"),
                ("go build", "golang:1.21-alpine"),
                ("java -jar", "openjdk:17-slim"),
                ("javac", "openjdk:17-slim"),
                ("ruby ", "ruby:3.2-slim"),
                ("php ", "php:8.2-cli"),
                ("dotnet run", "mcr.microsoft.com/dotnet/sdk:7.0"),
                
                # Data tools
                ("pandas", "jupyter/scipy-notebook:latest"),
                ("numpy", "jupyter/scipy-notebook:latest"),
                ("scipy", "jupyter/scipy-notebook:latest"),
                ("jupyter", "jupyter/scipy-notebook:latest"),
                ("tensorflow", "tensorflow/tensorflow:latest"),
                ("torch", "pytorch/pytorch:latest"),
                ("sklearn", "jupyter/scipy-notebook:latest"),
                
                # Database tools
                ("psql", "postgres:15-alpine"),
                ("mysql ", "mysql:8.0"),
                ("mongosh", "mongo:7.0"),
                ("redis-cli", "redis:7-alpine"),
                ("sqlite3", "alpine:latest"),
                
                # Cloud CLIs
                ("aws ", "amazon/aws-cli:latest"),
                ("gcloud ", "google/cloud-sdk:latest"),
                ("az ", "mcr.microsoft.com/azure-cli:latest"),
                ("kubectl", "bitnami/kubectl:latest"),
                ("terraform", "hashicorp/terraform:latest"),
                
                # Network tools
                ("curl -", "curlimages/curl:latest"),
                ("wget ", "alpine:latest"),
                ("httpie", "alpine:latest"),
                
                # Build tools
                ("docker build", "docker:24-dind"),
                ("docker-compose", "docker/compose:latest"),
                ("make ", "gcc:latest"),
                ("cmake", "gcc:latest"),
                ("gradle ", "gradle:8-jdk17"),
                ("mvn ", "maven:3.9-openjdk-17"),
                
                # Data processing
                ("jq ", "stedolan/jq:latest"),
                ("yq ", "mikefarah/yq:latest"),
                ("awk ", "alpine:latest"),
                ("sed ", "alpine:latest"),
            ]
            
            # Check each pattern
            for pattern, image in complex_patterns:
                if pattern in command.lower():
                    should_convert = True
                    suggested_image = image
                    break
            
            # Also convert if:
            # - Multi-line script with more than 3 lines
            # - Contains complex shell operators
            # - Has script content (not just command)
            if not should_convert:
                if step.get("script") or (command.count("\n") > 2):
                    should_convert = True
                    # Try to detect language from script content
                    if "#!/usr/bin/env python" in command or "import " in command:
                        suggested_image = "python:3.11-slim"
                    elif "#!/usr/bin/env node" in command or "require(" in command:
                        suggested_image = "node:20-slim"
                    elif "#!/bin/bash" in command:
                        suggested_image = "bash:latest"
                elif any(op in command for op in ["&&", "||", "|", "$(", "`", ">"]):
                    should_convert = True
                    suggested_image = "alpine:latest"
            
            # Convert to Docker step if needed
            if should_convert:
                step_copy = {
                    "name": step.get("name", "unnamed"),
                    "executor": {
                        "type": "docker",
                        "config": {
                            "image": suggested_image,
                            "content": command  # Use content field as entrypoint
                        }
                    }
                }
                
                # Preserve other step properties
                for key in ["depends", "env", "output", "timeout", "retryPolicy", "continueOn", "condition"]:
                    if key in step:
                        step_copy[key] = step[key]
                
                logger.info(f"Auto-converted step '{step_copy['name']}' to Docker with image '{suggested_image}'")
        
        modified_steps.append(step_copy)
    
    workflow_def["steps"] = modified_steps
    return workflow_def 