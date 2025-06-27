"""Output format schemas for MCP tools validation.

This module defines expected output schemas for all MCP tools to validate
that the final output structure and content conform to specifications.
"""

from typing import Dict, Any, List, Optional, Union
import jsonschema


class MCPOutputSchemas:
    """Schemas for validating MCP tool output formats."""

    # Schema for compile_workflow output
    COMPILE_WORKFLOW_SCHEMA = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "workflow_id": {"type": ["string", "null"]},
            "status": {"type": "string", "enum": ["compiled", "failed", "pending"]},
            "validation_errors": {
                "type": "array",
                "items": {"type": "string"}
            },
            "manifest": {
                "type": ["object", "null"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "run": {"type": ["string", "null"]},
                                "code": {"type": ["string", "null"]},
                                "docker": {"type": ["object", "null"]}
                            },
                            "required": ["name"]
                        }
                    }
                },
                "required": ["name", "steps"]
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"}
            },
            "docker_required": {"type": "boolean"},
            "runner_info": {
                "type": ["object", "null"],
                "properties": {
                    "name": {"type": "string"},
                    "status": {"type": "string"},
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "compilation_time": {"type": ["number", "null"]},
            "errors": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "anyOf": [
            {"required": ["success"]},
            {"required": ["status"]},
            {"required": ["errors"]}
        ]
    }

    # Schema for execute_workflow output
    EXECUTE_WORKFLOW_SCHEMA = {
        "type": "object",
        "properties": {
            "execution_id": {"type": ["string", "null"]},
            "status": {"type": "string", "enum": ["started", "running", "completed", "failed", "cancelled"]},
            "exit_code": {"type": ["integer", "null"]},
            "output": {"type": ["string", "null"]},
            "error": {"type": ["string", "null"]},
            "logs": {
                "type": "array",
                "items": {"type": "string"}
            },
            "duration": {"type": ["number", "null"]},
            "parameters_used": {
                "type": ["object", "null"]
            },
            "runner": {"type": ["string", "null"]},
            "image": {"type": ["string", "null"]},
            "stream_url": {"type": ["string", "null"]},
            "artifacts": {
                "type": ["array", "null"],
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "path": {"type": "string"},
                        "size": {"type": "integer"}
                    }
                }
            }
        },
        "anyOf": [
            {"required": ["execution_id"]},
            {"required": ["status"]},
            {"required": ["output"]},
            {"required": ["error"]}
        ]
    }

    # Schema for get_workflow_runners output
    GET_RUNNERS_SCHEMA = {
        "type": "object",
        "properties": {
            "runners": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "status": {"type": "string", "enum": ["healthy", "unhealthy", "maintenance", "offline"]},
                        "version": {"type": ["string", "null"]},
                        "capabilities": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "last_heartbeat": {"type": ["string", "null"]},
                        "health_info": {
                            "type": ["object", "null"],
                            "properties": {
                                "cpu_usage": {"type": "number"},
                                "memory_usage": {"type": "number"},
                                "disk_usage": {"type": "number"}
                            }
                        }
                    },
                    "required": ["id", "name", "status"]
                }
            },
            "total_count": {"type": ["integer", "null"]},
            "healthy_count": {"type": ["integer", "null"]},
            "filter_applied": {"type": ["string", "null"]},
            "last_refresh": {"type": ["string", "null"]}
        },
        "required": ["runners"]
    }

    # Schema for get_integrations output
    GET_INTEGRATIONS_SCHEMA = {
        "type": "object",
        "properties": {
            "integrations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": ["string", "null"]},
                        "category": {"type": ["string", "null"]},
                        "docker_image": {"type": ["string", "null"]},
                        "required_secrets": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "optional_secrets": {
                            "type": ["array", "null"],
                            "items": {"type": "string"}
                        },
                        "version": {"type": ["string", "null"]},
                        "documentation_url": {"type": ["string", "null"]},
                        "enabled": {"type": ["boolean", "null"]}
                    },
                    "required": ["name"]
                }
            },
            "categories": {
                "type": ["array", "null"],
                "items": {"type": "string"}
            },
            "total_count": {"type": ["integer", "null"]},
            "filtered_count": {"type": ["integer", "null"]},
            "category_filter": {"type": ["string", "null"]}
        },
        "required": ["integrations"]
    }

    # Schema for get_workflow_secrets output
    GET_SECRETS_SCHEMA = {
        "type": "object",
        "properties": {
            "secrets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": ["string", "null"]},
                        "task_type": {"type": ["string", "null"]},
                        "required": {"type": "boolean"},
                        "pattern": {"type": ["string", "null"]},
                        "example_value": {"type": ["string", "null"]},
                        "last_updated": {"type": ["string", "null"]},
                        "used_by": {
                            "type": ["array", "null"],
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["name", "required"]
                }
            },
            "total_count": {"type": ["integer", "null"]},
            "required_count": {"type": ["integer", "null"]},
            "optional_count": {"type": ["integer", "null"]},
            "pattern_filter": {"type": ["string", "null"]},
            "task_type_filter": {"type": ["string", "null"]}
        },
        "required": ["secrets"]
    }

    # Schema for MCP content response wrapper
    MCP_CONTENT_SCHEMA = {
        "type": "object",
        "properties": {
            "content": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["text", "image", "resource"]},
                        "text": {"type": ["string", "null"]},
                        "data": {"type": ["string", "null"]},
                        "mimeType": {"type": ["string", "null"]}
                    },
                    "anyOf": [
                        {"required": ["text"]},
                        {"required": ["data"]},
                        {"required": ["type"]}
                    ]
                }
            },
            "isError": {"type": "boolean"}
        },
        "required": ["content"]
    }

    # Error response schema
    ERROR_RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "error_code": {"type": ["integer", "string", "null"]},
            "error_type": {"type": ["string", "null"]},
            "details": {"type": ["object", "array", "string", "null"]},
            "suggestions": {
                "type": ["array", "null"],
                "items": {"type": "string"}
            },
            "timestamp": {"type": ["string", "null"]},
            "request_id": {"type": ["string", "null"]}
        },
        "required": ["error"]
    }

    @classmethod
    def validate_output(cls, tool_name: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool output against its schema.
        
        Args:
            tool_name: Name of the MCP tool
            output: Output data to validate
            
        Returns:
            Validation result with success status and any errors
        """
        schema_map = {
            "compile_workflow": cls.COMPILE_WORKFLOW_SCHEMA,
            "execute_workflow": cls.EXECUTE_WORKFLOW_SCHEMA,
            "get_workflow_runners": cls.GET_RUNNERS_SCHEMA,
            "get_integrations": cls.GET_INTEGRATIONS_SCHEMA,
            "get_workflow_secrets": cls.GET_SECRETS_SCHEMA
        }
        
        if tool_name not in schema_map:
            return {
                "valid": False,
                "errors": [f"No schema defined for tool: {tool_name}"]
            }
        
        schema = schema_map[tool_name]
        
        try:
            jsonschema.validate(output, schema)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {
                "valid": False,
                "errors": [f"Schema validation failed: {e.message}"],
                "error_path": list(e.absolute_path) if e.absolute_path else [],
                "failed_value": e.instance
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"]
            }

    @classmethod
    def validate_mcp_response(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate MCP response wrapper format.
        
        Args:
            response: MCP response to validate
            
        Returns:
            Validation result
        """
        try:
            jsonschema.validate(response, cls.MCP_CONTENT_SCHEMA)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {
                "valid": False,
                "errors": [f"MCP response validation failed: {e.message}"],
                "error_path": list(e.absolute_path) if e.absolute_path else []
            }

    @classmethod
    def extract_tool_output(cls, mcp_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tool output from MCP response wrapper.
        
        Args:
            mcp_response: MCP response containing content array
            
        Returns:
            Extracted tool output data
        """
        if not isinstance(mcp_response, dict):
            return {}
        
        content = mcp_response.get("content", [])
        if not isinstance(content, list) or len(content) == 0:
            return {}
        
        # Look for text content that contains JSON
        for item in content:
            if isinstance(item, dict) and "text" in item:
                text = item["text"]
                if isinstance(text, str):
                    # Try to parse as JSON
                    try:
                        import json
                        return json.loads(text)
                    except (json.JSONDecodeError, ValueError):
                        # Return as text if not JSON
                        return {"output": text}
        
        return {}

    @classmethod
    def create_golden_file_data(cls, tool_name: str) -> Dict[str, Any]:
        """Create golden file data for a tool based on its schema.
        
        Args:
            tool_name: Name of the MCP tool
            
        Returns:
            Sample valid output data
        """
        golden_data = {
            "compile_workflow": {
                "success": True,
                "workflow_id": "golden-wf-123",
                "status": "compiled",
                "validation_errors": [],
                "manifest": {
                    "name": "golden_test_workflow",
                    "description": "Golden file test workflow",
                    "steps": [
                        {
                            "name": "golden_step",
                            "run": "echo 'Golden test'"
                        }
                    ]
                },
                "suggestions": ["Consider using Docker for better isolation"],
                "docker_required": False,
                "runner_info": {
                    "name": "golden_runner",
                    "status": "healthy",
                    "capabilities": ["python", "shell"]
                },
                "compilation_time": 1.23
            },
            "execute_workflow": {
                "execution_id": "golden-exec-123",
                "status": "completed",
                "exit_code": 0,
                "output": "Golden execution output",
                "logs": ["Starting golden execution", "Golden step completed", "Execution finished"],
                "duration": 2.45,
                "parameters_used": {"GOLDEN_PARAM": "golden_value"},
                "runner": "golden_runner"
            },
            "get_workflow_runners": {
                "runners": [
                    {
                        "id": "golden-runner-1",
                        "name": "Golden Runner 1",
                        "status": "healthy",
                        "version": "1.0.0",
                        "capabilities": ["python", "shell", "docker"],
                        "last_heartbeat": "2024-01-01T00:00:00Z",
                        "health_info": {
                            "cpu_usage": 45.2,
                            "memory_usage": 67.8,
                            "disk_usage": 23.1
                        }
                    }
                ],
                "total_count": 1,
                "healthy_count": 1,
                "last_refresh": "2024-01-01T00:00:00Z"
            },
            "get_integrations": {
                "integrations": [
                    {
                        "name": "golden_integration",
                        "description": "Golden test integration",
                        "category": "testing",
                        "docker_image": "golden/integration:latest",
                        "required_secrets": ["GOLDEN_TOKEN"],
                        "optional_secrets": ["GOLDEN_CONFIG"],
                        "version": "1.0.0",
                        "documentation_url": "https://docs.golden.com",
                        "enabled": True
                    }
                ],
                "categories": ["testing", "development"],
                "total_count": 1,
                "filtered_count": 1
            },
            "get_workflow_secrets": {
                "secrets": [
                    {
                        "name": "GOLDEN_SECRET",
                        "description": "Golden test secret",
                        "task_type": "testing",
                        "required": True,
                        "pattern": "GOLDEN_*",
                        "example_value": "golden_secret_value",
                        "last_updated": "2024-01-01T00:00:00Z",
                        "used_by": ["golden_workflow", "golden_integration"]
                    }
                ],
                "total_count": 1,
                "required_count": 1,
                "optional_count": 0
            }
        }
        
        return golden_data.get(tool_name, {})