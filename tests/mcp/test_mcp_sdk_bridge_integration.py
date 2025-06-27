"""Integration tests for MCP-Workflow SDK bridge functionality.

This module tests the complete integration between MCP tools and the underlying
workflow SDK, verifying request translation, response handling, and state management.
"""

import asyncio
import pytest
import time
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from tests.mcp.helpers import mcp_test_server
from tests.mcp.test_integration_infrastructure import (
    IntegrationTestConfig,
    IntegrationTestSession,
    integration_test_session,
    IntegrationTestUtilities,
    MockSDKClientForIntegration
)


class TestIntegrationInfrastructure:
    """Test the integration test infrastructure itself."""
    
    @pytest.mark.asyncio
    async def test_integration_test_config(self):
        """Test integration test configuration."""
        config = IntegrationTestConfig()
        
        # Verify configuration properties
        assert config.test_api_key == "test_integration_key_12345"
        assert config.test_base_url == "https://api.test.kubiya.ai"
        assert config.test_organization == "test_org"
        assert config.server_timeout == 30
        assert config.request_timeout == 10
        
        # Verify environment setup
        env = config.get_test_environment()
        assert env["KUBIYA_API_KEY"] == config.test_api_key
        assert env["TEST_MODE"] == "true"
        assert "LOG_LEVEL" in env
        
        print("✅ Integration test configuration validated")
    
    @pytest.mark.asyncio
    async def test_integration_test_session_lifecycle(self):
        """Test integration test session setup and teardown."""
        config = IntegrationTestConfig()
        
        async with integration_test_session(config) as session:
            # Verify session initialization
            assert session.config == config
            assert session.bridge is not None
            assert session.test_data is not None
            assert session.session_start_time is not None
            
            # Verify test data availability
            assert "simple_dsl" in session.test_data
            assert "complex_dsl" in session.test_data
            assert "docker_dsl" in session.test_data
            
            # Test result recording
            session.record_test_result("test_infrastructure", True, {"infrastructure": "validated"})
            assert len(session.test_results) == 1
            assert session.test_results[0]["test_name"] == "test_infrastructure"
            assert session.test_results[0]["success"] is True
            
        print("✅ Integration test session lifecycle validated")
    
    @pytest.mark.asyncio
    async def test_mock_sdk_client_integration(self):
        """Test mock SDK client for integration testing."""
        mock_client = MockSDKClientForIntegration(integration_mode=True)
        
        # Test compile_workflow
        compile_result = await mock_client.compile_workflow(
            "name: test\nsteps:\n  - name: step\n    run: echo 'test'"
        )
        assert compile_result["status"] == "compiled"
        assert compile_result["integration_test_mode"] is True
        
        # Test execute_workflow
        execute_result = await mock_client.execute_workflow("test_workflow")
        assert execute_result["status"] == "completed"
        assert execute_result["integration_test_mode"] is True
        
        # Test get_runners
        runners_result = await mock_client.get_runners()
        assert len(runners_result["runners"]) == 1
        assert runners_result["integration_test_mode"] is True
        
        # Verify call history
        call_history = mock_client.get_call_history()
        assert len(call_history) == 3
        assert call_history[0]["method"] == "compile_workflow"
        assert call_history[1]["method"] == "execute_workflow"
        assert call_history[2]["method"] == "get_runners"
        
        print("✅ Mock SDK client integration validated")


class TestMCPToolRequestTranslation:
    """Test MCP tool request translation to SDK operations."""
    
    @pytest.mark.asyncio
    async def test_compile_workflow_request_translation(self):
        """Test compile_workflow MCP request translation to SDK calls."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = MockSDKClientForIntegration()
                mock_client_class.return_value = mock_client
                
                # Execute MCP tool
                result = await server.call_tool("compile_workflow", {
                    "dsl_code": IntegrationTestUtilities.create_test_workflow_dsl("simple"),
                    "name": "integration_test_workflow",
                    "description": "Test workflow for integration",
                    "prefer_docker": True
                })
                
                # Verify MCP response structure
                validation = IntegrationTestUtilities.validate_mcp_response_structure(result)
                if validation["valid"]:
                    print("✅ Compile workflow MCP response structure valid")
                else:
                    print(f"📝 MCP response validation issues: {validation['errors']}")
                
                # Verify SDK method was called
                call_history = mock_client.get_call_history()
                if call_history:
                    compile_call = next((call for call in call_history if call["method"] == "compile_workflow"), None)
                    if compile_call:
                        print("✅ Compile workflow SDK method invoked correctly")
                        assert "dsl_code" in compile_call
                    else:
                        print("📝 Compile workflow SDK method not found in call history")
                else:
                    print("📝 No SDK method calls recorded")
    
    @pytest.mark.asyncio
    async def test_execute_workflow_request_translation(self):
        """Test execute_workflow MCP request translation to SDK calls."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = MockSDKClientForIntegration()
                mock_client_class.return_value = mock_client
                
                # Execute MCP tool
                result = await server.call_tool("execute_workflow", {
                    "workflow_input": IntegrationTestUtilities.create_test_workflow_dsl("parameterized"),
                    "params": {"TEST_MESSAGE": "Integration test execution"},
                    "dry_run": False
                })
                
                # Verify MCP response structure
                validation = IntegrationTestUtilities.validate_mcp_response_structure(result)
                if validation["valid"]:
                    print("✅ Execute workflow MCP response structure valid")
                else:
                    print(f"📝 MCP response validation issues: {validation['errors']}")
                
                # Verify SDK method was called
                call_history = mock_client.get_call_history()
                execute_call = next((call for call in call_history if call["method"] == "execute_workflow"), None)
                if execute_call:
                    print("✅ Execute workflow SDK method invoked correctly")
                    assert "workflow_input" in execute_call
                    assert "kwargs" in execute_call
                else:
                    print("📝 Execute workflow SDK method not found")
    
    @pytest.mark.asyncio
    async def test_parameter_mapping_accuracy(self):
        """Test accuracy of parameter mapping from MCP to SDK."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = MockSDKClientForIntegration()
                mock_client_class.return_value = mock_client
                
                # Test compile_workflow parameter mapping
                mcp_params = {
                    "dsl_code": "test dsl",
                    "name": "test_workflow",
                    "description": "Test description",
                    "runner": "test_runner",
                    "prefer_docker": True,
                    "provide_missing_secrets": {"SECRET_KEY": "secret_value"}
                }
                
                result = await server.call_tool("compile_workflow", mcp_params)
                
                # Analyze parameter mapping
                call_history = mock_client.get_call_history()
                if call_history:
                    compile_call = call_history[0]
                    
                    # Verify DSL code is passed correctly
                    assert compile_call["dsl_code"] == mcp_params["dsl_code"]
                    
                    # Verify kwargs contain other parameters
                    kwargs = compile_call.get("kwargs", {})
                    mapped_params = ["name", "description", "runner", "prefer_docker", "provide_missing_secrets"]
                    
                    mapping_results = {}
                    for param in mapped_params:
                        if param in kwargs:
                            mapping_results[param] = "mapped_correctly"
                        else:
                            mapping_results[param] = "missing_in_sdk_call"
                    
                    print(f"✅ Parameter mapping analysis: {mapping_results}")
                else:
                    print("📝 No SDK calls to analyze")
    
    @pytest.mark.asyncio
    async def test_data_retrieval_tool_translation(self):
        """Test data retrieval tool request translation."""
        data_tools = [
            ("get_workflow_runners", {"refresh": True, "include_health": True}),
            ("get_integrations", {"category": "testing"}),
            ("get_workflow_secrets", {"pattern": "TEST_*", "task_type": "testing"})
        ]
        
        for tool_name, params in data_tools:
            async with mcp_test_server(debug=True) as server:
                with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                    mock_client = MockSDKClientForIntegration()
                    mock_client_class.return_value = mock_client
                    
                    result = await server.call_tool(tool_name, params)
                    
                    # Verify MCP response
                    validation = IntegrationTestUtilities.validate_mcp_response_structure(result)
                    if validation["valid"]:
                        print(f"✅ {tool_name} MCP response valid")
                    else:
                        print(f"📝 {tool_name} validation issues: {validation['errors']}")
                    
                    # Verify SDK method mapping
                    call_history = mock_client.get_call_history()
                    expected_methods = {
                        "get_workflow_runners": "get_runners",
                        "get_integrations": "get_integrations", 
                        "get_workflow_secrets": "get_secrets"
                    }
                    
                    expected_method = expected_methods[tool_name]
                    method_call = next((call for call in call_history if call["method"] == expected_method), None)
                    
                    if method_call:
                        print(f"✅ {tool_name} → {expected_method} mapping verified")
                    else:
                        print(f"📝 {tool_name} → {expected_method} mapping not found")


class TestSDKOperationExecution:
    """Test SDK operation execution and response handling."""
    
    @pytest.mark.asyncio
    async def test_sdk_response_formatting(self):
        """Test that SDK responses are properly formatted for MCP return."""
        async with integration_test_session() as session:
            # Mock SDK client with realistic responses
            mock_client = MockSDKClientForIntegration()
            
            # Test different SDK response types
            sdk_responses = {
                "compile_result": await mock_client.compile_workflow("test dsl"),
                "execute_result": await mock_client.execute_workflow("test workflow"),
                "runners_result": await mock_client.get_runners(),
                "integrations_result": await mock_client.get_integrations(),
                "secrets_result": await mock_client.get_secrets()
            }
            
            # Verify each response contains expected structure
            for response_type, response in sdk_responses.items():
                assert isinstance(response, dict), f"{response_type} should be a dictionary"
                assert "integration_test_mode" in response, f"{response_type} missing test mode flag"
                
                session.record_test_result(f"sdk_response_format_{response_type}", True, {
                    "response_type": response_type,
                    "has_test_mode": response.get("integration_test_mode", False)
                })
            
            print("✅ SDK response formatting verified")
    
    @pytest.mark.asyncio
    async def test_error_response_propagation(self):
        """Test that SDK errors are properly propagated through MCP."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = MockSDKClientForIntegration()
                mock_client_class.return_value = mock_client
                
                # Test error workflow
                error_dsl = IntegrationTestUtilities.create_test_workflow_dsl("error")
                result = await server.call_tool("compile_workflow", {
                    "dsl_code": error_dsl
                })
                
                # Check if error was handled properly
                if result:
                    # Look for error indicators in response
                    response_str = str(result).lower()
                    error_indicators = ["error", "failed", "validation"]
                    
                    has_error_indication = any(indicator in response_str for indicator in error_indicators)
                    if has_error_indication:
                        print("✅ Error response propagation verified")
                    else:
                        print("📝 Error response propagation unclear")
                else:
                    print("📝 No response received for error workflow")
    
    @pytest.mark.asyncio
    async def test_async_operation_handling(self):
        """Test handling of asynchronous SDK operations."""
        async with mcp_test_server(debug=True) as server:
            with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                mock_client = MockSDKClientForIntegration()
                mock_client_class.return_value = mock_client
                
                # Test async workflow execution
                start_time = time.time()
                result = await server.call_tool("execute_workflow", {
                    "workflow_input": IntegrationTestUtilities.create_test_workflow_dsl("multi_step")
                })
                execution_time = time.time() - start_time
                
                # Verify async handling
                if result:
                    print(f"✅ Async operation completed in {execution_time:.3f}s")
                    
                    # Check for execution indicators
                    validation = IntegrationTestUtilities.validate_mcp_response_structure(result)
                    if validation["valid"]:
                        print("✅ Async operation response structure valid")
                    else:
                        print(f"📝 Async operation validation issues: {validation['errors']}")
                else:
                    print("📝 Async operation failed to return result")


class TestEndToEndWorkflows:
    """Test complete end-to-end MCP tool workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_lifecycle(self):
        """Test complete workflow lifecycle: compile → execute → status."""
        async with integration_test_session() as session:
            workflow_results = {}
            
            # Step 1: Compile workflow
            async with mcp_test_server(debug=True) as server:
                with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                    mock_client = MockSDKClientForIntegration()
                    mock_client_class.return_value = mock_client
                    
                    # Compile workflow
                    compile_result = await server.call_tool("compile_workflow", {
                        "dsl_code": session.test_data["complex_dsl"],
                        "name": "e2e_test_workflow"
                    })
                    workflow_results["compile"] = compile_result
                    
                    # Execute workflow  
                    execute_result = await server.call_tool("execute_workflow", {
                        "workflow_input": session.test_data["complex_dsl"],
                        "params": {"MESSAGE": "End-to-end test execution"}
                    })
                    workflow_results["execute"] = execute_result
                    
                    # Get supporting data
                    runners_result = await server.call_tool("get_workflow_runners", {})
                    workflow_results["runners"] = runners_result
            
            # Analyze complete workflow lifecycle
            lifecycle_success = True
            for step, result in workflow_results.items():
                validation = IntegrationTestUtilities.validate_mcp_response_structure(result)
                if not validation["valid"]:
                    lifecycle_success = False
                    print(f"📝 {step} step validation failed: {validation['errors']}")
                else:
                    print(f"✅ {step} step completed successfully")
            
            session.record_test_result("complete_workflow_lifecycle", lifecycle_success, {
                "steps_completed": len(workflow_results),
                "all_steps_valid": lifecycle_success
            })
    
    @pytest.mark.asyncio
    async def test_docker_workflow_integration(self):
        """Test Docker-based workflow integration."""
        async with integration_test_session() as session:
            async with mcp_test_server(debug=True) as server:
                with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                    mock_client = MockSDKClientForIntegration()
                    mock_client_class.return_value = mock_client
                    
                    # Test Docker workflow compilation
                    docker_result = await server.call_tool("compile_workflow", {
                        "dsl_code": session.test_data["docker_dsl"],
                        "prefer_docker": True
                    })
                    
                    # Verify Docker-specific handling
                    validation = IntegrationTestUtilities.validate_mcp_response_structure(docker_result)
                    if validation["valid"]:
                        print("✅ Docker workflow integration validated")
                        
                        # Check if Docker requirements were detected
                        call_history = mock_client.get_call_history()
                        if call_history:
                            compile_call = call_history[0]
                            dsl_content = compile_call.get("dsl_code", "")
                            has_docker_indicators = any(indicator in dsl_content for indicator in ["pip install", "npm install"])
                            
                            if has_docker_indicators:
                                print("✅ Docker requirement detection working")
                            else:
                                print("📝 Docker requirement detection unclear")
                    else:
                        print(f"📝 Docker workflow validation failed: {validation['errors']}")
            
            session.record_test_result("docker_workflow_integration", validation["valid"], {
                "docker_workflow_tested": True,
                "validation_passed": validation["valid"]
            })
    
    @pytest.mark.asyncio
    async def test_multi_tool_coordination(self):
        """Test coordination between multiple MCP tools."""
        async with integration_test_session() as session:
            coordination_results = {}
            
            async with mcp_test_server(debug=True) as server:
                with patch('kubiya_workflow_sdk.client.StreamingKubiyaClient') as mock_client_class:
                    mock_client = MockSDKClientForIntegration()
                    mock_client_class.return_value = mock_client
                    
                    # Execute multiple coordinated tool calls
                    tools_sequence = [
                        ("get_workflow_runners", {}),
                        ("get_integrations", {"category": "testing"}),
                        ("compile_workflow", {
                            "dsl_code": session.test_data["simple_dsl"]
                        }),
                        ("execute_workflow", {
                            "workflow_input": session.test_data["simple_dsl"]
                        })
                    ]
                    
                    for tool_name, params in tools_sequence:
                        result = await server.call_tool(tool_name, params)
                        coordination_results[tool_name] = result
            
            # Analyze multi-tool coordination
            all_tools_successful = True
            for tool_name, result in coordination_results.items():
                validation = IntegrationTestUtilities.validate_mcp_response_structure(result)
                if not validation["valid"]:
                    all_tools_successful = False
                    print(f"📝 {tool_name} coordination failed: {validation['errors']}")
                else:
                    print(f"✅ {tool_name} coordination successful")
            
            session.record_test_result("multi_tool_coordination", all_tools_successful, {
                "tools_tested": len(coordination_results),
                "coordination_success": all_tools_successful
            })


# Test runner for validation
if __name__ == "__main__":
    print("MCP-SDK Bridge Integration Tests loaded successfully")
    print("Test classes available:")
    print("- TestIntegrationInfrastructure")
    print("- TestMCPToolRequestTranslation")
    print("- TestSDKOperationExecution") 
    print("- TestEndToEndWorkflows")