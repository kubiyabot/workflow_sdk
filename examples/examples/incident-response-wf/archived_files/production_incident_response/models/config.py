"""Configuration models for the incident response workflow."""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class ToolType(str, Enum):
    """Supported tool types for Claude Code investigation."""
    CLI = "cli"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    API = "api"
    FILE_SYSTEM = "filesystem"


class VolumeMount(BaseModel):
    """Docker volume mount configuration."""
    host_path: str = Field(..., description="Host path to mount")
    container_path: str = Field(..., description="Container path for mount")
    readonly: bool = Field(default=True, description="Whether mount is read-only")


class EnvironmentVariable(BaseModel):
    """Environment variable configuration."""
    name: str = Field(..., description="Environment variable name")
    value: str = Field(..., description="Environment variable value")
    secret: bool = Field(default=False, description="Whether this is a secret value")


class ToolDefinition(BaseModel):
    """Configurable tool definition for Claude Code investigation."""
    
    name: str = Field(..., description="Tool name identifier")
    type: ToolType = Field(..., description="Tool type")
    description: str = Field(..., description="Tool description")
    
    # Installation configuration
    install_commands: List[str] = Field(default_factory=list, description="Commands to install the tool")
    post_install_commands: List[str] = Field(default_factory=list, description="Commands to run after installation")
    
    # Environment setup
    environment_variables: List[EnvironmentVariable] = Field(default_factory=list, description="Required environment variables")
    config_files: Dict[str, str] = Field(default_factory=dict, description="Config files to create (path -> content)")
    
    # Docker-specific configuration
    volume_mounts: List[VolumeMount] = Field(default_factory=list, description="Volume mounts for Docker containers")
    
    # Validation commands
    validation_commands: List[str] = Field(default_factory=list, description="Commands to validate tool installation")
    
    # Usage examples
    usage_examples: List[str] = Field(default_factory=list, description="Example commands for using the tool")
    
    # Tool-specific metadata
    version: Optional[str] = Field(None, description="Required tool version")
    priority: int = Field(default=100, description="Installation priority (lower = higher priority)")
    enabled: bool = Field(default=True, description="Whether tool is enabled")


class ClaudeCodeConfig(BaseModel):
    """Configuration for Claude Code investigation step."""
    
    # Base Docker configuration
    base_image: str = Field(default="ubuntu:22.04", description="Base Docker image")
    working_directory: str = Field(default="/workspace", description="Working directory")
    
    # Tool definitions
    tools: List[ToolDefinition] = Field(default_factory=list, description="List of tools to install")
    
    # Environment setup
    global_environment: List[EnvironmentVariable] = Field(default_factory=list, description="Global environment variables")
    global_volume_mounts: List[VolumeMount] = Field(default_factory=list, description="Global volume mounts")
    
    # Timeouts and limits
    installation_timeout: int = Field(default=600, description="Tool installation timeout (seconds)")
    investigation_timeout: int = Field(default=1800, description="Investigation timeout (seconds)")
    
    # Kubernetes configuration
    kubernetes_enabled: bool = Field(default=True, description="Enable Kubernetes in-cluster access")
    service_account_path: str = Field(default="/var/run/secrets/kubernetes.io/serviceaccount", description="Service account path")
    
    def get_enabled_tools(self) -> List[ToolDefinition]:
        """Get list of enabled tools sorted by priority."""
        enabled_tools = [tool for tool in self.tools if tool.enabled]
        return sorted(enabled_tools, key=lambda t: t.priority)
    
    def get_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None


class SlackConfig(BaseModel):
    """Slack integration configuration."""
    
    # Channel naming
    channel_prefix: str = Field(default="inc", description="Prefix for incident channels")
    channel_suffix_length: int = Field(default=20, description="Maximum length for channel suffix")
    
    # Message formatting
    use_blocks: bool = Field(default=True, description="Use Slack blocks for rich formatting")
    update_interval: int = Field(default=300, description="Progress update interval (seconds)")
    
    # Notifications
    notify_on_start: bool = Field(default=True, description="Send notification when workflow starts")
    notify_on_completion: bool = Field(default=True, description="Send notification when workflow completes")
    notify_on_error: bool = Field(default=True, description="Send notification on errors")


class WorkflowConfig(BaseModel):
    """Main workflow configuration."""
    
    # Workflow metadata
    name: str = Field(default="production-incident-response", description="Workflow name")
    version: str = Field(default="2.0.0", description="Workflow version")
    description: str = Field(default="Production-grade incident response workflow", description="Workflow description")
    
    # Execution configuration
    runner: str = Field(default="core-testing-2", description="Kubiya runner name")
    timeout: int = Field(default=3600, description="Total workflow timeout (seconds)")
    
    # Component configurations
    claude_code: ClaudeCodeConfig = Field(default_factory=ClaudeCodeConfig, description="Claude Code configuration")
    slack: SlackConfig = Field(default_factory=SlackConfig, description="Slack configuration")
    
    # Feature flags
    enable_datadog_enrichment: bool = Field(default=True, description="Enable Datadog metric enrichment")
    enable_github_analysis: bool = Field(default=True, description="Enable GitHub commit analysis")
    enable_kubernetes_analysis: bool = Field(default=True, description="Enable Kubernetes resource analysis")
    
    # Demo mode settings
    demo_mode: bool = Field(default=False, description="Run in demo mode with mock data")
    demo_api_keys: Dict[str, str] = Field(default_factory=dict, description="Demo API keys for testing")
    
    @classmethod
    def create_default(cls) -> "WorkflowConfig":
        """Create default configuration with standard tools."""
        
        # Define standard tool configurations
        kubectl_tool = ToolDefinition(
            name="kubectl",
            type=ToolType.CLI,
            description="Kubernetes command-line tool",
            install_commands=[
                'curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"',
                "chmod +x kubectl && mv kubectl /usr/local/bin/"
            ],
            validation_commands=["kubectl version --client"],
            usage_examples=[
                "kubectl get pods --all-namespaces",
                "kubectl get nodes",
                "kubectl describe pod <pod-name>"
            ],
            priority=10
        )
        
        datadog_tool = ToolDefinition(
            name="datadog-cli",
            type=ToolType.CLI,
            description="Datadog CLI for metrics and monitoring",
            install_commands=[
                "apt-get install -y python3 python3-pip",
                "pip3 install datadog"
            ],
            environment_variables=[
                EnvironmentVariable(name="DATADOG_API_KEY", value="${DATADOG_API_KEY}", secret=True),
                EnvironmentVariable(name="DATADOG_APP_KEY", value="${DATADOG_APP_KEY}", secret=True)
            ],
            validation_commands=["python3 -c 'import datadog; print(\"Datadog CLI ready\")'"],
            usage_examples=[
                "dog metric post system.load.1 1.0",
                "dog event post 'Something happened'"
            ],
            priority=20
        )
        
        claude_code_tool = ToolDefinition(
            name="claude-code",
            type=ToolType.CLI,
            description="Claude Code CLI for AI-powered analysis",
            install_commands=[
                "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
                "apt-get install -y nodejs",
                "npm install -g @anthropic-ai/claude-code"
            ],
            environment_variables=[
                EnvironmentVariable(name="ANTHROPIC_API_KEY", value="${ANTHROPIC_API_KEY}", secret=True)
            ],
            validation_commands=["claude-code --version || echo 'Claude Code CLI installed'"],
            usage_examples=[
                "claude-code analyze-logs /var/log/",
                "claude-code investigate-error 'error message'"
            ],
            priority=30
        )
        
        github_tool = ToolDefinition(
            name="github-cli",
            type=ToolType.CLI,
            description="GitHub CLI for repository analysis",
            install_commands=[
                "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
                "chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg",
                'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list',
                "apt update && apt install -y gh"
            ],
            environment_variables=[
                EnvironmentVariable(name="GITHUB_TOKEN", value="${GITHUB_TOKEN}", secret=True)
            ],
            validation_commands=["gh --version"],
            usage_examples=[
                "gh repo view",
                "gh pr list",
                "gh api repos/:owner/:repo/commits"
            ],
            priority=40
        )
        
        claude_code_config = ClaudeCodeConfig(
            tools=[kubectl_tool, datadog_tool, claude_code_tool, github_tool]
        )
        
        return cls(
            claude_code=claude_code_config
        )