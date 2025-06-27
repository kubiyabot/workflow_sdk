"""Integration test infrastructure for MCP-Workflow SDK bridge testing.

This module provides foundational infrastructure for testing the complete
integration between MCP tools and the underlying workflow SDK.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from kubiya_workflow_sdk.client import StreamingKubiyaClient
from kubiya_workflow_sdk.mcp.server.core import KubiyaMCPServer, create_server
from tests.mcp.helpers import mcp_test_server


class IntegrationTestConfig:
    """Configuration for integration testing."""
    
    def __init__(self):
        self.test_api_key = "test_integration_key_12345"
        self.test_base_url = "https://api.test.kubiya.ai"
        self.test_organization = "test_org"
        self.server_timeout = 30
        self.request_timeout = 10
        self.debug_mode = False
        
    def get_test_environment(self) -> Dict[str, str]:
        """Get environment variables for testing."""
        return {
            "KUBIYA_API_KEY": self.test_api_key,
            "KUBIYA_BASE_URL": self.test_base_url,
            "KUBIYA_ORGANIZATION": self.test_organization,
            "TEST_MODE": "true",
            "LOG_LEVEL": "DEBUG" if self.debug_mode else "INFO"
        }


class MCPSDKBridge:
    """Bridge class for testing MCP-SDK integration."""
    
    def __init__(self, config: IntegrationTestConfig):
        self.config = config
        self.mcp_server = None
        self.sdk_client = None
        self.integration_context = {}
        
    async def initialize(self):
        """Initialize the MCP-SDK bridge for testing."""
        # Create SDK client with test configuration
        self.sdk_client = StreamingKubiyaClient(
            api_key=self.config.test_api_key,
            base_url=self.config.test_base_url,
            org_name=self.config.test_organization
        )
        
        # Initialize MCP server
        self.mcp_server = create_server()
        
        # Set up integration context
        self.integration_context = {
            "initialized_at": time.time(),
            "sdk_client_id": id(self.sdk_client),
            "mcp_server_id": id(self.mcp_server),
            "test_session": True
        }
        
    async def cleanup(self):
        """Clean up resources after testing."""
        if self.sdk_client:
            # Clean up SDK client resources
            await self.sdk_client.close() if hasattr(self.sdk_client, 'close') else None
            
        if self.mcp_server:
            # Clean up MCP server resources
            pass  # Server cleanup handled by context manager
            
        self.integration_context.clear()
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get status of the MCP-SDK bridge."""
        return {
            "sdk_client_initialized": self.sdk_client is not None,
            "mcp_server_initialized": self.mcp_server is not None,
            "integration_context": self.integration_context,
            "bridge_healthy": self.sdk_client is not None and self.mcp_server is not None
        }


class IntegrationTestSession:
    """Manages an integration test session with proper setup and teardown."""
    
    def __init__(self, config: IntegrationTestConfig = None):
        self.config = config or IntegrationTestConfig()
        self.bridge = MCPSDKBridge(self.config)
        self.test_data = {}
        self.test_results = []
        self.session_start_time = None
        
    async def setup_session(self):
        """Set up the test session."""
        self.session_start_time = time.time()
        
        # Initialize the bridge
        await self.bridge.initialize()
        
        # Set up test data
        self.test_data = {
            "simple_dsl": """
name: integration_test_workflow
description: Simple workflow for integration testing
steps:
  - name: hello_step
    run: echo "Hello from integration test"
""",
            "complex_dsl": """
name: complex_integration_test
description: Complex workflow for comprehensive integration testing
parameters:
  - name: MESSAGE
    type: string
    default: "Integration test message"
env:
  - TEST_ENV: "integration"
steps:
  - name: setup
    run: echo "Setting up integration test"
  - name: process
    run: |
      echo "Processing: $MESSAGE"
      echo "Environment: $TEST_ENV"
  - name: cleanup
    run: echo "Cleaning up integration test"
""",
            "docker_dsl": """
name: docker_integration_test
description: Docker-based workflow for integration testing
steps:
  - name: python_step
    run: |
      pip install requests
      python3 -c "import requests; print('Docker integration test successful')"
  - name: node_step
    run: |
      npm install lodash
      node -e "console.log('Node integration test successful')"
"""
        }
        
        print(f"✅ Integration test session initialized (session_id: {id(self)})")
        
    async def teardown_session(self):
        """Tear down the test session."""
        # Clean up bridge
        await self.bridge.cleanup()
        
        # Calculate session duration
        session_duration = time.time() - self.session_start_time if self.session_start_time else 0
        
        # Generate session summary
        session_summary = {
            "session_duration": session_duration,
            "tests_executed": len(self.test_results),
            "successful_tests": sum(1 for r in self.test_results if r.get("success", False)),
            "failed_tests": sum(1 for r in self.test_results if not r.get("success", False)),
            "bridge_status": self.bridge.get_bridge_status()
        }
        
        print(f"✅ Integration test session completed: {session_summary}")
        return session_summary
    
    def record_test_result(self, test_name: str, success: bool, details: Dict[str, Any] = None):
        """Record a test result."""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": time.time(),
            "details": details or {}
        }
        self.test_results.append(result)
        
    async def execute_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool and return the result."""
        # This will be implemented with actual MCP server integration
        # For now, return a mock response structure
        return {
            "tool_name": tool_name,
            "parameters": parameters,
            "execution_time": time.time(),
            "result": {"status": "executed", "tool": tool_name}
        }


@asynccontextmanager
async def integration_test_session(config: IntegrationTestConfig = None) -> AsyncGenerator[IntegrationTestSession, None]:
    """Context manager for integration test sessions."""
    session = IntegrationTestSession(config)
    try:
        await session.setup_session()
        yield session
    finally:
        await session.teardown_session()


class IntegrationTestUtilities:
    """Utility functions for integration testing."""
    
    @staticmethod
    def create_test_workflow_dsl(workflow_type: str = "simple") -> str:
        """Create test workflow DSL based on type."""
        workflows = {
            "simple": """
name: simple_test
description: Simple test workflow
steps:
  - name: test_step
    run: echo "Simple test successful"
""",
            "parameterized": """
name: parameterized_test
description: Parameterized test workflow
parameters:
  - name: TEST_MESSAGE
    type: string
    default: "Default test message"
steps:
  - name: param_step
    run: echo "Message: $TEST_MESSAGE"
""",
            "docker": """
name: docker_test
description: Docker-based test workflow
steps:
  - name: python_test
    run: |
      pip install requests
      python3 -c "print('Docker test successful')"
""",
            "multi_step": """
name: multi_step_test
description: Multi-step test workflow
steps:
  - name: step_1
    run: echo "Step 1 complete"
  - name: step_2
    run: echo "Step 2 complete"
  - name: step_3
    run: echo "Step 3 complete"
""",
            "error": """
name: error_test
description: Test workflow that should fail
steps:
  - name: failing_step
    run: exit 1
"""
        }
        return workflows.get(workflow_type, workflows["simple"])
    
    @staticmethod
    def validate_mcp_response_structure(response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate MCP response structure compliance."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required MCP response fields
        if not isinstance(response, dict):
            validation_result["valid"] = False
            validation_result["errors"].append("Response is not a dictionary")
            return validation_result
        
        # Check for content field
        if "content" not in response:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing 'content' field in response")
        
        # Check content structure
        content = response.get("content", [])
        if not isinstance(content, list):
            validation_result["valid"] = False
            validation_result["errors"].append("Content field must be a list")
        
        # Check for isError field
        if "isError" in response and not isinstance(response["isError"], bool):
            validation_result["warnings"].append("isError field should be boolean")
        
        return validation_result
    
    @staticmethod
    def extract_sdk_method_calls(mock_client: AsyncMock) -> List[Dict[str, Any]]:
        """Extract and analyze SDK method calls from mock client."""
        method_calls = []
        
        # Analyze common SDK methods
        sdk_methods = [
            "compile_workflow",
            "execute_workflow", 
            "get_runners",
            "get_integrations",
            "get_secrets"
        ]
        
        for method_name in sdk_methods:
            if hasattr(mock_client, method_name):
                method_mock = getattr(mock_client, method_name)
                if hasattr(method_mock, "call_args_list"):
                    for call_args in method_mock.call_args_list:
                        method_calls.append({
                            "method": method_name,
                            "args": call_args.args if call_args else [],
                            "kwargs": call_args.kwargs if call_args else {},
                            "call_count": method_mock.call_count
                        })
        
        return method_calls
    
    @staticmethod
    def compare_direct_sdk_vs_mcp_results(sdk_result: Dict[str, Any], mcp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare direct SDK results with MCP-mediated results."""
        comparison = {
            "identical": False,
            "differences": [],
            "similarity_score": 0.0,
            "mcp_overhead": 0.0
        }
        
        # Basic structure comparison
        if isinstance(sdk_result, dict) and isinstance(mcp_result, dict):
            sdk_keys = set(sdk_result.keys())
            mcp_keys = set(mcp_result.keys())
            
            common_keys = sdk_keys & mcp_keys
            only_sdk = sdk_keys - mcp_keys
            only_mcp = mcp_keys - sdk_keys
            
            if only_sdk:
                comparison["differences"].append(f"Keys only in SDK result: {only_sdk}")
            if only_mcp:
                comparison["differences"].append(f"Keys only in MCP result: {only_mcp}")
            
            # Calculate similarity score
            if sdk_keys or mcp_keys:
                comparison["similarity_score"] = len(common_keys) / len(sdk_keys | mcp_keys)
        
        comparison["identical"] = len(comparison["differences"]) == 0 and comparison["similarity_score"] == 1.0
        
        return comparison


class MockSDKClientForIntegration:
    """Mock SDK client specifically designed for integration testing."""
    
    def __init__(self, integration_mode: bool = True):
        self.integration_mode = integration_mode
        self.call_history = []
        self.responses = {}
        
    async def compile_workflow(self, dsl_code: str, **kwargs) -> Dict[str, Any]:
        """Mock compile_workflow with integration-aware responses."""
        self.call_history.append({
            "method": "compile_workflow",
            "dsl_code": dsl_code,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        # Generate realistic response based on DSL content
        if "error" in dsl_code.lower():
            return {
                "workflow_id": None,
                "status": "failed",
                "validation_errors": ["Integration test error simulation"],
                "integration_test_mode": self.integration_mode
            }
        
        return {
            "workflow_id": f"integration_test_{int(time.time())}",
            "status": "compiled",
            "validation_errors": [],
            "manifest": {
                "name": "integration_test_workflow",
                "steps": [{"name": "test_step", "run": "echo 'test'"}]
            },
            "docker_required": "pip install" in dsl_code or "npm install" in dsl_code,
            "integration_test_mode": self.integration_mode
        }
    
    async def execute_workflow(self, workflow_input, **kwargs) -> Dict[str, Any]:
        """Mock execute_workflow with streaming simulation."""
        self.call_history.append({
            "method": "execute_workflow",
            "workflow_input": workflow_input,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        return {
            "execution_id": f"integration_exec_{int(time.time())}",
            "status": "completed",
            "exit_code": 0,
            "output": "Integration test execution successful",
            "logs": [
                "Starting integration test execution",
                "Executing workflow steps",
                "Integration test completed successfully"
            ],
            "duration": 1.5,
            "integration_test_mode": self.integration_mode
        }
    
    async def get_runners(self, **kwargs) -> Dict[str, Any]:
        """Mock get_runners with test runner data."""
        self.call_history.append({
            "method": "get_runners",
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        return {
            "runners": [
                {
                    "id": "integration_test_runner",
                    "name": "Integration Test Runner",
                    "status": "healthy",
                    "version": "test-1.0.0",
                    "capabilities": ["python", "docker", "shell"],
                    "last_heartbeat": "2024-01-01T00:00:00Z"
                }
            ],
            "total_count": 1,
            "healthy_count": 1,
            "integration_test_mode": self.integration_mode
        }
    
    async def get_integrations(self, **kwargs) -> Dict[str, Any]:
        """Mock get_integrations with test integration data."""
        self.call_history.append({
            "method": "get_integrations",
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        return {
            "integrations": [
                {
                    "name": "integration_test_tool",
                    "description": "Test integration for testing",
                    "category": "testing",
                    "docker_image": "test/integration:latest",
                    "required_secrets": ["TEST_TOKEN"],
                    "version": "1.0.0"
                }
            ],
            "total_count": 1,
            "integration_test_mode": self.integration_mode
        }
    
    async def get_secrets(self, **kwargs) -> Dict[str, Any]:
        """Mock get_secrets with test secret data."""
        self.call_history.append({
            "method": "get_secrets", 
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        return {
            "secrets": [
                {
                    "name": "INTEGRATION_TEST_SECRET",
                    "description": "Secret for integration testing",
                    "task_type": "testing",
                    "required": True,
                    "pattern": "INTEGRATION_*"
                }
            ],
            "total_count": 1,
            "required_count": 1,
            "integration_test_mode": self.integration_mode
        }
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get complete call history for analysis."""
        return self.call_history.copy()
    
    def clear_call_history(self):
        """Clear call history."""
        self.call_history.clear()


# Export key classes and functions for integration testing
__all__ = [
    "IntegrationTestConfig",
    "MCPSDKBridge", 
    "IntegrationTestSession",
    "integration_test_session",
    "IntegrationTestUtilities",
    "MockSDKClientForIntegration"
]