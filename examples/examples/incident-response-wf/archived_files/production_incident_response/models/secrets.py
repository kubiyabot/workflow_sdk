"""Secrets and credentials models."""

from typing import Dict, Optional
from pydantic import BaseModel, Field, SecretStr
from datetime import datetime


class ToolCredentials(BaseModel):
    """Credentials for a specific tool."""
    
    tool_name: str = Field(..., description="Name of the tool")
    api_key: Optional[SecretStr] = Field(None, description="API key for the tool")
    username: Optional[str] = Field(None, description="Username for authentication")
    password: Optional[SecretStr] = Field(None, description="Password for authentication")
    token: Optional[SecretStr] = Field(None, description="Authentication token")
    server_url: Optional[str] = Field(None, description="Server URL for the tool")
    
    # Additional configuration
    config_data: Dict[str, str] = Field(default_factory=dict, description="Additional configuration data")
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for this tool."""
        env_vars = {}
        
        if self.api_key:
            env_vars[f"{self.tool_name.upper()}_API_KEY"] = self.api_key.get_secret_value()
        
        if self.username:
            env_vars[f"{self.tool_name.upper()}_USERNAME"] = self.username
            
        if self.password:
            env_vars[f"{self.tool_name.upper()}_PASSWORD"] = self.password.get_secret_value()
            
        if self.token:
            env_vars[f"{self.tool_name.upper()}_TOKEN"] = self.token.get_secret_value()
            
        if self.server_url:
            env_vars[f"{self.tool_name.upper()}_SERVER"] = self.server_url
        
        # Add any additional config as environment variables
        for key, value in self.config_data.items():
            env_key = f"{self.tool_name.upper()}_{key.upper()}"
            env_vars[env_key] = value
            
        return env_vars


class SecretsBundle(BaseModel):
    """Bundle of all secrets needed for the incident response workflow."""
    
    # Slack integration
    slack_bot_token: Optional[SecretStr] = Field(None, description="Slack bot token")
    
    # Tool credentials
    datadog: Optional[ToolCredentials] = Field(None, description="Datadog credentials")
    github: Optional[ToolCredentials] = Field(None, description="GitHub credentials")
    argocd: Optional[ToolCredentials] = Field(None, description="ArgoCD credentials")
    observe: Optional[ToolCredentials] = Field(None, description="Observe credentials")
    anthropic: Optional[ToolCredentials] = Field(None, description="Anthropic/Claude credentials")
    
    # Kubernetes access
    kubernetes_token: Optional[SecretStr] = Field(None, description="Kubernetes service account token")
    kubernetes_ca_cert: Optional[str] = Field(None, description="Kubernetes CA certificate")
    
    # Metadata
    secrets_fetched_at: datetime = Field(default_factory=datetime.utcnow, description="When secrets were fetched")
    step_status: str = Field(default="completed", description="Secrets fetching status")
    
    @classmethod
    def create_demo_bundle(cls) -> "SecretsBundle":
        """Create a demo secrets bundle for testing."""
        return cls(
            slack_bot_token=SecretStr("xoxb-demo-token"),
            datadog=ToolCredentials(
                tool_name="datadog",
                api_key=SecretStr("demo_datadog_key"),
                config_data={"app_key": "demo_datadog_app_key"}
            ),
            github=ToolCredentials(
                tool_name="github",
                token=SecretStr("ghp_demo_token")
            ),
            argocd=ToolCredentials(
                tool_name="argocd",
                username="admin",
                password=SecretStr("demo_password"),
                server_url="argocd.company.com"
            ),
            observe=ToolCredentials(
                tool_name="observe",
                api_key=SecretStr("demo_observe_key"),
                config_data={"customer": "demo_customer"}
            ),
            anthropic=ToolCredentials(
                tool_name="anthropic",
                api_key=SecretStr("sk-demo-anthropic-key")
            )
        )
    
    def get_all_env_vars(self) -> Dict[str, str]:
        """Get all environment variables from all tools."""
        env_vars = {}
        
        # Add Slack token
        if self.slack_bot_token:
            env_vars["SLACK_BOT_TOKEN"] = self.slack_bot_token.get_secret_value()
        
        # Add Kubernetes tokens
        if self.kubernetes_token:
            env_vars["KUBERNETES_TOKEN"] = self.kubernetes_token.get_secret_value()
        
        # Add tool credentials
        for tool_creds in [self.datadog, self.github, self.argocd, self.observe, self.anthropic]:
            if tool_creds:
                env_vars.update(tool_creds.get_env_vars())
        
        return env_vars
    
    def to_json_safe(self) -> Dict[str, str]:
        """Convert to JSON-safe format for shell scripts."""
        env_vars = self.get_all_env_vars()
        
        # Add metadata
        env_vars.update({
            "secrets_fetched_at": self.secrets_fetched_at.isoformat(),
            "step_status": self.step_status
        })
        
        return env_vars