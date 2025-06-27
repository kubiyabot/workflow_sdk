"""Unit tests for specific MCP tool function components.

This module tests isolated components of MCP tool functions with proper mocking
to avoid external dependencies.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional

from tests.mcp.mocks import MockWorkflowAPIClient
from tests.mcp.test_data import WorkflowTestData, ParameterTestData


class TestCompileWorkflowComponents:
    """Test isolated components of compile_workflow function."""

    def test_dsl_code_execution_namespace_setup(self):
        """Test execution namespace setup for DSL code."""
        from kubiya_workflow_sdk.dsl import Workflow
        
        # Create execution namespace like the tool does
        exec_globals = {
            "Workflow": Workflow,
            "__builtins__": __builtins__,
        }
        
        # Verify namespace contains required components
        assert "Workflow" in exec_globals
        assert exec_globals["Workflow"] == Workflow
        assert "__builtins__" in exec_globals
        
        # Test executing simple DSL code
        simple_dsl = """
wf = Workflow("test")
wf.description("Test workflow")
"""
        
        try:
            exec(simple_dsl, exec_globals)
            # Should have created workflow object
            assert "wf" in exec_globals
            assert isinstance(exec_globals["wf"], Workflow)
        except Exception as e:
            pytest.fail(f"DSL execution failed: {e}")

    def test_workflow_object_discovery(self):
        """Test workflow object discovery logic."""
        from kubiya_workflow_sdk.dsl import Workflow
        
        # Mock execution namespace with workflow
        exec_globals = {
            "Workflow": Workflow,
            "wf": Workflow("test-workflow"),
            "other_var": "value",
            "number": 123
        }
        
        # Find workflow object (simulating tool logic)
        workflow_obj = None
        for var_name, var_value in exec_globals.items():
            if isinstance(var_value, Workflow):
                workflow_obj = var_value
                break
        
        assert workflow_obj is not None
        assert isinstance(workflow_obj, Workflow)
        
        # Test namespace without workflow
        exec_globals_no_wf = {
            "Workflow": Workflow,
            "some_var": "value",
            "number": 123
        }
        
        workflow_obj = None
        for var_name, var_value in exec_globals_no_wf.items():
            if isinstance(var_value, Workflow):
                workflow_obj = var_value
                break
        
        assert workflow_obj is None

    def test_provide_missing_secrets_parsing(self):
        """Test provide_missing_secrets JSON parsing logic."""
        # Test valid JSON string
        json_string = '{"SECRET_KEY": "value", "API_TOKEN": "token123"}'
        try:
            parsed = json.loads(json_string)
            assert isinstance(parsed, dict)
            assert parsed["SECRET_KEY"] == "value"
            assert parsed["API_TOKEN"] == "token123"
        except json.JSONDecodeError as e:
            pytest.fail(f"Should parse valid JSON: {e}")
        
        # Test invalid JSON string
        invalid_json = '{"invalid": }'
        try:
            json.loads(invalid_json)
            pytest.fail("Should raise JSONDecodeError for invalid JSON")
        except json.JSONDecodeError:
            pass  # Expected
        
        # Test already parsed dict (should pass through)
        dict_secrets = {"SECRET_KEY": "value"}
        if isinstance(dict_secrets, dict):
            # No parsing needed
            assert dict_secrets["SECRET_KEY"] == "value"

    def test_docker_conversion_logic(self):
        """Test logic for converting steps to Docker when prefer_docker=True."""
        # Sample workflow definition
        workflow_def = {
            "name": "test_workflow",
            "steps": [
                {
                    "name": "python_step",
                    "type": "python",
                    "code": "import pandas; print('data processing')"
                },
                {
                    "name": "simple_step", 
                    "run": "echo 'hello'"
                }
            ]
        }
        
        # Mock Docker conversion logic
        def should_convert_to_docker(step):
            """Determine if step should be converted to Docker."""
            # Python steps with imports should use Docker
            if step.get("type") == "python" and step.get("code"):
                return "import " in step["code"]
            # Complex shell commands might need Docker
            if step.get("run"):
                complex_indicators = ["pip install", "apt-get", "yum install"]
                return any(indicator in step["run"] for indicator in complex_indicators)
            return False
        
        def convert_step_to_docker(step):
            """Convert step to Docker format."""
            if step.get("type") == "python":
                return {
                    "name": step["name"],
                    "docker": {
                        "image": "python:3.11-slim",
                        "code": step["code"]
                    }
                }
            return step
        
        # Test conversion logic
        converted_steps = []
        for step in workflow_def["steps"]:
            if should_convert_to_docker(step):
                converted_steps.append(convert_step_to_docker(step))
            else:
                converted_steps.append(step)
        
        # Python step should be converted
        assert len(converted_steps) == 2
        assert "docker" in converted_steps[0]
        assert converted_steps[0]["docker"]["image"] == "python:3.11-slim"
        
        # Simple step should remain unchanged
        assert "run" in converted_steps[1]
        assert "docker" not in converted_steps[1]

    def test_runner_validation_component(self):
        """Test runner validation component logic."""
        # Mock available runners
        available_runners = [
            {"name": "runner1", "status": "healthy", "capabilities": ["python"]},
            {"name": "runner2", "status": "unhealthy", "capabilities": ["shell"]},
            {"name": "runner3", "status": "healthy", "capabilities": ["docker"]}
        ]
        
        def validate_runner(runner_name, runners):
            """Validate runner availability and health."""
            runner = next((r for r in runners if r["name"] == runner_name), None)
            if not runner:
                return False, f"Runner '{runner_name}' not found"
            
            if runner["status"] != "healthy":
                return False, f"Runner '{runner_name}' is not healthy"
            
            return True, f"Runner '{runner_name}' is available"
        
        # Test valid runner
        valid, message = validate_runner("runner1", available_runners)
        assert valid is True
        assert "available" in message
        
        # Test invalid runner
        valid, message = validate_runner("nonexistent", available_runners)
        assert valid is False
        assert "not found" in message
        
        # Test unhealthy runner
        valid, message = validate_runner("runner2", available_runners)
        assert valid is False
        assert "not healthy" in message


class TestExecuteWorkflowComponents:
    """Test isolated components of execute_workflow function."""

    def test_workflow_input_type_detection(self):
        """Test logic for detecting workflow input type."""
        # String input (DSL)
        string_input = """
name: test_workflow
steps:
  - name: step1
    run: echo "test"
"""
        assert isinstance(string_input, str)
        
        # Dict input (parsed workflow)
        dict_input = {
            "name": "test_workflow",
            "steps": [{"name": "step1", "run": "echo 'test'"}]
        }
        assert isinstance(dict_input, dict)
        
        # Function to determine input type
        def get_workflow_input_type(workflow_input):
            if isinstance(workflow_input, str):
                return "dsl_string"
            elif isinstance(workflow_input, dict):
                return "workflow_dict"
            else:
                return "unknown"
        
        assert get_workflow_input_type(string_input) == "dsl_string"
        assert get_workflow_input_type(dict_input) == "workflow_dict"
        assert get_workflow_input_type(123) == "unknown"

    def test_parameter_merging_logic(self):
        """Test parameter merging and processing logic."""
        # Base parameters from workflow
        base_params = {"DEFAULT_ENV": "production", "TIMEOUT": 30}
        
        # User-provided parameters
        user_params_dict = {"ENV": "test", "TIMEOUT": 60, "DEBUG": True}
        user_params_json = '{"ENV": "test", "TIMEOUT": 60, "DEBUG": true}'
        
        # Merge logic (user params override base params)
        def merge_parameters(base, user_input):
            """Merge user parameters with base parameters."""
            merged = base.copy()
            
            if isinstance(user_input, str):
                try:
                    user_params = json.loads(user_input)
                except json.JSONDecodeError:
                    return merged, ["Invalid JSON in parameters"]
            elif isinstance(user_input, dict):
                user_params = user_input
            else:
                return merged, ["Parameters must be dict or JSON string"]
            
            merged.update(user_params)
            return merged, []
        
        # Test with dict parameters
        merged_dict, errors = merge_parameters(base_params, user_params_dict)
        assert len(errors) == 0
        assert merged_dict["ENV"] == "test"  # User override
        assert merged_dict["TIMEOUT"] == 60  # User override
        assert merged_dict["DEBUG"] is True  # User addition
        assert merged_dict["DEFAULT_ENV"] == "production"  # Base preserved
        
        # Test with JSON string parameters
        merged_json, errors = merge_parameters(base_params, user_params_json)
        assert len(errors) == 0
        assert merged_json["ENV"] == "test"
        assert merged_json["DEBUG"] is True
        
        # Test with invalid JSON
        invalid_json = '{"invalid": }'
        merged_invalid, errors = merge_parameters(base_params, invalid_json)
        assert len(errors) > 0
        assert "Invalid JSON" in errors[0]

    def test_execution_result_formatting(self):
        """Test execution result formatting logic."""
        # Mock execution result from client
        raw_result = {
            "id": "exec-123",
            "state": "completed",
            "exit_code": 0,
            "stdout": "Hello World\n",
            "stderr": "",
            "logs": ["Starting execution", "Running step 1", "Completed successfully"],
            "duration": 2.5,
            "metadata": {"runner": "test-runner", "image": "python:3.11"}
        }
        
        # Format for MCP response
        def format_execution_result(result):
            """Format execution result for MCP response."""
            formatted = {
                "execution_id": result["id"],
                "status": result["state"],
                "exit_code": result["exit_code"],
                "output": result["stdout"].strip() if result["stdout"] else "",
                "logs": result["logs"],
                "duration": result["duration"]
            }
            
            # Add error info if failed
            if result["exit_code"] != 0:
                formatted["error"] = result["stderr"] or "Execution failed"
            
            # Add metadata
            if "metadata" in result:
                formatted["runner"] = result["metadata"].get("runner")
                formatted["image"] = result["metadata"].get("image")
            
            return formatted
        
        formatted = format_execution_result(raw_result)
        assert formatted["execution_id"] == "exec-123"
        assert formatted["status"] == "completed"
        assert formatted["exit_code"] == 0
        assert formatted["output"] == "Hello World"
        assert len(formatted["logs"]) == 3
        assert formatted["duration"] == 2.5
        assert formatted["runner"] == "test-runner"
        
        # Test failed execution
        failed_result = {
            "id": "exec-456",
            "state": "failed",
            "exit_code": 1,
            "stdout": "",
            "stderr": "Command not found",
            "logs": ["Starting execution", "Error occurred"],
            "duration": 0.5
        }
        
        formatted_failed = format_execution_result(failed_result)
        assert formatted_failed["status"] == "failed"
        assert formatted_failed["exit_code"] == 1
        assert formatted_failed["error"] == "Command not found"


class TestDataRetrievalComponents:
    """Test components of data retrieval tools (runners, integrations, secrets)."""

    def test_runner_filtering_logic(self):
        """Test runner filtering and processing logic."""
        # Mock runner data
        raw_runners = [
            {"id": "r1", "name": "Runner 1", "status": "healthy", "capabilities": ["python", "docker"]},
            {"id": "r2", "name": "Runner 2", "status": "unhealthy", "capabilities": ["shell"]},
            {"id": "r3", "name": "Runner 3", "status": "healthy", "capabilities": ["python", "shell", "docker"]},
            {"id": "r4", "name": "Runner 4", "status": "maintenance", "capabilities": ["python"]}
        ]
        
        # Filter functions
        def filter_healthy_runners(runners):
            return [r for r in runners if r["status"] == "healthy"]
        
        def filter_docker_capable_runners(runners):
            return [r for r in runners if "docker" in r["capabilities"]]
        
        def get_runner_summary(runners):
            return {
                "total": len(runners),
                "healthy": len([r for r in runners if r["status"] == "healthy"]),
                "docker_capable": len([r for r in runners if "docker" in r["capabilities"]])
            }
        
        # Test filtering
        healthy = filter_healthy_runners(raw_runners)
        assert len(healthy) == 2
        assert all(r["status"] == "healthy" for r in healthy)
        
        docker_capable = filter_docker_capable_runners(raw_runners)
        assert len(docker_capable) == 2
        assert all("docker" in r["capabilities"] for r in docker_capable)
        
        summary = get_runner_summary(raw_runners)
        assert summary["total"] == 4
        assert summary["healthy"] == 2
        assert summary["docker_capable"] == 2

    def test_integration_categorization_logic(self):
        """Test integration categorization and filtering logic."""
        # Mock integration data
        raw_integrations = [
            {"name": "slack", "category": "communication", "secrets": ["SLACK_TOKEN"]},
            {"name": "github", "category": "version_control", "secrets": ["GITHUB_TOKEN"]},
            {"name": "jira", "category": "project_management", "secrets": ["JIRA_URL", "JIRA_TOKEN"]},
            {"name": "discord", "category": "communication", "secrets": ["DISCORD_TOKEN"]},
            {"name": "postgres", "category": "database", "secrets": ["DB_URL", "DB_PASSWORD"]}
        ]
        
        # Categorization functions
        def group_by_category(integrations):
            groups = {}
            for integration in integrations:
                category = integration["category"]
                if category not in groups:
                    groups[category] = []
                groups[category].append(integration)
            return groups
        
        def filter_by_category(integrations, category):
            return [i for i in integrations if i["category"] == category]
        
        def get_integration_stats(integrations):
            stats = {
                "total_integrations": len(integrations),
                "categories": {},
                "total_secrets": 0
            }
            
            for integration in integrations:
                category = integration["category"]
                stats["categories"][category] = stats["categories"].get(category, 0) + 1
                stats["total_secrets"] += len(integration["secrets"])
            
            return stats
        
        # Test categorization
        grouped = group_by_category(raw_integrations)
        assert "communication" in grouped
        assert len(grouped["communication"]) == 2
        assert len(grouped["version_control"]) == 1
        
        comm_integrations = filter_by_category(raw_integrations, "communication")
        assert len(comm_integrations) == 2
        assert all(i["category"] == "communication" for i in comm_integrations)
        
        stats = get_integration_stats(raw_integrations)
        assert stats["total_integrations"] == 5
        assert stats["categories"]["communication"] == 2
        assert stats["total_secrets"] == 7  # Sum of all secret counts

    def test_secrets_filtering_logic(self):
        """Test secrets filtering and organization logic."""
        # Mock secrets data
        raw_secrets = [
            {"name": "DB_URL", "task_type": "database", "required": True, "pattern": "DB_*"},
            {"name": "DB_PASSWORD", "task_type": "database", "required": True, "pattern": "DB_*"},
            {"name": "API_KEY", "task_type": "external_api", "required": False, "pattern": "API_*"},
            {"name": "JWT_SECRET", "task_type": "authentication", "required": True, "pattern": "*_SECRET"},
            {"name": "SLACK_TOKEN", "task_type": "notification", "required": False, "pattern": "*_TOKEN"}
        ]
        
        # Filtering functions
        def filter_by_pattern(secrets, pattern):
            if not pattern:
                return secrets
            
            import fnmatch
            return [s for s in secrets if fnmatch.fnmatch(s["name"], pattern)]
        
        def filter_by_task_type(secrets, task_type):
            if not task_type:
                return secrets
            return [s for s in secrets if s["task_type"] == task_type]
        
        def filter_required_secrets(secrets):
            return [s for s in secrets if s["required"]]
        
        def organize_secrets_by_type(secrets):
            organized = {}
            for secret in secrets:
                task_type = secret["task_type"]
                if task_type not in organized:
                    organized[task_type] = []
                organized[task_type].append(secret)
            return organized
        
        # Test filtering
        db_secrets = filter_by_pattern(raw_secrets, "DB_*")
        assert len(db_secrets) == 2
        assert all(s["name"].startswith("DB_") for s in db_secrets)
        
        database_secrets = filter_by_task_type(raw_secrets, "database")
        assert len(database_secrets) == 2
        assert all(s["task_type"] == "database" for s in database_secrets)
        
        required = filter_required_secrets(raw_secrets)
        assert len(required) == 3
        assert all(s["required"] for s in required)
        
        organized = organize_secrets_by_type(raw_secrets)
        assert "database" in organized
        assert "authentication" in organized
        assert len(organized["database"]) == 2


class TestErrorHandlingComponents:
    """Test error handling components across MCP tools."""

    def test_compilation_error_handling(self):
        """Test compilation error handling logic."""
        def handle_dsl_execution_error(error):
            """Handle DSL execution errors."""
            error_type = type(error).__name__
            error_msg = str(error)
            
            if error_type == "SyntaxError":
                return {
                    "error_type": "syntax_error",
                    "message": "Invalid Python syntax in DSL code",
                    "suggestion": "Check DSL syntax and ensure proper indentation"
                }
            elif error_type == "NameError":
                return {
                    "error_type": "name_error", 
                    "message": "Undefined variable or function in DSL",
                    "suggestion": "Ensure all imports and variable definitions are included"
                }
            elif error_type == "ImportError":
                return {
                    "error_type": "import_error",
                    "message": "Module import failed",
                    "suggestion": "Check that all required modules are available"
                }
            else:
                return {
                    "error_type": "execution_error",
                    "message": f"DSL execution failed: {error_msg}",
                    "suggestion": "Review DSL code for errors"
                }
        
        # Test different error types
        syntax_error = SyntaxError("invalid syntax")
        result = handle_dsl_execution_error(syntax_error)
        assert result["error_type"] == "syntax_error"
        assert "syntax" in result["message"].lower()
        
        name_error = NameError("name 'undefined_var' is not defined")
        result = handle_dsl_execution_error(name_error)
        assert result["error_type"] == "name_error"
        assert "variable" in result["message"].lower()

    def test_validation_error_aggregation(self):
        """Test validation error aggregation logic."""
        def collect_validation_errors(workflow_def):
            """Collect all validation errors for a workflow."""
            errors = []
            warnings = []
            
            # Name validation
            if not workflow_def.get("name"):
                errors.append("Workflow name is required")
            elif not isinstance(workflow_def["name"], str):
                errors.append("Workflow name must be a string")
            elif len(workflow_def["name"]) > 100:
                warnings.append("Workflow name is very long")
            
            # Steps validation
            if not workflow_def.get("steps"):
                errors.append("Workflow must have steps")
            elif not isinstance(workflow_def["steps"], list):
                errors.append("Steps must be a list")
            elif len(workflow_def["steps"]) == 0:
                errors.append("Workflow must have at least one step")
            else:
                for i, step in enumerate(workflow_def["steps"]):
                    if not step.get("name"):
                        errors.append(f"Step {i+1} missing name")
                    if not (step.get("run") or step.get("code") or step.get("docker")):
                        errors.append(f"Step {i+1} missing execution definition")
            
            return {"errors": errors, "warnings": warnings}
        
        # Test with valid workflow
        valid_workflow = {
            "name": "test",
            "steps": [{"name": "step1", "run": "echo test"}]
        }
        
        result = collect_validation_errors(valid_workflow)
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0
        
        # Test with invalid workflow
        invalid_workflow = {
            "steps": [{"run": "echo test"}]  # Missing name, step missing name
        }
        
        result = collect_validation_errors(invalid_workflow)
        assert len(result["errors"]) >= 2
        assert any("name is required" in error for error in result["errors"])
        assert any("Step 1 missing name" in error for error in result["errors"])

    def test_api_error_classification(self):
        """Test API error classification logic."""
        def classify_api_error(error):
            """Classify API errors for appropriate handling."""
            error_msg = str(error).lower()
            
            if "timeout" in error_msg or "timed out" in error_msg:
                return {
                    "type": "timeout",
                    "user_message": "Request timed out. Please try again.",
                    "retry_suggested": True
                }
            elif "unauthorized" in error_msg or "401" in error_msg:
                return {
                    "type": "authentication",
                    "user_message": "Authentication failed. Check your API key.",
                    "retry_suggested": False
                }
            elif "forbidden" in error_msg or "403" in error_msg:
                return {
                    "type": "authorization",
                    "user_message": "Access denied. Insufficient permissions.",
                    "retry_suggested": False
                }
            elif "not found" in error_msg or "404" in error_msg:
                return {
                    "type": "not_found",
                    "user_message": "Resource not found.",
                    "retry_suggested": False
                }
            elif "rate limit" in error_msg or "429" in error_msg:
                return {
                    "type": "rate_limit",
                    "user_message": "Rate limit exceeded. Please wait and try again.",
                    "retry_suggested": True
                }
            else:
                return {
                    "type": "unknown",
                    "user_message": f"API error: {error_msg}",
                    "retry_suggested": True
                }
        
        # Test different error classifications
        timeout_error = Exception("Request timed out after 30 seconds")
        result = classify_api_error(timeout_error)
        assert result["type"] == "timeout"
        assert result["retry_suggested"] is True
        
        auth_error = Exception("401 Unauthorized: Invalid API key")
        result = classify_api_error(auth_error)
        assert result["type"] == "authentication"
        assert result["retry_suggested"] is False
        
        rate_limit_error = Exception("429 Too Many Requests: Rate limit exceeded")
        result = classify_api_error(rate_limit_error)
        assert result["type"] == "rate_limit"
        assert result["retry_suggested"] is True