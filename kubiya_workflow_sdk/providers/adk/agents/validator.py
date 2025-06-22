"""Workflow validator agent for validating requirements fulfillment."""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from .base import (
    ADK_AVAILABLE, LlmAgent, CallbackContext,
    types, _get_model_for_agent, _get_default_generate_config,
    ValidationResult
)
from ..config import ADKConfig

logger = logging.getLogger(__name__)


class WorkflowValidatorAgent(LlmAgent):
    """Agent responsible for validating workflows meet user requirements."""
    
    def __init__(self, config: ADKConfig):
        self._config = config
        
        super().__init__(
            name="WorkflowValidator",
            model=_get_model_for_agent(config, "fast"),
            instruction=self._get_instruction(),
            description="Validates workflows meet requirements",
            generate_content_config=_get_default_generate_config(),
            after_model_callback=self._after_model_callback
        )
    
    def _get_instruction(self) -> str:
        return """You are responsible for validating that generated workflows meet the user's requirements.

Your tasks:
1. Get the original user requirements from session state under 'workflow_requirements'
2. Get the compiled workflow from session state under 'compiled_workflow'
3. Get the execution result from session state under 'execution_result' (if available)
4. Analyze whether the workflow meets all requirements
5. Provide a comprehensive validation summary

Validation checks:
1. **Functional Requirements**: Does the workflow do what was requested?
2. **Resource Usage**: Are the right runners, integrations, and tools used?
3. **Best Practices**: Does it follow Kubiya best practices?
4. **Error Handling**: Is there proper error handling?
5. **Security**: Are secrets handled properly?
6. **Performance**: Is the workflow efficient?

First, provide a natural language summary of your validation findings:

## 📊 Workflow Validation Summary

Describe your analysis of how well the workflow meets the requirements. Include:
- Whether all requirements are addressed
- Key features of the generated workflow
- Any concerns or improvements needed
- Overall assessment

If execution results are available, include:
- Execution status and performance
- Any issues encountered
- Output analysis

Then provide the structured result:
<validation_result>
{
  "valid": true/false,
  "meets_requirements": true/false,
  "missing_requirements": [
    "Requirement 1 not met",
    "Requirement 2 partially met"
  ],
  "errors": [],
  "warnings": [
    "Consider adding error handling to step X",
    "Step Y could be optimized"
  ],
  "suggestions": [
    "Add a validation step before processing",
    "Consider using parallel execution for steps X and Y"
  ],
  "summary": "The workflow successfully meets the core requirements but could benefit from improved error handling."
}
</validation_result>

Be thorough but constructive in your feedback. Make the summary engaging and helpful.
"""
    
    async def _after_model_callback(
        self,
        llm_response: Any,
        callback_context: CallbackContext
    ) -> Optional[Any]:
        """Save validation results as artifacts."""
        if not llm_response or not hasattr(llm_response, 'content'):
            return llm_response
        
        try:
            if hasattr(llm_response.content, 'parts'):
                response_text = llm_response.content.parts[0].text
            else:
                response_text = str(llm_response.content)
            
            # Extract validation result
            result_match = re.search(
                r'<validation_result>\s*(.*?)\s*</validation_result>',
                response_text,
                re.DOTALL
            )
            
            if result_match and hasattr(callback_context, 'save_artifact'):
                try:
                    result_data = json.loads(result_match.group(1))
                    
                    # Save validation result as artifact
                    result_artifact = types.Part.from_bytes(
                        data=json.dumps(result_data, indent=2).encode(),
                        mime_type="application/json"
                    )
                    version = await callback_context.save_artifact(
                        filename="validation_result.json",
                        artifact=result_artifact
                    )
                    logger.info(f"Saved validation result as artifact version {version}")
                    
                    # Save to session state
                    if hasattr(callback_context, 'session'):
                        callback_context.session.state["validation_result"] = result_data
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse validation result")
        
        except Exception as e:
            logger.error(f"Error in after_model_callback: {e}")
        
        return llm_response
    
    def validate_workflow_structure(
        self,
        workflow_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform structural validation of a workflow.
        
        Args:
            workflow_json: Compiled workflow JSON
            
        Returns:
            Validation results
        """
        errors = []
        warnings = []
        
        # Check workflow metadata
        if not workflow_json.get("name"):
            errors.append("Workflow must have a name")
        
        if not workflow_json.get("description"):
            warnings.append("Workflow should have a description")
        
        if not workflow_json.get("runner"):
            errors.append("Workflow must specify a runner")
        
        # Check steps
        steps = workflow_json.get("steps", [])
        if not steps:
            errors.append("Workflow must have at least one step")
        
        # Check each step
        for i, step in enumerate(steps):
            step_name = step.get("name", f"Step {i+1}")
            
            # Check executor
            executor = step.get("executor", {})
            if not executor:
                errors.append(f"{step_name}: Missing executor")
                continue
            
            executor_type = executor.get("type")
            if executor_type == "tool":
                # Validate tool configuration
                config = executor.get("config", {})
                tool_def = config.get("tool_def")
                
                if tool_def:
                    if not tool_def.get("type") == "docker":
                        warnings.append(f"{step_name}: Consider using Docker-based tools")
                    
                    if not tool_def.get("content", "").startswith("#!/"):
                        warnings.append(f"{step_name}: Script should start with shebang")
                    
                    if "set -e" not in tool_def.get("content", ""):
                        warnings.append(f"{step_name}: Consider adding 'set -e' for error handling")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def check_requirements_coverage(
        self,
        requirements: str,
        workflow_json: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Check if workflow covers all requirements using LLM analysis.
        
        Args:
            requirements: Original user requirements
            workflow_json: Compiled workflow
            execution_result: Optional execution results
            
        Returns:
            ValidationResult with detailed analysis
        """
        # This method is called by the LLM agent itself during validation
        # The actual analysis happens in the agent's instruction prompt
        # This is just a helper for programmatic access
        
        # The LLM agent will analyze:
        # 1. Whether each requirement is addressed
        # 2. How well it's implemented
        # 3. Any gaps or improvements needed
        # 4. Best practices compliance
        
        # Return a placeholder - actual validation happens via LLM
        return ValidationResult(
            valid=True,
            meets_requirements=True,
            missing_requirements=[],
            errors=[],
            warnings=[],
            suggestions=[]
        )


def create_workflow_validator_agent(config: ADKConfig) -> WorkflowValidatorAgent:
    """Create a workflow validator agent."""
    return WorkflowValidatorAgent(config) 