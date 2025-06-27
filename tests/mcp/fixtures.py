"""Test fixtures providing structured test data for MCP functional testing.

This module creates pytest fixtures from the test data sets to make them
easily available to test functions.
"""

import pytest
from typing import Dict, Any, List
from tests.mcp.test_data import (
    WorkflowTestData,
    ParameterTestData,
    ResponseTestData,
    IntegrationTestData,
    BoundaryTestData
)


# Workflow fixtures
@pytest.fixture
def simple_workflows():
    """Fixture providing simple workflow test data."""
    return WorkflowTestData.SIMPLE_WORKFLOWS


@pytest.fixture
def complex_workflows():
    """Fixture providing complex workflow test data."""
    return WorkflowTestData.COMPLEX_WORKFLOWS


@pytest.fixture
def docker_workflows():
    """Fixture providing Docker-required workflow test data."""
    return WorkflowTestData.DOCKER_WORKFLOWS


@pytest.fixture
def error_workflows():
    """Fixture providing error scenario workflow test data."""
    return WorkflowTestData.ERROR_WORKFLOWS


@pytest.fixture(params=list(WorkflowTestData.SIMPLE_WORKFLOWS.keys()))
def simple_workflow_case(request, simple_workflows):
    """Parametrized fixture providing individual simple workflow cases."""
    return simple_workflows[request.param]


@pytest.fixture(params=list(WorkflowTestData.COMPLEX_WORKFLOWS.keys()))
def complex_workflow_case(request, complex_workflows):
    """Parametrized fixture providing individual complex workflow cases."""
    return complex_workflows[request.param]


@pytest.fixture(params=list(WorkflowTestData.DOCKER_WORKFLOWS.keys()))
def docker_workflow_case(request, docker_workflows):
    """Parametrized fixture providing individual Docker workflow cases."""
    return docker_workflows[request.param]


# Parameter fixtures
@pytest.fixture
def valid_parameters():
    """Fixture providing valid parameter combinations."""
    return ParameterTestData.VALID_PARAMETERS


@pytest.fixture
def edge_case_parameters():
    """Fixture providing edge case parameter combinations."""
    return ParameterTestData.EDGE_CASE_PARAMETERS


@pytest.fixture(params=ParameterTestData.VALID_PARAMETERS["compile_workflow"])
def compile_workflow_params(request):
    """Parametrized fixture for compile_workflow parameter combinations."""
    return request.param


@pytest.fixture(params=ParameterTestData.VALID_PARAMETERS["execute_workflow"])
def execute_workflow_params(request):
    """Parametrized fixture for execute_workflow parameter combinations."""
    return request.param


@pytest.fixture(params=ParameterTestData.VALID_PARAMETERS["get_workflow_runners"])
def get_runners_params(request):
    """Parametrized fixture for get_workflow_runners parameter combinations."""
    return request.param


@pytest.fixture(params=ParameterTestData.VALID_PARAMETERS["get_integrations"])
def get_integrations_params(request):
    """Parametrized fixture for get_integrations parameter combinations."""
    return request.param


@pytest.fixture(params=ParameterTestData.VALID_PARAMETERS["get_workflow_secrets"])
def get_secrets_params(request):
    """Parametrized fixture for get_workflow_secrets parameter combinations."""
    return request.param


# Response fixtures
@pytest.fixture
def success_responses():
    """Fixture providing expected success response data."""
    return ResponseTestData.SUCCESS_RESPONSES


@pytest.fixture
def error_responses():
    """Fixture providing expected error response data."""
    return ResponseTestData.ERROR_RESPONSES


# Integration test fixtures
@pytest.fixture
def integration_scenarios():
    """Fixture providing integration test scenarios."""
    return IntegrationTestData.INTEGRATION_SCENARIOS


@pytest.fixture
def compile_and_execute_scenario():
    """Fixture providing compile and execute integration scenario."""
    return IntegrationTestData.INTEGRATION_SCENARIOS["compile_and_execute"]


@pytest.fixture
def full_pipeline_scenario():
    """Fixture providing full pipeline integration scenario."""
    return IntegrationTestData.INTEGRATION_SCENARIOS["full_pipeline"]


# Boundary test fixtures
@pytest.fixture
def resource_limits():
    """Fixture providing resource limit test data."""
    return BoundaryTestData.RESOURCE_LIMITS


@pytest.fixture
def time_scenarios():
    """Fixture providing time-based test scenarios."""
    return BoundaryTestData.TIME_SCENARIOS


@pytest.fixture
def long_running_workflow():
    """Fixture providing long-running workflow test data."""
    return BoundaryTestData.TIME_SCENARIOS["long_running_workflow"]


@pytest.fixture
def quick_workflow():
    """Fixture providing quick workflow test data."""
    return BoundaryTestData.TIME_SCENARIOS["quick_workflow"]


# Edge case fixtures
@pytest.fixture
def empty_parameter_cases():
    """Fixture providing empty parameter edge cases."""
    return ParameterTestData.EDGE_CASE_PARAMETERS["empty_values"]


@pytest.fixture
def large_parameter_cases():
    """Fixture providing large parameter edge cases."""
    return ParameterTestData.EDGE_CASE_PARAMETERS["large_values"]


@pytest.fixture
def special_character_cases():
    """Fixture providing special character edge cases."""
    return ParameterTestData.EDGE_CASE_PARAMETERS["special_characters"]


# Combined fixtures for comprehensive testing
@pytest.fixture
def all_workflow_types(simple_workflows, complex_workflows, docker_workflows):
    """Fixture combining all workflow types for comprehensive testing."""
    return {
        "simple": simple_workflows,
        "complex": complex_workflows,
        "docker": docker_workflows
    }


@pytest.fixture
def all_parameter_combinations(valid_parameters, edge_case_parameters):
    """Fixture combining all parameter combinations."""
    return {
        "valid": valid_parameters,
        "edge_cases": edge_case_parameters
    }


# Error scenario fixtures
@pytest.fixture(params=list(WorkflowTestData.ERROR_WORKFLOWS.keys()))
def error_scenario(request, error_workflows):
    """Parametrized fixture providing individual error scenarios."""
    return error_workflows[request.param]


@pytest.fixture
def compilation_error_scenario():
    """Fixture providing compilation error scenario."""
    return WorkflowTestData.ERROR_WORKFLOWS["compilation_error"]


@pytest.fixture
def execution_error_scenario():
    """Fixture providing execution error scenario."""
    return WorkflowTestData.ERROR_WORKFLOWS["execution_error"]


@pytest.fixture
def missing_dependency_scenario():
    """Fixture providing missing dependency error scenario."""
    return WorkflowTestData.ERROR_WORKFLOWS["missing_dependency"]


# Tool-specific data fixtures
@pytest.fixture
def compile_workflow_test_data():
    """Fixture providing comprehensive compile_workflow test data."""
    return {
        "valid_cases": [
            {
                "input": params,
                "expected": ResponseTestData.SUCCESS_RESPONSES["compile_workflow"]
            }
            for params in ParameterTestData.VALID_PARAMETERS["compile_workflow"]
        ],
        "error_cases": [
            {
                "input": {"dsl_code": WorkflowTestData.ERROR_WORKFLOWS["compilation_error"]["dsl"]},
                "expected": ResponseTestData.ERROR_RESPONSES["validation_error"]
            }
        ],
        "edge_cases": [
            {
                "input": ParameterTestData.EDGE_CASE_PARAMETERS["empty_values"]["compile_workflow"],
                "expected": ResponseTestData.ERROR_RESPONSES["validation_error"]
            }
        ]
    }


@pytest.fixture
def execute_workflow_test_data():
    """Fixture providing comprehensive execute_workflow test data."""
    return {
        "valid_cases": [
            {
                "input": params,
                "expected": ResponseTestData.SUCCESS_RESPONSES["execute_workflow"]
            }
            for params in ParameterTestData.VALID_PARAMETERS["execute_workflow"]
        ],
        "error_cases": [
            {
                "input": {"workflow_input": WorkflowTestData.ERROR_WORKFLOWS["execution_error"]["dsl"]},
                "expected": ResponseTestData.ERROR_RESPONSES["execution_error"]
            }
        ]
    }


# JSON test data files (can be written to filesystem if needed)
@pytest.fixture
def json_test_data_files(tmp_path):
    """Fixture creating JSON test data files in temporary directory."""
    import json
    
    # Create test data files
    files = {}
    
    # Simple workflows file
    simple_file = tmp_path / "simple_workflows.json"
    simple_file.write_text(json.dumps(WorkflowTestData.SIMPLE_WORKFLOWS, indent=2))
    files["simple_workflows"] = str(simple_file)
    
    # Complex workflows file
    complex_file = tmp_path / "complex_workflows.json"
    complex_file.write_text(json.dumps(WorkflowTestData.COMPLEX_WORKFLOWS, indent=2))
    files["complex_workflows"] = str(complex_file)
    
    # Parameters file
    params_file = tmp_path / "test_parameters.json"
    params_file.write_text(json.dumps(ParameterTestData.VALID_PARAMETERS, indent=2))
    files["parameters"] = str(params_file)
    
    # Expected responses file
    responses_file = tmp_path / "expected_responses.json"
    responses_file.write_text(json.dumps(ResponseTestData.SUCCESS_RESPONSES, indent=2))
    files["responses"] = str(responses_file)
    
    return files


@pytest.fixture
def yaml_test_data_files(tmp_path):
    """Fixture creating YAML test data files in temporary directory."""
    import yaml
    
    files = {}
    
    # Individual workflow YAML files
    for name, data in WorkflowTestData.SIMPLE_WORKFLOWS.items():
        workflow_file = tmp_path / f"{name}.yaml"
        workflow_file.write_text(data["dsl"])
        files[name] = str(workflow_file)
    
    return files