"""Tool registry with predefined tool definitions."""

from typing import Dict, List
from ..models.config import ToolDefinition, ToolType, EnvironmentVariable


class ToolRegistry:
    """Registry of predefined tool definitions for common CLI tools."""
    
    @staticmethod
    def kubectl() -> ToolDefinition:
        """Kubernetes kubectl CLI tool."""
        return ToolDefinition(
            name="kubectl",
            type=ToolType.CLI,
            description="Kubernetes command-line tool for cluster management",
            install_commands=[
                'curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"',
                "chmod +x kubectl && mv kubectl /usr/local/bin/"
            ],
            validation_commands=[
                "kubectl version --client",
                "kubectl cluster-info || echo 'Cluster not accessible in this environment'"
            ],
            usage_examples=[
                "kubectl get pods --all-namespaces",
                "kubectl get nodes -o wide",
                "kubectl describe pod <pod-name>",
                "kubectl logs <pod-name> -f",
                "kubectl top pods --all-namespaces"
            ],
            priority=10,
            version="latest"
        )
    
    @staticmethod
    def helm() -> ToolDefinition:
        """Helm package manager for Kubernetes."""
        return ToolDefinition(
            name="helm",
            type=ToolType.CLI,
            description="Kubernetes package manager",
            install_commands=[
                "curl https://get.helm.sh/helm-v3.14.0-linux-amd64.tar.gz | tar -xz",
                "mv linux-amd64/helm /usr/local/bin/ && rm -rf linux-amd64"
            ],
            validation_commands=[
                "helm version",
                "helm repo list || echo 'No helm repositories configured'"
            ],
            usage_examples=[
                "helm list --all-namespaces",
                "helm history <release-name>",
                "helm get values <release-name>"
            ],
            priority=20,
            version="v3.14.0"
        )
    
    @staticmethod
    def argocd() -> ToolDefinition:
        """ArgoCD CLI for GitOps deployment management."""
        return ToolDefinition(
            name="argocd",
            type=ToolType.CLI,
            description="ArgoCD CLI for GitOps deployment management",
            install_commands=[
                "curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64",
                "chmod +x argocd-linux-amd64 && mv argocd-linux-amd64 /usr/local/bin/argocd"
            ],
            environment_variables=[
                EnvironmentVariable(name="ARGOCD_SERVER", value="${ARGOCD_SERVER}"),
                EnvironmentVariable(name="ARGOCD_USERNAME", value="${ARGOCD_USERNAME}"),
                EnvironmentVariable(name="ARGOCD_PASSWORD", value="${ARGOCD_PASSWORD}", secret=True)
            ],
            post_install_commands=[
                "argocd login $ARGOCD_SERVER --username $ARGOCD_USERNAME --password $ARGOCD_PASSWORD --insecure || echo 'ArgoCD login failed - check credentials'"
            ],
            validation_commands=[
                "argocd version --client",
                "argocd context || echo 'ArgoCD context not configured'"
            ],
            usage_examples=[
                "argocd app list",
                "argocd app get <app-name>",
                "argocd app sync <app-name>",
                "argocd app history <app-name>"
            ],
            priority=30
        )
    
    @staticmethod
    def datadog_cli() -> ToolDefinition:
        """Datadog CLI for metrics and monitoring."""
        return ToolDefinition(
            name="datadog-cli",
            type=ToolType.CLI,
            description="Datadog CLI for metrics and monitoring queries",
            install_commands=[
                "apt-get install -y python3 python3-pip",
                "pip3 install datadog"
            ],
            environment_variables=[
                EnvironmentVariable(name="DATADOG_API_KEY", value="${DATADOG_API_KEY}", secret=True),
                EnvironmentVariable(name="DATADOG_APP_KEY", value="${DATADOG_APP_KEY}", secret=True)
            ],
            config_files={
                "/root/.datadog/config": """[Connection]
api_key = ${DATADOG_API_KEY}
app_key = ${DATADOG_APP_KEY}
"""
            },
            validation_commands=[
                "python3 -c 'import datadog; print(\"Datadog CLI ready\")'",
                "dog --help || echo 'Datadog CLI validation complete'"
            ],
            usage_examples=[
                "dog metric query 'avg:system.load.1{*}' --from 1h",
                "dog event post 'Investigation started' --tags incident_response",
                "dog monitor search --query 'status:Alert'"
            ],
            priority=40
        )
    
    @staticmethod
    def github_cli() -> ToolDefinition:
        """GitHub CLI for repository analysis."""
        return ToolDefinition(
            name="github-cli",
            type=ToolType.CLI,
            description="GitHub CLI for repository and deployment analysis",
            install_commands=[
                "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
                "chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg",
                'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list',
                "apt update && apt install -y gh"
            ],
            environment_variables=[
                EnvironmentVariable(name="GITHUB_TOKEN", value="${GITHUB_TOKEN}", secret=True)
            ],
            post_install_commands=[
                "echo $GITHUB_TOKEN | gh auth login --with-token || echo 'GitHub auth failed - check token'"
            ],
            validation_commands=[
                "gh --version",
                "gh auth status || echo 'GitHub not authenticated'"
            ],
            usage_examples=[
                "gh repo view",
                "gh pr list --state all --limit 10",
                "gh api repos/:owner/:repo/commits",
                "gh workflow list",
                "gh run list --limit 5"
            ],
            priority=50
        )
    
    @staticmethod
    def observe_cli() -> ToolDefinition:
        """Observe CLI for observability and tracing."""
        return ToolDefinition(
            name="observe-cli",
            type=ToolType.CLI,
            description="Observe CLI for observability data and trace analysis",
            install_commands=[
                "curl -L -o observe-cli https://github.com/observeinc/observe-cli/releases/latest/download/observe-cli-linux-amd64",
                "chmod +x observe-cli && mv observe-cli /usr/local/bin/observe"
            ],
            environment_variables=[
                EnvironmentVariable(name="OBSERVE_API_KEY", value="${OBSERVE_API_KEY}", secret=True),
                EnvironmentVariable(name="OBSERVE_CUSTOMER", value="${OBSERVE_CUSTOMER}")
            ],
            validation_commands=[
                "observe --version || echo 'Observe CLI installed'",
                "observe auth status || echo 'Observe auth check complete'"
            ],
            usage_examples=[
                "observe query 'from logs | filter error'",
                "observe search --query 'error AND payment'",
                "observe trace search --service payment-service"
            ],
            priority=60
        )
    
    @staticmethod
    def claude_code_cli() -> ToolDefinition:
        """Claude Code CLI for AI-powered analysis."""
        return ToolDefinition(
            name="claude-code",
            type=ToolType.CLI,
            description="Claude Code CLI for AI-powered incident analysis",
            install_commands=[
                "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
                "apt-get install -y nodejs",
                "npm install -g @anthropic-ai/claude-code || echo 'Claude Code CLI installation attempted'"
            ],
            environment_variables=[
                EnvironmentVariable(name="ANTHROPIC_API_KEY", value="${ANTHROPIC_API_KEY}", secret=True)
            ],
            validation_commands=[
                "node --version",
                "npm --version", 
                "claude-code --version || echo 'Claude Code CLI installation complete'"
            ],
            usage_examples=[
                "claude-code analyze-logs /var/log/",
                "claude-code investigate-error 'database connection timeout'",
                "claude-code suggest-fix --error-type 'pod crash loop'"
            ],
            priority=70
        )
    
    @staticmethod
    def docker_cli() -> ToolDefinition:
        """Docker CLI for container management."""
        return ToolDefinition(
            name="docker",
            type=ToolType.CLI,
            description="Docker CLI for container analysis and management",
            install_commands=[
                "apt-get install -y apt-transport-https ca-certificates curl software-properties-common",
                "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -",
                'add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"',
                "apt-get update && apt-get install -y docker-ce-cli"
            ],
            validation_commands=[
                "docker --version",
                "docker info || echo 'Docker daemon not accessible in this environment'"
            ],
            usage_examples=[
                "docker ps -a",
                "docker logs <container-id>",
                "docker inspect <container-id>",
                "docker stats --no-stream"
            ],
            priority=80
        )
    
    @staticmethod
    def jq_tool() -> ToolDefinition:
        """jq JSON processor."""
        return ToolDefinition(
            name="jq",
            type=ToolType.CLI,
            description="Command-line JSON processor",
            install_commands=[
                "apt-get install -y jq"
            ],
            validation_commands=[
                "jq --version"
            ],
            usage_examples=[
                "echo '{\"key\":\"value\"}' | jq .",
                "cat file.json | jq '.field'",
                "curl -s api/endpoint | jq '.data[]'"
            ],
            priority=5  # High priority - many other tools depend on jq
        )
    
    @staticmethod
    def get_all_tools(self) -> Dict[str, ToolDefinition]:
        """Get all available tools in the registry."""
        return {
            "kubectl": self.kubectl(),
            "helm": self.helm(),
            "argocd": self.argocd(),
            "datadog-cli": self.datadog_cli(),
            "github-cli": self.github_cli(),
            "observe-cli": self.observe_cli(),
            "claude-code": self.claude_code_cli(),
            "docker": self.docker_cli(),
            "jq": self.jq_tool()
        }


def get_default_tools() -> List[ToolDefinition]:
    """Get the default recommended set of tools for incident response."""
    registry = ToolRegistry()
    
    return [
        registry.jq_tool(),        # Essential JSON processing
        registry.kubectl(),       # Kubernetes management
        registry.helm(),          # Kubernetes package management
        registry.datadog_cli(),   # Monitoring and metrics
        registry.github_cli(),    # Code and deployment analysis
        registry.claude_code_cli()  # AI-powered analysis
    ]


def get_minimal_tools() -> List[ToolDefinition]:
    """Get a minimal set of tools for basic incident response."""
    registry = ToolRegistry()
    
    return [
        registry.jq_tool(),
        registry.kubectl(),
        registry.datadog_cli()
    ]


def get_full_toolset() -> List[ToolDefinition]:
    """Get the complete toolset for comprehensive incident response."""
    registry = ToolRegistry()
    
    return [
        registry.jq_tool(),
        registry.kubectl(),
        registry.helm(),
        registry.argocd(),
        registry.datadog_cli(),
        registry.github_cli(),
        registry.observe_cli(),
        registry.claude_code_cli(),
        registry.docker_cli()
    ]