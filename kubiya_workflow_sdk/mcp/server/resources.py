"""MCP Resources for workflow examples and templates."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def register_resources(mcp, server):
    """Register resources for workflow examples and templates."""
    
    @mcp.resource("workflow://examples/hello-world")
    async def hello_world_example() -> str:
        """Simple hello world workflow example."""
        return """from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("hello-world")
wf.description("A simple greeting workflow")

# Basic step
wf.step("greet", "echo 'Hello, World!'")
wf.step("timestamp", "date '+%Y-%m-%d %H:%M:%S'")
"""

    @mcp.resource("workflow://examples/docker-python")
    async def docker_python_example() -> str:
        """Python Docker workflow example."""
        return """from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("python-data-processor")
wf.description("Process data using Python in Docker")
wf.params(
    input_data={"default": "1,2,3,4,5", "description": "Comma-separated numbers"},
    operation={"default": "sum", "description": "sum, mean, or max"}
)

wf.step("process").docker(
    image="python:3.11-slim",
    content='''
data = [float(x) for x in "{{input_data}}".split(",")]
operation = "{{operation}}"

if operation == "sum":
    result = sum(data)
elif operation == "mean":
    result = sum(data) / len(data)
elif operation == "max":
    result = max(data)
else:
    result = "Unknown operation"

print(f"Result of {operation}: {result}")
print(f"Input data: {data}")
'''
)
"""

    @mcp.resource("workflow://examples/parallel-processing")
    async def parallel_example() -> str:
        """Parallel processing workflow example."""
        return """from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("parallel-processor")
wf.description("Process multiple tasks in parallel")
wf.params(
    urls={"default": "https://api.github.com,https://api.gitlab.com", "description": "Comma-separated URLs"}
)

# Split URLs into list
wf.step("prepare", "echo '{{urls}}' > urls.txt")

# Process in parallel
with wf.parallel_steps():
    wf.step("check-github").docker(
        image="alpine/curl",
        content="curl -s -o /dev/null -w '%{http_code}' https://api.github.com"
    )
    
    wf.step("check-gitlab").docker(
        image="alpine/curl", 
        content="curl -s -o /dev/null -w '%{http_code}' https://api.gitlab.com"
    )
    
    wf.step("check-docker").docker(
        image="alpine/curl",
        content="curl -s -o /dev/null -w '%{http_code}' https://hub.docker.com"
    )

# Combine results
wf.step("report", "echo 'All health checks completed'")
"""

    @mcp.resource("workflow://examples/ci-cd-pipeline")
    async def cicd_example() -> str:
        """CI/CD pipeline workflow example."""
        return """from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("ci-cd-pipeline")
wf.description("Complete CI/CD pipeline with testing and deployment")
wf.params(
    repo_url={"required": True, "description": "Git repository URL"},
    branch={"default": "main", "description": "Branch to build"},
    deploy_env={"default": "staging", "description": "staging or production"}
)

# Clone repository
wf.step("clone").docker(
    image="alpine/git",
    content="git clone -b {{branch}} {{repo_url}} /workspace"
)

# Run tests
wf.step("test").docker(
    image="python:3.11",
    content='''
cd /workspace
pip install -r requirements.txt
pytest tests/ -v --junitxml=test-results.xml
'''
).depends_on("clone")

# Build Docker image
wf.step("build").docker(
    image="docker:24-dind",
    content="cd /workspace && docker build -t myapp:{{branch}}-$(date +%s) ."
).depends_on("test")

# Deploy based on environment
wf.step("deploy-staging").docker(
    image="bitnami/kubectl:latest",
    content="kubectl set image deployment/myapp myapp=myapp:{{branch}}-latest -n staging"
).depends_on("build").condition("{{deploy_env}} == 'staging'")

wf.step("deploy-production").docker(
    image="bitnami/kubectl:latest",
    content="kubectl set image deployment/myapp myapp=myapp:{{branch}}-latest -n production"
).depends_on("build").condition("{{deploy_env}} == 'production'")

# Cleanup
wf.step("cleanup", "echo 'Pipeline completed'").continue_on("any")
"""

    @mcp.resource("workflow://examples/data-pipeline")
    async def data_pipeline_example() -> str:
        """Data processing pipeline example."""
        return """from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("data-etl-pipeline")
wf.description("Extract, Transform, Load data pipeline")
wf.params(
    source_url={"required": True, "description": "Data source URL"},
    target_format={"default": "parquet", "description": "csv, json, or parquet"},
    quality_check={"default": True, "description": "Run data quality checks"}
)

# Extract data
wf.step("extract").docker(
    image="alpine/curl",
    content="curl -L -o raw_data.csv {{source_url}}"
)

# Transform data
wf.step("transform").docker(
    image="jupyter/scipy-notebook:latest",
    content='''
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv("raw_data.csv")
print(f"Loaded {len(df)} rows")

# Clean data
df = df.dropna()
df = df[df.select_dtypes(include=[np.number]).columns].clip(lower=0)

# Save in target format
if "{{target_format}}" == "parquet":
    df.to_parquet("transformed_data.parquet")
elif "{{target_format}}" == "json":
    df.to_json("transformed_data.json", orient="records")
else:
    df.to_csv("transformed_data.csv", index=False)

print(f"Transformed {len(df)} rows to {{target_format}}")
'''
).depends_on("extract")

# Quality checks
wf.step("quality-check").docker(
    image="python:3.11-slim",
    content='''
import pandas as pd

# Load transformed data
if "{{target_format}}" == "parquet":
    df = pd.read_parquet("transformed_data.parquet")
else:
    df = pd.read_csv("transformed_data.csv")

# Run checks
print(f"Row count: {len(df)}")
print(f"Column count: {len(df.columns)}")
print(f"Missing values: {df.isnull().sum().sum()}")
print(f"Memory usage: {df.memory_usage().sum() / 1024**2:.2f} MB")

# Validate
assert len(df) > 0, "No data found"
assert df.isnull().sum().sum() == 0, "Found missing values"
'''
).depends_on("transform").condition("{{quality_check}}")

# Load to destination
wf.step("load", "echo 'Data ready for loading to destination'").depends_on("transform")
"""

    @mcp.resource("workflow://templates/docker-commands")
    async def docker_templates() -> Dict[str, Any]:
        """Common Docker command templates."""
        return {
            "python_script": {
                "description": "Run Python script in Docker",
                "template": '''wf.step("python-task").docker(
    image="python:3.11-slim",
    content=\'\'\'
# Your Python code here
import sys
print(f"Python {sys.version}")
\'\'\'
)'''
            },
            "nodejs_script": {
                "description": "Run Node.js script in Docker",
                "template": '''wf.step("node-task").docker(
    image="node:20-slim",
    content=\'\'\'
console.log(`Node.js ${process.version}`);
// Your JavaScript code here
\'\'\'
)'''
            },
            "database_query": {
                "description": "Run database queries",
                "template": '''wf.step("db-query").docker(
    image="postgres:15-alpine",
    content="psql -h {{db_host}} -U {{db_user}} -d {{db_name}} -c 'SELECT COUNT(*) FROM users;'"
)'''
            },
            "api_call": {
                "description": "Make API calls",
                "template": '''wf.step("api-call").docker(
    image="alpine/curl",
    content="curl -X GET {{api_url}} -H 'Authorization: Bearer {{api_token}}'"
)'''
            },
            "file_processing": {
                "description": "Process files with tools",
                "template": '''wf.step("process-file").docker(
    image="alpine:latest",
    content="awk '{print $1}' input.txt | sort | uniq > output.txt"
)'''
            }
        }

    @mcp.resource("workflow://templates/patterns")
    async def workflow_patterns() -> Dict[str, Any]:
        """Common workflow patterns."""
        return {
            "retry_with_backoff": {
                "description": "Retry failed steps",
                "code": '''wf.step("flaky-operation", "curl https://unreliable-api.com").retry(
    max_attempts=5,
    delay_seconds=2,
)'''
            },
            "conditional_execution": {
                "description": "Execute steps based on conditions",
                "code": '''wf.step("prod-only", "deploy-to-prod.sh").condition("{{environment}} == 'production'")
wf.step("debug", "enable-debug-mode.sh").condition("{{debug_mode}} == true")'''
            },
            "error_handling": {
                "description": "Handle errors gracefully",
                "code": '''wf.step("main-task", "process-data.sh")
wf.step("on-error", "send-alert.sh").condition("{{main-task.status}} == 'failed'")
wf.step("cleanup", "rm -rf /tmp/*").continue_on("any")'''
            },
            "parallel_map": {
                "description": "Process list items in parallel",
                "code": '''items = ["item1", "item2", "item3"]
with wf.parallel_steps():
    for item in items:
        wf.step(f"process-{item}", f"echo 'Processing {item}'")'''
            },
            "approval_gate": {
                "description": "Manual approval before proceeding",
                "code": '''wf.step("build", "build-app.sh")
wf.step("approval", "echo 'Waiting for approval'").approval_required()
wf.step("deploy", "deploy-app.sh").depends_on("approval")'''
            }
        }

    @mcp.resource("workflow://best-practices")
    async def best_practices() -> Dict[str, List[str]]:
        """Workflow development best practices."""
        return {
            "naming": [
                "Use kebab-case for workflow names",
                "Use descriptive step names",
                "Prefix related steps (e.g., 'db-migrate', 'db-seed')"
            ],
            "docker": [
                "Use specific image tags, not 'latest'",
                "Prefer slim/alpine variants for size",
                "Use official images when possible",
                "Cache dependencies in custom images"
            ],
            "parameters": [
                "Provide defaults for optional parameters",
                "Use descriptive parameter names",
                "Validate parameter values early",
                "Document parameter purpose"
            ],
            "error_handling": [
                "Add retry logic for network operations",
                "Use continue_on for cleanup steps",
                "Log errors with context",
                "Set appropriate timeouts"
            ],
            "security": [
                "Never hardcode secrets",
                "Use parameter masking for sensitive data",
                "Scan Docker images for vulnerabilities",
                "Limit container permissions"
            ],
            "performance": [
                "Run independent steps in parallel",
                "Use appropriate runner sizes",
                "Cache build artifacts",
                "Minimize Docker image sizes"
            ]
        }

    @mcp.resource("workflow://docker-images")
    async def recommended_images() -> Dict[str, List[Dict[str, str]]]:
        """Recommended Docker images by category."""
        return {
            "languages": [
                {"name": "python:3.11-slim", "description": "Python 3.11 minimal"},
                {"name": "node:20-alpine", "description": "Node.js 20 Alpine"},
                {"name": "golang:1.21-alpine", "description": "Go 1.21 Alpine"},
                {"name": "openjdk:17-slim", "description": "Java 17 OpenJDK"},
                {"name": "ruby:3.2-slim", "description": "Ruby 3.2 minimal"}
            ],
            "databases": [
                {"name": "postgres:15-alpine", "description": "PostgreSQL 15"},
                {"name": "mysql:8.0", "description": "MySQL 8.0"},
                {"name": "mongo:7.0", "description": "MongoDB 7.0"},
                {"name": "redis:7-alpine", "description": "Redis 7"}
            ],
            "tools": [
                {"name": "alpine/curl", "description": "curl in Alpine"},
                {"name": "alpine/git", "description": "git in Alpine"},
                {"name": "docker:24-dind", "description": "Docker in Docker"},
                {"name": "bitnami/kubectl", "description": "Kubernetes CLI"}
            ],
            "data_science": [
                {"name": "jupyter/scipy-notebook", "description": "Jupyter with scientific packages"},
                {"name": "tensorflow/tensorflow", "description": "TensorFlow latest"},
                {"name": "pytorch/pytorch", "description": "PyTorch latest"}
            ]
        }


# Export for easy access
workflow_examples = [
    "workflow://examples/hello-world",
    "workflow://examples/docker-python",
    "workflow://examples/parallel-processing",
    "workflow://examples/ci-cd-pipeline",
    "workflow://examples/data-pipeline"
]

docker_templates = [
    "workflow://templates/docker-commands",
    "workflow://templates/patterns"
] 