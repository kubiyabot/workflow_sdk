"""Pytest configuration and fixtures for MCP testing."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

import pytest
import pytest_asyncio

from tests.mcp.helpers import (
    MCPTestServer,
    mcp_test_server,
    create_test_workflow_context,
    generate_test_dsl,
    generate_complex_test_dsl
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mcp_server() -> AsyncGenerator[MCPTestServer, None]:
    """Fixture to provide a running MCP server for tests."""
    async with mcp_test_server(
        server_module="kubiya_workflow_sdk.mcp.server",
        debug=os.getenv("MCP_TEST_DEBUG", "false").lower() == "true"
    ) as server:
        yield server


@pytest_asyncio.fixture
async def mcp_server_with_auth() -> AsyncGenerator[MCPTestServer, None]:
    """Fixture to provide a running MCP server with authentication for tests."""
    # Set up test environment variables for auth
    test_env = os.environ.copy()
    test_env.update({
        "KUBIYA_API_KEY": "test_api_key",
        "KUBIYA_BASE_URL": "https://api.kubiya.ai/api/v1"
    })
    
    async with mcp_test_server(
        server_module="kubiya_workflow_sdk.mcp.server",
        server_args=["--auth"],
        debug=os.getenv("MCP_TEST_DEBUG", "false").lower() == "true"
    ) as server:
        yield server


@pytest.fixture
def test_workflow_context() -> Dict[str, Any]:
    """Fixture providing test workflow context."""
    return {
        "workflow_name": "test_workflow",
        "runner_id": "test_runner", 
        "api_key": "test_api_key",
        "base_url": "https://api.kubiya.ai/api/v1",
        "secrets": {
            "TEST_SECRET": "test_value",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test"
        }
    }


@pytest.fixture
def simple_dsl() -> str:
    """Fixture providing simple test DSL."""
    return generate_test_dsl()


@pytest.fixture
def complex_dsl() -> str:
    """Fixture providing complex test DSL."""
    return generate_complex_test_dsl()


@pytest.fixture
def temp_workflow_file(simple_dsl: str) -> str:
    """Fixture providing a temporary workflow file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(simple_dsl)
        f.flush()
        yield f.name
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def invalid_dsl() -> str:
    """Fixture providing invalid DSL for error testing."""
    return """
invalid_yaml_structure:
  - missing_required_fields
  - no_proper_structure
    invalid_indentation
"""


@pytest.fixture
def docker_dsl() -> str:
    """Fixture providing DSL that should trigger Docker conversion."""
    return """
name: docker_test_workflow
description: Workflow that should be converted to Docker
steps:
  - name: complex_python_step
    type: python
    code: |
      import requests
      import pandas as pd
      import numpy as np
      
      # Complex operations that should trigger Docker
      data = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
      result = np.sum(data.values)
      
      # Make HTTP request
      response = requests.get('https://api.example.com/data')
      print(f"Result: {result}, Status: {response.status_code}")
      
  - name: shell_with_packages
    type: shell
    shell: |
      # Commands that suggest package dependencies
      pip install pandas numpy
      python -c "import pandas; print('pandas works')"
"""


@pytest.fixture
def test_secrets() -> Dict[str, str]:
    """Fixture providing test secrets."""
    return {
        "API_KEY": "test_api_key_value",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "JWT_SECRET": "test_jwt_secret",
        "WEBHOOK_SECRET": "test_webhook_secret"
    }
    

@pytest.fixture
def test_integrations() -> Dict[str, Any]:
    """Fixture providing test integration data."""
    return {
        "available_integrations": [
            {
                "name": "slack",
                "description": "Slack integration",
                "docker_image": "kubiya/slack-integration:latest",
                "required_secrets": ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"]
            },
            {
                "name": "github",
                "description": "GitHub integration", 
                "docker_image": "kubiya/github-integration:latest",
                "required_secrets": ["GITHUB_TOKEN"]
            },
            {
                "name": "jira",
                "description": "Jira integration",
                "docker_image": "kubiya/jira-integration:latest", 
                "required_secrets": ["JIRA_URL", "JIRA_USERNAME", "JIRA_PASSWORD"]
            }
        ]
    }


@pytest.fixture
def test_runners() -> Dict[str, Any]:
    """Fixture providing test runner data."""
    return {
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


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Auto-fixture to set up test environment variables."""
    # Set up test environment
    test_env_vars = {
        "KUBIYA_API_KEY": "test_api_key",
        "KUBIYA_BASE_URL": "https://api.kubiya.ai/api/v1",
        "MCP_TEST_MODE": "true",
        "PYTHONPATH": str(Path(__file__).parent.parent.parent)
    }
    
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def mock_http_responses():
    """Fixture for mocking HTTP responses in tests."""
    return {
        "runners": {
            "status_code": 200,
            "json": {
                "runners": [
                    {
                        "id": "test-runner-1",
                        "name": "Test Runner 1", 
                        "status": "healthy",
                        "version": "1.0.0"
                    }
                ]
            }
        },
        "integrations": {
            "status_code": 200,
            "json": {
                "integrations": [
                    {
                        "name": "test-integration",
                        "description": "Test integration",
                        "docker_image": "test/integration:latest"
                    }
                ]
            }
        }
    }