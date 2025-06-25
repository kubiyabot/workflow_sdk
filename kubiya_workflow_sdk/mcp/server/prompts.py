"""MCP Prompts for enhanced workflow generation."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def register_prompts(mcp, server):
    """Register prompts for better DSL generation."""
    
    @mcp.prompt()
    async def workflow_dsl_guide(
        task_description: str,
        prefer_docker: bool = True,
        complexity: str = "medium"
    ) -> str:
        """
        Generate a comprehensive guide for creating a workflow based on the task.
        
        Args:
            task_description: What the workflow should accomplish
            prefer_docker: Whether to prioritize Docker-based solutions
            complexity: simple, medium, or complex
            
        Returns:
            Detailed DSL guide with examples
        """
        # Get context
        runners = server.workflow_context.get_runner_suggestions()
        integrations = server.integration_context.get_context_prompt()
        secrets = server.secrets_context.get_context_prompt()
        docker_suggestions = server.integration_context.get_docker_suggestions(task_description)
        
        guide = f"""# Kubiya Workflow DSL Guide

## Task: {task_description}

### Key Rules:
1. NO decorators - use simple DSL: `wf = Workflow("name")`
2. Use descriptive step names
3. **ALWAYS use Docker for complex steps** (see guidelines below)
4. Add error handling for production workflows
5. Use secrets securely via {{{{secret:NAME}}}} syntax
6. Include files with wf.with_files() for configs/scripts

### When to Use Docker Steps (REQUIRED):
Use `wf.step("name").docker(image="...", content="...")` for:
- Package installations (pip, npm, apt-get, etc.)
- Scripts with imports or dependencies
- Multi-line scripts (>3 lines)
- Complex shell operations (&&, ||, pipes)
- Language-specific execution (Python, Node.js, Go, etc.)
- Database operations
- API calls with specific tools
- Data processing tasks

Simple one-line shell commands can use: `wf.step("name", "echo hello")`

### Basic Structure:
```python
from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("workflow-name")
wf.description("{task_description}")

# Add parameters
wf.params(
    param1={{"default": "value", "description": "What this parameter does"}},
    param2={{"required": True, "description": "Required parameter"}},
    secret_param={{"required": True, "secret": True, "description": "Sensitive value"}}
)

# Add environment variables (including secrets)
wf.env(
    MY_VAR="value",
    API_KEY="{{{{secret:API_KEY}}}}"
)

# Add files to the workflow
wf.with_files({{
    "config.json": '{{"key": "value"}}',
    "script.sh": '''#!/bin/bash
echo "Hello from script"
'''
}})

# Simple shell step (only for basic commands)
wf.step("simple", "echo 'Starting workflow'")

# Docker step (for anything complex)
wf.step("process").docker(
    image="python:3.11-slim",
    content="pip install pandas && python script.py"
)

# Docker with inline script
wf.step("analyze").docker(
    image="python:3.11-slim",
    content='''
import pandas as pd
df = pd.read_csv("data.csv")
print(df.describe())
'''
)
```

### Context:
{runners}

{integrations}

{secrets}

### Docker Recommendations:
"""
        
        if prefer_docker and docker_suggestions:
            guide += f"\nFor your task, consider these Docker images:\n"
            for img in docker_suggestions[:3]:
                guide += f"- {img}\n"
        
        # Add complexity-specific examples
        if complexity == "simple":
            guide += """
### Simple Example:
```python
wf = Workflow("hello-world")
wf.description("Simple greeting workflow")
wf.step("greet", "echo 'Hello, World!'")
wf.step("date", "date")
```
"""
        elif complexity == "medium":
            guide += """
### Medium Example:
```python
wf = Workflow("data-processor")
wf.description("Process data with Python")
wf.params(
    input_file={{"default": "data.csv"}},
    output_format={{"default": "json"}},
    api_key={{"required": True, "secret": True}}
)

# Use secrets
wf.env(API_KEY="{{{{params.api_key}}}}")

# Include processing script
wf.with_files({{
    "process.py": '''
import pandas as pd
import os

api_key = os.environ.get("API_KEY")
df = pd.read_csv("{{{{input_file}}}}")
result = df.describe()

if "{{{{output_format}}}}" == "json":
    print(result.to_json())
else:
    print(result.to_csv())
'''
}})

wf.step("process").docker(
    image="python:3.11-slim",
    content="python process.py"
)
```
"""
        else:  # complex
            guide += """
### Complex Example:
```python
wf = Workflow("ml-pipeline")
wf.description("ML training pipeline with secrets")
wf.params(
    dataset_url={{"required": True}},
    model_name={{"default": "model"}},
    epochs={{"default": 10}},
    aws_access_key={{"required": True, "secret": True}},
    aws_secret_key={{"required": True, "secret": True}}
)

# Set up AWS credentials
wf.env(
    AWS_ACCESS_KEY_ID="{{{{params.aws_access_key}}}}",
    AWS_SECRET_ACCESS_KEY="{{{{params.aws_secret_key}}}}"
)

# Include training script
wf.with_files({{
    "train.py": open("local_train.py").read(),
    "requirements.txt": '''
pandas==2.0.0
scikit-learn==1.3.0
boto3==1.28.0
'''
}})

# Download data
wf.step("download").docker(
    image="amazon/aws-cli:latest",
    content="aws s3 cp {{{{dataset_url}}}} dataset.csv"
)

# Install dependencies
wf.step("setup").docker(
    image="python:3.11",
    content="pip install -r requirements.txt"
).depends_on("download")

# Train model
wf.step("train").docker(
    image="python:3.11",
    content="python train.py --epochs {{{{epochs}}}}"
).depends_on("setup")

# Upload results
wf.step("upload").docker(
    image="amazon/aws-cli:latest",
    content="aws s3 cp model.pkl s3://models/{{{{model_name}}}}.pkl"
).depends_on("train")

# Error handling
wf.step("cleanup").run("rm -f *.csv *.pkl").continue_on("failure")
```
"""
        
        guide += """
### Best Practices:
1. Use meaningful step names
2. Add descriptions to workflows and parameters
3. Use Docker for complex dependencies
4. Add error handling with continue_on or retry policies
5. Use depends_on for step dependencies
6. Validate inputs early in the workflow
7. Store secrets in Kubiya vault, not in code
8. Use wf.with_files() for configuration and scripts

### Common Patterns:
- Data processing: Use pandas/numpy in Docker
- API calls: Use curl or Python requests
- File operations: Mount volumes for large files
- Parallel processing: Use parallel_steps()
- Conditional execution: Use condition parameter
- Secrets: Use {{secret:NAME}} or parameters
- Files: Use wf.with_files() for configs
"""
        
        return guide
    
    @mcp.prompt()
    async def docker_workflow_examples(
        use_case: str,
        language: str = "python"
    ) -> str:
        """
        Provide Docker-focused workflow examples for specific use cases.
        
        Args:
            use_case: Type of workflow (data_processing, ci_cd, ml, api, etc)
            language: Primary language (python, nodejs, go, etc)
            
        Returns:
            Docker-based workflow examples
        """
        # Get secrets context
        secrets_prompt = server.secrets_context.get_context_prompt()
        
        examples = {
            "data_processing": {
                "python": """# Data Processing with Pandas
```python
wf = Workflow("csv-analyzer")
wf.description("Analyze CSV files with pandas")
wf.params(
    csv_url={{"required": True, "description": "URL of CSV file"}},
    analysis_type={{"default": "summary", "description": "summary or correlation"}},
    output_bucket={{"required": True, "description": "S3 bucket for results"}}
)

# Use AWS credentials from secrets
wf.env(
    AWS_ACCESS_KEY_ID="{{{{secret:AWS_ACCESS_KEY_ID}}}}",
    AWS_SECRET_ACCESS_KEY="{{{{secret:AWS_SECRET_ACCESS_KEY}}}}"
)

# Include analysis script
wf.with_files({{
    "analyze.py": '''
import pandas as pd
import numpy as np
import boto3
import json

df = pd.read_csv("data.csv")
print(f"Dataset shape: {{df.shape}}")

if "{{{{analysis_type}}}}" == "summary":
    result = df.describe().to_dict()
elif "{{{{analysis_type}}}}" == "correlation":
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    result = df[numeric_cols].corr().to_dict()

# Save to S3
s3 = boto3.client('s3')
s3.put_object(
    Bucket="{{{{output_bucket}}}}",
    Key="analysis_result.json",
    Body=json.dumps(result)
)
'''
}})

# Download data
wf.step("download").docker(
    image="alpine/curl",
    content="curl -L -o data.csv {{{{csv_url}}}}"
)

# Analyze
wf.step("analyze").docker(
    image="jupyter/scipy-notebook:latest",
    content="python analyze.py"
).depends_on("download")
```""",
                "nodejs": """# Data Processing with Node.js
```python
wf = Workflow("json-transformer")
wf.description("Transform JSON data")
wf.params(
    input_url={{"required": True}},
    transform={{"default": "flatten"}},
    github_token={{"required": True, "secret": True}}
)

wf.env(GITHUB_TOKEN="{{{{params.github_token}}}}")

wf.with_files({{
    "transform.js": '''
const https = require('https');
const fs = require('fs');

const options = {{
    headers: {{
        'Authorization': `token ${{process.env.GITHUB_TOKEN}}`,
        'User-Agent': 'NodeJS-Transformer'
    }}
}};

https.get('{{{{input_url}}}}', options, (res) => {{
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {{
        const json = JSON.parse(data);
        if ('{{{{transform}}}}' === 'flatten') {{
            console.log(JSON.stringify(json, null, 2));
        }}
        fs.writeFileSync('output.json', JSON.stringify(json));
    }});
}});
'''
}})

wf.step("process").docker(
    image="node:20-slim",
    content="node transform.js"
)
```"""
            },
            "ci_cd": {
                "python": """# CI/CD Pipeline with Secrets
```python
wf = Workflow("python-ci")
wf.description("CI pipeline for Python project")
wf.params(
    repo_url={{"required": True}},
    branch={{"default": "main"}},
    run_tests={{"default": True}},
    docker_registry={{"required": True}},
    registry_user={{"required": True, "secret": True}},
    registry_pass={{"required": True, "secret": True}}
)

# Docker registry auth
wf.env(
    DOCKER_USER="{{{{params.registry_user}}}}",
    DOCKER_PASS="{{{{params.registry_pass}}}}"
)

# Clone repo
wf.step("clone").docker(
    image="alpine/git",
    content="git clone -b {{{{branch}}}} {{{{repo_url}}}} /workspace"
)

# Install deps and test
wf.step("test").docker(
    image="python:3.11",
    content='''
cd /workspace
pip install -r requirements.txt
if {{{{run_tests}}}}; then
    pytest tests/ --cov=src --cov-report=xml
fi
'''
).depends_on("clone")

# Build and push Docker image
wf.step("build-push").docker(
    image="docker:24-dind",
    content='''
cd /workspace
echo "$DOCKER_PASS" | docker login {{{{docker_registry}}}} -u "$DOCKER_USER" --password-stdin
docker build -t {{{{docker_registry}}}}/myapp:{{{{branch}}}}-latest .
docker push {{{{docker_registry}}}}/myapp:{{{{branch}}}}-latest
'''
).depends_on("test")
```"""
            },
            "ml": {
                "python": """# Machine Learning Pipeline with Secrets
```python
wf = Workflow("ml-training")
wf.description("Train and deploy ML model")
wf.params(
    dataset={{"required": True}},
    model_type={{"default": "random_forest"}},
    test_size={{"default": 0.2}},
    mlflow_tracking_uri={{"required": True}},
    mlflow_token={{"required": True, "secret": True}}
)

# MLflow authentication
wf.env(
    MLFLOW_TRACKING_URI="{{{{params.mlflow_tracking_uri}}}}",
    MLFLOW_TRACKING_TOKEN="{{{{params.mlflow_token}}}}"
)

wf.with_files({{
    "train.py": '''
import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
import joblib

# MLflow setup
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])

# Load data
df = pd.read_csv("{{{{dataset}}}}")
X = df.drop('target', axis=1)
y = df['target']

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size={{{{test_size}}}}, random_state=42
)

# Start MLflow run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("model_type", "{{{{model_type}}}}")
    mlflow.log_param("test_size", {{{{test_size}}}})
    
    # Train
    if "{{{{model_type}}}}" == "random_forest":
        model = RandomForestClassifier(n_estimators=100)
    else:
        model = LogisticRegression(max_iter=1000)
    
    model.fit(X_train, y_train)
    
    # Evaluate
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    f1 = f1_score(y_test, predictions, average='weighted')
    
    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("f1_score", f1)
    
    # Log model
    mlflow.sklearn.log_model(model, "model")
    
    print(f"Model accuracy: {{accuracy:.4f}}")
    print(f"F1 score: {{f1:.4f}}")
    
    # Save locally too
    joblib.dump(model, 'model.pkl')
''',
    "requirements.txt": '''
pandas==2.0.0
scikit-learn==1.3.0
mlflow==2.8.0
joblib==1.3.0
'''
}})

# Install dependencies
wf.step("setup").docker(
    image="python:3.11",
    content="pip install -r requirements.txt"
)

# Train model
wf.step("train").docker(
    image="python:3.11",
    content="python train.py"
).depends_on("setup")
```"""
            }
        }
        
        # Get the example
        use_case_examples = examples.get(use_case, {})
        example = use_case_examples.get(language, "")
        
        if not example:
            # Provide generic example
            docker_images = server.integration_context.get_docker_suggestions(f"{use_case} {language}")
            example = f"""# Generic {use_case} Example
```python
wf = Workflow("{use_case}-workflow")
wf.description("{use_case} workflow using {language}")

# Add parameters for secrets
wf.params(
    api_key={{"required": True, "secret": True, "description": "API key for service"}},
    secret_value={{"required": True, "secret": True, "description": "Secret configuration"}}
)

# Use secrets as environment variables
wf.env(
    API_KEY="{{{{params.api_key}}}}",
    SECRET_VALUE="{{{{params.secret_value}}}}"
)

# Suggested Docker images:
"""
            for img in docker_images[:3]:
                example += f"# - {img}\n"
            
            example += """
wf.step("main").docker(
    image="{docker_images[0]}",
    content='''
# Your {language} code here
# Access secrets via environment variables
import os
api_key = os.environ.get("API_KEY")
'''
)
```"""
        
        return f"""# Docker Workflow Examples: {use_case}

## Language: {language}

{example}

## Secrets Context:
{secrets_prompt}

## Tips:
1. Use official Docker images when possible
2. Use slim/alpine variants for smaller size
3. Mount volumes for persistent data
4. Set working directories with WORKDIR
5. Use multi-stage builds for production
6. Store secrets in Kubiya vault
7. Pass secrets as parameters for missing ones
8. Use wf.with_files() for scripts and configs

## Common Docker Images:
- Python: python:3.11-slim, jupyter/scipy-notebook
- Node.js: node:20-slim, node:20-alpine
- Go: golang:1.21-alpine
- Java: openjdk:17-slim
- Ruby: ruby:3.2-slim
"""
    
    @mcp.prompt()
    async def workflow_patterns(
        pattern: str
    ) -> str:
        """
        Provide common workflow patterns and best practices.
        
        Args:
            pattern: Pattern type (parallel, conditional, error_handling, secrets, files, etc)
            
        Returns:
            Pattern examples and explanations
        """
        patterns = {
            "parallel": """# Parallel Execution Pattern
```python
wf = Workflow("parallel-tasks")
wf.description("Execute tasks in parallel")

# Define parallel steps
with wf.parallel_steps():
    wf.step("task1", "echo 'Task 1 running'")
    wf.step("task2", "echo 'Task 2 running'")
    wf.step("task3").docker(
        image="python:3.11-slim",
        content="python -c 'print(\"Task 3\")'")

# Wait for all parallel tasks
wf.step("combine", "echo 'All tasks complete'")
```""",
            
            "conditional": """# Conditional Execution Pattern
```python
wf = Workflow("conditional-flow")
wf.description("Execute steps conditionally")
wf.params(
    environment={{"default": "dev"}},
    skip_tests={{"default": False}}
)

# Always run
wf.step("build", "echo 'Building...'")

# Conditional steps
wf.step("test", "echo 'Running tests'").condition("not {{{{skip_tests}}}}")

wf.step("deploy-dev", "echo 'Deploying to dev'").condition("{{{{environment}}}} == 'dev'")
wf.step("deploy-prod", "echo 'Deploying to prod'").condition("{{{{environment}}}} == 'prod'")
```""",
            
            "error_handling": """# Error Handling Pattern
```python
wf = Workflow("resilient-workflow")
wf.description("Workflow with error handling")

# Retry on failure
wf.step("flaky-api", "curl https://api.example.com").retry(
    max_attempts=3,
    delay_seconds=10
)

# Continue on failure
wf.step("optional-task", "might-fail-command").continue_on("failure")

# Cleanup always runs
wf.step("cleanup", "rm -f temp-files/*").continue_on("any")

# Error notification
wf.step("notify-error").docker(
    image="curlimages/curl",
    content="curl -X POST https://webhook.example.com/error -d '{{\"workflow\": \"failed\"}}'"
).continue_on("failure")
```""",
            
            "secrets": """# Secrets Management Pattern
```python
wf = Workflow("secure-workflow")
wf.description("Workflow with secure secret handling")
wf.params(
    # For secrets not in vault
    db_password={{"required": True, "secret": True}},
    api_token={{"required": True, "secret": True}}
)

# Use secrets from Kubiya vault
wf.env(
    # From vault
    AWS_ACCESS_KEY_ID="{{{{secret:AWS_ACCESS_KEY_ID}}}}",
    AWS_SECRET_ACCESS_KEY="{{{{secret:AWS_SECRET_ACCESS_KEY}}}}",
    # From parameters
    DB_PASSWORD="{{{{params.db_password}}}}",
    API_TOKEN="{{{{params.api_token}}}}"
)

# Use in Docker step
wf.step("connect-db").docker(
    image="postgres:15-alpine",
    content="psql -h $DB_HOST -U $DB_USER -c 'SELECT * FROM users LIMIT 10'"
)

# Use in API call
wf.step("api-call").docker(
    image="curlimages/curl",
    content='''
curl -X POST https://api.example.com/data \\
  -H "Authorization: Bearer $API_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{{{payload}}}}'
'''
)
```""",
            
            "files": """# File Management Pattern
```python
wf = Workflow("file-workflow")
wf.description("Workflow with file handling")
wf.params(
    config_override={{"default": "{{}}", "description": "JSON config override"}}
)

# Add files to workflow
wf.with_files({{
    # Static configuration
    "config.json": '''{{
        "version": "1.0",
        "features": {{
            "logging": true,
            "debug": false
        }}
    }}''',
    
    # Dynamic configuration
    "dynamic_config.json": "{{{{params.config_override}}}}",
    
    # Script from local file
    "process.py": open("local_scripts/processor.py").read(),
    
    # Multi-line script
    "run.sh": '''#!/bin/bash
set -e

echo "Processing with config:"
cat config.json

python process.py --config config.json
'''
}})

# Use files in steps
wf.step("process").docker(
    image="python:3.11-slim",
    content="python process.py"
)
```""",
            
            "data_pipeline": """# Data Pipeline Pattern
```python
wf = Workflow("etl-pipeline")
wf.description("Extract, Transform, Load pipeline")
wf.params(
    source_db={{"required": True}},
    target_db={{"required": True}},
    batch_size={{"default": 1000}}
)

# Database credentials from vault
wf.env(
    SOURCE_DB_URL="{{{{secret:SOURCE_DATABASE_URL}}}}",
    TARGET_DB_URL="{{{{secret:TARGET_DATABASE_URL}}}}"
)

# ETL script
wf.with_files({{
    "etl.py": '''
import pandas as pd
from sqlalchemy import create_engine
import os

source_engine = create_engine(os.environ["SOURCE_DB_URL"])
target_engine = create_engine(os.environ["TARGET_DB_URL"])

# Extract
query = "SELECT * FROM source_table"
df = pd.read_sql(query, source_engine, chunksize={{{{batch_size}}}})

# Transform and Load
for chunk in df:
    # Transform
    chunk['processed_at'] = pd.Timestamp.now()
    chunk = chunk.dropna()
    
    # Load
    chunk.to_sql('target_table', target_engine, if_exists='append', index=False)
    print(f"Processed {{len(chunk)}} rows")
'''
}})

# Extract
wf.step("extract").docker(
    image="curlimages/curl",
    content="curl -L -o raw_data.csv {{{{source_url}}}}"
)

# Validate
wf.step("validate").docker(
    image="python:3.11-slim",
    content='''
import pandas as pd
df = pd.read_csv("raw_data.csv")
assert len(df) > 0, "Empty dataset"
assert "{{{{required_column}}}}" in df.columns, "Missing required column"
print(f"Valid dataset with {{len(df)}} rows")
'''
).depends_on("extract")
```"""
        }
        
        pattern_content = patterns.get(pattern, f"Pattern '{pattern}' not found")
        
        return f"""# Workflow Pattern: {pattern}

{pattern_content}

## General Best Practices:
1. Use meaningful step names
2. Add proper error handling
3. Set appropriate timeouts
4. Use dependencies wisely
5. Log important information
6. Clean up resources
7. Use parameters for flexibility
8. Document complex logic
9. Store secrets in Kubiya vault
10. Use wf.with_files() for scripts

## Available Patterns:
- parallel: Run steps concurrently
- conditional: Execute based on conditions
- error_handling: Resilient workflows
- secrets: Secure credential management
- files: Include scripts and configs
- data_pipeline: ETL workflows
- approval: Manual approval steps
- notification: Send notifications
- scheduled: Time-based execution
""" 