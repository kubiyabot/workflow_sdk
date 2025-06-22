"""
Configuration for ADK Provider.

This module provides configuration management for the ADK provider,
including model selection, API keys, and runtime settings.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


class ModelProvider(str, Enum):
    """Supported model providers."""
    TOGETHER_AI = "together_ai"
    GOOGLE_AI = "google_ai"
    VERTEX_AI = "vertex_ai"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: ModelProvider
    model_id: str
    display_name: str
    description: str
    max_tokens: int = 8192
    temperature: float = 0.1
    capabilities: list = field(default_factory=list)


# Default model configurations optimized for different tasks
MODEL_REGISTRY = {
    # Orchestration and coordination models
    "orchestrator": ModelConfig(
        provider=ModelProvider.TOGETHER_AI,
        model_id="together_ai/deepseek-ai/DeepSeek-V3",
        display_name="DeepSeek V3",
        description="Main orchestrator for coordinating workflow generation",
        max_tokens=24000,
        temperature=0.1,
        capabilities=["reasoning", "planning", "coordination"]
    ),
    
    # Context loading and analysis
    "context_loader": ModelConfig(
        provider=ModelProvider.TOGETHER_AI,
        model_id="together_ai/deepseek-ai/DeepSeek-V3",
        display_name="DeepSeek V3",
        description="Loads and analyzes platform context",
        max_tokens=8192,
        temperature=0.0,
        capabilities=["analysis", "data_extraction"]
    ),
    
    # Workflow generation
    "workflow_generator": ModelConfig(
        provider=ModelProvider.TOGETHER_AI,
        model_id="together_ai/deepseek-ai/DeepSeek-V3",
        display_name="DeepSeek V3",
        description="Generates Kubiya workflow code",
        max_tokens=16384,
        temperature=0.1,
        capabilities=["code_generation", "workflow_design"]
    ),
    
    # Compilation and validation
    "compiler": ModelConfig(
        provider=ModelProvider.TOGETHER_AI,
        model_id="together_ai/deepseek-ai/DeepSeek-V3",
        display_name="DeepSeek V3",
        description="Validates and compiles workflows",
        max_tokens=8192,
        temperature=0.0,
        capabilities=["validation", "syntax_checking"]
    ),
    
    # Refinement and error correction
    "refinement": ModelConfig(
        provider=ModelProvider.TOGETHER_AI,
        model_id="together_ai/deepseek-ai/DeepSeek-V3",
        display_name="DeepSeek V3",
        description="Advanced reasoning for workflow refinement",
        max_tokens=16384,
        temperature=0.2,
        capabilities=["reasoning", "error_correction", "optimization"]
    ),
    
    # Fast responses and simple tasks
    "fast": ModelConfig(
        provider=ModelProvider.TOGETHER_AI,
        model_id="together_ai/deepseek-ai/DeepSeek-V3",
        display_name="DeepSeek V3",
        description="Fast model for simple operations",
        max_tokens=4096,
        temperature=0.0,
        capabilities=["quick_response"]
    )
}


@dataclass
class ADKConfig:
    """Main configuration for ADK Provider."""
    
    # API Keys
    together_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    kubiya_api_key: Optional[str] = None
    
    # Kubiya Platform
    kubiya_base_url: str = "https://api.kubiya.ai"
    kubiya_org_name: Optional[str] = None
    default_runner: str = "core-testing-2"
    
    # Model Configuration
    model_provider: ModelProvider = ModelProvider.TOGETHER_AI
    model_overrides: Dict[str, str] = field(default_factory=dict)
    
    # Execution Settings
    max_refinement_iterations: int = 5
    execute_workflows: bool = False  # Whether to execute workflows during generation
    max_loop_iterations: int = 3  # Maximum iterations for validation loop
    enable_streaming: bool = True
    stream_format: str = "sse"  # "sse" or "vercel"
    request_timeout: int = 300
    
    # Feature Flags
    enable_caching: bool = True
    enable_telemetry: bool = False
    enable_debug: bool = False
    
    def __post_init__(self):
        """Load configuration from environment variables."""
        # API Keys
        self.together_api_key = self.together_api_key or os.getenv("TOGETHER_API_KEY")
        self.google_api_key = self.google_api_key or os.getenv("GOOGLE_API_KEY")
        self.kubiya_api_key = self.kubiya_api_key or os.getenv("KUBIYA_API_KEY")
        
        # Kubiya settings
        self.kubiya_base_url = os.getenv("KUBIYA_API_BASE_URL", self.kubiya_base_url)
        self.kubiya_org_name = os.getenv("KUBIYA_ORG_NAME", self.kubiya_org_name)
        self.default_runner = os.getenv("KUBIYA_DEFAULT_RUNNER", self.default_runner)
        
        # Model provider
        provider_env = os.getenv("ADK_MODEL_PROVIDER")
        if provider_env:
            # Check if it's already a valid enum value
            for member in ModelProvider:
                if member.value == provider_env:
                    self.model_provider = member
                    break
        
        # Load model overrides from environment
        for role in MODEL_REGISTRY:
            env_key = f"ADK_MODEL_{role.upper()}"
            if env_value := os.getenv(env_key):
                self.model_overrides[role] = env_value
        
        # Execution settings
        if max_iter := os.getenv("ADK_MAX_REFINEMENT_ITERATIONS"):
            self.max_refinement_iterations = int(max_iter)
        
        if max_loop := os.getenv("ADK_MAX_LOOP_ITERATIONS"):
            self.max_loop_iterations = int(max_loop)
        
        self.execute_workflows = os.getenv("ADK_EXECUTE_WORKFLOWS", "false").lower() == "true"
        self.enable_streaming = os.getenv("ADK_ENABLE_STREAMING", "true").lower() == "true"
        self.stream_format = os.getenv("ADK_STREAM_FORMAT", self.stream_format)
        
        if timeout := os.getenv("ADK_REQUEST_TIMEOUT"):
            self.request_timeout = int(timeout)
        
        # Feature flags
        self.enable_caching = os.getenv("ADK_ENABLE_CACHING", "true").lower() == "true"
        self.enable_telemetry = os.getenv("ADK_ENABLE_TELEMETRY", "false").lower() == "true"
        self.enable_debug = os.getenv("ADK_DEBUG", "false").lower() == "true"
    
    def get_model_config(self, role: str) -> ModelConfig:
        """Get model configuration for a specific role."""
        base_config = MODEL_REGISTRY.get(role, MODEL_REGISTRY["orchestrator"])
        
        # Apply overrides if any
        if role in self.model_overrides:
            base_config.model_id = self.model_overrides[role]
        
        # All models will be wrapped with LiteLLM in the agents
        return base_config
    
    def get_model_for_role(self, role: str) -> str:
        """Get model ID for a specific role."""
        config = self.get_model_config(role)
        return config.model_id
    
    def get_api_key(self) -> str:
        """Get the appropriate API key based on the model provider."""
        if self.model_provider == ModelProvider.TOGETHER_AI:
            if not self.together_api_key:
                raise ValueError("TOGETHER_API_KEY is required for Together AI models")
            return self.together_api_key
        elif self.model_provider in [ModelProvider.GOOGLE_AI, ModelProvider.VERTEX_AI]:
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY is required for Google AI models")
            return self.google_api_key
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")
    
    def setup_environment(self):
        """Set up environment variables for the selected provider."""
        # Always import and configure LiteLLM as all models will be wrapped with it
        try:
            import litellm
            litellm.set_verbose = self.enable_debug
        except ImportError:
            pass
        
        if self.model_provider == ModelProvider.TOGETHER_AI:
            # Set up for Together AI via LiteLLM
            os.environ["TOGETHER_API_KEY"] = self.together_api_key or ""
            # LiteLLM also uses TOGETHERAI_API_KEY
            os.environ["TOGETHERAI_API_KEY"] = self.together_api_key or ""
        elif self.model_provider == ModelProvider.GOOGLE_AI:
            os.environ["GOOGLE_API_KEY"] = self.google_api_key or ""
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
        elif self.model_provider == ModelProvider.VERTEX_AI:
            os.environ["GOOGLE_API_KEY"] = self.google_api_key or ""
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
            # Vertex AI also needs project and location
            if project := os.getenv("GOOGLE_CLOUD_PROJECT"):
                os.environ["GOOGLE_CLOUD_PROJECT"] = project
            if location := os.getenv("GOOGLE_CLOUD_LOCATION"):
                os.environ["GOOGLE_CLOUD_LOCATION"] = location
    
    def validate(self) -> Dict[str, Any]:
        """Validate the configuration."""
        errors = []
        warnings = []
        
        # Check API keys
        try:
            self.get_api_key()
        except ValueError as e:
            errors.append(str(e))
        
        if not self.kubiya_api_key:
            warnings.append("KUBIYA_API_KEY not set - some platform features may be limited")
        
        # Check model configurations
        for role, override in self.model_overrides.items():
            if role not in MODEL_REGISTRY:
                warnings.append(f"Unknown model role '{role}' in overrides")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model_provider": self.model_provider.value if isinstance(self.model_provider, ModelProvider) else self.model_provider,
            "models": {
                role: self.get_model_config(role).model_id
                for role in MODEL_REGISTRY
            },
            "kubiya": {
                "base_url": self.kubiya_base_url,
                "org_name": self.kubiya_org_name,
                "default_runner": self.default_runner
            },
            "execution": {
                "max_refinement_iterations": self.max_refinement_iterations,
                "execute_workflows": self.execute_workflows,
                "max_loop_iterations": self.max_loop_iterations,
                "enable_streaming": self.enable_streaming,
                "stream_format": self.stream_format,
                "request_timeout": self.request_timeout
            },
            "features": {
                "caching": self.enable_caching,
                "telemetry": self.enable_telemetry,
                "debug": self.enable_debug
            }
        }


# Default configuration instance
default_config = ADKConfig()


def get_config() -> ADKConfig:
    """Get the current configuration."""
    return default_config


def create_config(**kwargs) -> ADKConfig:
    """Create a new configuration with overrides."""
    config = ADKConfig(**kwargs)
    config.validate()
    return config 