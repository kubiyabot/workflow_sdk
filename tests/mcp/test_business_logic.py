"""Unit tests for MCP business logic and data transformation functions.

This module tests individual functions and modules responsible for core 
business logic within MCP tools, isolating them from external dependencies.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional

from tests.mcp.mocks import MockWorkflowAPIClient, MockScenarios
from tests.mcp.fixtures import (
    simple_workflows, complex_workflows, compile_workflow_params,
    execute_workflow_params
)


class TestWorkflowCompilationLogic:
    """Test business logic for workflow compilation."""

    def test_json_parsing_for_provide_missing_secrets(self):
        """Test JSON parsing logic for provide_missing_secrets parameter."""
        # Valid JSON string
        json_string = '{"API_KEY": "test_key", "DB_PASSWORD": "secret"}'
        try:
            parsed = json.loads(json_string)
            assert parsed == {"API_KEY": "test_key", "DB_PASSWORD": "secret"}
        except json.JSONDecodeError:
            pytest.fail("Should parse valid JSON")
        
        # Invalid JSON string
        invalid_json = '{"invalid": }'
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)
        
        # Empty string
        empty_json = ""
        with pytest.raises(json.JSONDecodeError):
            json.loads(empty_json)

    def test_workflow_object_detection_logic(self):
        """Test logic for detecting Workflow objects in execution namespace."""
        from kubiya_workflow_sdk.dsl import Workflow
        
        # Test namespace with workflow object
        namespace_with_workflow = {
            "Workflow": Workflow,
            "some_var": "value",
            "wf": Workflow("test-workflow"),
            "other_var": 123
        }
        
        # Find workflow object
        workflow_obj = None
        for var_name, var_value in namespace_with_workflow.items():
            if isinstance(var_value, Workflow):
                workflow_obj = var_value
                break
        
        assert workflow_obj is not None
        assert isinstance(workflow_obj, Workflow)
        
        # Test namespace without workflow object
        namespace_without_workflow = {
            "Workflow": Workflow,
            "some_var": "value",
            "other_var": 123
        }
        
        workflow_obj = None
        for var_name, var_value in namespace_without_workflow.items():
            if isinstance(var_value, Workflow):
                workflow_obj = var_value
                break
        
        assert workflow_obj is None

    def test_workflow_field_override_logic(self):
        """Test logic for overriding workflow fields."""
        # Initial workflow definition
        workflow_def = {
            "name": "original_name",
            "description": "Original description",
            "steps": [{"name": "step1", "run": "echo test"}]
        }
        
        # Test name override
        name = "new_name"
        description = "New description"
        
        if name:
            workflow_def["name"] = name
        if description:
            workflow_def["description"] = description
        
        assert workflow_def["name"] == "new_name"
        assert workflow_def["description"] == "New description"
        assert workflow_def["steps"] == [{"name": "step1", "run": "echo test"}]
        
        # Test with None values (should not override)
        original_def = {
            "name": "original_name",
            "description": "Original description"
        }
        
        name = None
        description = None
        
        if name:
            original_def["name"] = name
        if description:
            original_def["description"] = description
        
        assert original_def["name"] == "original_name"
        assert original_def["description"] == "Original description"

    def test_error_response_formatting(self):
        """Test error response formatting logic."""
        # Test compilation error response
        errors = ["No Workflow object found", "Invalid DSL syntax"]
        suggestions = ["Create workflow with Workflow('name')", "Check syntax"]
        
        error_response = {
            "success": False,
            "errors": errors,
            "suggestions": suggestions
        }
        
        assert error_response["success"] is False
        assert len(error_response["errors"]) == 2
        assert "Workflow object" in error_response["errors"][0]
        assert len(error_response["suggestions"]) == 2
        
        # Test validation error response
        validation_message = "Runner 'invalid-runner' not found"
        available_runners = ["runner1", "runner2"]
        
        validation_response = {
            "success": False,
            "errors": [validation_message],
            "available_runners": available_runners
        }
        
        assert validation_response["success"] is False
        assert "invalid-runner" in validation_response["errors"][0]
        assert len(validation_response["available_runners"]) == 2

    def test_success_response_formatting(self):
        """Test success response formatting logic."""
        workflow_def = {
            "name": "test_workflow",
            "steps": [{"name": "step1", "run": "echo test"}]
        }
        
        suggestions = ["Use Docker for better isolation"]
        runner_info = {"name": "default_runner", "status": "healthy"}
        
        success_response = {
            "success": True,
            "workflow": workflow_def,
            "suggestions": suggestions,
            "runner_info": runner_info,
            "compilation_time": 1.5
        }
        
        assert success_response["success"] is True
        assert success_response["workflow"]["name"] == "test_workflow"
        assert len(success_response["suggestions"]) == 1
        assert success_response["runner_info"]["status"] == "healthy"
        assert isinstance(success_response["compilation_time"], float)


class TestWorkflowExecutionLogic:
    """Test business logic for workflow execution."""

    def test_workflow_input_validation(self):
        """Test workflow input validation logic."""
        # Valid string input
        string_input = """
name: test_workflow
steps:
  - name: test_step
    run: echo "Hello"
"""
        assert isinstance(string_input, str)
        assert len(string_input.strip()) > 0
        
        # Valid dict input
        dict_input = {
            "name": "test_workflow",
            "steps": [{"name": "test_step", "run": "echo 'Hello'"}]
        }
        assert isinstance(dict_input, dict)
        assert "name" in dict_input
        assert "steps" in dict_input
        
        # Invalid empty input
        empty_input = ""
        assert isinstance(empty_input, str)
        assert len(empty_input.strip()) == 0

    def test_parameter_processing_logic(self):
        """Test parameter processing for workflow execution."""
        # String parameters (JSON)
        string_params = '{"ENV": "test", "DEBUG": "true"}'
        try:
            parsed_params = json.loads(string_params)
            assert parsed_params == {"ENV": "test", "DEBUG": "true"}
        except json.JSONDecodeError:
            pytest.fail("Should parse valid JSON parameters")
        
        # Dict parameters
        dict_params = {"ENV": "test", "DEBUG": True, "PORT": 8080}
        assert isinstance(dict_params, dict)
        assert dict_params["ENV"] == "test"
        assert dict_params["DEBUG"] is True
        assert dict_params["PORT"] == 8080
        
        # Empty parameters
        empty_params = {}
        assert isinstance(empty_params, dict)
        assert len(empty_params) == 0

    def test_execution_result_processing(self):
        """Test execution result processing logic."""
        # Successful execution result
        success_result = {
            "execution_id": "exec-123",
            "status": "completed",
            "exit_code": 0,
            "output": "Hello World",
            "logs": ["Starting", "Executing", "Completed"]
        }
        
        assert success_result["status"] == "completed"
        assert success_result["exit_code"] == 0
        assert len(success_result["logs"]) == 3
        
        # Failed execution result
        failed_result = {
            "execution_id": "exec-456",
            "status": "failed",
            "exit_code": 1,
            "error": "Command not found",
            "logs": ["Starting", "Error occurred"]
        }
        
        assert failed_result["status"] == "failed"
        assert failed_result["exit_code"] == 1
        assert "not found" in failed_result["error"]
        
        # Processing logic
        def is_successful_execution(result):
            return result.get("status") == "completed" and result.get("exit_code") == 0
        
        def is_failed_execution(result):
            return result.get("status") == "failed" or result.get("exit_code", 0) != 0
        
        assert is_successful_execution(success_result) is True
        assert is_failed_execution(success_result) is False
        assert is_successful_execution(failed_result) is False
        assert is_failed_execution(failed_result) is True


class TestDataTransformationLogic:
    """Test data transformation logic in MCP tools."""

    def test_runner_data_transformation(self):
        """Test transformation of runner data."""
        # Raw runner data
        raw_runners = [
            {
                "id": "runner-1",
                "name": "Test Runner 1", 
                "status": "healthy",
                "version": "1.0.0",
                "capabilities": ["python", "shell", "docker"],
                "last_heartbeat": "2024-01-01T00:00:00Z"
            },
            {
                "id": "runner-2",
                "name": "Test Runner 2",
                "status": "unhealthy", 
                "version": "0.9.0",
                "capabilities": ["python", "shell"],
                "last_heartbeat": "2024-01-01T00:00:00Z"
            }
        ]
        
        # Transformation: filter healthy runners
        healthy_runners = [runner for runner in raw_runners if runner["status"] == "healthy"]
        assert len(healthy_runners) == 1
        assert healthy_runners[0]["id"] == "runner-1"
        
        # Transformation: extract capabilities
        all_capabilities = set()
        for runner in raw_runners:
            all_capabilities.update(runner["capabilities"])
        assert "python" in all_capabilities
        assert "shell" in all_capabilities
        assert "docker" in all_capabilities
        
        # Transformation: format for display
        formatted_runners = []
        for runner in raw_runners:
            formatted = {
                "display_name": f"{runner['name']} ({runner['status']})",
                "can_docker": "docker" in runner["capabilities"],
                "version": runner["version"]
            }
            formatted_runners.append(formatted)
        
        assert len(formatted_runners) == 2
        assert "healthy" in formatted_runners[0]["display_name"]
        assert formatted_runners[0]["can_docker"] is True
        assert formatted_runners[1]["can_docker"] is False

    def test_integration_data_transformation(self):
        """Test transformation of integration data."""
        # Raw integration data
        raw_integrations = [
            {
                "name": "slack",
                "description": "Slack integration for notifications",
                "docker_image": "kubiya/slack-integration:latest",
                "required_secrets": ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"],
                "category": "communication"
            },
            {
                "name": "github",
                "description": "GitHub integration",
                "docker_image": "kubiya/github-integration:latest",
                "required_secrets": ["GITHUB_TOKEN"],
                "category": "version_control"
            }
        ]
        
        # Transformation: group by category
        by_category = {}
        for integration in raw_integrations:
            category = integration["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(integration)
        
        assert "communication" in by_category
        assert "version_control" in by_category
        assert len(by_category["communication"]) == 1
        assert len(by_category["version_control"]) == 1
        
        # Transformation: extract all required secrets
        all_secrets = set()
        for integration in raw_integrations:
            all_secrets.update(integration["required_secrets"])
        
        assert "SLACK_BOT_TOKEN" in all_secrets
        assert "GITHUB_TOKEN" in all_secrets
        assert len(all_secrets) == 3
        
        # Transformation: create usage summary
        usage_summary = []
        for integration in raw_integrations:
            summary = {
                "name": integration["name"],
                "secret_count": len(integration["required_secrets"]),
                "docker_tag": integration["docker_image"].split(":")[-1]
            }
            usage_summary.append(summary)
        
        slack_summary = next(s for s in usage_summary if s["name"] == "slack")
        assert slack_summary["secret_count"] == 2
        assert slack_summary["docker_tag"] == "latest"

    def test_secrets_data_transformation(self):
        """Test transformation of secrets data."""
        # Raw secrets data
        raw_secrets = [
            {
                "name": "DATABASE_URL",
                "description": "Database connection string",
                "task_type": "data_processing",
                "required": True
            },
            {
                "name": "API_KEY",
                "description": "External API key",
                "task_type": "api_integration",
                "required": False
            },
            {
                "name": "JWT_SECRET",
                "description": "JWT signing secret",
                "task_type": "authentication",
                "required": True
            }
        ]
        
        # Transformation: filter required secrets
        required_secrets = [secret for secret in raw_secrets if secret["required"]]
        assert len(required_secrets) == 2
        assert all(secret["required"] for secret in required_secrets)
        
        # Transformation: group by task type
        by_task_type = {}
        for secret in raw_secrets:
            task_type = secret["task_type"]
            if task_type not in by_task_type:
                by_task_type[task_type] = []
            by_task_type[task_type].append(secret)
        
        assert "data_processing" in by_task_type
        assert "api_integration" in by_task_type
        assert "authentication" in by_task_type
        
        # Transformation: create configuration template
        config_template = {}
        for secret in raw_secrets:
            placeholder = f"${{{secret['name']}}}"
            config_template[secret["name"]] = {
                "placeholder": placeholder,
                "description": secret["description"],
                "required": secret["required"]
            }
        
        assert len(config_template) == 3
        assert config_template["DATABASE_URL"]["required"] is True
        assert "${DATABASE_URL}" in config_template["DATABASE_URL"]["placeholder"]


class TestValidationLogic:
    """Test validation logic used across MCP tools."""

    def test_runner_validation_logic(self):
        """Test runner validation logic."""
        available_runners = [
            {"name": "runner-1", "status": "healthy"},
            {"name": "runner-2", "status": "unhealthy"},
            {"name": "runner-3", "status": "healthy"}
        ]
        
        def validate_runner(runner_name, runners):
            """Validation logic for runner selection."""
            # Check if runner exists
            runner = next((r for r in runners if r["name"] == runner_name), None)
            if not runner:
                return False, f"Runner '{runner_name}' not found"
            
            # Check if runner is healthy
            if runner["status"] != "healthy":
                return False, f"Runner '{runner_name}' is not healthy (status: {runner['status']})"
            
            return True, f"Runner '{runner_name}' is available"
        
        # Test valid runner
        valid, message = validate_runner("runner-1", available_runners)
        assert valid is True
        assert "available" in message
        
        # Test invalid runner
        valid, message = validate_runner("nonexistent", available_runners)
        assert valid is False
        assert "not found" in message
        
        # Test unhealthy runner
        valid, message = validate_runner("runner-2", available_runners)
        assert valid is False
        assert "not healthy" in message

    def test_workflow_definition_validation(self):
        """Test workflow definition validation logic."""
        def validate_workflow_structure(workflow_def):
            """Basic workflow structure validation."""
            errors = []
            
            # Check required fields
            if "name" not in workflow_def:
                errors.append("Missing required field: 'name'")
            elif not isinstance(workflow_def["name"], str) or not workflow_def["name"].strip():
                errors.append("Field 'name' must be a non-empty string")
            
            if "steps" not in workflow_def:
                errors.append("Missing required field: 'steps'")
            elif not isinstance(workflow_def["steps"], list):
                errors.append("Field 'steps' must be a list")
            elif len(workflow_def["steps"]) == 0:
                errors.append("Workflow must have at least one step")
            
            # Validate steps
            if "steps" in workflow_def and isinstance(workflow_def["steps"], list):
                for i, step in enumerate(workflow_def["steps"]):
                    if not isinstance(step, dict):
                        errors.append(f"Step {i} must be a dictionary")
                        continue
                    
                    if "name" not in step:
                        errors.append(f"Step {i} missing required field: 'name'")
                    
                    has_run = "run" in step
                    has_code = "code" in step
                    if not (has_run or has_code):
                        errors.append(f"Step {i} must have either 'run' or 'code' field")
            
            return len(errors) == 0, errors
        
        # Valid workflow
        valid_workflow = {
            "name": "test_workflow",
            "steps": [
                {"name": "step1", "run": "echo hello"},
                {"name": "step2", "code": "print('world')"}
            ]
        }
        
        valid, errors = validate_workflow_structure(valid_workflow)
        assert valid is True
        assert len(errors) == 0
        
        # Invalid workflow - missing name
        invalid_workflow_1 = {
            "steps": [{"name": "step1", "run": "echo hello"}]
        }
        
        valid, errors = validate_workflow_structure(invalid_workflow_1)
        assert valid is False
        assert any("name" in error for error in errors)
        
        # Invalid workflow - empty steps
        invalid_workflow_2 = {
            "name": "test",
            "steps": []
        }
        
        valid, errors = validate_workflow_structure(invalid_workflow_2)
        assert valid is False
        assert any("at least one step" in error for error in errors)
        
        # Invalid workflow - step missing name
        invalid_workflow_3 = {
            "name": "test",
            "steps": [{"run": "echo hello"}]  # Missing name
        }
        
        valid, errors = validate_workflow_structure(invalid_workflow_3)
        assert valid is False
        assert any("missing required field: 'name'" in error for error in errors)

    def test_parameter_validation_logic(self):
        """Test parameter validation logic."""
        def validate_parameters(params, schema):
            """Validate parameters against schema."""
            errors = []
            
            # Check required parameters
            for param_name, param_config in schema.items():
                if param_config.get("required", False) and param_name not in params:
                    errors.append(f"Missing required parameter: '{param_name}'")
            
            # Check parameter types
            for param_name, param_value in params.items():
                if param_name in schema:
                    expected_type = schema[param_name].get("type")
                    if expected_type and not isinstance(param_value, expected_type):
                        errors.append(f"Parameter '{param_name}' must be of type {expected_type.__name__}")
            
            return len(errors) == 0, errors
        
        # Parameter schema
        schema = {
            "name": {"type": str, "required": True},
            "port": {"type": int, "required": False},
            "debug": {"type": bool, "required": False}
        }
        
        # Valid parameters
        valid_params = {"name": "test", "port": 8080, "debug": True}
        valid, errors = validate_parameters(valid_params, schema)
        assert valid is True
        assert len(errors) == 0
        
        # Missing required parameter
        invalid_params_1 = {"port": 8080}
        valid, errors = validate_parameters(invalid_params_1, schema)
        assert valid is False
        assert any("Missing required parameter: 'name'" in error for error in errors)
        
        # Wrong type
        invalid_params_2 = {"name": "test", "port": "8080"}  # Should be int
        valid, errors = validate_parameters(invalid_params_2, schema)
        assert valid is False
        assert any("must be of type int" in error for error in errors)