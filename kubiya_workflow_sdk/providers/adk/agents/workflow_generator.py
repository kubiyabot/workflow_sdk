"""Workflow generator agent for creating Kubiya workflows."""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from .base import (
    ADK_AVAILABLE, LlmAgent, LlmRequest, LlmResponse, CallbackContext, 
    types, _get_model_for_agent, _get_default_generate_config,
    get_docker_registry_context, get_dsl_context, FunctionTool
)
from ..config import ADKConfig
from ..tools import KubiyaContextTools

logger = logging.getLogger(__name__)


class WorkflowGeneratorAgent(LlmAgent):
    """Agent for generating Kubiya workflows using the SDK DSL."""
    
    def __init__(self, config: ADKConfig, context_tools: KubiyaContextTools):
        self._config = config
        self._context_tools = context_tools
        
        # Create tools from context tools
        tools = []
        if ADK_AVAILABLE and context_tools:
            tools = [
                FunctionTool(self._context_tools.get_runners),
                FunctionTool(self._context_tools.get_integrations),
                FunctionTool(self._context_tools.get_secrets_metadata)
            ]
        
        super().__init__(
            name="WorkflowGenerator",
            model=_get_model_for_agent(config, "workflow_generator"),
            instruction=self._get_instruction(),
            description="Generates Kubiya workflows using the SDK DSL",
            tools=tools,
            generate_content_config=_get_default_generate_config(),
            before_model_callback=self._before_model_callback,
            after_model_callback=self._after_model_callback
        )
    
    def _get_instruction(self) -> str:
        return """You are an expert workflow generator for the Kubiya platform. You use the Kubiya SDK Python API to create production-ready workflows.

CRITICAL: Generate workflows using Python code with the Kubiya SDK, NOT YAML!

Your task is to:
1. Analyze the user's requirements
2. Use the platform context ONLY if available (runners, integrations, secrets)
3. Generate a complete Python script that creates the workflow using the SDK
4. Include all necessary imports and proper error handling
5. Make the workflow production-ready with logging and validation

Platform Context Usage:
- If runners are available, select the most appropriate one based on user requirements
- If no specific runner is mentioned, use "kubiya-hosted" as the default
- If integrations are available, leverage them. Otherwise, use basic bash/python
- If secrets are available, reference them properly. Otherwise, document what secrets would be needed
- DO NOT assume any context variables exist unless explicitly provided

Runner Selection Logic:
1. If user mentions specific requirements (e.g., "use kubernetes runner"), match them to available runners
2. If multiple runners match, prefer the one with the most relevant capabilities
3. Default to "kubiya-hosted" if no specific requirements or no runners match

Output your workflow generation code within <workflow_code> tags.

Example structure:
```python
from kubiya_workflow_sdk.dsl import Workflow, Step, parallel, sequence
from kubiya_workflow_sdk.dsl.executors import BashExecutor, PythonExecutor

# Create workflow
workflow = Workflow(
    name="example_workflow",
    description="Description of what the workflow does",
    runner="kubiya-hosted"  # Default runner, or select from available runners based on requirements
)

# Add workflow steps
step1 = Step(
    name="step_name",
    executor=BashExecutor(script="echo 'Hello World'")
)

workflow.add_step(step1)

# Export as JSON
workflow_dict = workflow.to_dict()
```

IMPORTANT:
- Always use the SDK's Python API, not raw dictionaries
- Include proper error handling
- Make workflows idempotent where possible
- Use appropriate executors (BashExecutor, PythonExecutor, etc.)
- DO NOT reference undefined variables like 'bucket_name' unless they are in the context
- Use descriptive names and add helpful descriptions

Runner Selection Guidelines:
- Check if specific runner is mentioned in requirements (e.g., "kubernetes runner", "docker runner")
- Match runner capabilities to workflow needs:
  - kubernetes: For k8s operations, helm, kubectl
  - docker: For container operations
  - python: For Python-heavy workflows
  - bash: For shell script operations
- If no specific match, use "kubiya-hosted" as the default runner
- Never use "auto" - always select a specific runner
"""
    
    async def _before_model_callback(
        self,
        llm_request: LlmRequest,
        callback_context: CallbackContext
    ) -> Optional[LlmResponse]:
        """Log and potentially modify LLM requests."""
        logger.debug(f"WorkflowGenerator sending request to model")
        
        # Save the request as an artifact for debugging
        if hasattr(callback_context, 'save_artifact'):
            try:
                request_artifact = types.Part.from_bytes(
                    data=json.dumps({
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent": "WorkflowGenerator",
                        "request_type": "model_call",
                        "content": str(llm_request.contents[-1].parts[0].text if llm_request.contents else "")
                    }).encode(),
                    mime_type="application/json"
                )
                await callback_context.save_artifact(
                    filename=f"workflow_gen_request_{uuid.uuid4().hex[:8]}.json",
                    artifact=request_artifact
                )
            except Exception as e:
                logger.warning(f"Failed to save request artifact: {e}")
        
        return None  # Continue with normal execution
    
    async def _after_model_callback(
        self,
        llm_response: LlmResponse,
        callback_context: CallbackContext
    ) -> Optional[LlmResponse]:
        """Process and potentially save workflow artifacts."""
        if not llm_response or not llm_response.content:
            return llm_response
        
        try:
            # Safely extract response text
            if hasattr(llm_response.content, 'parts') and llm_response.content.parts:
                response_text = str(llm_response.content.parts[0].text if hasattr(llm_response.content.parts[0], 'text') else llm_response.content.parts[0])
            else:
                response_text = str(llm_response.content)
            
            # Extract workflow code
            code_match = re.search(
                r'<workflow_code>\s*(.*?)\s*</workflow_code>',
                response_text,
                re.DOTALL
            )
            
            # Save as artifacts if found
            if hasattr(callback_context, 'save_artifact'):
                if code_match:
                    code_artifact = types.Part.from_bytes(
                        data=code_match.group(1).encode(),
                        mime_type="text/x-python"
                    )
                    version = await callback_context.save_artifact(
                        filename="generated_workflow.py",
                        artifact=code_artifact
                    )
                    logger.info(f"Saved workflow code as artifact version {version}")
                    
                    # Also save to session state for compiler
                    if hasattr(callback_context, 'session'):
                        callback_context.session.state["workflow_code"] = code_match.group(1)
        
        except Exception as e:
            logger.error(f"Error in after_model_callback: {e}")
        
        return llm_response


def create_workflow_generator_agent(
    config: ADKConfig,
    context_tools: KubiyaContextTools
) -> WorkflowGeneratorAgent:
    """Create a workflow generator agent."""
    return WorkflowGeneratorAgent(config, context_tools) 