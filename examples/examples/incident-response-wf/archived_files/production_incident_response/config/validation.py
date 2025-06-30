"""Configuration validation utilities."""

from typing import Dict, List, Any, Optional
from ..models.config import WorkflowConfig, ToolDefinition


class ValidationResult:
    """Result of configuration validation."""
    
    def __init__(self):
        self.valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.tool_results: Dict[str, Dict[str, Any]] = {}
    
    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)
    
    def add_tool_result(self, tool_name: str, valid: bool, issues: List[str]):
        """Add tool validation result."""
        self.tool_results[tool_name] = {
            "valid": valid,
            "issues": issues
        }
        if not valid:
            self.valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "tool_results": self.tool_results
        }


class ConfigValidator:
    """Validates workflow configurations."""
    
    @staticmethod
    def validate(config: WorkflowConfig) -> ValidationResult:
        """Validate a complete workflow configuration."""
        
        result = ValidationResult()
        
        # Validate basic configuration
        ConfigValidator._validate_basic_config(config, result)
        
        # Validate Claude Code configuration
        ConfigValidator._validate_claude_code_config(config.claude_code, result)
        
        # Validate Slack configuration
        ConfigValidator._validate_slack_config(config.slack, result)
        
        # Validate feature flags
        ConfigValidator._validate_feature_flags(config, result)
        
        return result
    
    @staticmethod
    def _validate_basic_config(config: WorkflowConfig, result: ValidationResult):
        """Validate basic workflow configuration."""
        
        if not config.name:
            result.add_error("Workflow name is required")
        elif len(config.name) < 3:
            result.add_error("Workflow name must be at least 3 characters")
        elif not config.name.replace('-', '').replace('_', '').isalnum():
            result.add_error("Workflow name must contain only alphanumeric characters, hyphens, and underscores")
        
        if not config.description:
            result.add_warning("Workflow description is recommended")
        
        if not config.runner:
            result.add_error("Workflow runner is required")
        
        if config.timeout < 60:
            result.add_warning("Workflow timeout is very short (< 60 seconds)")
        elif config.timeout > 7200:
            result.add_warning("Workflow timeout is very long (> 2 hours)")
        
        if not config.version:
            result.add_warning("Workflow version is recommended for tracking")
    
    @staticmethod
    def _validate_claude_code_config(claude_config, result: ValidationResult):
        """Validate Claude Code configuration."""
        
        if not claude_config.tools:
            result.add_warning("No tools configured for Claude Code investigation")
            return
        
        # Validate each tool
        tool_names = set()
        priorities = set()
        
        for tool in claude_config.tools:
            tool_result = ConfigValidator._validate_tool(tool)
            result.add_tool_result(tool.name or "unnamed", tool_result["valid"], tool_result["issues"])
            
            if tool.name:
                if tool.name in tool_names:
                    result.add_error(f"Duplicate tool name: {tool.name}")
                tool_names.add(tool.name)
            
            if tool.priority in priorities:
                result.add_warning(f"Multiple tools have the same priority: {tool.priority}")
            priorities.add(tool.priority)
        
        # Validate timeouts
        if claude_config.installation_timeout < 60:
            result.add_warning("Installation timeout is very short")
        elif claude_config.installation_timeout > 1800:
            result.add_warning("Installation timeout is very long")
        
        if claude_config.investigation_timeout < 300:
            result.add_warning("Investigation timeout is very short")
        elif claude_config.investigation_timeout > 3600:
            result.add_warning("Investigation timeout is very long")
        
        # Validate base image
        if not claude_config.base_image:
            result.add_error("Base Docker image is required")
        elif not (":" in claude_config.base_image or "@" in claude_config.base_image):
            result.add_warning("Base image should specify a tag or digest")
    
    @staticmethod
    def _validate_tool(tool: ToolDefinition) -> Dict[str, Any]:
        """Validate a single tool definition."""
        
        issues = []
        valid = True
        
        if not tool.name:
            issues.append("Tool name is required")
            valid = False
        elif len(tool.name) < 2:
            issues.append("Tool name is too short")
            valid = False
        
        if not tool.description:
            issues.append("Tool description is recommended")
        
        if not tool.install_commands:
            issues.append("Installation commands are required")
            valid = False
        
        # Check for potentially dangerous commands
        dangerous_patterns = ['rm -rf /', 'format', 'mkfs', '> /dev/']
        for cmd in tool.install_commands:
            for pattern in dangerous_patterns:
                if pattern in cmd.lower():
                    issues.append(f"Potentially dangerous command detected: {cmd}")
        
        # Validate environment variables
        for env_var in tool.environment_variables:
            if not env_var.name:
                issues.append("Environment variable name is required")
                valid = False
            elif not env_var.name.isidentifier():
                issues.append(f"Invalid environment variable name: {env_var.name}")
                valid = False
        
        # Validate priority
        if tool.priority < 0:
            issues.append("Tool priority cannot be negative")
            valid = False
        
        return {
            "valid": valid,
            "issues": issues
        }
    
    @staticmethod
    def _validate_slack_config(slack_config, result: ValidationResult):
        """Validate Slack configuration."""
        
        if not slack_config.channel_prefix:
            result.add_warning("Slack channel prefix is recommended")
        elif len(slack_config.channel_prefix) > 10:
            result.add_warning("Slack channel prefix is quite long")
        
        if slack_config.channel_suffix_length < 5:
            result.add_warning("Channel suffix length is very short")
        elif slack_config.channel_suffix_length > 50:
            result.add_warning("Channel suffix length might be too long for Slack")
        
        if slack_config.update_interval < 30:
            result.add_warning("Update interval is very frequent")
        elif slack_config.update_interval > 1800:
            result.add_warning("Update interval is very infrequent")
    
    @staticmethod
    def _validate_feature_flags(config: WorkflowConfig, result: ValidationResult):
        """Validate feature flag combinations."""
        
        if config.enable_datadog_enrichment:
            # Check if datadog tools are configured
            has_datadog_tool = any(tool.name == "datadog-cli" for tool in config.claude_code.tools)
            if not has_datadog_tool:
                result.add_warning("Datadog enrichment enabled but no Datadog CLI tool configured")
        
        if config.enable_github_analysis:
            # Check if GitHub tools are configured
            has_github_tool = any(tool.name == "github-cli" for tool in config.claude_code.tools)
            if not has_github_tool:
                result.add_warning("GitHub analysis enabled but no GitHub CLI tool configured")
        
        if config.enable_kubernetes_analysis and not config.claude_code.kubernetes_enabled:
            result.add_warning("Kubernetes analysis enabled but Kubernetes access disabled")
        
        if config.demo_mode:
            result.add_warning("Demo mode is enabled - workflow will use mock data")


class SecurityValidator:
    """Validates security aspects of configurations."""
    
    @staticmethod
    def validate_security(config: WorkflowConfig) -> ValidationResult:
        """Validate security aspects of the configuration."""
        
        result = ValidationResult()
        
        # Check for hardcoded secrets
        SecurityValidator._check_hardcoded_secrets(config, result)
        
        # Check for privileged operations
        SecurityValidator._check_privileged_operations(config, result)
        
        # Check for network access
        SecurityValidator._check_network_access(config, result)
        
        return result
    
    @staticmethod
    def _check_hardcoded_secrets(config: WorkflowConfig, result: ValidationResult):
        """Check for hardcoded secrets in configuration."""
        
        secret_patterns = ['password', 'token', 'key', 'secret']
        
        for tool in config.claude_code.tools:
            # Check environment variables
            for env_var in tool.environment_variables:
                if not env_var.secret and any(pattern in env_var.name.lower() for pattern in secret_patterns):
                    if not env_var.value.startswith('${'):
                        result.add_error(f"Potential hardcoded secret in tool {tool.name}: {env_var.name}")
            
            # Check installation commands for hardcoded credentials
            for cmd in tool.install_commands:
                if any(pattern in cmd.lower() for pattern in secret_patterns):
                    if not ('${' in cmd or '$(' in cmd):
                        result.add_warning(f"Potential hardcoded credential in tool {tool.name}: {cmd[:50]}...")
    
    @staticmethod
    def _check_privileged_operations(config: WorkflowConfig, result: ValidationResult):
        """Check for privileged operations that might be risky."""
        
        privileged_patterns = ['sudo', 'su -', 'chmod 777', 'chown root', '--privileged']
        
        for tool in config.claude_code.tools:
            for cmd in tool.install_commands:
                for pattern in privileged_patterns:
                    if pattern in cmd.lower():
                        result.add_warning(f"Privileged operation detected in tool {tool.name}: {pattern}")
    
    @staticmethod
    def _check_network_access(config: WorkflowConfig, result: ValidationResult):
        """Check for network access patterns."""
        
        network_patterns = ['curl', 'wget', 'nc ', 'telnet', 'ssh', 'scp']
        
        for tool in config.claude_code.tools:
            for cmd in tool.install_commands:
                for pattern in network_patterns:
                    if pattern in cmd.lower():
                        # This is usually expected for installation, just note it
                        break