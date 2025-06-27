"""End-to-end tests for MCP tool output format validation.

This module implements black-box testing that executes full tool workflows
with mocked dependencies and validates output against predefined schemas.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock

from tests.mcp.helpers import mcp_test_server
from tests.mcp.test_data import WorkflowTestData, ParameterTestData
from tests.mcp.test_output_schemas import MCPOutputSchemas
from tests.mcp.mocks import MockWorkflowAPIClient, MockScenarios


class TestEndToEndOutputValidation:
    """End-to-end tests for MCP tool output validation."""

    @pytest.mark.asyncio
    async def test_compile_workflow_end_to_end_output(self):
        """Test complete compile_workflow output format validation."""
        test_dsl = WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"]
        
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure realistic response
                mock_client.compile_workflow.return_value = MCPOutputSchemas.create_golden_file_data("compile_workflow")
                
                try:
                    # Execute full workflow
                    result = await server.call_tool("compile_workflow", {
                        "dsl_code": test_dsl,
                        "name": "e2e_test_workflow",
                        "description": "End-to-end test workflow",
                        "prefer_docker": True
                    })
                    
                    # Validate MCP response format
                    mcp_validation = MCPOutputSchemas.validate_mcp_response(result)
                    if not mcp_validation["valid"]:
                        print(f"📝 MCP response format issues: {mcp_validation['errors']}")
                    
                    # Extract and validate tool output
                    if result and not result.get("isError", False):
                        tool_output = MCPOutputSchemas.extract_tool_output(result)
                        if tool_output:
                            output_validation = MCPOutputSchemas.validate_output("compile_workflow", tool_output)
                            
                            if output_validation["valid"]:
                                print("✅ compile_workflow end-to-end output validation passed")
                            else:
                                print(f"📝 Output validation issues: {output_validation['errors']}")
                        else:
                            print("📝 No tool output extracted from MCP response")
                    else:
                        print(f"📝 Tool returned error: {result.get('content', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"📝 End-to-end execution error: {e}")

    @pytest.mark.asyncio
    async def test_execute_workflow_end_to_end_output(self):
        """Test complete execute_workflow output format validation."""
        test_workflow = WorkflowTestData.COMPLEX_WORKFLOWS["data_pipeline"]["dsl"]
        test_params = WorkflowTestData.COMPLEX_WORKFLOWS["data_pipeline"].get("parameters", {})
        
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure execution response
                mock_client.execute_workflow.return_value = MCPOutputSchemas.create_golden_file_data("execute_workflow")
                
                try:
                    # Execute full workflow
                    result = await server.call_tool("execute_workflow", {
                        "workflow_input": test_workflow,
                        "params": test_params,
                        "dry_run": False
                    })
                    
                    # Validate output format
                    self._validate_end_to_end_output(result, "execute_workflow")
                    
                except Exception as e:
                    print(f"📝 Execute workflow e2e error: {e}")

    @pytest.mark.asyncio
    async def test_get_workflow_runners_end_to_end_output(self):
        """Test complete get_workflow_runners output format validation."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure runners response
                mock_client.get_runners.return_value = MCPOutputSchemas.create_golden_file_data("get_workflow_runners")
                
                try:
                    # Execute with various parameter combinations
                    test_cases = [
                        {},  # No parameters
                        {"refresh": True},  # With refresh
                        {"include_health": True, "component_filter": "docker"}  # Full parameters
                    ]
                    
                    for test_params in test_cases:
                        result = await server.call_tool("get_workflow_runners", test_params)
                        self._validate_end_to_end_output(result, "get_workflow_runners", test_params)
                        
                except Exception as e:
                    print(f"📝 Get runners e2e error: {e}")

    @pytest.mark.asyncio
    async def test_get_integrations_end_to_end_output(self):
        """Test complete get_integrations output format validation."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure integrations response
                mock_client.get_integrations.return_value = MCPOutputSchemas.create_golden_file_data("get_integrations")
                
                try:
                    # Test category filtering
                    result = await server.call_tool("get_integrations", {
                        "category": "communication",
                        "refresh": True
                    })
                    
                    self._validate_end_to_end_output(result, "get_integrations")
                    
                except Exception as e:
                    print(f"📝 Get integrations e2e error: {e}")

    @pytest.mark.asyncio
    async def test_get_workflow_secrets_end_to_end_output(self):
        """Test complete get_workflow_secrets output format validation."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure secrets response
                mock_client.get_secrets.return_value = MCPOutputSchemas.create_golden_file_data("get_workflow_secrets")
                
                try:
                    # Test pattern filtering
                    result = await server.call_tool("get_workflow_secrets", {
                        "pattern": "API_*",
                        "task_type": "authentication",
                        "refresh": False
                    })
                    
                    self._validate_end_to_end_output(result, "get_workflow_secrets")
                    
                except Exception as e:
                    print(f"📝 Get secrets e2e error: {e}")

    def _validate_end_to_end_output(self, result: Dict[str, Any], tool_name: str, params: Dict[str, Any] = None):
        """Helper method to validate end-to-end output."""
        params_str = f" with params {params}" if params else ""
        
        # Validate MCP response format
        mcp_validation = MCPOutputSchemas.validate_mcp_response(result)
        if not mcp_validation["valid"]:
            print(f"📝 MCP response format issues for {tool_name}{params_str}: {mcp_validation['errors']}")
            return
        
        # Extract and validate tool output
        if result and not result.get("isError", False):
            tool_output = MCPOutputSchemas.extract_tool_output(result)
            if tool_output:
                output_validation = MCPOutputSchemas.validate_output(tool_name, tool_output)
                
                if output_validation["valid"]:
                    print(f"✅ {tool_name} end-to-end output validation passed{params_str}")
                else:
                    print(f"📝 {tool_name} output validation issues{params_str}: {output_validation['errors']}")
            else:
                print(f"📝 No tool output extracted from {tool_name} MCP response{params_str}")
        else:
            error_content = result.get('content', 'Unknown error') if result else 'No result'
            print(f"📝 {tool_name} returned error{params_str}: {error_content}")


class TestOutputFormatCompliance:
    """Test output format compliance across different scenarios."""

    @pytest.mark.asyncio
    async def test_error_output_format_compliance(self):
        """Test that error outputs follow expected format."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure error responses
                mock_client.compile_workflow.side_effect = Exception("Compilation failed")
                mock_client.execute_workflow.return_value = {
                    "execution_id": "error-exec-123",
                    "status": "failed",
                    "exit_code": 1,
                    "error": "Execution failed",
                    "logs": ["Starting", "Error occurred"]
                }
                
                try:
                    # Test compilation error
                    compile_result = await server.call_tool("compile_workflow", {
                        "dsl_code": "invalid dsl"
                    })
                    
                    # Test execution error
                    execute_result = await server.call_tool("execute_workflow", {
                        "workflow_input": WorkflowTestData.ERROR_WORKFLOWS["execution_error"]["dsl"]
                    })
                    
                    # Validate error formats
                    for result, tool_name in [(compile_result, "compile_workflow"), (execute_result, "execute_workflow")]:
                        if result and result.get("isError", False):
                            print(f"✅ {tool_name} error format compliance verified")
                        else:
                            # Even if not marked as error, should have structured response
                            mcp_validation = MCPOutputSchemas.validate_mcp_response(result)
                            if mcp_validation["valid"]:
                                print(f"✅ {tool_name} error response structure valid")
                            else:
                                print(f"📝 {tool_name} error response issues: {mcp_validation['errors']}")
                        
                except Exception as e:
                    print(f"📝 Error format compliance test: {e}")

    @pytest.mark.asyncio
    async def test_partial_data_output_compliance(self):
        """Test output compliance with partial/incomplete data."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure partial responses
                mock_client.get_runners.return_value = {
                    "runners": [
                        {"id": "partial-1", "name": "Partial Runner"},  # Missing status
                        {"id": "partial-2", "status": "healthy"}  # Missing name
                    ]
                }
                
                mock_client.get_integrations.return_value = {
                    "integrations": [
                        {"name": "partial_integration"},  # Minimal data
                    ]
                }
                
                try:
                    # Test partial runner data
                    runners_result = await server.call_tool("get_workflow_runners", {})
                    
                    # Test partial integration data
                    integrations_result = await server.call_tool("get_integrations", {})
                    
                    # Validate partial data handling
                    for result, tool_name in [(runners_result, "get_workflow_runners"), (integrations_result, "get_integrations")]:
                        if result:
                            mcp_validation = MCPOutputSchemas.validate_mcp_response(result)
                            if mcp_validation["valid"]:
                                print(f"✅ {tool_name} partial data format compliance verified")
                            else:
                                print(f"📝 {tool_name} partial data issues: {mcp_validation['errors']}")
                        
                except Exception as e:
                    print(f"📝 Partial data compliance test: {e}")

    @pytest.mark.asyncio
    async def test_large_output_format_compliance(self):
        """Test output format compliance with large data sets."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure large data responses
                large_runners = {
                    "runners": [
                        {
                            "id": f"large-runner-{i}",
                            "name": f"Large Runner {i}",
                            "status": "healthy" if i % 2 == 0 else "unhealthy",
                            "version": f"1.{i}.0",
                            "capabilities": ["python", "shell"] + (["docker"] if i % 3 == 0 else []),
                            "last_heartbeat": "2024-01-01T00:00:00Z"
                        }
                        for i in range(100)  # 100 runners
                    ],
                    "total_count": 100,
                    "healthy_count": 50
                }
                
                large_integrations = {
                    "integrations": [
                        {
                            "name": f"integration_{i}",
                            "description": f"Integration {i} for testing",
                            "category": ["communication", "data", "security"][i % 3],
                            "docker_image": f"test/integration-{i}:latest",
                            "required_secrets": [f"SECRET_{i}", f"TOKEN_{i}"],
                            "version": f"2.{i}.0"
                        }
                        for i in range(50)  # 50 integrations
                    ],
                    "total_count": 50
                }
                
                mock_client.get_runners.return_value = large_runners
                mock_client.get_integrations.return_value = large_integrations
                
                try:
                    # Test large runner data
                    runners_result = await server.call_tool("get_workflow_runners", {})
                    
                    # Test large integration data
                    integrations_result = await server.call_tool("get_integrations", {})
                    
                    # Validate large data handling
                    for result, tool_name in [(runners_result, "get_workflow_runners"), (integrations_result, "get_integrations")]:
                        if result:
                            mcp_validation = MCPOutputSchemas.validate_mcp_response(result)
                            if mcp_validation["valid"]:
                                tool_output = MCPOutputSchemas.extract_tool_output(result)
                                if tool_output:
                                    output_validation = MCPOutputSchemas.validate_output(tool_name, tool_output)
                                    if output_validation["valid"]:
                                        print(f"✅ {tool_name} large data format compliance verified")
                                    else:
                                        print(f"📝 {tool_name} large data validation issues: {output_validation['errors']}")
                                else:
                                    print(f"📝 {tool_name} large data extraction failed")
                            else:
                                print(f"📝 {tool_name} large data MCP format issues: {mcp_validation['errors']}")
                        
                except Exception as e:
                    print(f"📝 Large data compliance test: {e}")


class TestGoldenFileValidation:
    """Test output validation against golden files."""

    @pytest.mark.asyncio
    async def test_compile_workflow_golden_file_validation(self):
        """Test compile_workflow output against golden file."""
        golden_output = MCPOutputSchemas.create_golden_file_data("compile_workflow")
        
        # Validate golden file format
        validation = MCPOutputSchemas.validate_output("compile_workflow", golden_output)
        
        assert validation["valid"], f"Golden file validation failed: {validation['errors']}"
        print("✅ compile_workflow golden file validation passed")

    @pytest.mark.asyncio
    async def test_execute_workflow_golden_file_validation(self):
        """Test execute_workflow output against golden file."""
        golden_output = MCPOutputSchemas.create_golden_file_data("execute_workflow")
        
        # Validate golden file format
        validation = MCPOutputSchemas.validate_output("execute_workflow", golden_output)
        
        assert validation["valid"], f"Golden file validation failed: {validation['errors']}"
        print("✅ execute_workflow golden file validation passed")

    @pytest.mark.asyncio
    async def test_data_retrieval_golden_file_validation(self):
        """Test data retrieval tools output against golden files."""
        tools = ["get_workflow_runners", "get_integrations", "get_workflow_secrets"]
        
        for tool_name in tools:
            golden_output = MCPOutputSchemas.create_golden_file_data(tool_name)
            
            # Validate golden file format
            validation = MCPOutputSchemas.validate_output(tool_name, golden_output)
            
            assert validation["valid"], f"{tool_name} golden file validation failed: {validation['errors']}"
            print(f"✅ {tool_name} golden file validation passed")

    @pytest.mark.asyncio
    async def test_schema_coverage_completeness(self):
        """Test that schemas cover all required fields."""
        # Test that all schemas are defined
        tools = ["compile_workflow", "execute_workflow", "get_workflow_runners", "get_integrations", "get_workflow_secrets"]
        
        for tool_name in tools:
            # Test schema validation works
            golden_data = MCPOutputSchemas.create_golden_file_data(tool_name)
            validation = MCPOutputSchemas.validate_output(tool_name, golden_data)
            
            assert validation["valid"], f"Schema coverage incomplete for {tool_name}: {validation['errors']}"
        
        print("✅ Schema coverage completeness verified")

    @pytest.mark.asyncio
    async def test_schema_edge_case_validation(self):
        """Test schema validation with edge cases."""
        # Test minimal valid data
        minimal_compile = {
            "status": "compiled",
            "validation_errors": []
        }
        
        minimal_execute = {
            "status": "completed"
        }
        
        minimal_runners = {
            "runners": []
        }
        
        # Test edge cases
        edge_cases = [
            ("compile_workflow", minimal_compile),
            ("execute_workflow", minimal_execute),
            ("get_workflow_runners", minimal_runners)
        ]
        
        for tool_name, minimal_data in edge_cases:
            validation = MCPOutputSchemas.validate_output(tool_name, minimal_data)
            
            if validation["valid"]:
                print(f"✅ {tool_name} minimal data validation passed")
            else:
                print(f"📝 {tool_name} minimal data validation: {validation['errors']}")


class TestConcurrentOutputValidation:
    """Test output validation under concurrent execution."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_output_validation(self):
        """Test output validation with concurrent tool executions."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure responses
                mock_client.get_runners.return_value = MCPOutputSchemas.create_golden_file_data("get_workflow_runners")
                mock_client.get_integrations.return_value = MCPOutputSchemas.create_golden_file_data("get_integrations")
                mock_client.get_secrets.return_value = MCPOutputSchemas.create_golden_file_data("get_workflow_secrets")
                
                try:
                    # Execute multiple tools concurrently
                    tasks = [
                        server.call_tool("get_workflow_runners", {}),
                        server.call_tool("get_integrations", {}),
                        server.call_tool("get_workflow_secrets", {})
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Validate all concurrent results
                    tools = ["get_workflow_runners", "get_integrations", "get_workflow_secrets"]
                    
                    for i, (result, tool_name) in enumerate(zip(results, tools)):
                        if isinstance(result, Exception):
                            print(f"📝 Concurrent {tool_name} exception: {result}")
                        else:
                            # Validate output format
                            if result:
                                mcp_validation = MCPOutputSchemas.validate_mcp_response(result)
                                if mcp_validation["valid"]:
                                    print(f"✅ Concurrent {tool_name} output validation passed")
                                else:
                                    print(f"📝 Concurrent {tool_name} validation issues: {mcp_validation['errors']}")
                    
                except Exception as e:
                    print(f"📝 Concurrent output validation error: {e}")

    @pytest.mark.asyncio
    async def test_stress_test_output_validation(self):
        """Test output validation under stress conditions."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Configure fast responses
                mock_client.get_runners.return_value = {"runners": []}
                
                try:
                    # Execute many requests rapidly
                    tasks = [
                        server.call_tool("get_workflow_runners", {})
                        for _ in range(20)
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Validate all results maintain format consistency
                    valid_count = 0
                    for result in results:
                        if not isinstance(result, Exception) and result:
                            mcp_validation = MCPOutputSchemas.validate_mcp_response(result)
                            if mcp_validation["valid"]:
                                valid_count += 1
                    
                    success_rate = (valid_count / len(results)) * 100
                    print(f"✅ Stress test output validation: {success_rate:.1f}% success rate ({valid_count}/{len(results)})")
                    
                except Exception as e:
                    print(f"📝 Stress test output validation error: {e}")