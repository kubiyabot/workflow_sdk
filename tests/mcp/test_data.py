"""Comprehensive test data sets for MCP functional correctness testing.

This module contains extensive test data covering various scenarios including
typical use cases, edge cases, error conditions, and boundary testing.
"""

import json
from typing import Any, Dict, List, Optional, Union


class WorkflowTestData:
    """Test data for workflow compilation and execution."""
    
    # Simple workflow scenarios
    SIMPLE_WORKFLOWS = {
        "hello_world": {
            "dsl": """
name: hello_world
description: Simple hello world workflow
steps:
  - name: greet
    run: echo "Hello, World!"
""",
            "expected_output": "Hello, World!",
            "docker_required": False
        },
        
        "environment_check": {
            "dsl": """
name: env_check
description: Check environment variables
steps:
  - name: check_env
    run: |
      echo "Current user: $(whoami)"
      echo "Current directory: $(pwd)"
      echo "Environment: $ENV"
""",
            "expected_output": "Current user:",
            "docker_required": False
        },
        
        "file_operations": {
            "dsl": """
name: file_ops
description: Basic file operations
steps:
  - name: create_file
    run: echo "test content" > /tmp/test.txt
  - name: read_file
    run: cat /tmp/test.txt
  - name: cleanup
    run: rm -f /tmp/test.txt
""",
            "expected_output": "test content",
            "docker_required": False
        }
    }
    
    # Complex workflow scenarios
    COMPLEX_WORKFLOWS = {
        "data_pipeline": {
            "dsl": """
name: data_processing_pipeline
description: Complex data processing workflow
environment:
  variables:
    BATCH_SIZE: 1000
    OUTPUT_FORMAT: json
steps:
  - name: validate_input
    run: |
      if [ ! -f "$INPUT_FILE" ]; then
        echo "Error: Input file not found"
        exit 1
      fi
      echo "Input validation passed"
  
  - name: process_data
    depends_on: [validate_input]
    run: |
      echo "Processing data with batch size: $BATCH_SIZE"
      # Simulate data processing
      for i in {1..5}; do
        echo "Processing batch $i"
        sleep 0.1
      done
      echo "Data processing completed"
  
  - name: generate_report
    depends_on: [process_data]
    run: |
      echo "Generating report in format: $OUTPUT_FORMAT"
      echo '{"status": "completed", "batches_processed": 5}' > /tmp/report.json
      echo "Report generated successfully"
  
  - name: validate_output
    depends_on: [generate_report]
    run: |
      if [ -f "/tmp/report.json" ]; then
        echo "Output validation passed"
        cat /tmp/report.json
      else
        echo "Error: Output file not found"
        exit 1
      fi
""",
            "parameters": {
                "INPUT_FILE": "/tmp/input.csv",
                "BATCH_SIZE": 500,
                "OUTPUT_FORMAT": "json"
            },
            "expected_output": "Output validation passed",
            "docker_required": False
        },
        
        "ci_cd_pipeline": {
            "dsl": """
name: ci_cd_pipeline
description: Continuous integration and deployment pipeline
steps:
  - name: checkout_code
    run: |
      echo "Checking out code from repository"
      mkdir -p /tmp/project
      echo "print('Hello from CI/CD')" > /tmp/project/main.py
  
  - name: install_dependencies
    depends_on: [checkout_code]
    run: |
      echo "Installing dependencies"
      # Simulate dependency installation
      echo "Dependencies installed successfully"
  
  - name: run_tests
    depends_on: [install_dependencies]
    run: |
      echo "Running test suite"
      cd /tmp/project
      python3 -c "print('All tests passed')"
  
  - name: build_artifact
    depends_on: [run_tests]
    run: |
      echo "Building deployment artifact"
      cd /tmp/project
      tar -czf app.tar.gz main.py
      echo "Artifact built successfully"
  
  - name: deploy
    depends_on: [build_artifact]
    run: |
      echo "Deploying to production"
      echo "Deployment completed successfully"
""",
            "expected_output": "Deployment completed successfully",
            "docker_required": False
        }
    }
    
    # Docker-required workflows
    DOCKER_WORKFLOWS = {
        "python_data_analysis": {
            "dsl": """
name: python_data_analysis
description: Python data analysis requiring specialized packages
steps:
  - name: setup_environment
    type: python
    code: |
      import sys
      print(f"Python version: {sys.version}")
      
  - name: data_analysis
    type: python
    code: |
      import pandas as pd
      import numpy as np
      import matplotlib.pyplot as plt
      
      # Create sample data
      data = pd.DataFrame({
          'x': np.random.randn(100),
          'y': np.random.randn(100)
      })
      
      # Perform analysis
      correlation = data['x'].corr(data['y'])
      print(f"Correlation: {correlation}")
      
      # Generate plot
      plt.figure(figsize=(8, 6))
      plt.scatter(data['x'], data['y'])
      plt.title('Data Analysis Results')
      plt.savefig('/tmp/analysis.png')
      print("Analysis completed successfully")
  
  - name: generate_report
    run: |
      echo "Analysis report generated"
      if [ -f "/tmp/analysis.png" ]; then
        echo "Plot saved successfully"
      fi
""",
            "expected_output": "Analysis completed successfully",
            "docker_required": True,
            "required_packages": ["pandas", "numpy", "matplotlib"]
        },
        
        "machine_learning_workflow": {
            "dsl": """
name: ml_training
description: Machine learning model training workflow
steps:
  - name: prepare_data
    type: python
    code: |
      import pandas as pd
      from sklearn.model_selection import train_test_split
      from sklearn.datasets import make_classification
      
      # Generate sample dataset
      X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
      X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
      
      print(f"Training set size: {len(X_train)}")
      print(f"Test set size: {len(X_test)}")
  
  - name: train_model
    type: python
    code: |
      from sklearn.ensemble import RandomForestClassifier
      from sklearn.metrics import accuracy_score
      import pickle
      
      # Train model
      model = RandomForestClassifier(n_estimators=100)
      model.fit(X_train, y_train)
      
      # Evaluate model
      predictions = model.predict(X_test)
      accuracy = accuracy_score(y_test, predictions)
      
      print(f"Model accuracy: {accuracy}")
      
      # Save model
      with open('/tmp/model.pkl', 'wb') as f:
          pickle.dump(model, f)
      print("Model saved successfully")
""",
            "expected_output": "Model saved successfully",
            "docker_required": True,
            "required_packages": ["pandas", "scikit-learn", "numpy"]
        }
    }
    
    # Error scenarios
    ERROR_WORKFLOWS = {
        "compilation_error": {
            "dsl": """
invalid_workflow_structure:
  - missing_name_field
  - improper_steps_format
    bad_indentation:
""",
            "expected_error": "validation_errors",
            "error_type": "compilation"
        },
        
        "execution_error": {
            "dsl": """
name: failing_workflow
description: Workflow that fails during execution
steps:
  - name: failing_step
    run: |
      echo "About to fail"
      exit 1
  - name: unreachable_step
    depends_on: [failing_step]
    run: echo "This should not execute"
""",
            "expected_error": "exit_code",
            "error_type": "execution"
        },
        
        "missing_dependency": {
            "dsl": """
name: missing_dep
description: Workflow with missing command
steps:
  - name: missing_command
    run: nonexistent_command --help
""",
            "expected_error": "command not found",
            "error_type": "execution"
        }
    }


class ParameterTestData:
    """Test data for parameter validation and handling."""
    
    # Valid parameter combinations
    VALID_PARAMETERS = {
        "compile_workflow": [
            {
                "dsl_code": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"],
                "name": "test_workflow_1"
            },
            {
                "dsl_code": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"],
                "name": "test_workflow_2",
                "description": "Test workflow with description"
            },
            {
                "dsl_code": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"],
                "name": "test_workflow_3",
                "description": "Test workflow with all options",
                "runner": "default_runner",
                "prefer_docker": True,
                "provide_missing_secrets": {"API_KEY": "test_key"}
            }
        ],
        
        "execute_workflow": [
            {
                "workflow_input": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"]
            },
            {
                "workflow_input": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"],
                "params": {"ENV": "test"}
            },
            {
                "workflow_input": {
                    "name": "dict_workflow",
                    "steps": [{"name": "test", "run": "echo test"}]
                },
                "params": {"TEST_VAR": "value"},
                "dry_run": True
            }
        ],
        
        "get_workflow_runners": [
            {},
            {"refresh": True},
            {"include_health": True, "component_filter": "docker"}
        ],
        
        "get_integrations": [
            {},
            {"category": "communication"},
            {"refresh": True, "category": "data_processing"}
        ],
        
        "get_workflow_secrets": [
            {},
            {"pattern": "DB_*"},
            {"task_type": "data_processing", "refresh": True}
        ]
    }
    
    # Edge case parameters
    EDGE_CASE_PARAMETERS = {
        "empty_values": {
            "compile_workflow": {
                "dsl_code": "",
                "name": "",
                "description": ""
            },
            "execute_workflow": {
                "workflow_input": "",
                "params": {}
            }
        },
        
        "large_values": {
            "compile_workflow": {
                "dsl_code": "name: large_workflow\n" + "steps:\n" + 
                           "".join([f"  - name: step_{i}\n    run: echo 'Step {i}'\n" for i in range(100)]),
                "name": "x" * 1000,
                "description": "y" * 5000
            }
        },
        
        "special_characters": {
            "compile_workflow": {
                "dsl_code": """
name: special_chars_workflow
description: Workflow with special characters: åäö!@#$%^&*()
steps:
  - name: unicode_test
    run: echo "Testing unicode: 🚀🎉🔥"
""",
                "name": "workflow_with_émojis_🚀",
                "description": "Description with special chars: !@#$%^&*()"
            }
        }
    }


class ResponseTestData:
    """Expected response data for different scenarios."""
    
    # Expected successful responses
    SUCCESS_RESPONSES = {
        "compile_workflow": {
            "status": "compiled",
            "workflow_id": "wf-12345",
            "validation_errors": [],
            "docker_required": False
        },
        
        "execute_workflow": {
            "status": "completed",
            "execution_id": "exec-12345",
            "exit_code": 0,
            "output": "Hello, World!"
        },
        
        "get_workflow_runners": {
            "runners": [
                {
                    "id": "runner-1",
                    "name": "Test Runner",
                    "status": "healthy",
                    "capabilities": ["python", "shell"]
                }
            ]
        },
        
        "get_integrations": {
            "integrations": [
                {
                    "name": "slack",
                    "category": "communication",
                    "required_secrets": ["SLACK_TOKEN"]
                }
            ]
        },
        
        "get_workflow_secrets": {
            "secrets": [
                {
                    "name": "DATABASE_URL",
                    "required": True,
                    "task_type": "data_processing"
                }
            ]
        }
    }
    
    # Expected error responses
    ERROR_RESPONSES = {
        "authentication_error": {
            "status": "error",
            "error": "Authentication failed: Invalid API key",
            "error_code": 401
        },
        
        "validation_error": {
            "status": "failed",
            "validation_errors": [
                "Missing required field: 'name'",
                "Invalid step format in step 2"
            ],
            "error_code": 400
        },
        
        "execution_error": {
            "status": "failed",
            "execution_id": "exec-failed-123",
            "exit_code": 1,
            "error": "Command failed",
            "logs": ["Starting execution", "Error: Command not found"]
        },
        
        "timeout_error": {
            "status": "timeout",
            "error": "Request timed out after 30 seconds",
            "error_code": 408
        }
    }


class IntegrationTestData:
    """Test data for integration scenarios."""
    
    # Multi-step workflow scenarios
    INTEGRATION_SCENARIOS = {
        "compile_and_execute": {
            "compile_params": {
                "dsl_code": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"],
                "name": "integration_test_workflow"
            },
            "execute_params": {
                "workflow_input": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"]
            },
            "expected_flow": [
                "compile_workflow",
                "execute_workflow"
            ]
        },
        
        "full_pipeline": {
            "steps": [
                ("get_workflow_runners", {}),
                ("get_integrations", {"category": "data"}),
                ("compile_workflow", {
                    "dsl_code": WorkflowTestData.COMPLEX_WORKFLOWS["data_pipeline"]["dsl"],
                    "name": "pipeline_test"
                }),
                ("execute_workflow", {
                    "workflow_input": WorkflowTestData.COMPLEX_WORKFLOWS["data_pipeline"]["dsl"],
                    "params": WorkflowTestData.COMPLEX_WORKFLOWS["data_pipeline"]["parameters"]
                })
            ]
        }
    }


class BoundaryTestData:
    """Test data for boundary condition testing."""
    
    # Resource limits
    RESOURCE_LIMITS = {
        "max_workflow_size": {
            "dsl_code": "name: large_workflow\n" + 
                       "steps:\n" + 
                       "".join([f"  - name: step_{i}\n    run: echo 'Step {i}'\n" 
                               for i in range(1000)]),  # 1000 steps
            "expected_behavior": "should_handle_gracefully"
        },
        
        "max_parameter_length": {
            "params": {
                "LARGE_PARAM": "x" * 100000  # 100KB parameter
            },
            "expected_behavior": "should_validate_size"
        },
        
        "concurrent_executions": {
            "concurrent_count": 10,
            "workflow": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"],
            "expected_behavior": "should_handle_concurrency"
        }
    }
    
    # Time-based scenarios
    TIME_SCENARIOS = {
        "long_running_workflow": {
            "dsl": """
name: long_running_test
description: Workflow that takes time to execute
steps:
  - name: wait_step
    run: sleep 5
  - name: complete_step
    run: echo "Long task completed"
""",
            "expected_duration": 5,
            "timeout_threshold": 10
        },
        
        "quick_workflow": {
            "dsl": WorkflowTestData.SIMPLE_WORKFLOWS["hello_world"]["dsl"],
            "expected_duration": 0.1,
            "timeout_threshold": 1
        }
    }


# Export test data classes for easy import
__all__ = [
    'WorkflowTestData',
    'ParameterTestData', 
    'ResponseTestData',
    'IntegrationTestData',
    'BoundaryTestData'
]