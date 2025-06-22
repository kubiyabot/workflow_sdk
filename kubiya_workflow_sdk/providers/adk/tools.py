"""
Tools for ADK agents to interact with the Kubiya platform.

These tools provide access to platform resources like runners,
integrations, secrets metadata, etc. using the enhanced Kubiya SDK.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from kubiya_workflow_sdk.client import KubiyaClient

logger = logging.getLogger(__name__)


@dataclass
class KubiyaContextTools:
    """
    Tools for loading context from the Kubiya platform.
    
    These tools are used by ADK agents to fetch information about
    available resources in the Kubiya platform using the SDK.
    """
    
    api_key: Optional[str] = None
    base_url: str = "https://api.kubiya.ai"
    org_name: Optional[str] = None
    
    def __post_init__(self):
        """Initialize the Kubiya client."""
        self.api_key = self.api_key or os.getenv("KUBIYA_API_KEY")
        if self.api_key:
            self.client = KubiyaClient(
                api_key=self.api_key,
                base_url=self.base_url,
                org_name=self.org_name
            )
            logger.info(f"Initialized Kubiya client for org: {self.org_name}")
        else:
            logger.warning("No Kubiya API key provided. Platform features will be limited.")
            self.client = None
    
    def get_runners(self) -> Dict[str, Any]:
        """
        Get available runners for workflow execution.
        
        Uses the enhanced SDK client to fetch runner information.
        
        Returns:
            Dict containing runner information
        """
        try:
            if not self.client:
                return {
                    "status": "error",
                    "message": "No API key provided",
                    "runners": [{
                        "name": "core-testing-2",
                        "type": "default",
                        "description": "Default testing runner"
                    }]
                }
            
            # Use the SDK's get_runners method
            runners = self.client.get_runners()
            
            return {
                "status": "success",
                "runners": runners
            }
            
        except Exception as e:
            logger.error(f"Error fetching runners: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "runners": []
            }
    
    def get_integrations(self) -> Dict[str, Any]:
        """
        Get available integrations and their capabilities.
        
        Uses the enhanced SDK client to fetch integration information.
        
        Returns:
            Dict containing integration information
        """
        try:
            if not self.client:
                return {
                    "status": "error",
                    "message": "No API key provided",
                    "integrations": [
                        {
                            "name": "bash",
                            "type": "shell",
                            "commands": ["bash", "sh"],
                            "description": "Bash shell commands"
                        }
                    ]
                }
            
            # Use the SDK's get_integrations method
            integrations = self.client.get_integrations()
            
            return {
                "status": "success",
                "integrations": integrations
            }
            
        except Exception as e:
            logger.error(f"Error fetching integrations: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "integrations": []
            }
    
    def get_secrets_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about available secrets (not the actual values).
        
        Uses the enhanced SDK client to fetch secret metadata.
        
        Returns:
            Dict containing secret metadata
        """
        try:
            if not self.client:
                return {
                    "status": "error",
                    "message": "No API key provided",
                    "secrets": []
                }
            
            # Use the SDK's get_secrets_metadata method which now uses the correct endpoint
            secrets = self.client.get_secrets_metadata()
            
            return {
                "status": "success",
                "secrets": secrets
            }
            
        except Exception as e:
            logger.error(f"Error fetching secrets metadata: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "secrets": []
            }
    
    def get_org_info(self) -> Dict[str, Any]:
        """
        Get organization information.
        
        Uses the enhanced SDK client to fetch organization details.
        
        Returns:
            Dict containing organization details
        """
        try:
            if not self.client:
                return {
                    "status": "error",
                    "message": "No API key provided",
                    "organization": {
                        "id": "unknown",
                        "name": "Unknown Organization"
                    }
                }
            
            # Use the SDK's get_organization_info method
            org_info = self.client.get_organization_info()
            
            return {
                "status": "success",
                "organization": org_info
            }
            
        except Exception as e:
            logger.error(f"Error fetching organization info: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "organization": {}
            }
    
    def list_agents(self, search: Optional[str] = None) -> Dict[str, Any]:
        """
        List available agents in the organization.
        
        Args:
            search: Optional search term
            
        Returns:
            Dict containing agent list
        """
        try:
            if not self.client:
                return {
                    "status": "error",
                    "message": "No API key provided",
                    "agents": []
                }
            
            # Use the SDK's list_agents method
            agents = self.client.list_agents(search=search)
            
            return {
                "status": "success",
                "agents": agents
            }
            
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "agents": []
            }
    
    def create_kubiya_agent(
        self,
        name: str,
        description: str,
        system_message: str,
        tools: Optional[List[str]] = None,
        model: str = "together_ai/deepseek-ai/DeepSeek-V3"
    ) -> Dict[str, Any]:
        """
        Create a new agent in the Kubiya platform.
        
        Args:
            name: Agent name
            description: Agent description
            system_message: System prompt
            tools: List of tools to enable
            model: LLM model to use
            
        Returns:
            Dict with creation result
        """
        try:
            if not self.client:
                return {
                    "status": "error",
                    "message": "No API key provided",
                    "agent": None
                }
            
            # Use the SDK's create_agent method
            agent = self.client.create_agent(
                name=name,
                description=description,
                system_message=system_message,
                tools=tools,
                model=model
            )
            
            return {
                "status": "success",
                "agent": agent
            }
            
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "agent": None
            }
    
    def check_missing_context(
        self,
        workflow: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if workflow has any missing context or requirements.
        
        Args:
            workflow: The workflow definition
            context: Available platform context
            
        Returns:
            Dict with missing requirements
        """
        missing = {
            "secrets": [],
            "integrations": [],
            "runners": [],
            "other": []
        }
        
        try:
            # Get available resources from context
            available_secrets = {s["name"] for s in context.get("secrets", [])}
            available_integrations = {i["name"] for i in context.get("integrations", [])}
            available_runners = {r["name"] for r in context.get("runners", [])}
            
            # Check workflow steps
            steps = workflow.get("steps", [])
            
            for step in steps:
                # Check for secret references
                if step.get("type") == "get_secret":
                    secret_name = step.get("secret_name") or step.get("name")
                    if secret_name and secret_name not in available_secrets:
                        missing["secrets"].append(secret_name)
                
                # Check for integration usage in commands
                command = step.get("command", "")
                
                # Common integration patterns
                integration_patterns = {
                    "kubectl": "kubernetes",
                    "helm": "kubernetes",
                    "aws": "aws",
                    "gcloud": "gcp",
                    "az": "azure",
                    "git": "github",
                    "gh": "github",
                    "docker": "docker",
                    "terraform": "terraform",
                    "ansible": "ansible",
                    "slack": "slack",
                    "datadog": "datadog"
                }
                
                for pattern, integration in integration_patterns.items():
                    if pattern in command and integration not in available_integrations:
                        if integration not in missing["integrations"]:
                            missing["integrations"].append(integration)
                
                # Check for Kubiya executor usage
                if step.get("type") == "kubiya" or "kubiya:" in command:
                    executor = step.get("executor") or "default"
                    # Extract integration from kubiya:integration:command format
                    if "kubiya:" in command:
                        parts = command.split(":")
                        if len(parts) >= 2:
                            integration = parts[1]
                            if integration not in available_integrations:
                                missing["integrations"].append(integration)
            
            # Check runner requirements
            runner = workflow.get("runner")
            if runner and runner not in available_runners:
                missing["runners"].append(runner)
            
            # Check for environment variables that might need secrets
            env_vars = workflow.get("env", {})
            for var_name, var_value in env_vars.items():
                if isinstance(var_value, str) and var_value.startswith("$"):
                    # This might be a secret reference
                    secret_ref = var_value[1:]  # Remove $
                    if secret_ref not in available_secrets:
                        missing["secrets"].append(secret_ref)
            
            return {
                "status": "success",
                "has_missing": any(missing.values()),
                "missing": missing
            }
            
        except Exception as e:
            logger.error(f"Error checking missing context: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "has_missing": False,
                "missing": missing
            } 