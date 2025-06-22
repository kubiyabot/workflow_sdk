"""Context loader agent for loading Kubiya platform resources."""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from .base import (
    ADK_AVAILABLE, LlmAgent, CallbackContext, InvocationContext,
    Event, types, _get_model_for_agent, _get_default_generate_config,
    AsyncIterator, FunctionTool
)
from ..config import ADKConfig
from ..tools import KubiyaContextTools

logger = logging.getLogger(__name__)


class ContextLoaderAgent(LlmAgent):
    """Agent responsible for loading platform context and resources."""
    
    def __init__(self, config: ADKConfig, context_tools: KubiyaContextTools):
        self._config = config
        self._context_tools = context_tools
        
        # Create tools from context tools
        tools = []
        if ADK_AVAILABLE:
            tools = [
                FunctionTool(self._context_tools.get_runners),
                FunctionTool(self._context_tools.get_integrations),
                FunctionTool(self._context_tools.get_secrets_metadata),
                FunctionTool(self._context_tools.get_org_info)
            ]
        
        super().__init__(
            name="ContextLoader",
            model=_get_model_for_agent(config, "context_loader"),
            instruction=self._get_instruction(),
            description="Loads Kubiya platform context and resources",
            tools=tools,
            generate_content_config=_get_default_generate_config(),
            before_tool_callback=self._before_tool_callback,
            after_model_callback=self._after_model_callback
        )
    
    def _get_instruction(self) -> str:
        return """You are responsible for loading context from the Kubiya platform to help with workflow generation.

Your role is to:
1. Analyze the user's requirements to determine what context is needed
2. Use the available tools to load relevant resources:
   - Runners: For workflow execution environments
   - Integrations: For available platform capabilities
   - Secrets metadata: To know what secrets are available (names only)
   - Organization info: For org-specific configuration

3. Identify any missing resources or capabilities
4. Summarize the loaded context in a structured format

Use the tools efficiently - only load what's relevant to the user's request.

Output format:
<context_summary>
{
  "available_runners": ["runner1", "runner2"],
  "relevant_integrations": {
    "kubernetes": {"enabled": true, "clusters": ["prod", "dev"]},
    "aws": {"enabled": true, "regions": ["us-east-1"]}
  },
  "available_secrets": ["API_KEY", "DB_PASSWORD"],
  "organization": {
    "name": "org_name",
    "settings": {}
  },
  "missing_resources": [],
  "recommendations": []
}
</context_summary>
"""
    
    def _before_tool_callback(
        self,
        tool_name: str,
        args: Dict[str, Any],
        callback_context: CallbackContext
    ) -> Optional[Dict[str, Any]]:
        """Log tool usage."""
        logger.debug(f"ContextLoader calling tool: {tool_name} with args: {args}")
        return None  # Allow tool execution
    
    async def _after_model_callback(
        self,
        llm_response: Any,
        callback_context: CallbackContext
    ) -> Optional[Any]:
        """Extract and save context summary."""
        if not llm_response or not hasattr(llm_response, 'content'):
            return llm_response
        
        try:
            if hasattr(llm_response.content, 'parts'):
                response_text = llm_response.content.parts[0].text
            else:
                response_text = str(llm_response.content)
            
            # Extract context summary
            summary_match = re.search(
                r'<context_summary>\s*(.*?)\s*</context_summary>',
                response_text,
                re.DOTALL
            )
            
            if summary_match and hasattr(callback_context, 'save_artifact'):
                try:
                    context_data = json.loads(summary_match.group(1))
                    
                    # Save context summary as artifact
                    context_artifact = types.Part.from_bytes(
                        data=json.dumps(context_data, indent=2).encode(),
                        mime_type="application/json"
                    )
                    version = await callback_context.save_artifact(
                        filename="platform_context.json",
                        artifact=context_artifact
                    )
                    logger.info(f"Saved platform context as artifact version {version}")
                    
                    # Also save to session state for other agents
                    if hasattr(callback_context, 'session'):
                        callback_context.session.state["platform_context"] = context_data
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse context summary")
        
        except Exception as e:
            logger.error(f"Error in after_model_callback: {e}")
        
        return llm_response
    
    async def load_context(self, requirements: str, session: Any) -> Dict[str, Any]:
        """
        Load context based on requirements.
        
        Args:
            requirements: User requirements string
            session: ADK session
            
        Returns:
            Loaded context dictionary
        """
        # Create a mock invocation context for running the agent
        class MockContext:
            def __init__(self, session, requirements, agent=None):
                self.session = session
                self.invocation_id = "context_load"
                self.user_content = types.Content(
                    role="user",
                    parts=[types.Part(text=requirements)]
                )
                self.end_invocation = False  # ADK expects this attribute
                self.agent = agent or self  # ADK expects agent reference
                self.branch = None  # Optional ADK attribute
                self.artifact_service = None  # Optional ADK attribute
                self.session_service = None  # Optional ADK attribute
                self.memory_service = None  # Optional ADK attribute
                self.credential_service = None  # Optional ADK attribute
                self.live_request_queue = None  # Optional ADK attribute
                self.active_streaming_tools = None  # Optional ADK attribute
                self.transcription_cache = None  # Optional ADK attribute
                
                # Create a mock run_config with required attributes
                class MockRunConfig:
                    def __init__(self):
                        self.response_modalities = []  # ADK expects this
                        self.enable_multi_step_tool_use = True
                        self.enable_grounding = False
                        self.force_json_output = False
                        self.max_tool_rounds = 10
                        self.speech_config = None  # ADK expects this
                        self.system_instruction = None
                        self.config_dict = {}
                        self.output_audio_transcription = False  # ADK expects this
                        self.input_audio_transcription = False  # ADK expects this
                        self.enable_code_execution = False
                        self.model = None
                        self.realtime_input_config = None  # ADK expects this
                    
                    def __getattr__(self, name):
                        """Handle any missing attributes by returning None."""
                        return None
                        
                self.run_config = MockRunConfig()
            
            def model_copy(self, **kwargs):
                """Mock model_copy method that ADK expects."""
                new_ctx = MockContext(self.session, "", agent=kwargs.get('agent', self.agent))
                for key, value in kwargs.items():
                    setattr(new_ctx, key, value)
                return new_ctx
            
            def increment_llm_call_count(self):
                """Mock increment_llm_call_count method that ADK expects."""
                pass
            
            def __getattr__(self, name):
                """Handle any missing attributes by returning None or a no-op function."""
                if name.startswith('increment_') or name.startswith('track_') or name.startswith('log_'):
                    return lambda *args, **kwargs: None
                return None
        
        ctx = MockContext(session, requirements, agent=self)
        
        # Run the agent to load context
        events = []
        async for event in self.run_async(ctx):
            events.append(event)
        
        # Extract context from session state
        return session.state.get("platform_context", {})


def create_context_loader_agent(
    config: ADKConfig,
    context_tools: KubiyaContextTools
) -> ContextLoaderAgent:
    """Create a context loader agent."""
    return ContextLoaderAgent(config, context_tools) 