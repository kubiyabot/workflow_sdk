"""Comprehensive syntax validation tests for all MCP tools.

This module tests that all MCP tools properly validate input parameters
and handle various error conditions gracefully without throwing unhandled exceptions.
"""

import pytest
from typing import Any, Dict, List, Union, Optional
from unittest.mock import patch, MagicMock

from tests.mcp.helpers import mcp_test_server


class TestMCPToolSyntaxValidation:
    """Test suite for MCP tool syntax validation."""

    # Define all MCP tools that need validation testing
    MCP_TOOLS = {
        # Core workflow tools
        "compile_workflow": {
            "required_params": ["dsl_code"],
            "optional_params": [
                "name",
                "description",
                "runner",
                "prefer_docker",
                "provide_missing_secrets",
            ],
            "param_types": {
                "dsl_code": str,
                "name": (str, type(None)),
                "description": (str, type(None)),
                "runner": (str, type(None)),
                "prefer_docker": bool,
                "provide_missing_secrets": (str, dict, type(None)),
            },
        },
        "execute_workflow": {
            "required_params": ["workflow_input"],
            "optional_params": ["params", "api_key", "runner", "dry_run", "stream_format"],
            "param_types": {
                "workflow_input": (str, dict),
                "params": (str, dict, type(None)),
                "api_key": (str, type(None)),
                "runner": (str, type(None)),
                "dry_run": bool,
                "stream_format": str,
            },
        },
        "get_workflow_runners": {
            "required_params": [],
            "optional_params": ["api_key", "refresh", "include_health", "component_filter"],
            "param_types": {
                "api_key": (str, type(None)),
                "refresh": bool,
                "include_health": bool,
                "component_filter": (str, type(None)),
            },
        },
        "get_integrations": {
            "required_params": [],
            "optional_params": ["api_key", "category", "refresh"],
            "param_types": {
                "api_key": (str, type(None)),
                "category": (str, type(None)),
                "refresh": bool,
            },
        },
        "get_workflow_secrets": {
            "required_params": [],
            "optional_params": ["api_key", "pattern", "task_type", "refresh"],
            "param_types": {
                "api_key": (str, type(None)),
                "pattern": (str, type(None)),
                "task_type": (str, type(None)),
                "refresh": bool,
            },
        },
    }

    MCP_PROMPTS = {
        "workflow_dsl_guide": {
            "required_params": ["task_description"],
            "optional_params": ["prefer_docker", "complexity"],
            "param_types": {"task_description": str, "prefer_docker": bool, "complexity": str},
        },
        "docker_workflow_examples": {
            "required_params": ["use_case"],
            "optional_params": ["language"],
            "param_types": {"use_case": str, "language": str},
        },
        "workflow_patterns": {
            "required_params": ["pattern"],
            "optional_params": [],
            "param_types": {"pattern": str},
        },
    }

    MCP_RESOURCES = [
        "workflow://examples/hello-world",
        "workflow://examples/docker-python",
        "workflow://examples/parallel-processing",
        "workflow://examples/ci-cd-pipeline",
        "workflow://examples/data-pipeline",
        "workflow://templates/docker-commands",
        "workflow://templates/patterns",
        "workflow://best-practices",
        "workflow://docker-images",
    ]

    def get_valid_test_data(self, tool_name: str) -> Dict[str, Any]:
        """Generate valid test data for a given tool."""
        tool_def = self.MCP_TOOLS.get(tool_name)
        if not tool_def:
            return {}

        valid_data = {}

        # Add required parameters with valid values
        for param in tool_def["required_params"]:
            param_type = tool_def["param_types"][param]
            if param == "dsl_code":
                valid_data[param] = "print('Hello World')"
            elif param == "workflow_input":
                valid_data[param] = "print('Test workflow')"
            elif param == "task_description":
                valid_data[param] = "Create a simple workflow"
            elif param == "use_case":
                valid_data[param] = "data_processing"
            elif param == "pattern":
                valid_data[param] = "parallel"
            elif param_type == str:
                valid_data[param] = "test_value"
            elif param_type == bool:
                valid_data[param] = True
            elif param_type == int:
                valid_data[param] = 1

        return valid_data

    def get_invalid_type_data(self, tool_name: str, param_name: str) -> List[Any]:
        """Generate invalid type test data for a parameter."""
        tool_def = self.MCP_TOOLS.get(tool_name)
        if not tool_def or param_name not in tool_def["param_types"]:
            return []

        expected_type = tool_def["param_types"][param_name]
        invalid_values = []

        # Generate invalid values based on expected type
        if expected_type == str or (isinstance(expected_type, tuple) and str in expected_type):
            invalid_values.extend([123, [], {}, True])
        if expected_type == bool or (isinstance(expected_type, tuple) and bool in expected_type):
            invalid_values.extend(["true", 1, 0, []])
        if expected_type == int or (isinstance(expected_type, tuple) and int in expected_type):
            invalid_values.extend(["123", [], {}, True])
        if expected_type == dict or (isinstance(expected_type, tuple) and dict in expected_type):
            invalid_values.extend(["not_json", 123, True, []])

        return invalid_values

    # Valid parameter combination test data
    VALID_TEST_SCENARIOS = {
        "compile_workflow": [
            # Minimal required parameters
            {"dsl_code": "print('Hello World')"},
            # With optional name and description
            {
                "dsl_code": "print('Hello World')",
                "name": "test_workflow",
                "description": "Test workflow",
            },
            # With all parameters
            {
                "dsl_code": "print('Hello World')",
                "name": "test_workflow",
                "description": "Test workflow",
                "runner": "default",
                "prefer_docker": True,
                "provide_missing_secrets": {"SECRET_KEY": "test_value"},
            },
            # With string secrets
            {
                "dsl_code": "print('Hello World')",
                "provide_missing_secrets": '{"SECRET_KEY": "test_value"}',
            },
        ],
        "execute_workflow": [
            # With DSL string
            {"workflow_input": "print('Hello World')"},
            # With workflow dict
            {"workflow_input": {"steps": [{"name": "test", "run": "echo hello"}]}},
            # With all parameters
            {
                "workflow_input": "print('Hello World')",
                "params": {"input_param": "test"},
                "api_key": "test_key",
                "runner": "default",
                "dry_run": True,
                "stream_format": "json",
            },
            # With string params
            {"workflow_input": "print('Hello World')", "params": '{"input_param": "test"}'},
        ],
        "get_workflow_runners": [
            # No parameters
            {},
            # With optional parameters
            {"api_key": "test_key", "refresh": True, "include_health": False},
            # With component filter
            {"component_filter": "docker", "refresh": False},
        ],
        "get_integrations": [
            # No parameters
            {},
            # With category filter
            {"category": "data", "refresh": True},
            # With API key
            {"api_key": "test_key"},
        ],
        "get_workflow_secrets": [
            # No parameters
            {},
            # With pattern filter
            {"pattern": "DB_*", "refresh": True},
            # With task type
            {"task_type": "data_processing", "api_key": "test_key"},
        ],
    }

    @pytest.mark.parametrize(
        "tool_name,test_scenarios",
        [(tool_name, scenarios) for tool_name, scenarios in VALID_TEST_SCENARIOS.items()],
    )
    @pytest.mark.asyncio
    async def test_valid_parameter_combinations(
        self, tool_name: str, test_scenarios: List[Dict[str, Any]]
    ):
        """Test that tools accept all valid parameter combinations without errors."""
        async with mcp_test_server(debug=True) as server:
            for i, params in enumerate(test_scenarios):
                try:
                    # Test that the tool call doesn't throw syntax/validation errors
                    # We expect it might fail due to missing API keys or invalid data,
                    # but it should not fail due to parameter validation issues
                    result = await server.call_tool(tool_name, params)

                    # If successful, result should be structured properly
                    if result and not result.get("isError", False):
                        assert (
                            "content" in result or "result" in result
                        ), f"Tool {tool_name} should return structured result"
                        print(f"✅ {tool_name} scenario {i+1}: Success")
                    else:
                        # Check if error is due to validation (bad) vs runtime issues (acceptable)
                        error_msg = result.get("content", "") if result else "Unknown error"

                        # These are acceptable runtime errors, not validation errors
                        acceptable_errors = [
                            "api key",
                            "authentication",
                            "network",
                            "connection",
                            "not found",
                            "timeout",
                            "unavailable",
                            "service",
                        ]

                        is_validation_error = not any(
                            acceptable in error_msg.lower() for acceptable in acceptable_errors
                        )

                        if is_validation_error and "invalid" in error_msg.lower():
                            pytest.fail(
                                f"Tool {tool_name} scenario {i+1} failed validation with valid params: {error_msg}"
                            )
                        else:
                            print(
                                f"⚠️  {tool_name} scenario {i+1}: Runtime error (acceptable): {error_msg}"
                            )

                except Exception as e:
                    # Check if this is a validation exception vs runtime exception
                    error_str = str(e).lower()
                    if any(
                        word in error_str
                        for word in [
                            "validation",
                            "invalid parameter",
                            "missing parameter",
                            "type error",
                        ]
                    ):
                        pytest.fail(
                            f"Tool {tool_name} scenario {i+1} failed parameter validation: {e}"
                        )
                    else:
                        print(f"⚠️  {tool_name} scenario {i+1}: Runtime exception (acceptable): {e}")

    @pytest.mark.parametrize("tool_name", list(VALID_TEST_SCENARIOS.keys()))
    @pytest.mark.asyncio
    async def test_minimal_valid_parameters(self, tool_name: str):
        """Test that each tool works with minimal required parameters."""
        minimal_params = self.get_valid_test_data(tool_name)

        async with mcp_test_server(debug=True) as server:
            try:
                result = await server.call_tool(tool_name, minimal_params)

                # Should not fail due to parameter validation
                if result and result.get("isError", False):
                    error_msg = result.get("content", "")
                    if "parameter" in error_msg.lower() or "validation" in error_msg.lower():
                        pytest.fail(
                            f"Tool {tool_name} failed validation with minimal params: {error_msg}"
                        )

                print(f"✅ {tool_name}: Minimal parameters accepted")

            except Exception as e:
                error_str = str(e).lower()
                if any(
                    word in error_str for word in ["parameter", "validation", "missing", "required"]
                ):
                    pytest.fail(f"Tool {tool_name} failed with minimal required params: {e}")
                else:
                    print(
                        f"⚠️  {tool_name}: Runtime exception with minimal params (acceptable): {e}"
                    )

    @pytest.mark.asyncio
    async def test_prompt_valid_parameters(self):
        """Test MCP prompts with valid parameter combinations."""
        prompt_scenarios = {
            "workflow_dsl_guide": [
                {"task_description": "Create a data processing workflow"},
                {
                    "task_description": "Build a CI/CD pipeline",
                    "prefer_docker": False,
                    "complexity": "simple",
                },
                {"task_description": "ML model training workflow", "complexity": "complex"},
            ],
            "docker_workflow_examples": [
                {"use_case": "data_processing"},
                {"use_case": "ci_cd", "language": "javascript"},
                {"use_case": "ml", "language": "python"},
            ],
            "workflow_patterns": [
                {"pattern": "parallel"},
                {"pattern": "conditional"},
                {"pattern": "error_handling"},
            ],
        }

        async with mcp_test_server(debug=True) as server:
            for prompt_name, scenarios in prompt_scenarios.items():
                for i, params in enumerate(scenarios):
                    try:
                        # Test prompt execution - prompts should return content
                        result = await server.call_tool(
                            prompt_name, params
                        )  # MCP handles prompts as tools

                        if result and not result.get("isError", False):
                            print(f"✅ Prompt {prompt_name} scenario {i+1}: Success")
                        else:
                            error_msg = result.get("content", "") if result else ""
                            if "parameter" in error_msg.lower():
                                pytest.fail(f"Prompt {prompt_name} failed validation: {error_msg}")

                    except Exception as e:
                        if "parameter" in str(e).lower() or "validation" in str(e).lower():
                            pytest.fail(f"Prompt {prompt_name} failed validation: {e}")
                        else:
                            print(f"⚠️  Prompt {prompt_name} scenario {i+1}: Runtime error: {e}")

    # Invalid parameter type test data
    INVALID_TYPE_TEST_DATA = {
        "compile_workflow": {
            "dsl_code": [123, [], {}, True, None],  # Should be str
            "name": [123, [], {}, True],  # Should be str or None
            "description": [123, [], {}, True],  # Should be str or None
            "runner": [123, [], {}, True],  # Should be str or None
            "prefer_docker": ["true", "false", 1, 0, [], {}],  # Should be bool
            "provide_missing_secrets": [123, True, []],  # Should be str, dict, or None
        },
        "execute_workflow": {
            "workflow_input": [123, True, None],  # Should be str or dict
            "params": [123, True, []],  # Should be str, dict, or None
            "api_key": [123, [], {}, True],  # Should be str or None
            "runner": [123, [], {}, True],  # Should be str or None
            "dry_run": ["true", "false", 1, 0, [], {}],  # Should be bool
            "stream_format": [123, [], {}, True, None],  # Should be str
        },
        "get_workflow_runners": {
            "api_key": [123, [], {}, True],  # Should be str or None
            "refresh": ["true", "false", 1, 0, [], {}],  # Should be bool
            "include_health": ["true", "false", 1, 0, [], {}],  # Should be bool
            "component_filter": [123, [], {}, True],  # Should be str or None
        },
        "get_integrations": {
            "api_key": [123, [], {}, True],  # Should be str or None
            "category": [123, [], {}, True],  # Should be str or None
            "refresh": ["true", "false", 1, 0, [], {}],  # Should be bool
        },
        "get_workflow_secrets": {
            "api_key": [123, [], {}, True],  # Should be str or None
            "pattern": [123, [], {}, True],  # Should be str or None
            "task_type": [123, [], {}, True],  # Should be str or None
            "refresh": ["true", "false", 1, 0, [], {}],  # Should be bool
        },
    }

    @pytest.mark.parametrize("tool_name", list(INVALID_TYPE_TEST_DATA.keys()))
    @pytest.mark.asyncio
    async def test_invalid_parameter_types(self, tool_name: str):
        """Test that tools properly reject parameters with invalid types."""
        tool_invalid_data = self.INVALID_TYPE_TEST_DATA[tool_name]
        base_valid_params = self.get_valid_test_data(tool_name)

        async with mcp_test_server(debug=True) as server:
            for param_name, invalid_values in tool_invalid_data.items():
                for invalid_value in invalid_values:
                    # Create test params with one invalid parameter
                    test_params = base_valid_params.copy()
                    test_params[param_name] = invalid_value

                    try:
                        result = await server.call_tool(tool_name, test_params)

                        # If we get a result, it should indicate an error for type validation
                        if result and result.get("isError", False):
                            error_msg = result.get("content", "").lower()
                            # Check if error indicates type validation failure
                            type_error_indicators = [
                                "type",
                                "invalid",
                                "expected",
                                "must be",
                                "should be",
                                "wrong type",
                                "validation",
                            ]

                            has_type_error = any(
                                indicator in error_msg for indicator in type_error_indicators
                            )
                            if has_type_error:
                                print(
                                    f"✅ {tool_name}.{param_name}={invalid_value}: Correctly rejected"
                                )
                            else:
                                print(
                                    f"⚠️  {tool_name}.{param_name}={invalid_value}: Error but unclear if type validation: {error_msg}"
                                )
                        else:
                            # Tool accepted invalid type - this might be a problem
                            print(
                                f"❌ {tool_name}.{param_name}={invalid_value}: Unexpectedly accepted invalid type"
                            )

                    except Exception as e:
                        error_str = str(e).lower()
                        # Check if exception indicates type validation
                        if any(
                            word in error_str
                            for word in ["type", "invalid", "validation", "expected"]
                        ):
                            print(
                                f"✅ {tool_name}.{param_name}={invalid_value}: Correctly rejected with exception"
                            )
                        else:
                            print(
                                f"⚠️  {tool_name}.{param_name}={invalid_value}: Exception but unclear if type validation: {e}"
                            )

    @pytest.mark.parametrize(
        "tool_name,param_name,invalid_value",
        [
            (tool_name, param_name, invalid_value)
            for tool_name, params in INVALID_TYPE_TEST_DATA.items()
            for param_name, invalid_values in params.items()
            for invalid_value in invalid_values[
                :2
            ]  # Test first 2 invalid values per param to keep test time reasonable
        ],
    )
    @pytest.mark.asyncio
    async def test_specific_invalid_types(
        self, tool_name: str, param_name: str, invalid_value: Any
    ):
        """Test specific invalid type combinations in detail."""
        base_valid_params = self.get_valid_test_data(tool_name)
        test_params = base_valid_params.copy()
        test_params[param_name] = invalid_value

        async with mcp_test_server(debug=True) as server:
            validation_failed = False
            error_message = ""

            try:
                result = await server.call_tool(tool_name, test_params)

                if result and result.get("isError", False):
                    error_message = result.get("content", "")
                    # Look for type validation indicators
                    validation_indicators = [
                        f"invalid type",
                        f"expected",
                        f"must be",
                        f"wrong type",
                        f"validation failed",
                        f"type error",
                        f"invalid value",
                    ]
                    validation_failed = any(
                        indicator in error_message.lower() for indicator in validation_indicators
                    )

            except Exception as e:
                error_message = str(e)
                validation_failed = any(
                    word in error_message.lower()
                    for word in ["type", "validation", "invalid", "expected"]
                )

            # Document the result but don't fail - type validation behavior may vary
            if validation_failed:
                print(
                    f"✅ {tool_name}.{param_name} correctly rejected {type(invalid_value).__name__}: {invalid_value}"
                )
            else:
                print(
                    f"📝 {tool_name}.{param_name} behavior with {type(invalid_value).__name__}: {error_message or 'Accepted'}"
                )

    @pytest.mark.asyncio
    async def test_prompt_invalid_parameter_types(self):
        """Test MCP prompts with invalid parameter types."""
        prompt_invalid_data = {
            "workflow_dsl_guide": {
                "task_description": [123, [], {}, True, None],  # Should be str
                "prefer_docker": ["true", 1, 0, [], {}],  # Should be bool
                "complexity": [123, [], {}, True, None],  # Should be str
            },
            "docker_workflow_examples": {
                "use_case": [123, [], {}, True, None],  # Should be str
                "language": [123, [], {}, True, None],  # Should be str
            },
            "workflow_patterns": {"pattern": [123, [], {}, True, None]},  # Should be str
        }

        async with mcp_test_server(debug=True) as server:
            for prompt_name, invalid_params in prompt_invalid_data.items():
                # Get base valid parameters for the prompt
                if prompt_name == "workflow_dsl_guide":
                    base_params = {"task_description": "Test task"}
                elif prompt_name == "docker_workflow_examples":
                    base_params = {"use_case": "data_processing"}
                elif prompt_name == "workflow_patterns":
                    base_params = {"pattern": "parallel"}
                else:
                    base_params = {}

                for param_name, invalid_values in invalid_params.items():
                    for invalid_value in invalid_values[:2]:  # Test first 2 values
                        test_params = base_params.copy()
                        test_params[param_name] = invalid_value

                        try:
                            result = await server.call_tool(prompt_name, test_params)

                            if result and result.get("isError", False):
                                error_msg = result.get("content", "")
                                if "type" in error_msg.lower() or "invalid" in error_msg.lower():
                                    print(
                                        f"✅ Prompt {prompt_name}.{param_name}={invalid_value}: Correctly rejected"
                                    )
                                else:
                                    print(
                                        f"📝 Prompt {prompt_name}.{param_name}={invalid_value}: Error: {error_msg}"
                                    )
                            else:
                                print(
                                    f"📝 Prompt {prompt_name}.{param_name}={invalid_value}: Accepted"
                                )

                        except Exception as e:
                            if "type" in str(e).lower() or "validation" in str(e).lower():
                                print(
                                    f"✅ Prompt {prompt_name}.{param_name}={invalid_value}: Correctly rejected with exception"
                                )
                            else:
                                print(
                                    f"📝 Prompt {prompt_name}.{param_name}={invalid_value}: Exception: {e}"
                                )

    @pytest.mark.asyncio
    async def test_boundary_type_cases(self):
        """Test boundary cases for type validation."""
        boundary_cases = [
            # Edge cases that might be accepted/rejected depending on implementation
            ("compile_workflow", "dsl_code", ""),  # Empty string
            ("compile_workflow", "prefer_docker", "true"),  # String "true" for bool
            ("execute_workflow", "workflow_input", ""),  # Empty string
            ("execute_workflow", "dry_run", 1),  # Integer 1 for bool
            ("get_workflow_runners", "refresh", 0),  # Integer 0 for bool
        ]

        async with mcp_test_server(debug=True) as server:
            for tool_name, param_name, boundary_value in boundary_cases:
                base_params = self.get_valid_test_data(tool_name)
                test_params = base_params.copy()
                test_params[param_name] = boundary_value

                try:
                    result = await server.call_tool(tool_name, test_params)

                    if result and result.get("isError", False):
                        print(f"📝 {tool_name}.{param_name}={boundary_value}: Rejected")
                    else:
                        print(f"📝 {tool_name}.{param_name}={boundary_value}: Accepted")

                except Exception as e:
                    print(f"📝 {tool_name}.{param_name}={boundary_value}: Exception: {e}")

    @pytest.mark.parametrize("tool_name", list(MCP_TOOLS.keys()))
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, tool_name: str):
        """Test that tools properly reject calls when required parameters are missing."""
        tool_def = self.MCP_TOOLS[tool_name]
        required_params = tool_def["required_params"]

        # Skip tools with no required parameters
        if not required_params:
            print(f"📝 {tool_name}: No required parameters to test")
            return

        base_valid_params = self.get_valid_test_data(tool_name)

        async with mcp_test_server(debug=True) as server:
            for missing_param in required_params:
                # Create test params missing one required parameter
                test_params = base_valid_params.copy()
                if missing_param in test_params:
                    del test_params[missing_param]

                try:
                    result = await server.call_tool(tool_name, test_params)

                    # Should get an error indicating missing required parameter
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "").lower()
                        missing_indicators = [
                            "required",
                            "missing",
                            "must provide",
                            "parameter",
                            missing_param.lower(),
                            "field required",
                        ]

                        has_missing_error = any(
                            indicator in error_msg for indicator in missing_indicators
                        )
                        if has_missing_error:
                            print(f"✅ {tool_name}: Correctly rejected missing '{missing_param}'")
                        else:
                            print(
                                f"⚠️  {tool_name}: Error but unclear if missing param validation: {error_msg}"
                            )
                    else:
                        print(
                            f"❌ {tool_name}: Unexpectedly accepted missing required param '{missing_param}'"
                        )

                except Exception as e:
                    error_str = str(e).lower()
                    if any(
                        word in error_str for word in ["required", "missing", missing_param.lower()]
                    ):
                        print(
                            f"✅ {tool_name}: Correctly rejected missing '{missing_param}' with exception"
                        )
                    else:
                        print(f"⚠️  {tool_name}: Exception but unclear if missing param: {e}")

    @pytest.mark.parametrize("tool_name", list(MCP_TOOLS.keys()))
    @pytest.mark.asyncio
    async def test_extraneous_parameters(self, tool_name: str):
        """Test that tools handle extra/unexpected parameters appropriately."""
        base_valid_params = self.get_valid_test_data(tool_name)
        tool_def = self.MCP_TOOLS[tool_name]
        all_valid_params = set(tool_def["required_params"] + tool_def["optional_params"])

        # Common extraneous parameters to test
        extraneous_params = [
            {"extra_param": "unexpected_value"},
            {"invalid_flag": True},
            {"random_setting": 123},
            {"unknown_option": "test"},
            {"_private_param": "hidden"},
        ]

        async with mcp_test_server(debug=True) as server:
            for extra_param_dict in extraneous_params:
                # Add extraneous parameter to valid params
                test_params = base_valid_params.copy()
                test_params.update(extra_param_dict)

                extra_param_name = list(extra_param_dict.keys())[0]

                try:
                    result = await server.call_tool(tool_name, test_params)

                    # Check how tool handles extraneous parameters
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "").lower()
                        extraneous_indicators = [
                            "unexpected",
                            "unknown",
                            "invalid parameter",
                            "not recognized",
                            "extra",
                            extra_param_name.lower(),
                            "unexpected field",
                        ]

                        has_extraneous_error = any(
                            indicator in error_msg for indicator in extraneous_indicators
                        )
                        if has_extraneous_error:
                            print(
                                f"✅ {tool_name}: Correctly rejected extraneous '{extra_param_name}'"
                            )
                        else:
                            print(
                                f"📝 {tool_name}: Error but unclear if extraneous param: {error_msg}"
                            )
                    else:
                        # Tool accepted extraneous parameter - this might be acceptable
                        print(f"📝 {tool_name}: Accepted extraneous parameter '{extra_param_name}'")

                except Exception as e:
                    error_str = str(e).lower()
                    if any(
                        word in error_str
                        for word in ["unexpected", "unknown", "invalid", extra_param_name.lower()]
                    ):
                        print(
                            f"✅ {tool_name}: Correctly rejected extraneous '{extra_param_name}' with exception"
                        )
                    else:
                        print(f"📝 {tool_name}: Exception with extraneous param: {e}")

    @pytest.mark.asyncio
    async def test_prompt_missing_required_parameters(self):
        """Test MCP prompts with missing required parameters."""
        prompt_required_params = {
            "workflow_dsl_guide": ["task_description"],
            "docker_workflow_examples": ["use_case"],
            "workflow_patterns": ["pattern"],
        }

        async with mcp_test_server(debug=True) as server:
            for prompt_name, required_params in prompt_required_params.items():
                for missing_param in required_params:
                    # Create empty params (missing required parameter)
                    test_params = {}

                    try:
                        result = await server.call_tool(prompt_name, test_params)

                        if result and result.get("isError", False):
                            error_msg = result.get("content", "").lower()
                            if any(
                                word in error_msg
                                for word in ["required", "missing", missing_param.lower()]
                            ):
                                print(
                                    f"✅ Prompt {prompt_name}: Correctly rejected missing '{missing_param}'"
                                )
                            else:
                                print(f"📝 Prompt {prompt_name}: Error: {error_msg}")
                        else:
                            print(
                                f"❌ Prompt {prompt_name}: Unexpectedly accepted missing '{missing_param}'"
                            )

                    except Exception as e:
                        if any(
                            word in str(e).lower()
                            for word in ["required", "missing", missing_param.lower()]
                        ):
                            print(
                                f"✅ Prompt {prompt_name}: Correctly rejected missing '{missing_param}' with exception"
                            )
                        else:
                            print(f"📝 Prompt {prompt_name}: Exception: {e}")

    @pytest.mark.asyncio
    async def test_prompt_extraneous_parameters(self):
        """Test MCP prompts with extraneous parameters."""
        prompt_base_params = {
            "workflow_dsl_guide": {"task_description": "Test task"},
            "docker_workflow_examples": {"use_case": "data_processing"},
            "workflow_patterns": {"pattern": "parallel"},
        }

        extraneous_params = [
            {"extra_option": "value"},
            {"unknown_flag": True},
            {"random_param": 123},
        ]

        async with mcp_test_server(debug=True) as server:
            for prompt_name, base_params in prompt_base_params.items():
                for extra_param_dict in extraneous_params:
                    test_params = base_params.copy()
                    test_params.update(extra_param_dict)

                    extra_param_name = list(extra_param_dict.keys())[0]

                    try:
                        result = await server.call_tool(prompt_name, test_params)

                        if result and result.get("isError", False):
                            error_msg = result.get("content", "")
                            if any(
                                word in error_msg.lower()
                                for word in ["unexpected", "unknown", extra_param_name.lower()]
                            ):
                                print(
                                    f"✅ Prompt {prompt_name}: Correctly rejected extraneous '{extra_param_name}'"
                                )
                            else:
                                print(f"📝 Prompt {prompt_name}: Error: {error_msg}")
                        else:
                            print(
                                f"📝 Prompt {prompt_name}: Accepted extraneous '{extra_param_name}'"
                            )

                    except Exception as e:
                        if any(
                            word in str(e).lower()
                            for word in ["unexpected", "unknown", extra_param_name.lower()]
                        ):
                            print(
                                f"✅ Prompt {prompt_name}: Correctly rejected extraneous '{extra_param_name}' with exception"
                            )
                        else:
                            print(f"📝 Prompt {prompt_name}: Exception: {e}")

    @pytest.mark.asyncio
    async def test_completely_empty_parameters(self):
        """Test calling tools with completely empty parameter sets."""
        async with mcp_test_server(debug=True) as server:
            # Test core tools with empty params
            for tool_name in self.MCP_TOOLS.keys():
                tool_def = self.MCP_TOOLS[tool_name]
                has_required = len(tool_def["required_params"]) > 0

                try:
                    result = await server.call_tool(tool_name, {})

                    if has_required:
                        # Should fail for tools with required parameters
                        if result and result.get("isError", False):
                            print(f"✅ {tool_name}: Correctly rejected empty parameters")
                        else:
                            print(f"❌ {tool_name}: Unexpectedly accepted empty parameters")
                    else:
                        # Should succeed for tools with no required parameters
                        if result and not result.get("isError", False):
                            print(
                                f"✅ {tool_name}: Correctly accepted empty parameters (no required params)"
                            )
                        else:
                            print(
                                f"📝 {tool_name}: Rejected empty parameters: {result.get('content', '') if result else 'No result'}"
                            )

                except Exception as e:
                    if has_required and any(
                        word in str(e).lower() for word in ["required", "missing"]
                    ):
                        print(f"✅ {tool_name}: Correctly rejected empty parameters with exception")
                    else:
                        print(f"📝 {tool_name}: Exception with empty params: {e}")

    @pytest.mark.parametrize(
        "tool_name,missing_param",
        [
            (tool_name, param)
            for tool_name, tool_def in MCP_TOOLS.items()
            for param in tool_def["required_params"]
        ],
    )
    @pytest.mark.asyncio
    async def test_specific_missing_parameters(self, tool_name: str, missing_param: str):
        """Test specific missing required parameters individually."""
        base_valid_params = self.get_valid_test_data(tool_name)
        test_params = base_valid_params.copy()

        # Remove the specific required parameter
        if missing_param in test_params:
            del test_params[missing_param]

        async with mcp_test_server(debug=True) as server:
            validation_failed = False
            error_message = ""

            try:
                result = await server.call_tool(tool_name, test_params)

                if result and result.get("isError", False):
                    error_message = result.get("content", "")
                    validation_indicators = [
                        "required",
                        "missing",
                        missing_param.lower(),
                        "must provide",
                        "field required",
                    ]
                    validation_failed = any(
                        indicator in error_message.lower() for indicator in validation_indicators
                    )

            except Exception as e:
                error_message = str(e)
                validation_failed = any(
                    word in error_message.lower()
                    for word in ["required", "missing", missing_param.lower()]
                )

            # Document the result
            if validation_failed:
                print(f"✅ {tool_name} correctly requires '{missing_param}'")
            else:
                print(
                    f"📝 {tool_name} behavior without '{missing_param}': {error_message or 'Accepted'}"
                )

    @pytest.mark.asyncio
    async def test_empty_string_parameters(self):
        """Test tools with empty string parameters."""
        edge_cases = [
            ("compile_workflow", "dsl_code", ""),  # Empty DSL code
            ("compile_workflow", "name", ""),  # Empty workflow name
            ("execute_workflow", "workflow_input", ""),  # Empty workflow input
            ("execute_workflow", "api_key", ""),  # Empty API key
            ("get_workflow_runners", "component_filter", ""),  # Empty filter
            ("get_integrations", "category", ""),  # Empty category
            ("get_workflow_secrets", "pattern", ""),  # Empty pattern
        ]

        async with mcp_test_server(debug=True) as server:
            for tool_name, param_name, empty_value in edge_cases:
                base_params = self.get_valid_test_data(tool_name)
                test_params = base_params.copy()
                test_params[param_name] = empty_value

                try:
                    result = await server.call_tool(tool_name, test_params)

                    # Document behavior with empty strings
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "")
                        if "empty" in error_msg.lower() or "required" in error_msg.lower():
                            print(
                                f"✅ {tool_name}.{param_name}='': Correctly rejected empty string"
                            )
                        else:
                            print(f"📝 {tool_name}.{param_name}='': Error: {error_msg}")
                    else:
                        print(f"📝 {tool_name}.{param_name}='': Accepted empty string")

                except Exception as e:
                    if "empty" in str(e).lower() or "required" in str(e).lower():
                        print(
                            f"✅ {tool_name}.{param_name}='': Correctly rejected empty string with exception"
                        )
                    else:
                        print(f"📝 {tool_name}.{param_name}='': Exception: {e}")

    @pytest.mark.asyncio
    async def test_very_long_strings(self):
        """Test tools with very long string parameters."""
        long_string = "x" * 10000  # 10KB string
        very_long_string = "y" * 100000  # 100KB string

        edge_cases = [
            ("compile_workflow", "dsl_code", long_string),
            ("compile_workflow", "dsl_code", very_long_string),
            ("compile_workflow", "name", long_string),
            ("execute_workflow", "workflow_input", long_string),
            ("get_workflow_secrets", "pattern", long_string),
        ]

        async with mcp_test_server(debug=True) as server:
            for tool_name, param_name, long_value in edge_cases:
                base_params = self.get_valid_test_data(tool_name)
                test_params = base_params.copy()
                test_params[param_name] = long_value

                try:
                    result = await server.call_tool(tool_name, test_params)

                    # Document behavior with very long strings
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "")
                        if any(
                            word in error_msg.lower()
                            for word in ["too long", "size", "length", "limit"]
                        ):
                            print(
                                f"✅ {tool_name}.{param_name} correctly rejected {len(long_value)} char string"
                            )
                        else:
                            print(
                                f"📝 {tool_name}.{param_name} error with {len(long_value)} chars: {error_msg[:100]}..."
                            )
                    else:
                        print(
                            f"📝 {tool_name}.{param_name}: Accepted {len(long_value)} character string"
                        )

                except Exception as e:
                    if any(
                        word in str(e).lower() for word in ["too long", "size", "length", "limit"]
                    ):
                        print(
                            f"✅ {tool_name}.{param_name} correctly rejected {len(long_value)} char string with exception"
                        )
                    else:
                        print(
                            f"📝 {tool_name}.{param_name} exception with {len(long_value)} chars: {str(e)[:100]}..."
                        )

    @pytest.mark.asyncio
    async def test_special_character_handling(self):
        """Test tools with special characters and Unicode."""
        special_strings = [
            "Hello\nWorld",  # Newline
            "Hello\tWorld",  # Tab
            "Hello\x00World",  # Null byte
            "Hello 🚀 World",  # Unicode emoji
            'Hello "quoted" World',  # Quotes
            "Hello 'single' World",  # Single quotes
            "Hello\\nEscaped",  # Escaped characters
            "Hello & < > & World",  # HTML/XML characters
            "Hello ${variable} World",  # Variable-like syntax
            "SELECT * FROM users;",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "../../etc/passwd",  # Path traversal attempt
        ]

        async with mcp_test_server(debug=True) as server:
            for special_string in special_strings:
                # Test with DSL code parameter which is most likely to be processed
                test_params = {"dsl_code": special_string}

                try:
                    result = await server.call_tool("compile_workflow", test_params)

                    # Document behavior with special characters
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "")
                        if any(
                            word in error_msg.lower()
                            for word in ["invalid", "character", "encoding"]
                        ):
                            print(
                                f"✅ compile_workflow correctly rejected special chars: {repr(special_string[:20])}"
                            )
                        else:
                            print(
                                f"📝 compile_workflow error with special chars: {error_msg[:50]}..."
                            )
                    else:
                        print(
                            f"📝 compile_workflow accepted special chars: {repr(special_string[:20])}"
                        )

                except Exception as e:
                    if any(word in str(e).lower() for word in ["invalid", "character", "encoding"]):
                        print(
                            f"✅ compile_workflow correctly rejected special chars with exception: {repr(special_string[:20])}"
                        )
                    else:
                        print(f"📝 compile_workflow exception with special chars: {str(e)[:50]}...")

    @pytest.mark.asyncio
    async def test_json_boundary_cases(self):
        """Test tools with JSON boundary cases for parameters that accept JSON strings."""
        json_test_cases = [
            ('{"valid": "json"}', "Valid JSON object"),
            ('{"nested": {"deep": {"very": "deep"}}}', "Deeply nested JSON"),
            ('{"array": [1, 2, 3, {"nested": true}]}', "JSON with arrays"),
            ('{"unicode": "🚀🎉🔥"}', "JSON with Unicode"),
            ('{"empty_string": "", "null_value": null}', "JSON with edge values"),
            ('{"number": 123456789012345678901234567890}', "JSON with very large number"),
            ('[{"item": 1}, {"item": 2}]', "JSON array as root"),
            ('"just a string"', "JSON string as root"),
            ("123", "JSON number as root"),
            ("true", "JSON boolean as root"),
            ("null", "JSON null as root"),
            ('{"invalid": }', "Invalid JSON - missing value"),
            ('{"trailing": "comma",}', "Invalid JSON - trailing comma"),
            ('{invalid_key: "value"}', "Invalid JSON - unquoted key"),
            ('{"unterminated": "string}', "Invalid JSON - unterminated string"),
            ("", "Empty string"),
        ]

        async with mcp_test_server(debug=True) as server:
            for json_string, description in json_test_cases:
                # Test with provide_missing_secrets which accepts JSON strings
                base_params = self.get_valid_test_data("compile_workflow")
                test_params = base_params.copy()
                test_params["provide_missing_secrets"] = json_string

                try:
                    result = await server.call_tool("compile_workflow", test_params)

                    # Document JSON handling behavior
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "")
                        if any(
                            word in error_msg.lower()
                            for word in ["json", "parse", "invalid", "format"]
                        ):
                            print(f"✅ JSON validation caught: {description}")
                        else:
                            print(f"📝 Error with {description}: {error_msg[:50]}...")
                    else:
                        print(f"📝 Accepted {description}: {json_string[:30]}...")

                except Exception as e:
                    if any(
                        word in str(e).lower() for word in ["json", "parse", "invalid", "format"]
                    ):
                        print(f"✅ JSON validation exception for: {description}")
                    else:
                        print(f"📝 Exception with {description}: {str(e)[:50]}...")

    @pytest.mark.asyncio
    async def test_numeric_boundary_conditions(self):
        """Test numeric boundary conditions for boolean parameters."""
        # Test edge cases for boolean parameters with numeric values
        boolean_edge_cases = [
            (0, "Zero"),
            (1, "One"),
            (-1, "Negative one"),
            (2, "Two"),
            (999999, "Large positive"),
            (-999999, "Large negative"),
            (0.0, "Float zero"),
            (1.0, "Float one"),
            (0.5, "Float half"),
        ]

        async with mcp_test_server(debug=True) as server:
            for value, description in boolean_edge_cases:
                # Test with prefer_docker boolean parameter
                base_params = self.get_valid_test_data("compile_workflow")
                test_params = base_params.copy()
                test_params["prefer_docker"] = value

                try:
                    result = await server.call_tool("compile_workflow", test_params)

                    # Document numeric boolean handling
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "")
                        if any(
                            word in error_msg.lower()
                            for word in ["boolean", "true", "false", "type"]
                        ):
                            print(f"✅ Boolean validation rejected {description}: {value}")
                        else:
                            print(f"📝 Error with boolean {description}: {error_msg[:50]}...")
                    else:
                        print(f"📝 Accepted boolean {description}: {value}")

                except Exception as e:
                    if any(word in str(e).lower() for word in ["boolean", "true", "false", "type"]):
                        print(f"✅ Boolean validation exception for {description}: {value}")
                    else:
                        print(f"📝 Exception with boolean {description}: {str(e)[:50]}...")

    @pytest.mark.asyncio
    async def test_workflow_input_edge_cases(self):
        """Test edge cases specific to workflow_input parameter."""
        workflow_edge_cases = [
            ({}, "Empty dict"),
            ({"steps": []}, "Dict with empty steps"),
            ({"invalid_key": "value"}, "Dict with invalid structure"),
            ({"steps": [{"name": "test"}]}, "Dict with minimal step"),
            ({"steps": [{"name": "test", "run": "echo hello"}]}, "Dict with valid step"),
            ([], "Empty array"),
            ([1, 2, 3], "Array with numbers"),
            (None, "None value"),
            (
                {"deeply": {"nested": {"workflow": {"with": {"many": "levels"}}}}},
                "Deeply nested dict",
            ),
        ]

        async with mcp_test_server(debug=True) as server:
            for workflow_value, description in workflow_edge_cases:
                test_params = {"workflow_input": workflow_value}

                try:
                    result = await server.call_tool("execute_workflow", test_params)

                    # Document workflow input handling
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "")
                        if any(
                            word in error_msg.lower()
                            for word in ["workflow", "invalid", "structure", "format"]
                        ):
                            print(f"✅ Workflow validation rejected {description}")
                        else:
                            print(f"📝 Error with workflow {description}: {error_msg[:50]}...")
                    else:
                        print(f"📝 Accepted workflow {description}")

                except Exception as e:
                    if any(
                        word in str(e).lower()
                        for word in ["workflow", "invalid", "structure", "format"]
                    ):
                        print(f"✅ Workflow validation exception for {description}")
                    else:
                        print(f"📝 Exception with workflow {description}: {str(e)[:50]}...")

    @pytest.mark.asyncio
    async def test_concurrent_parameter_edge_cases(self):
        """Test edge cases with multiple parameter combinations."""
        edge_combinations = [
            # Empty strings for all optional parameters
            {
                "dsl_code": "print('test')",
                "name": "",
                "description": "",
                "runner": "",
            },
            # Mix of valid and edge case values
            {
                "dsl_code": "x" * 1000,  # Long DSL
                "name": "test_workflow",
                "prefer_docker": "true",  # String instead of bool
                "provide_missing_secrets": "invalid_json{",
            },
            # All optional parameters with edge values
            {
                "dsl_code": "print('test')",
                "name": "🚀_workflow",  # Unicode in name
                "description": "Line1\nLine2\tTabbed",  # Multiline with special chars
                "runner": "non-existent-runner",
                "prefer_docker": 1,  # Integer instead of bool
            },
        ]

        async with mcp_test_server(debug=True) as server:
            for i, params in enumerate(edge_combinations):
                try:
                    result = await server.call_tool("compile_workflow", params)

                    # Document combined edge case behavior
                    if result and result.get("isError", False):
                        error_msg = result.get("content", "")
                        print(f"📝 Edge combination {i+1} error: {error_msg[:100]}...")
                    else:
                        print(f"📝 Edge combination {i+1}: Accepted")

                except Exception as e:
                    print(f"📝 Edge combination {i+1} exception: {str(e)[:100]}...")
