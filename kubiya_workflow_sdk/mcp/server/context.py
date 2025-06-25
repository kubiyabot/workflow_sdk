"""Context management for intelligent workflow generation."""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RunnerInfo:
    """Information about a Kubiya runner."""
    name: str
    type: str
    status: str
    description: Optional[str] = None
    docker_enabled: bool = True
    # Health information
    health_status: str = "unknown"
    is_healthy: bool = False
    health_data: Optional[Dict[str, Any]] = None
    component_versions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    meets_requirements: bool = True
    last_health_check: Optional[datetime] = None
    
    @property
    def is_available(self) -> bool:
        """Check if runner is available."""
        # Runner must be active AND healthy
        return (self.status.lower() in ["active", "ready", "available"] and 
                self.is_healthy and 
                self.meets_requirements)
    
    def supports_docker(self) -> bool:
        """Check if runner supports Docker containers."""
        return self.docker_enabled
    
    def get_component_version(self, component_name: str) -> Optional[str]:
        """Get version of a specific component."""
        component = self.component_versions.get(component_name, {})
        return component.get("version")
    
    def has_component(self, component_name: str, min_version: Optional[str] = None) -> bool:
        """Check if runner has a component with optional minimum version."""
        if component_name not in self.component_versions:
            return False
        
        component = self.component_versions[component_name]
        if component.get("status") != "ok":
            return False
        
        if min_version and component.get("version"):
            # Simple version comparison (assumes semantic versioning)
            try:
                from packaging import version
                return version.parse(component["version"]) >= version.parse(min_version)
            except:
                # Fallback to string comparison
                return component["version"] >= min_version
        
        return True


@dataclass
class IntegrationInfo:
    """Information about an available integration."""
    name: str
    type: str
    description: str
    commands: List[str] = field(default_factory=list)
    docker_image: Optional[str] = None
    environment_vars: List[str] = field(default_factory=list)
    required_secrets: List[str] = field(default_factory=list)
    
    @property
    def is_docker_based(self) -> bool:
        """Check if this integration uses Docker."""
        return bool(self.docker_image)


@dataclass
class SecretInfo:
    """Information about an available secret."""
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if secret name matches a pattern."""
        import fnmatch
        return fnmatch.fnmatch(self.name.lower(), pattern.lower())


class WorkflowContext:
    """Manages workflow-related context for better DSL generation."""
    
    def __init__(self):
        self.runners: Dict[str, RunnerInfo] = {}
        self.default_runner = "kubiya-hosted"
        self.last_updated: Optional[datetime] = None
        self.component_requirements: Dict[str, str] = {}
        self._load_component_requirements()
    
    def _load_component_requirements(self):
        """Load component requirements from environment."""
        import os
        
        if os.environ.get("KUBIYA_REQUIRED_AGENT_MANAGER_VERSION"):
            self.component_requirements["agent-manager"] = os.environ["KUBIYA_REQUIRED_AGENT_MANAGER_VERSION"]
        if os.environ.get("KUBIYA_REQUIRED_TOOL_MANAGER_VERSION"):
            self.component_requirements["tool-manager"] = os.environ["KUBIYA_REQUIRED_TOOL_MANAGER_VERSION"]
        
    def update_runners(self, runners: List[Dict[str, Any]]):
        """Update available runners with health information."""
        self.runners.clear()
        
        for runner_data in runners:
            # Extract health information
            health_data = runner_data.get("health", {})
            component_versions = runner_data.get("component_versions", {})
            
            runner = RunnerInfo(
                name=runner_data.get("name", ""),
                type=runner_data.get("type", "kubernetes"),
                status=runner_data.get("status", "unknown"),
                description=runner_data.get("description"),
                docker_enabled=runner_data.get("docker_enabled", True),
                # Health fields
                health_status=runner_data.get("health_status", "unknown"),
                is_healthy=runner_data.get("is_healthy", False),
                health_data=health_data,
                component_versions=component_versions,
                meets_requirements=runner_data.get("meets_requirements", True),
                last_health_check=datetime.now() if health_data else None
            )
            self.runners[runner.name] = runner
        
        self.last_updated = datetime.now()
        logger.info(f"Updated {len(self.runners)} runners")
    
    def get_available_runners(self) -> List[RunnerInfo]:
        """Get list of available runners (healthy and meeting requirements)."""
        return [r for r in self.runners.values() if r.is_available]
    
    def get_docker_runners(self) -> List[RunnerInfo]:
        """Get runners that support Docker."""
        return [r for r in self.runners.values() if r.is_available and r.supports_docker()]
    
    def get_runners_by_component(self, component_name: str, min_version: Optional[str] = None) -> List[RunnerInfo]:
        """Get runners that have a specific component."""
        return [
            r for r in self.runners.values() 
            if r.is_available and r.has_component(component_name, min_version)
        ]
    
    def validate_runner(self, runner_name: str) -> tuple[bool, str]:
        """Validate if a runner exists and is available."""
        if runner_name not in self.runners:
            available = [r.name for r in self.get_available_runners()]
            return False, f"Runner '{runner_name}' not found. Available: {', '.join(available)}"
        
        runner = self.runners[runner_name]
        if not runner.is_healthy:
            return False, f"Runner '{runner_name}' is not healthy (status: {runner.health_status})"
        
        if not runner.meets_requirements:
            missing = []
            for comp, req_version in self.component_requirements.items():
                if not runner.has_component(comp, req_version):
                    actual = runner.get_component_version(comp) or "not installed"
                    missing.append(f"{comp} (required: {req_version}, actual: {actual})")
            return False, f"Runner '{runner_name}' does not meet component requirements: {', '.join(missing)}"
        
        if not runner.is_available:
            return False, f"Runner '{runner_name}' is not available (status: {runner.status})"
        
        return True, f"Runner '{runner_name}' is available and healthy"
    
    def get_runner_suggestions(self) -> str:
        """Get helpful runner suggestions for DSL generation."""
        available_runners = self.get_available_runners()
        docker_runners = self.get_docker_runners()
        
        if not available_runners:
            return "No healthy runners available. Please check runner health status."
        
        suggestions = []
        
        # Group by capabilities
        if docker_runners:
            suggestions.append("Docker-enabled runners:")
            for runner in docker_runners[:3]:
                desc = f"  - {runner.name}: {runner.type}"
                # Add component info
                components = []
                for comp, info in runner.component_versions.items():
                    if info.get("status") == "ok":
                        components.append(f"{comp} v{info.get('version', 'unknown')}")
                if components:
                    desc += f" [{', '.join(components[:2])}]"
                suggestions.append(desc)
        
        # Non-Docker runners
        non_docker = [r for r in available_runners if not r.supports_docker()]
        if non_docker:
            suggestions.append("\nStandard runners:")
            for runner in non_docker[:2]:
                desc = f"  - {runner.name}: {runner.type}"
                suggestions.append(desc)
        
        if self.component_requirements:
            suggestions.append("\nComponent requirements:")
            for comp, version in self.component_requirements.items():
                suggestions.append(f"  - {comp}: {version}")
        
        return "\n".join(suggestions)


class IntegrationContext:
    """Manages integration context for tool generation."""
    
    def __init__(self):
        self.integrations: Dict[str, IntegrationInfo] = {}
        self.docker_images: Dict[str, List[str]] = {}  # Category -> images
        self.last_updated: Optional[datetime] = None
        
        # Default Docker images for common tasks
        self._init_default_images()
    
    def _init_default_images(self):
        """Initialize default Docker images by category."""
        self.docker_images = {
            "python": [
                "python:3.11-slim",
                "python:3.11-alpine", 
                "python:3.11"
            ],
            "nodejs": [
                "node:20-slim",
                "node:20-alpine",
                "node:20"
            ],
            "data_processing": [
                "jupyter/scipy-notebook:latest",
                "apache/spark:latest",
                "pandas/pandas:latest"
            ],
            "cloud_cli": [
                "amazon/aws-cli:latest",
                "google/cloud-sdk:latest",
                "mcr.microsoft.com/azure-cli:latest"
            ],
            "databases": [
                "postgres:15-alpine",
                "mysql:8.0",
                "mongo:7.0",
                "redis:7-alpine"
            ],
            "ci_cd": [
                "docker:24-dind",
                "docker/compose:latest",
                "alpine/git:latest"
            ],
            "monitoring": [
                "prom/prometheus:latest",
                "grafana/grafana:latest",
                "elastic/elasticsearch:8.11.0"
            ],
            "security": [
                "aquasec/trivy:latest",
                "anchore/grype:latest",
                "owasp/zap2docker-stable:latest"
            ]
        }
    
    def update_integrations(self, integrations: List[Dict[str, Any]]):
        """Update available integrations."""
        self.integrations.clear()
        
        for int_data in integrations:
            # Handle the actual API response format
            integration = IntegrationInfo(
                name=int_data.get("name", ""),
                type=int_data.get("integration_type", int_data.get("type", "")),
                description=int_data.get("description", ""),
                commands=int_data.get("commands", []),
                docker_image=int_data.get("docker_image"),
                environment_vars=int_data.get("environment_vars", []),
                required_secrets=int_data.get("required_secrets", [])
            )
            self.integrations[integration.name] = integration
        
        self.last_updated = datetime.now()
        logger.info(f"Updated {len(self.integrations)} integrations")
    
    def get_docker_suggestions(self, task_type: str) -> List[str]:
        """Get Docker image suggestions for a task type."""
        # Check integrations first
        docker_integrations = [
            i for i in self.integrations.values() 
            if i.is_docker_based and task_type.lower() in i.description.lower()
        ]
        
        suggestions = []
        
        # Add integration-based images
        for integration in docker_integrations[:2]:
            suggestions.append(integration.docker_image)
        
        # Add category-based images
        for category, images in self.docker_images.items():
            if task_type.lower() in category.lower():
                suggestions.extend(images[:2])
                break
        
        # Default suggestions if nothing matches
        if not suggestions:
            suggestions = ["ubuntu:22.04", "alpine:latest"]
        
        return suggestions
    
    def get_integration_by_command(self, command: str) -> Optional[IntegrationInfo]:
        """Find integration that provides a specific command."""
        for integration in self.integrations.values():
            if command in integration.commands:
                return integration
        return None
    
    def get_context_prompt(self) -> str:
        """Generate a context prompt for better DSL generation."""
        docker_count = sum(1 for i in self.integrations.values() if i.is_docker_based)
        
        prompt = f"""
Available integrations: {len(self.integrations)} total ({docker_count} Docker-based)

Key Docker images by category:
"""
        
        for category, images in list(self.docker_images.items())[:5]:
            prompt += f"\n{category}: {', '.join(images[:2])}"
        
        if self.integrations:
            prompt += "\n\nAvailable tools:\n"
            for name, integration in list(self.integrations.items())[:5]:
                prompt += f"- {name}: {integration.description}\n"
        
        return prompt


class SecretsContext:
    """Manages secrets context for secure workflow generation."""
    
    def __init__(self):
        self.secrets: Dict[str, SecretInfo] = {}
        self.required_secrets: Set[str] = set()  # Secrets needed but not available
        self.last_updated: Optional[datetime] = None
    
    def update_secrets(self, secrets: List[Dict[str, Any]]):
        """Update available secrets from API."""
        self.secrets.clear()
        
        for secret_data in secrets:
            secret = SecretInfo(
                name=secret_data.get("name", ""),
                description=secret_data.get("description"),
                type=secret_data.get("type"),
                tags=secret_data.get("tags", [])
            )
            self.secrets[secret.name] = secret
        
        self.last_updated = datetime.now()
        logger.info(f"Updated {len(self.secrets)} secrets")
    
    def has_secret(self, secret_name: str) -> bool:
        """Check if a secret exists."""
        return secret_name in self.secrets
    
    def find_secrets_by_pattern(self, pattern: str) -> List[SecretInfo]:
        """Find secrets matching a pattern."""
        return [s for s in self.secrets.values() if s.matches_pattern(pattern)]
    
    def mark_required(self, secret_name: str):
        """Mark a secret as required for the workflow."""
        if not self.has_secret(secret_name):
            self.required_secrets.add(secret_name)
    
    def get_missing_secrets(self) -> List[str]:
        """Get list of required secrets that are not available."""
        return list(self.required_secrets)
    
    def get_secret_suggestions(self, task_type: str) -> Dict[str, Any]:
        """Get secret suggestions based on task type."""
        suggestions = {
            "available": [],
            "commonly_needed": [],
            "missing": []
        }
        
        # Common secret patterns by task type
        patterns = {
            "aws": ["AWS_*", "aws_*", "*_aws_*"],
            "gcp": ["GCP_*", "GOOGLE_*", "gcp_*"],
            "azure": ["AZURE_*", "azure_*", "*_azure_*"],
            "database": ["*_DB_*", "*_DATABASE_*", "DB_*"],
            "api": ["*_API_KEY", "*_TOKEN", "API_*"],
            "github": ["GITHUB_*", "GH_*"],
            "docker": ["DOCKER_*", "REGISTRY_*"]
        }
        
        # Find matching patterns
        for key, pattern_list in patterns.items():
            if task_type.lower() in key.lower():
                for pattern in pattern_list:
                    matching = self.find_secrets_by_pattern(pattern)
                    suggestions["available"].extend([s.name for s in matching])
                
                # Common secrets that might be needed
                if key == "aws":
                    suggestions["commonly_needed"] = [
                        "AWS_ACCESS_KEY_ID",
                        "AWS_SECRET_ACCESS_KEY",
                        "AWS_REGION"
                    ]
                elif key == "gcp":
                    suggestions["commonly_needed"] = [
                        "GOOGLE_APPLICATION_CREDENTIALS",
                        "GCP_PROJECT_ID"
                    ]
                elif key == "database":
                    suggestions["commonly_needed"] = [
                        "DATABASE_URL",
                        "DB_HOST",
                        "DB_USER",
                        "DB_PASSWORD"
                    ]
        
        # Check which commonly needed secrets are missing
        for secret in suggestions["commonly_needed"]:
            if not self.has_secret(secret):
                suggestions["missing"].append(secret)
        
        return suggestions
    
    def get_context_prompt(self) -> str:
        """Generate context about available secrets."""
        if not self.secrets:
            return "No secrets available. Secrets can be passed as environment variables in the workflow."
        
        # Group secrets by prefix
        grouped = {}
        for secret in self.secrets.values():
            prefix = secret.name.split('_')[0].upper()
            if prefix not in grouped:
                grouped[prefix] = []
            grouped[prefix].append(secret.name)
        
        prompt = f"Available secrets ({len(self.secrets)} total):\n"
        
        for prefix, names in sorted(grouped.items())[:5]:  # Top 5 groups
            prompt += f"\n{prefix} secrets: {', '.join(names[:3])}"
            if len(names) > 3:
                prompt += f" (and {len(names) - 3} more)"
        
        if self.required_secrets:
            prompt += f"\n\nRequired but missing secrets:\n"
            for secret in list(self.required_secrets)[:5]:
                prompt += f"- {secret}\n"
        
        prompt += "\n\nSecrets usage in DSL:\n"
        prompt += "- Use {{secret:SECRET_NAME}} in commands\n"
        prompt += "- Pass as env vars: wf.env(MY_VAR='{{secret:SECRET_NAME}}')\n"
        prompt += "- For missing secrets, pass via workflow parameters"
        
        return prompt
    
    def generate_env_mapping(self) -> Dict[str, str]:
        """Generate environment variable mapping for missing secrets."""
        env_mapping = {}
        
        for secret in self.required_secrets:
            # Convert to parameter name
            param_name = secret.lower().replace('_', '-')
            env_mapping[secret] = f"{{{{params.{param_name}}}}}"
        
        return env_mapping 