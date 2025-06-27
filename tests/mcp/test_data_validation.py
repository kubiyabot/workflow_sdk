"""Validation tests for comprehensive test data sets.

This module validates that all test data is properly structured and contains
the expected fields and formats for functional correctness testing.
"""

import pytest
import yaml
import json
from typing import Dict, Any, List

from tests.mcp.test_data import (
    WorkflowTestData,
    ParameterTestData,
    ResponseTestData,
    IntegrationTestData,
    BoundaryTestData
)


class TestDataValidation:
    """Validate test data structure and content."""

    def test_simple_workflows_structure(self):
        """Test that simple workflows have required structure."""
        for name, workflow in WorkflowTestData.SIMPLE_WORKFLOWS.items():
            # Check required fields
            assert "dsl" in workflow, f"Simple workflow '{name}' missing 'dsl' field"
            assert "expected_output" in workflow, f"Simple workflow '{name}' missing 'expected_output' field"
            assert "docker_required" in workflow, f"Simple workflow '{name}' missing 'docker_required' field"
            
            # Validate DSL is valid YAML
            try:
                yaml.safe_load(workflow["dsl"])
            except yaml.YAMLError as e:
                pytest.fail(f"Simple workflow '{name}' has invalid YAML DSL: {e}")
            
            # Check DSL contains name and steps
            dsl_data = yaml.safe_load(workflow["dsl"])
            assert "name" in dsl_data, f"Simple workflow '{name}' DSL missing 'name' field"
            assert "steps" in dsl_data, f"Simple workflow '{name}' DSL missing 'steps' field"
            assert isinstance(dsl_data["steps"], list), f"Simple workflow '{name}' steps must be a list"
            assert len(dsl_data["steps"]) > 0, f"Simple workflow '{name}' must have at least one step"

    def test_complex_workflows_structure(self):
        """Test that complex workflows have required structure."""
        for name, workflow in WorkflowTestData.COMPLEX_WORKFLOWS.items():
            # Check required fields
            assert "dsl" in workflow, f"Complex workflow '{name}' missing 'dsl' field"
            assert "expected_output" in workflow, f"Complex workflow '{name}' missing 'expected_output' field"
            assert "docker_required" in workflow, f"Complex workflow '{name}' missing 'docker_required' field"
            
            # Validate DSL is valid YAML
            try:
                dsl_data = yaml.safe_load(workflow["dsl"])
            except yaml.YAMLError as e:
                pytest.fail(f"Complex workflow '{name}' has invalid YAML DSL: {e}")
            
            # Check complex workflow has multiple steps
            assert len(dsl_data["steps"]) >= 2, f"Complex workflow '{name}' should have multiple steps"
            
            # Check for dependencies in complex workflows
            has_dependencies = any("depends_on" in step for step in dsl_data["steps"])
            assert has_dependencies, f"Complex workflow '{name}' should have step dependencies"

    def test_docker_workflows_structure(self):
        """Test that Docker workflows have required structure."""
        for name, workflow in WorkflowTestData.DOCKER_WORKFLOWS.items():
            # Check required fields
            assert "dsl" in workflow, f"Docker workflow '{name}' missing 'dsl' field"
            assert "expected_output" in workflow, f"Docker workflow '{name}' missing 'expected_output' field"
            assert "docker_required" in workflow, f"Docker workflow '{name}' missing 'docker_required' field"
            assert "required_packages" in workflow, f"Docker workflow '{name}' missing 'required_packages' field"
            
            # Docker workflows should require Docker
            assert workflow["docker_required"] is True, f"Docker workflow '{name}' should require Docker"
            
            # Should have required packages list
            assert isinstance(workflow["required_packages"], list), f"Docker workflow '{name}' required_packages must be a list"
            assert len(workflow["required_packages"]) > 0, f"Docker workflow '{name}' should specify required packages"

    def test_error_workflows_structure(self):
        """Test that error workflows have required structure."""
        for name, workflow in WorkflowTestData.ERROR_WORKFLOWS.items():
            # Check required fields
            assert "dsl" in workflow, f"Error workflow '{name}' missing 'dsl' field"
            assert "expected_error" in workflow, f"Error workflow '{name}' missing 'expected_error' field"
            assert "error_type" in workflow, f"Error workflow '{name}' missing 'error_type' field"
            
            # Check error type is valid
            valid_error_types = ["compilation", "execution", "timeout", "authentication"]
            assert workflow["error_type"] in valid_error_types, f"Error workflow '{name}' has invalid error_type"

    def test_parameter_data_structure(self):
        """Test that parameter test data has required structure."""
        # Check valid parameters
        assert "compile_workflow" in ParameterTestData.VALID_PARAMETERS
        assert "execute_workflow" in ParameterTestData.VALID_PARAMETERS
        assert "get_workflow_runners" in ParameterTestData.VALID_PARAMETERS
        assert "get_integrations" in ParameterTestData.VALID_PARAMETERS
        assert "get_workflow_secrets" in ParameterTestData.VALID_PARAMETERS
        
        # Each tool should have parameter combinations
        for tool_name, params_list in ParameterTestData.VALID_PARAMETERS.items():
            assert isinstance(params_list, list), f"Valid parameters for '{tool_name}' must be a list"
            assert len(params_list) > 0, f"Valid parameters for '{tool_name}' must not be empty"
            
            # Each parameter combination should be a dict
            for i, params in enumerate(params_list):
                assert isinstance(params, dict), f"Parameter combination {i} for '{tool_name}' must be a dict"

    def test_edge_case_parameters_structure(self):
        """Test that edge case parameters have required structure."""
        edge_cases = ParameterTestData.EDGE_CASE_PARAMETERS
        
        # Check required edge case categories
        assert "empty_values" in edge_cases
        assert "large_values" in edge_cases  
        assert "special_characters" in edge_cases
        
        # Each category should have tool-specific data
        for category_name, category_data in edge_cases.items():
            assert isinstance(category_data, dict), f"Edge case category '{category_name}' must be a dict"

    def test_response_data_structure(self):
        """Test that response test data has required structure."""
        # Check success responses
        success = ResponseTestData.SUCCESS_RESPONSES
        required_tools = ["compile_workflow", "execute_workflow", "get_workflow_runners", 
                         "get_integrations", "get_workflow_secrets"]
        
        for tool in required_tools:
            assert tool in success, f"Success responses missing '{tool}'"
            assert isinstance(success[tool], dict), f"Success response for '{tool}' must be a dict"
        
        # Check error responses
        errors = ResponseTestData.ERROR_RESPONSES
        required_errors = ["authentication_error", "validation_error", "execution_error", "timeout_error"]
        
        for error_type in required_errors:
            assert error_type in errors, f"Error responses missing '{error_type}'"
            assert isinstance(errors[error_type], dict), f"Error response for '{error_type}' must be a dict"

    def test_integration_scenarios_structure(self):
        """Test that integration test scenarios have required structure."""
        scenarios = IntegrationTestData.INTEGRATION_SCENARIOS
        
        # Check compile_and_execute scenario
        assert "compile_and_execute" in scenarios
        scenario = scenarios["compile_and_execute"]
        assert "compile_params" in scenario
        assert "execute_params" in scenario
        assert "expected_flow" in scenario
        
        # Check full_pipeline scenario
        assert "full_pipeline" in scenarios
        pipeline = scenarios["full_pipeline"]
        assert "steps" in pipeline
        assert isinstance(pipeline["steps"], list)
        assert len(pipeline["steps"]) > 0

    def test_boundary_test_data_structure(self):
        """Test that boundary test data has required structure."""
        # Check resource limits
        limits = BoundaryTestData.RESOURCE_LIMITS
        assert "max_workflow_size" in limits
        assert "max_parameter_length" in limits
        assert "concurrent_executions" in limits
        
        # Check time scenarios
        time_scenarios = BoundaryTestData.TIME_SCENARIOS
        assert "long_running_workflow" in time_scenarios
        assert "quick_workflow" in time_scenarios
        
        for scenario_name, scenario_data in time_scenarios.items():
            assert "dsl" in scenario_data, f"Time scenario '{scenario_name}' missing 'dsl'"
            assert "expected_duration" in scenario_data, f"Time scenario '{scenario_name}' missing 'expected_duration'"
            assert "timeout_threshold" in scenario_data, f"Time scenario '{scenario_name}' missing 'timeout_threshold'"

    def test_workflow_dsl_syntax_validity(self):
        """Test that all workflow DSL strings are valid YAML."""
        all_workflows = {
            **WorkflowTestData.SIMPLE_WORKFLOWS,
            **WorkflowTestData.COMPLEX_WORKFLOWS,
            **WorkflowTestData.DOCKER_WORKFLOWS
        }
        
        for name, workflow in all_workflows.items():
            try:
                parsed_dsl = yaml.safe_load(workflow["dsl"])
                
                # Basic structure validation
                assert "name" in parsed_dsl, f"Workflow '{name}' DSL missing 'name'"
                assert "steps" in parsed_dsl, f"Workflow '{name}' DSL missing 'steps'"
                assert isinstance(parsed_dsl["steps"], list), f"Workflow '{name}' steps must be a list"
                
                # Step validation
                for i, step in enumerate(parsed_dsl["steps"]):
                    assert "name" in step, f"Workflow '{name}' step {i} missing 'name'"
                    assert isinstance(step["name"], str), f"Workflow '{name}' step {i} name must be string"
                    
                    # Step must have either 'run' or 'code' field
                    has_run = "run" in step
                    has_code = "code" in step
                    assert has_run or has_code, f"Workflow '{name}' step {i} must have 'run' or 'code'"
                    
            except yaml.YAMLError as e:
                pytest.fail(f"Workflow '{name}' has invalid YAML syntax: {e}")
            except Exception as e:
                pytest.fail(f"Workflow '{name}' validation failed: {e}")

    def test_parameter_json_serializable(self):
        """Test that all parameter data is JSON serializable."""
        try:
            # Test valid parameters
            json.dumps(ParameterTestData.VALID_PARAMETERS)
            
            # Test edge case parameters
            json.dumps(ParameterTestData.EDGE_CASE_PARAMETERS)
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"Parameter data is not JSON serializable: {e}")

    def test_response_data_completeness(self):
        """Test that response data covers all expected scenarios."""
        success_responses = ResponseTestData.SUCCESS_RESPONSES
        error_responses = ResponseTestData.ERROR_RESPONSES
        
        # Success responses should have status indicators
        for tool, response in success_responses.items():
            if tool in ["compile_workflow", "execute_workflow"]:
                assert "status" in response, f"Success response for '{tool}' missing 'status'"
            
            if tool == "get_workflow_runners":
                assert "runners" in response, f"Success response for '{tool}' missing 'runners'"
                assert isinstance(response["runners"], list), f"Runners must be a list"
            
            if tool == "get_integrations":
                assert "integrations" in response, f"Success response for '{tool}' missing 'integrations'"
                assert isinstance(response["integrations"], list), f"Integrations must be a list"
            
            if tool == "get_workflow_secrets":
                assert "secrets" in response, f"Success response for '{tool}' missing 'secrets'"
                assert isinstance(response["secrets"], list), f"Secrets must be a list"
        
        # Error responses should have error information
        for error_type, response in error_responses.items():
            assert "error" in response or "status" in response, f"Error response '{error_type}' missing error info"

    def test_test_data_consistency(self):
        """Test that test data is internally consistent."""
        # Check that workflow names in DSL match dictionary keys where applicable
        for category_name, workflows in [
            ("simple", WorkflowTestData.SIMPLE_WORKFLOWS),
            ("complex", WorkflowTestData.COMPLEX_WORKFLOWS),
            ("docker", WorkflowTestData.DOCKER_WORKFLOWS)
        ]:
            for key, workflow in workflows.items():
                try:
                    dsl_data = yaml.safe_load(workflow["dsl"])
                    dsl_name = dsl_data.get("name", "")
                    
                    # Names don't have to match exactly, but should be related
                    # This is more of a documentation check
                    assert len(dsl_name) > 0, f"{category_name} workflow '{key}' has empty name in DSL"
                    
                except yaml.YAMLError:
                    # Skip YAML validation here, covered in other tests
                    pass

    def test_boundary_conditions_realistic(self):
        """Test that boundary conditions are realistic and testable."""
        limits = BoundaryTestData.RESOURCE_LIMITS
        time_scenarios = BoundaryTestData.TIME_SCENARIOS
        
        # Check max workflow size is reasonable (not too large for testing)
        max_workflow = limits["max_workflow_size"]
        dsl_length = len(max_workflow["dsl_code"])
        assert 1000 < dsl_length < 1000000, "Max workflow size should be reasonable for testing"
        
        # Check max parameter length is reasonable
        max_param = limits["max_parameter_length"]
        param_length = len(max_param["params"]["LARGE_PARAM"])
        assert 10000 < param_length < 10000000, "Max parameter length should be reasonable for testing"
        
        # Check time scenarios have reasonable durations
        for scenario_name, scenario in time_scenarios.items():
            duration = scenario["expected_duration"]
            threshold = scenario["timeout_threshold"]
            
            assert 0 <= duration <= 30, f"Time scenario '{scenario_name}' duration should be reasonable for testing"
            assert duration < threshold, f"Time scenario '{scenario_name}' timeout should be greater than expected duration"