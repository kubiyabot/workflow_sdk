"""Mock infrastructure for MCP functional correctness testing.

This module provides mock classes and fixtures for testing MCP tools
in isolation from external dependencies.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock
import pytest


class MockWorkflowAPIClient:
    """Mock implementation of the Workflow API client for testing."""
    
    def __init__(self):
        self.compile_workflow = AsyncMock()
        self.execute_workflow = AsyncMock()
        self.get_runners = AsyncMock()
        self.get_integrations = AsyncMock()
        self.get_secrets = AsyncMock()
        
        # Set up default return values
        self._setup_default_responses()
    
    def _setup_default_responses(self):
        """Set up realistic default responses for API methods."""
        
        # Default compile_workflow response
        self.compile_workflow.return_value = {
            "workflow_id": "wf-12345",
            "status": "compiled",
            "validation_errors": [],
            "docker_required": False,
            "compiled_dsl": "# Compiled workflow content",
            "dependencies": []
        }
        
        # Default execute_workflow response
        self.execute_workflow.return_value = {
            "execution_id": "exec-12345",
            "status": "completed",
            "output": "Workflow executed successfully",
            "logs": ["Starting workflow", "Step 1 completed", "Workflow finished"],
            "exit_code": 0,
            "duration": 2.5
        }
        
        # Default get_runners response
        self.get_runners.return_value = {
            "runners": [
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
        }
        
        # Default get_integrations response
        self.get_integrations.return_value = {
            "integrations": [
                {
                    "name": "slack",
                    "description": "Slack integration for notifications",
                    "docker_image": "kubiya/slack-integration:latest",
                    "required_secrets": ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"],
                    "category": "communication"
                },
                {
                    "name": "github",
                    "description": "GitHub integration for repository operations",
                    "docker_image": "kubiya/github-integration:latest",
                    "required_secrets": ["GITHUB_TOKEN"],
                    "category": "version_control"
                }
            ]
        }
        
        # Default get_secrets response
        self.get_secrets.return_value = {
            "secrets": [
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
                }
            ]
        }


class MockMCPToolResponse:
    """Mock MCP tool response for testing."""
    
    def __init__(self, content: Union[str, Dict], is_error: bool = False):
        self.content = content
        self.is_error = is_error
    
    def get(self, key: str, default=None):
        """Mock dict-like access."""
        if key == "content":
            if isinstance(self.content, str):
                return [{"text": self.content}]
            return self.content
        elif key == "isError":
            return self.is_error
        return default


class FunctionalTestDataGenerator:
    """Generate test data for functional correctness tests."""
    
    @staticmethod
    def get_simple_workflow_dsl() -> str:
        """Generate a simple workflow DSL for testing."""
        return """
name: simple_test_workflow
description: A simple workflow for testing
steps:
  - name: hello_world
    run: echo "Hello, World!"
  - name: current_date
    run: date
"""
    
    @staticmethod
    def get_complex_workflow_dsl() -> str:
        """Generate a complex workflow DSL for testing."""
        return """
name: complex_test_workflow
description: A complex workflow with multiple steps and dependencies
environment:
  variables:
    ENV: test
    DEBUG: true
steps:
  - name: setup
    run: |
      echo "Setting up environment"
      mkdir -p /tmp/test
  - name: process_data
    depends_on: [setup]
    run: |
      echo "Processing data..."
      echo '{"status": "processing"}' > /tmp/test/status.json
  - name: validate_output
    depends_on: [process_data]
    run: |
      if [ -f /tmp/test/status.json ]; then
        echo "Validation passed"
      else
        echo "Validation failed"
        exit 1
      fi
"""
    
    @staticmethod
    def get_docker_workflow_dsl() -> str:
        """Generate a workflow DSL that should trigger Docker usage."""
        return """
name: docker_workflow
description: Workflow requiring Docker containers
steps:
  - name: python_analysis
    type: python
    code: |
      import pandas as pd
      import numpy as np
      
      # This would require pandas/numpy packages
      data = pd.DataFrame({'values': [1, 2, 3, 4, 5]})
      result = np.mean(data['values'])
      print(f"Mean value: {result}")
  - name: install_packages
    run: |
      pip install requests beautifulsoup4
      python -c "import requests; print('Packages installed')"
"""
    
    @staticmethod
    def get_test_parameters() -> Dict[str, Any]:
        """Generate test parameters for workflow execution."""
        return {
            "INPUT_FILE": "/tmp/test/input.txt",
            "OUTPUT_DIR": "/tmp/test/output",
            "BATCH_SIZE": 100,
            "TIMEOUT": 300,
            "ENVIRONMENT": "test"
        }
    
    @staticmethod
    def get_workflow_dict() -> Dict[str, Any]:
        """Generate workflow as dictionary for testing."""
        return {
            "name": "dict_workflow",
            "description": "Workflow provided as dictionary",
            "steps": [
                {
                    "name": "step1",
                    "run": "echo 'Step 1'"
                },
                {
                    "name": "step2", 
                    "run": "echo 'Step 2'",
                    "depends_on": ["step1"]
                }
            ]
        }
    
    @staticmethod
    def get_invalid_workflow_dsl() -> str:
        """Generate invalid workflow DSL for error testing."""
        return """
invalid_structure:
  - missing_required_fields
  - no_proper_workflow_format
    improper_indentation:
"""

    @staticmethod
    def get_secrets_data() -> Dict[str, str]:
        """Generate test secrets data."""
        return {
            "DATABASE_URL": "postgresql://test:test@localhost:5432/testdb",
            "API_KEY": "test_api_key_12345",
            "JWT_SECRET": "test_jwt_secret_key",
            "REDIS_URL": "redis://localhost:6379/0",
            "WEBHOOK_SECRET": "test_webhook_secret"
        }


@pytest.fixture
def mock_api_client():
    """Fixture providing a mock API client."""
    return MockWorkflowAPIClient()


@pytest.fixture
def test_data_generator():
    """Fixture providing test data generator."""
    return FunctionalTestDataGenerator()


@pytest.fixture
def simple_workflow_dsl(test_data_generator):
    """Fixture providing simple workflow DSL."""
    return test_data_generator.get_simple_workflow_dsl()


@pytest.fixture
def complex_workflow_dsl(test_data_generator):
    """Fixture providing complex workflow DSL."""
    return test_data_generator.get_complex_workflow_dsl()


@pytest.fixture
def docker_workflow_dsl(test_data_generator):
    """Fixture providing Docker workflow DSL."""
    return test_data_generator.get_docker_workflow_dsl()


@pytest.fixture
def test_parameters(test_data_generator):
    """Fixture providing test workflow parameters."""
    return test_data_generator.get_test_parameters()


@pytest.fixture
def workflow_dict(test_data_generator):
    """Fixture providing workflow as dictionary."""
    return test_data_generator.get_workflow_dict()


@pytest.fixture
def invalid_workflow_dsl(test_data_generator):
    """Fixture providing invalid workflow DSL."""
    return test_data_generator.get_invalid_workflow_dsl()


@pytest.fixture
def test_secrets(test_data_generator):
    """Fixture providing test secrets."""
    return test_data_generator.get_secrets_data()


class MockScenarios:
    """Pre-defined mock scenarios for different test cases."""
    
    @staticmethod
    def api_timeout_error():
        """Scenario: API timeout error."""
        mock = MockWorkflowAPIClient()
        mock.compile_workflow.side_effect = asyncio.TimeoutError("API request timed out")
        return mock
    
    @staticmethod
    def api_authentication_error():
        """Scenario: API authentication error."""
        mock = MockWorkflowAPIClient()
        mock.compile_workflow.side_effect = Exception("Authentication failed: Invalid API key")
        return mock
    
    @staticmethod
    def workflow_compilation_error():
        """Scenario: Workflow compilation error."""
        mock = MockWorkflowAPIClient()
        mock.compile_workflow.return_value = {
            "workflow_id": None,
            "status": "failed",
            "validation_errors": [
                "Invalid step name: 'invalid-step-name'",
                "Missing required field: 'run' in step 2"
            ],
            "docker_required": False
        }
        return mock
    
    @staticmethod
    def workflow_execution_failure():
        """Scenario: Workflow execution failure."""
        mock = MockWorkflowAPIClient()
        mock.execute_workflow.return_value = {
            "execution_id": "exec-failed-123",
            "status": "failed",
            "output": "Command failed with exit code 1",
            "logs": ["Starting workflow", "Step 1 failed", "Workflow terminated"],
            "exit_code": 1,
            "error": "Step execution failed"
        }
        return mock
    
    @staticmethod
    def no_runners_available():
        """Scenario: No workflow runners available."""
        mock = MockWorkflowAPIClient()
        mock.get_runners.return_value = {"runners": []}
        return mock
    
    @staticmethod
    def unhealthy_runners():
        """Scenario: All runners are unhealthy."""
        mock = MockWorkflowAPIClient()
        mock.get_runners.return_value = {
            "runners": [
                {
                    "id": "runner-1",
                    "name": "Unhealthy Runner 1",
                    "status": "unhealthy",
                    "version": "1.0.0",
                    "capabilities": ["python"],
                    "last_heartbeat": "2024-01-01T00:00:00Z"
                }
            ]
        }
        return mock


@pytest.fixture
def mock_scenarios():
    """Fixture providing mock scenarios."""
    return MockScenarios()