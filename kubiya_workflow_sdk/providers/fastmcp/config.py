"""
FastMCP Provider Configuration.

Defines configuration options for the FastMCP provider.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import os


@dataclass
class FastMCPConfig:
    """Configuration for FastMCP provider."""
    
    # MCP Server Configuration
    mcp_servers: List[Dict[str, Any]] = field(default_factory=list)
    default_server_url: Optional[str] = None
    
    # Protocol Configuration
    protocol_version: str = "2024-11-05"
    client_info: Dict[str, str] = field(default_factory=lambda: {
        "name": "kubiya-workflow-sdk",
        "version": "1.0.0"
    })
    
    # Connection Settings
    connection_timeout: int = 30
    request_timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Workflow Generation Settings
    enable_streaming: bool = True
    stream_format: str = "vercel"  # "vercel" or "sse"
    max_loop_iterations: int = 5
    enable_tool_calls: bool = True
    enable_prompts: bool = True
    enable_resources: bool = True
    
    # Model Configuration
    model_provider: str = "anthropic"  # Default LLM provider for generation
    model_name: str = "claude-3-5-sonnet-latest"
    model_temperature: float = 0.7
    max_tokens: int = 4000
    
    # Tool Execution Settings
    execute_tools: bool = False  # Whether to actually execute MCP tools
    tool_execution_timeout: int = 30
    sandbox_execution: bool = True
    
    # Caching Settings
    enable_tool_cache: bool = True
    cache_ttl: int = 300  # 5 minutes
    enable_response_cache: bool = True
    
    # Security Settings
    allowed_tool_patterns: List[str] = field(default_factory=list)
    blocked_tool_patterns: List[str] = field(default_factory=list)
    require_tool_confirmation: bool = True
    
    # Logging and Debug
    enable_debug_logging: bool = False
    log_mcp_messages: bool = False
    log_tool_calls: bool = True
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Set default server if none provided
        if not self.mcp_servers and not self.default_server_url:
            # Look for environment variable
            default_url = os.getenv("FASTMCP_DEFAULT_SERVER_URL")
            if default_url:
                self.default_server_url = default_url
        
        # Auto-configure from environment
        if os.getenv("FASTMCP_ENABLE_TOOL_EXECUTION") == "true":
            self.execute_tools = True
            
        if os.getenv("FASTMCP_DEBUG") == "true":
            self.enable_debug_logging = True
            self.log_mcp_messages = True
            
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration settings."""
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
            
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
            
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
            
        if self.max_loop_iterations <= 0:
            raise ValueError("max_loop_iterations must be positive")
            
        if self.stream_format not in ["vercel", "sse"]:
            raise ValueError("stream_format must be 'vercel' or 'sse'")
    
    def add_mcp_server(
        self,
        name: str,
        url: str,
        description: str = "",
        auth: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """Add an MCP server to the configuration."""
        server_config = {
            "name": name,
            "url": url,
            "description": description,
            "auth": auth or {},
            **kwargs
        }
        self.mcp_servers.append(server_config)
    
    def get_server_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get MCP server configuration by name."""
        for server in self.mcp_servers:
            if server.get("name") == name:
                return server
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "mcp_servers": self.mcp_servers,
            "default_server_url": self.default_server_url,
            "protocol_version": self.protocol_version,
            "client_info": self.client_info,
            "connection_timeout": self.connection_timeout,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "enable_streaming": self.enable_streaming,
            "stream_format": self.stream_format,
            "max_loop_iterations": self.max_loop_iterations,
            "enable_tool_calls": self.enable_tool_calls,
            "enable_prompts": self.enable_prompts,
            "enable_resources": self.enable_resources,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "model_temperature": self.model_temperature,
            "max_tokens": self.max_tokens,
            "execute_tools": self.execute_tools,
            "tool_execution_timeout": self.tool_execution_timeout,
            "sandbox_execution": self.sandbox_execution,
            "enable_tool_cache": self.enable_tool_cache,
            "cache_ttl": self.cache_ttl,
            "enable_response_cache": self.enable_response_cache,
            "allowed_tool_patterns": self.allowed_tool_patterns,
            "blocked_tool_patterns": self.blocked_tool_patterns,
            "require_tool_confirmation": self.require_tool_confirmation,
            "enable_debug_logging": self.enable_debug_logging,
            "log_mcp_messages": self.log_mcp_messages,
            "log_tool_calls": self.log_tool_calls
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FastMCPConfig":
        """Create configuration from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "FastMCPConfig":
        """Create configuration from environment variables."""
        config = cls()
        
        # Override with environment variables
        if os.getenv("FASTMCP_PROTOCOL_VERSION"):
            config.protocol_version = os.getenv("FASTMCP_PROTOCOL_VERSION")
            
        if os.getenv("FASTMCP_CONNECTION_TIMEOUT"):
            config.connection_timeout = int(os.getenv("FASTMCP_CONNECTION_TIMEOUT"))
            
        if os.getenv("FASTMCP_REQUEST_TIMEOUT"):
            config.request_timeout = int(os.getenv("FASTMCP_REQUEST_TIMEOUT"))
            
        if os.getenv("FASTMCP_MAX_RETRIES"):
            config.max_retries = int(os.getenv("FASTMCP_MAX_RETRIES"))
            
        if os.getenv("FASTMCP_STREAM_FORMAT"):
            config.stream_format = os.getenv("FASTMCP_STREAM_FORMAT")
            
        if os.getenv("FASTMCP_MODEL_PROVIDER"):
            config.model_provider = os.getenv("FASTMCP_MODEL_PROVIDER")
            
        if os.getenv("FASTMCP_MODEL_NAME"):
            config.model_name = os.getenv("FASTMCP_MODEL_NAME")
            
        if os.getenv("FASTMCP_MODEL_TEMPERATURE"):
            config.model_temperature = float(os.getenv("FASTMCP_MODEL_TEMPERATURE"))
            
        return config 