"""Compiler agent for validating and compiling workflows."""

import json
import logging
import re
from typing import Dict, Any, Optional

from .base import (
    ADK_AVAILABLE, LlmAgent, LlmResponse, CallbackContext,
    types, _get_model_for_agent, _get_default_generate_config
)
from ..config import ADKConfig

logger = logging.getLogger(__name__)


class CompilerAgent(LlmAgent):
    """Agent for compiling and validating workflows."""
    
    def __init__(self, config: ADKConfig):
        self._config = config
        
        super().__init__(
            name="WorkflowCompiler",
            model=_get_model_for_agent(config, "compiler"),
            instruction=self._get_instruction(),
            description="Compiles and validates Kubiya workflows",
            generate_content_config=_get_default_generate_config(),
            before_tool_callback=self._before_tool_callback,
            after_model_callback=self._after_model_callback
        )
    
    def _get_instruction(self) -> str:
        return """You are a workflow compilation expert for Kubiya SDK.

Your task is to:
1. Get the workflow Python code from session state under the key 'workflow_code'
2. Execute the code in a safe environment to create the workflow object
3. Call workflow.to_json() to compile it to JSON format
4. Validate the JSON structure
5. Check for common issues and provide warnings

Here's how to properly execute and compile:

```python
# Execute the workflow code
namespace = {}
try:
    exec(workflow_code, namespace)
except Exception as e:
    # Handle syntax errors
    return {"status": "error", "errors": [str(e)]}

# Find the workflow object (usually named 'wf' or 'workflow')
workflow = None
for name, obj in namespace.items():
    if hasattr(obj, 'to_json') and hasattr(obj, 'data'):
        workflow = obj
        break

# Compile to JSON
if workflow:
    try:
        workflow_json = workflow.to_json()
        # Parse to ensure it's valid JSON
        import json
        compiled = json.loads(workflow_json)
    except Exception as e:
        return {"status": "error", "errors": [f"Failed to compile: {str(e)}"]}
```

Expected JSON structure:
{
  "name": "workflow_name",
  "description": "Description",
  "runner": "runner_name",
  "env": {},
  "params": {},
  "steps": [
    {
      "name": "step_name",
      "description": "Step description",
      "executor": {
        "type": "tool",
        "config": {
          "tool_def": {
            "name": "tool_name",
            "type": "docker",
            "image": "image:tag",
            "content": "script content",
            "args": []
          }
        }
      }
    }
  ]
}

Validation checks:
1. Workflow has a name
2. At least one step exists
3. All steps have unique names
4. Docker images are from trusted registries
5. Scripts have proper error handling (set -e)
6. Tool definitions are complete
7. Step dependencies reference existing steps

Return format:
<compilation_result>
{
  "status": "success",
  "workflow": {
    "name": "workflow_name",
    "description": "Description",
    "steps": [...]
  },
  "errors": [],
  "warnings": []
}
</compilation_result>

If compilation fails, return:
<compilation_result>
{
  "status": "error",
  "workflow": null,
  "errors": ["Error message describing what went wrong"],
  "warnings": []
}
</compilation_result>
"""
    
    def _before_tool_callback(
        self,
        tool_name: str,
        args: Dict[str, Any],
        callback_context: CallbackContext
    ) -> Optional[Dict[str, Any]]:
        """Validate tool calls before execution."""
        logger.debug(f"CompilerAgent calling tool: {tool_name}")
        return None  # Allow tool execution
    
    async def _after_model_callback(
        self,
        llm_response: LlmResponse,
        callback_context: CallbackContext
    ) -> Optional[LlmResponse]:
        """Save compilation results as artifacts."""
        if not llm_response or not llm_response.content:
            return llm_response
        
        try:
            response_text = llm_response.content.parts[0].text
            
            # Extract compilation result
            result_match = re.search(
                r'<compilation_result>\s*(.*?)\s*</compilation_result>',
                response_text,
                re.DOTALL
            )
            
            if result_match and hasattr(callback_context, 'save_artifact'):
                try:
                    result_json = json.loads(result_match.group(1))
                    
                    # Save compilation result
                    result_artifact = types.Part.from_bytes(
                        data=json.dumps(result_json, indent=2).encode(),
                        mime_type="application/json"
                    )
                    version = await callback_context.save_artifact(
                        filename="compilation_result.json",
                        artifact=result_artifact
                    )
                    logger.info(f"Saved compilation result as artifact version {version}")
                    
                    # If successful, save the compiled workflow separately
                    if result_json.get("status") == "success" and "workflow" in result_json:
                        workflow_artifact = types.Part.from_bytes(
                            data=json.dumps(result_json["workflow"], indent=2).encode(),
                            mime_type="application/json"
                        )
                        version = await callback_context.save_artifact(
                            filename="compiled_workflow.json",
                            artifact=workflow_artifact
                        )
                        logger.info(f"Saved compiled workflow as artifact version {version}")
                        
                        # Save to session state for other agents
                        if hasattr(callback_context, 'session'):
                            callback_context.session.state["compiled_workflow"] = result_json["workflow"]
                            callback_context.session.state["compilation_result"] = result_json
                    else:
                        # Save errors to session state
                        if hasattr(callback_context, 'session'):
                            callback_context.session.state["compilation_errors"] = result_json.get("errors", [])
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse compilation result")
        
        except Exception as e:
            logger.error(f"Error saving compilation artifacts: {e}")
        
        return llm_response
    
    def validate_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a compiled workflow.
        
        Args:
            workflow_json: Compiled workflow dictionary
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        # Check basic structure
        if not workflow_json.get("name"):
            errors.append("Workflow must have a name")
        
        if not workflow_json.get("steps"):
            errors.append("Workflow must have at least one step")
        
        # Check steps
        step_names = set()
        for i, step in enumerate(workflow_json.get("steps", [])):
            if not step.get("name"):
                errors.append(f"Step {i+1} must have a name")
            else:
                step_name = step["name"]
                if step_name in step_names:
                    errors.append(f"Duplicate step name: {step_name}")
                step_names.add(step_name)
            
            # Check executor
            executor = step.get("executor", {})
            if not executor.get("type"):
                errors.append(f"Step '{step.get('name', i+1)}' must have an executor type")
            
            # Check tool definitions
            if executor.get("type") == "tool":
                config = executor.get("config", {})
                tool_def = config.get("tool_def")
                if tool_def:
                    if not tool_def.get("image"):
                        errors.append(f"Step '{step.get('name', i+1)}' tool definition must have an image")
                    if not tool_def.get("content"):
                        warnings.append(f"Step '{step.get('name', i+1)}' tool definition has no content")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


def create_compiler_agent(config: ADKConfig) -> CompilerAgent:
    """Create a compiler agent."""
    return CompilerAgent(config) 