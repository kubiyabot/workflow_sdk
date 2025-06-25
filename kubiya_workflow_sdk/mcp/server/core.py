"""Core MCP Server implementation with authentication and context management."""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

from kubiya_workflow_sdk.client import KubiyaClient
from .context import WorkflowContext, IntegrationContext, SecretsContext
from .tools import register_tools
from .prompts import register_prompts
from .resources import register_resources

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """MCP Server configuration."""
    name: str = "Kubiya Workflow MCP"
    description: str = "Smart MCP server for Kubiya workflow creation and execution"
    base_url: str = "https://api.kubiya.ai"
    enable_auth: bool = True
    default_runner: str = "kubiya-hosted"
    cache_ttl: int = 300  # 5 minutes


class KubiyaMCPServer:
    """Production-ready MCP Server for Kubiya workflows."""
    
    def __init__(self, config: Optional[ServerConfig] = None):
        """Initialize the MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config or ServerConfig()
        self.mcp = FastMCP(name=self.config.name)
        
        # Context managers
        self.workflow_context = WorkflowContext()
        self.integration_context = IntegrationContext()
        self.secrets_context = SecretsContext()
        
        # Client cache for authenticated requests
        self._client_cache: Dict[str, tuple[KubiyaClient, float]] = {}
        
        # Initialize server components
        self._setup_server()
        
    def _setup_server(self):
        """Set up all server components."""
        # Register tools with context
        register_tools(self.mcp, self)
        
        # Register prompts for better DSL generation
        register_prompts(self.mcp, self)
        
        # Register resources (examples, templates)
        register_resources(self.mcp, self)
        
        logger.info(f"Initialized {self.config.name} with auth={'enabled' if self.config.enable_auth else 'disabled'}")
    
    def get_client(self, api_key: Optional[str] = None) -> KubiyaClient:
        """Get or create a Kubiya client with proper authentication.
        
        This method handles authentication in multiple ways:
        1. Explicit API key parameter (highest priority)
        2. HTTP Authorization header (for web deployments)
        3. Environment variable KUBIYA_API_KEY (fallback)
        
        Args:
            api_key: Optional explicit API key
            
        Returns:
            Authenticated KubiyaClient instance
            
        Raises:
            ValueError: If no API key is available
        """
        # Priority 1: Explicit API key
        if api_key:
            return self._create_client(api_key)
        
        # Priority 2: HTTP Authorization header (if in web context)
        if self.config.enable_auth:
            try:
                headers = get_http_headers()
                auth_header = headers.get("authorization", "")
                
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    return self._create_client(token)
                elif auth_header.startswith("UserKey "):
                    token = auth_header[8:]  # Remove "UserKey " prefix
                    return self._create_client(token)
            except:
                # Not in HTTP context, continue to next method
                pass
        
        # Priority 3: Environment variable
        env_key = os.getenv("KUBIYA_API_KEY")
        if env_key:
            return self._create_client(env_key)
        
        # No authentication available
        raise ValueError(
            "No Kubiya API key available. Please provide one via:\n"
            "1. The api_key parameter\n"
            "2. HTTP Authorization header (Bearer token)\n"
            "3. KUBIYA_API_KEY environment variable"
        )
    
    def _create_client(self, api_key: str) -> KubiyaClient:
        """Create or retrieve cached client."""
        import time
        
        # Check cache
        if api_key in self._client_cache:
            client, created_at = self._client_cache[api_key]
            if time.time() - created_at < self.config.cache_ttl:
                return client
        
        # Create new client
        client = KubiyaClient(
            api_key=api_key,
            base_url=self.config.base_url,
            runner=self.config.default_runner
        )
        
        # Cache it
        self._client_cache[api_key] = (client, time.time())
        
        # Clean old entries
        self._cleanup_cache()
        
        return client
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        import time
        current_time = time.time()
        
        expired_keys = [
            key for key, (_, created_at) in self._client_cache.items()
            if current_time - created_at >= self.config.cache_ttl
        ]
        
        for key in expired_keys:
            del self._client_cache[key]
    
    async def refresh_context(self, api_key: Optional[str] = None):
        """Refresh context data (runners, integrations, secrets) with health checks."""
        try:
            client = self.get_client(api_key)
            
            # Update runners with health information
            # Check if we should include health checks based on environment
            check_health = os.getenv("KUBIYA_CHECK_RUNNER_HEALTH", "true").lower() == "true"
            
            if check_health:
                # Get runners with health status and component filtering
                runners = client.get_runners_with_health(
                    check_health=True,
                    required_components=self.workflow_context.component_requirements
                )
                logger.info(
                    f"Retrieved {len(runners)} runners with health checks. "
                    f"Healthy: {sum(1 for r in runners if r.get('is_healthy'))}"
                )
            else:
                # Get basic runner info without health checks
                runners = client.get_runners()
                # Convert to expected format
                runners = [
                    {
                        **runner,
                        "health_status": "unknown",
                        "is_healthy": True,  # Assume healthy if not checking
                        "meets_requirements": True,
                        "component_versions": {}
                    }
                    for runner in runners
                ]
            
            self.workflow_context.update_runners(runners)
            
            # Update integrations
            integrations = client.get_integrations()
            self.integration_context.update_integrations(integrations)
            
            # Update secrets
            secrets = client.list_secrets()
            self.secrets_context.update_secrets(secrets)
            
            # Log summary
            available_runners = self.workflow_context.get_available_runners()
            logger.info(
                f"Context refreshed: {len(available_runners)} available runners "
                f"(out of {len(runners)} total), "
                f"{len(integrations)} integrations, {len(secrets)} secrets"
            )
            
            # Log component requirements if any
            if self.workflow_context.component_requirements:
                logger.info(f"Component requirements: {self.workflow_context.component_requirements}")
            
        except Exception as e:
            logger.warning(f"Failed to refresh context: {e}")
            # Set empty context on failure
            self.workflow_context.update_runners([])
            self.integration_context.update_integrations([])
            self.secrets_context.update_secrets([])
    
    def run(self, transport: str = "stdio"):
        """Run the MCP server.
        
        Args:
            transport: Transport type (stdio, http, sse)
        """
        # For HTTP transports, we'll get auth from headers
        if transport in ["http", "sse"]:
            logger.info(f"Running in {transport} mode with header-based authentication")
        
        # Run the FastMCP server
        self.mcp.run(transport=transport)


def create_server(
    name: Optional[str] = None,
    base_url: Optional[str] = None,
    enable_auth: bool = True,
    **kwargs
) -> KubiyaMCPServer:
    """Create a configured MCP server instance.
    
    Args:
        name: Server name
        base_url: Kubiya API base URL
        enable_auth: Enable authentication via headers
        **kwargs: Additional config options
        
    Returns:
        Configured server instance
    """
    config = ServerConfig(
        name=name or ServerConfig.name,
        base_url=base_url or ServerConfig.base_url,
        enable_auth=enable_auth,
        **kwargs
    )
    
    return KubiyaMCPServer(config) 