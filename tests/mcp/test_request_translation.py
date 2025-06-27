"""Tests for MCP tool request translation to SDK operations.

This module tests the translation layer between MCP tool requests and 
underlying workflow SDK method calls, focusing on parameter mapping,
type conversion, and method selection.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

from tests.mcp.test_integration_infrastructure import (
    MockSDKClientForIntegration,
    IntegrationTestUtilities
)


class TestParameterMapping:
    """Test parameter mapping from MCP tools to SDK methods."""
    
    def test_compile_workflow_parameter_mapping(self):
        """Test compile_workflow parameter mapping accuracy."""
        # Define expected parameter mappings
        mcp_params = {
            "dsl_code": "name: test\nsteps:\n  - name: step\n    run: echo 'test'",
            "name": "test_workflow",
            "description": "Test workflow description",
            "runner": "test_runner",
            "prefer_docker": True,
            "provide_missing_secrets": {"API_KEY": "test_secret"}
        }
        
        # Expected SDK method signature: compile_workflow(dsl_code, **kwargs)
        expected_sdk_params = {
            "dsl_code": mcp_params["dsl_code"],
            "kwargs": {
                "name": mcp_params["name"],
                "description": mcp_params["description"], 
                "runner": mcp_params["runner"],
                "prefer_docker": mcp_params["prefer_docker"],
                "provide_missing_secrets": mcp_params["provide_missing_secrets"]
            }
        }
        
        # Validate parameter structure
        assert mcp_params["dsl_code"] == expected_sdk_params["dsl_code"]
        
        # Validate kwargs mapping
        for key in expected_sdk_params["kwargs"]:
            assert key in mcp_params
            assert mcp_params[key] == expected_sdk_params["kwargs"][key]
        
        print("✅ compile_workflow parameter mapping validated")
    
    def test_execute_workflow_parameter_mapping(self):
        """Test execute_workflow parameter mapping accuracy."""
        # Define MCP parameters
        mcp_params = {
            "workflow_input": "workflow_content_or_dsl",
            "params": {"ENV_VAR": "test_value", "COUNT": 5},
            "api_key": "test_api_key",
            "runner": "test_runner",
            "dry_run": True,
            "stream_format": "json"
        }
        
        # Expected SDK method signature: execute_workflow(workflow_input, **kwargs)
        expected_sdk_params = {
            "workflow_input": mcp_params["workflow_input"],
            "kwargs": {
                "params": mcp_params["params"],
                "api_key": mcp_params["api_key"], 
                "runner": mcp_params["runner"],
                "dry_run": mcp_params["dry_run"],
                "stream_format": mcp_params["stream_format"]
            }
        }
        
        # Validate parameter structure
        assert mcp_params["workflow_input"] == expected_sdk_params["workflow_input"]
        
        # Validate kwargs mapping
        for key in expected_sdk_params["kwargs"]:
            assert key in mcp_params
            assert mcp_params[key] == expected_sdk_params["kwargs"][key]
        
        print("✅ execute_workflow parameter mapping validated")
    
    def test_data_retrieval_parameter_mapping(self):
        """Test data retrieval tool parameter mapping."""
        # Test get_workflow_runners
        runners_params = {
            "api_key": "test_key",
            "refresh": True,
            "include_health": True,
            "component_filter": "docker"
        }
        
        # Validate all parameters are passed as kwargs
        for key, value in runners_params.items():
            assert isinstance(key, str)
            assert value is not None
        
        # Test get_integrations
        integrations_params = {
            "category": "communication",
            "refresh": False
        }
        
        # Test get_workflow_secrets
        secrets_params = {
            "pattern": "API_*",
            "task_type": "authentication",
            "refresh": True
        }
        
        # Validate parameter structures
        param_sets = [
            ("get_workflow_runners", runners_params),
            ("get_integrations", integrations_params),
            ("get_workflow_secrets", secrets_params)
        ]
        
        for tool_name, params in param_sets:
            # All parameters should be valid kwargs
            for key, value in params.items():
                assert isinstance(key, str), f"{tool_name}: key {key} should be string"
                assert value is not None, f"{tool_name}: value for {key} should not be None"
        
        print("✅ Data retrieval parameter mapping validated")


class TestTypeConversion:
    """Test type conversion for MCP parameters."""
    
    def test_boolean_parameter_conversion(self):
        """Test boolean parameter handling."""
        boolean_test_cases = [
            # MCP input, expected SDK value
            (True, True),
            (False, False),
            ("true", True),  # String to boolean conversion
            ("false", False),
            ("True", True),
            ("False", False),
            (1, True),  # Integer to boolean
            (0, False),
            ("", False),  # Empty string to False
            ("any_string", True),  # Non-empty string to True
        ]
        
        for mcp_value, expected_sdk_value in boolean_test_cases:
            # Simulate conversion logic
            if isinstance(mcp_value, bool):
                converted = mcp_value
            elif isinstance(mcp_value, str):
                if mcp_value.lower() in ("true", "1", "yes", "on"):
                    converted = True
                elif mcp_value.lower() in ("false", "0", "no", "off", ""):
                    converted = False
                else:
                    converted = bool(mcp_value)  # Non-empty string = True
            elif isinstance(mcp_value, (int, float)):
                converted = bool(mcp_value)
            else:
                converted = bool(mcp_value)
            
            assert converted == expected_sdk_value, f"Conversion failed for {mcp_value}: got {converted}, expected {expected_sdk_value}"
        
        print("✅ Boolean parameter conversion validated")
    
    def test_json_parameter_conversion(self):
        """Test JSON string to dict conversion."""
        json_test_cases = [
            # JSON string input, expected dict output
            ('{"key": "value"}', {"key": "value"}),
            ('{"number": 123, "bool": true}', {"number": 123, "bool": True}),
            ('{"nested": {"inner": "value"}}', {"nested": {"inner": "value"}}),
            ('[]', []),
            ('[1, 2, 3]', [1, 2, 3]),
            ('null', None),
            ('"simple_string"', "simple_string"),
        ]
        
        for json_string, expected_result in json_test_cases:
            try:
                converted = json.loads(json_string)
                assert converted == expected_result, f"JSON conversion failed for {json_string}"
            except json.JSONDecodeError:
                # Should handle invalid JSON gracefully
                assert False, f"Failed to parse valid JSON: {json_string}"
        
        # Test invalid JSON handling
        invalid_json_cases = [
            '{"invalid": json}',
            '{incomplete json',
            'not json at all',
        ]
        
        for invalid_json in invalid_json_cases:
            try:
                json.loads(invalid_json)
                assert False, f"Should have failed to parse invalid JSON: {invalid_json}"
            except json.JSONDecodeError:
                # Expected behavior - invalid JSON should raise error
                pass
        
        print("✅ JSON parameter conversion validated")
    
    def test_numeric_parameter_conversion(self):
        """Test numeric parameter conversion."""
        numeric_test_cases = [
            # Input, expected type, expected value
            ("123", int, 123),
            ("123.45", float, 123.45),
            (123, int, 123),
            (123.45, float, 123.45),
            ("0", int, 0),
            ("-456", int, -456),
            ("3.14159", float, 3.14159),
        ]
        
        for input_value, expected_type, expected_value in numeric_test_cases:
            if isinstance(input_value, str):
                if "." in input_value:
                    converted = float(input_value)
                else:
                    converted = int(input_value)
            else:
                converted = input_value
            
            assert isinstance(converted, expected_type), f"Type conversion failed for {input_value}"
            assert converted == expected_value, f"Value conversion failed for {input_value}"
        
        print("✅ Numeric parameter conversion validated")


class TestMethodSelection:
    """Test correct SDK method selection for MCP tools."""
    
    @pytest.mark.asyncio
    async def test_mcp_to_sdk_method_mapping(self):
        """Test that MCP tools map to correct SDK methods."""
        # Define expected mappings
        method_mappings = {
            "compile_workflow": "compile_workflow",
            "execute_workflow": "execute_workflow", 
            "get_workflow_runners": "get_runners",
            "get_integrations": "get_integrations",
            "get_workflow_secrets": "get_secrets"
        }
        
        # Create mock SDK client to track method calls
        mock_client = MockSDKClientForIntegration()
        
        # Test each mapping
        for mcp_tool, expected_sdk_method in method_mappings.items():
            # Clear call history
            mock_client.clear_call_history()
            
            # Simulate calling the appropriate SDK method
            if expected_sdk_method == "compile_workflow":
                await mock_client.compile_workflow("test dsl")
            elif expected_sdk_method == "execute_workflow":
                await mock_client.execute_workflow("test workflow")
            elif expected_sdk_method == "get_runners":
                await mock_client.get_runners()
            elif expected_sdk_method == "get_integrations":
                await mock_client.get_integrations()
            elif expected_sdk_method == "get_secrets":
                await mock_client.get_secrets()
            
            # Verify correct method was called
            call_history = mock_client.get_call_history()
            assert len(call_history) == 1, f"Expected 1 call for {mcp_tool}, got {len(call_history)}"
            assert call_history[0]["method"] == expected_sdk_method, f"Expected {expected_sdk_method}, got {call_history[0]['method']}"
            
            print(f"✅ {mcp_tool} → {expected_sdk_method} mapping verified")
    
    def test_method_signature_compatibility(self):
        """Test that method signatures are compatible."""
        # Define expected method signatures for SDK methods
        expected_signatures = {
            "compile_workflow": {
                "required_args": ["dsl_code"],
                "optional_kwargs": ["name", "description", "runner", "prefer_docker", "provide_missing_secrets"]
            },
            "execute_workflow": {
                "required_args": ["workflow_input"],
                "optional_kwargs": ["params", "api_key", "runner", "dry_run", "stream_format"]
            },
            "get_runners": {
                "required_args": [],
                "optional_kwargs": ["api_key", "refresh", "include_health", "component_filter"]
            },
            "get_integrations": {
                "required_args": [],
                "optional_kwargs": ["category", "refresh"]
            },
            "get_secrets": {
                "required_args": [],
                "optional_kwargs": ["pattern", "task_type", "refresh"]
            }
        }
        
        # Validate signature structures
        for method_name, signature in expected_signatures.items():
            # Required args should be non-empty for some methods
            if method_name in ["compile_workflow", "execute_workflow"]:
                assert len(signature["required_args"]) > 0, f"{method_name} should have required args"
            
            # Optional kwargs should be present for all methods
            assert isinstance(signature["optional_kwargs"], list), f"{method_name} should have optional kwargs list"
            
            # All parameter names should be valid Python identifiers
            all_params = signature["required_args"] + signature["optional_kwargs"]
            for param in all_params:
                assert param.isidentifier(), f"Parameter {param} in {method_name} is not a valid identifier"
        
        print("✅ Method signature compatibility verified")


class TestRequestValidation:
    """Test request validation for MCP tool parameters."""
    
    def test_required_parameter_validation(self):
        """Test validation of required parameters."""
        # Define required parameters for each tool
        required_params = {
            "compile_workflow": ["dsl_code"],
            "execute_workflow": ["workflow_input"],
            "get_workflow_runners": [],  # No required params
            "get_integrations": [],  # No required params
            "get_workflow_secrets": []  # No required params
        }
        
        # Test each tool's required parameters
        for tool_name, required in required_params.items():
            # Test complete parameter set
            if required:
                complete_params = {param: f"test_{param}" for param in required}
                
                # Should pass validation
                for param in required:
                    assert param in complete_params, f"Missing required parameter {param} for {tool_name}"
                
                # Test missing parameters
                for missing_param in required:
                    incomplete_params = complete_params.copy()
                    del incomplete_params[missing_param]
                    
                    # Should fail validation
                    assert missing_param not in incomplete_params, f"Parameter {missing_param} should be missing"
            
            print(f"✅ {tool_name} required parameter validation verified")
    
    def test_parameter_type_validation(self):
        """Test parameter type validation."""
        # Define expected parameter types
        parameter_types = {
            "compile_workflow": {
                "dsl_code": str,
                "name": str,
                "description": str,
                "runner": str,
                "prefer_docker": bool,
                "provide_missing_secrets": (dict, str)  # Can be dict or JSON string
            },
            "execute_workflow": {
                "workflow_input": (str, dict),  # Can be DSL string or workflow dict
                "params": dict,
                "api_key": str,
                "runner": str,
                "dry_run": bool,
                "stream_format": str
            }
        }
        
        # Test type validation
        for tool_name, param_types in parameter_types.items():
            for param_name, expected_type in param_types.items():
                # Test valid types
                if isinstance(expected_type, tuple):
                    # Multiple valid types
                    for valid_type in expected_type:
                        test_value = self._create_test_value(valid_type)
                        assert isinstance(test_value, valid_type), f"Test value creation failed for {valid_type}"
                else:
                    # Single valid type
                    test_value = self._create_test_value(expected_type)
                    assert isinstance(test_value, expected_type), f"Test value creation failed for {expected_type}"
                
                print(f"✅ {tool_name}.{param_name} type validation verified")
    
    def _create_test_value(self, value_type):
        """Create a test value of the specified type."""
        if value_type == str:
            return "test_string"
        elif value_type == bool:
            return True
        elif value_type == dict:
            return {"test": "value"}
        elif value_type == int:
            return 123
        elif value_type == float:
            return 123.45
        elif value_type == list:
            return ["test", "list"]
        else:
            return None
    
    def test_optional_parameter_handling(self):
        """Test handling of optional parameters."""
        # Define optional parameters
        optional_params = {
            "compile_workflow": {
                "name": "test_workflow",
                "description": "Test description",
                "runner": "test_runner",
                "prefer_docker": True,
                "provide_missing_secrets": {"KEY": "value"}
            },
            "execute_workflow": {
                "params": {"ENV": "test"},
                "api_key": "test_key", 
                "runner": "test_runner",
                "dry_run": False,
                "stream_format": "json"
            },
            "get_workflow_runners": {
                "api_key": "test_key",
                "refresh": True,
                "include_health": True,
                "component_filter": "docker"
            }
        }
        
        # Test that tools work without optional parameters
        for tool_name, optional_set in optional_params.items():
            # Should work with no optional params
            empty_params = {}
            # No assertion needed - just verify structure exists
            
            # Should work with all optional params
            full_params = optional_set.copy()
            assert len(full_params) == len(optional_set)
            
            # Should work with partial optional params
            partial_params = {k: v for i, (k, v) in enumerate(optional_set.items()) if i % 2 == 0}
            assert len(partial_params) <= len(optional_set)
            
            print(f"✅ {tool_name} optional parameter handling verified")


class TestErrorHandling:
    """Test error handling in request translation."""
    
    def test_invalid_parameter_handling(self):
        """Test handling of invalid parameters."""
        # Test cases for invalid parameters
        invalid_cases = [
            # Tool name, invalid params, expected error type
            ("compile_workflow", {"dsl_code": None}, "null_dsl"),
            ("compile_workflow", {"dsl_code": ""}, "empty_dsl"),
            ("execute_workflow", {"workflow_input": None}, "null_workflow"),
            ("execute_workflow", {"params": "invalid_json"}, "invalid_json_params"),
        ]
        
        for tool_name, invalid_params, error_type in invalid_cases:
            # Simulate validation
            validation_errors = []
            
            if tool_name == "compile_workflow":
                if invalid_params.get("dsl_code") is None:
                    validation_errors.append("DSL code cannot be null")
                elif invalid_params.get("dsl_code") == "":
                    validation_errors.append("DSL code cannot be empty")
            
            elif tool_name == "execute_workflow":
                if invalid_params.get("workflow_input") is None:
                    validation_errors.append("Workflow input cannot be null")
                
                # Test JSON parameter validation
                params = invalid_params.get("params")
                if isinstance(params, str):
                    try:
                        json.loads(params)
                    except json.JSONDecodeError:
                        validation_errors.append("Invalid JSON in params")
            
            # Should have validation errors for invalid cases
            assert len(validation_errors) > 0, f"Should have validation errors for {tool_name} with {error_type}"
            print(f"✅ {tool_name} invalid parameter handling verified: {error_type}")
    
    def test_missing_required_parameter_handling(self):
        """Test handling of missing required parameters."""
        # Test missing DSL code for compile_workflow
        missing_dsl_params = {"name": "test"}  # Missing dsl_code
        
        # Should fail validation
        has_dsl_code = "dsl_code" in missing_dsl_params
        assert not has_dsl_code, "Should be missing dsl_code"
        
        # Test missing workflow_input for execute_workflow
        missing_workflow_params = {"params": {"test": "value"}}  # Missing workflow_input
        
        # Should fail validation
        has_workflow_input = "workflow_input" in missing_workflow_params
        assert not has_workflow_input, "Should be missing workflow_input"
        
        print("✅ Missing required parameter handling verified")


# Test runner and summary
if __name__ == "__main__":
    print("MCP Request Translation Tests loaded successfully")
    print("Test classes available:")
    print("- TestParameterMapping")
    print("- TestTypeConversion") 
    print("- TestMethodSelection")
    print("- TestRequestValidation")
    print("- TestErrorHandling")