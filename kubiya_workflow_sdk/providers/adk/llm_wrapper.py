"""
LiteLLM wrapper for ADK to use Together AI models.

This module provides a custom LLM implementation that routes ADK requests
through LiteLLM to use Together AI models.
"""

import os
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
import litellm
from litellm import acompletion

logger = logging.getLogger(__name__)

# Configure LiteLLM for Together AI
litellm.set_verbose = True

try:
    from google.genai import types
    from google.adk.models.base_llm import BaseLlm
except ImportError:
    # Mock for when ADK is not installed
    class BaseLlm:
        pass
    class types:
        class GenerateContentResponse:
            pass
        class Candidate:
            pass
        class Content:
            pass
        class Part:
            pass


class LLMResponse:
    """Custom response class that mimics ADK's expected response format."""
    
    def __init__(self, candidates, partial=False):
        self.candidates = candidates
        self.partial = partial
        # Add content property for compatibility
        if candidates and candidates[0].content:
            self.content = candidates[0].content
        else:
            self.content = None
    
    def model_dump(self, exclude_none=False):
        """Return a dictionary representation of the response."""
        # ADK expects specific fields for Event
        data = {}
        
        # If we have content, use it directly
        if self.content:
            data["content"] = self.content
        
        # Add other expected Event fields
        data["partial"] = self.partial
        
        # Don't include candidates directly as it's not an Event field
        return data


from pydantic import Field, PrivateAttr
from typing import Optional


class TogetherAILLM(BaseLlm):
    """Custom LLM implementation that routes through LiteLLM to Together AI."""
    
    # Additional fields for our implementation
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=8192)
    api_key: Optional[str] = Field(default=None)
    
    # Private attribute to store generate_content_config
    _generate_content_config: Optional[Any] = PrivateAttr(default=None)
    
    def __init__(self, model: str, **kwargs):
        """Initialize Together AI LLM wrapper.
        
        Args:
            model: Model ID (e.g., "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo")
            **kwargs: Additional configuration including generate_content_config
        """
        # For LiteLLM, ensure we have the together_ai/ prefix
        if not model.startswith("together_ai/") and not model.startswith("together/"):
            model = f"together_ai/{model}"
        
        # Get or create generate_content_config
        generate_content_config = kwargs.get("generate_content_config", None)
        if generate_content_config is None:
            # Create a default config with required fields
            try:
                from google.genai.types import GenerateContentConfig
                generate_content_config = GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=8192,
                    response_modalities=["TEXT"]  # This is required by ADK
                )
            except ImportError:
                # If ADK is not available, just set to None
                generate_content_config = None
        
        # Extract settings from config if available
        temperature = 0.1
        max_tokens = 8192
        if generate_content_config:
            temperature = getattr(generate_content_config, "temperature", 0.1)
            max_tokens = getattr(generate_content_config, "max_output_tokens", 8192)
        else:
            temperature = kwargs.get("temperature", 0.1)
            max_tokens = kwargs.get("max_tokens", 8192)
        
        api_key = os.getenv("TOGETHER_API_KEY")
        
        if not api_key:
            raise ValueError("TOGETHER_API_KEY environment variable not set")
        
        # Set the API key for LiteLLM
        os.environ["TOGETHERAI_API_KEY"] = api_key
        
        # Initialize parent Pydantic model with all fields
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
        )
        
        # Set generate_content_config after initialization
        self._generate_content_config = generate_content_config
        
        logger.info(f"Initialized TogetherAILLM with model: {model}")
    
    @property
    def generate_content_config(self):
        """Ensure generate_content_config is never None for ADK."""
        if self._generate_content_config is None:
            # Create a default config on demand
            try:
                from google.genai.types import GenerateContentConfig
                self._generate_content_config = GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    response_modalities=["TEXT"]
                )
            except ImportError:
                pass
        return self._generate_content_config
    
    @generate_content_config.setter
    def generate_content_config(self, value):
        self._generate_content_config = value
    
    def _convert_adk_to_litellm(self, request: Any) -> Dict[str, Any]:
        """Convert ADK request format to LiteLLM format."""
        messages = []
        
        # Extract messages from ADK request
        if hasattr(request, 'contents'):
            for content in request.contents:
                role = content.role if hasattr(content, 'role') else 'user'
                
                # Map ADK roles to LiteLLM roles
                if role == 'model':
                    role = 'assistant'
                
                # Extract text from parts
                text_parts = []
                if hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                
                if text_parts:
                    messages.append({
                        "role": role,
                        "content": " ".join(text_parts)
                    })
        
        # Extract other parameters
        config = {
            "model": self.model,  # Use model directly for LiteLLM
            "messages": messages,
            "temperature": getattr(request, 'temperature', self.temperature),
            "max_tokens": getattr(request, 'max_output_tokens', self.max_tokens),
        }
        
        # Add system message if provided
        if hasattr(request, 'system_instruction') and request.system_instruction:
            config["messages"].insert(0, {
                "role": "system",
                "content": request.system_instruction.parts[0].text if hasattr(request.system_instruction, 'parts') else str(request.system_instruction)
            })
        
        return config
    
    def _convert_litellm_to_adk(self, response: Any) -> Any:
        """Convert LiteLLM response to ADK format."""
        # Create ADK response structure
        candidates = []
        
        if hasattr(response, 'choices'):
            for choice in response.choices:
                part = types.Part()
                part.text = choice.message.content
                
                content = types.Content()
                content.role = "model"
                content.parts = [part]
                
                candidate = types.Candidate()
                candidate.content = content
                candidate.finish_reason = "STOP"
                
                candidates.append(candidate)
        
        # Create response object
        class Response:
            def __init__(self, candidates):
                self.candidates = candidates
        
        return Response(candidates)
    
    async def generate_content_async(
        self,
        request: Any,
        **kwargs
    ) -> AsyncIterator[Any]:
        """Generate content asynchronously using Together AI via LiteLLM.
        
        Args:
            request: ADK request object
            **kwargs: Additional parameters
            
        Yields:
            ADK response objects
        """
        try:
            # Convert request
            litellm_request = self._convert_adk_to_litellm(request)
            
            logger.debug(f"Sending request to Together AI: {litellm_request['model']}")
            
            # Make async streaming call
            response = await acompletion(
                **litellm_request,
                stream=True,
                api_key=self.api_key
            )
            
            # Stream responses
            async for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    for choice in chunk.choices:
                        if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                            content = choice.delta.content
                            if content:
                                # Create partial response
                                part = types.Part()
                                part.text = content
                                
                                content_obj = types.Content()
                                content_obj.role = "model"
                                content_obj.parts = [part]
                                
                                candidate = types.Candidate()
                                candidate.content = content_obj
                                candidate.finish_reason = None
                                
                                candidates = [candidate]
                                
                                # Create a proper response object
                                response = LLMResponse(candidates, partial=True)
                                
                                yield response
            
            # Send final response
            final_part = types.Part()
            final_part.text = ""
            
            final_content = types.Content()
            final_content.role = "model"
            final_content.parts = [final_part]
            
            final_candidate = types.Candidate()
            final_candidate.content = final_content
            final_candidate.finish_reason = "STOP"
            
            final_response = LLMResponse([final_candidate], partial=False)
            
            yield final_response
            
        except Exception as e:
            logger.error(f"Error calling Together AI: {e}")
            raise


def create_together_ai_llm(model_id: str, **kwargs) -> TogetherAILLM:
    """Factory function to create Together AI LLM instances.
    
    Args:
        model_id: Model identifier
        **kwargs: Additional configuration
        
    Returns:
        TogetherAILLM instance
    """
    return TogetherAILLM(model_id, **kwargs) 