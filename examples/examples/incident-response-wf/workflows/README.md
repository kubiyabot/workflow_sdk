# Incident Response Workflow CLI

A comprehensive CLI tool for managing incident response workflows with preflight checks, test execution, and workflow compilation.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Environment Setup

```bash
export KUBIYA_API_KEY="your-api-key-here"
export KUBIYA_BASE_URL="https://api.kubiya.ai"  # Optional
```

### Commands

#### 1. Preflight Check
Verify all dependencies and platform requirements:

```bash
python cli.py preflight
python cli.py preflight --verbose  # Detailed output
```

Checks:
- ✅ Kubiya API connectivity
- ✅ Required integrations (Slack)
- ✅ Secret availability (ANTHROPIC_API_KEY, SLACK_BOT_TOKEN)
- ✅ Environment variables

#### 2. Test Webhook
Execute workflow with test parameters:

```bash
# Basic test
python cli.py test-webhook

# Custom parameters
python cli.py test-webhook \
  --incident-id "TEST-2024-001" \
  --severity "critical" \
  --title "Production Database Outage" \
  --source "datadog" \
  --channel "#incidents"

# Dry run (show payload without execution)
python cli.py test-webhook --dry-run
```

#### 3. Compile Workflow
Convert workflow definition to JSON/YAML:

```bash
# Compile to JSON
python cli.py compile --format json --output workflow.json

# Compile to YAML with pretty formatting
python cli.py compile --format yaml --pretty --output workflow.yaml

# Print to stdout
python cli.py compile --format json --pretty
```

#### 4. Execute Workflow
Run full workflow with monitoring:

```bash
# Execute with streaming
python cli.py execute --incident-id "PROD-2024-001"

# Execute without streaming
python cli.py execute --incident-id "PROD-2024-001" --no-stream
```

#### 5. Status Check
View current platform and workflow status:

```bash
python cli.py status
```

## Examples

### Complete Workflow Test

```bash
# 1. Check prerequisites
python cli.py preflight --verbose

# 2. Test with custom incident
python cli.py test-webhook \
  --incident-id "E2E-TEST-001" \
  --severity "critical" \
  --title "Payment Service Down" \
  --source "prometheus" \
  --channel "#sre-alerts"

# 3. Check execution status
python cli.py status
```

### Development Workflow

```bash
# 1. Compile workflow for review
python cli.py compile --format yaml --pretty --output compiled-workflow.yaml

# 2. Run preflight checks
python cli.py preflight

# 3. Execute test
python cli.py execute --incident-id "DEV-TEST-001"
```

## CLI Help

```bash
python cli.py --help
python cli.py preflight --help
python cli.py test-webhook --help
python cli.py compile --help
python cli.py execute --help
python cli.py status --help
```

## Output Examples

### Preflight Check Output
```
🔍 Running preflight checks for incident response workflow...
============================================================
1. Checking Kubiya API connectivity...
   ✅ API connectivity: OK (0.45s)
2. Checking required integrations...
   ✅ Slack integration: Available
3. Checking required secrets...
   ✅ ANTHROPIC_API_KEY: Available
   ✅ SLACK_BOT_TOKEN: Available
4. Checking environment variables...
   ✅ KUBIYA_API_KEY: Set
============================================================
✅ Preflight checks completed
```

### Test Webhook Output
```
🚀 Test Webhook Execution
========================================
📋 Incident ID: CLI-TEST-001
🚨 Severity: critical
📝 Title: CLI Test Incident
📡 Source: cli
💬 Channel: #incident-test

⏳ Executing workflow with test payload...
✅ Workflow execution initiated successfully
📊 Execution ID: 20240630_143022
🔗 Stream URL: https://api.kubiya.ai/stream/20240630_143022
```

### Status Output
```
📊 Incident Response Workflow Status
========================================
🌐 API Status: Success
   Response Time: 0.32s
🔗 Integrations:
   ✅ Slack: Available
📈 Recent Executions:
   📄 incident-response-e2e-test_20240630_143022_execution_report.md
   📄 incident-response-e2e-test_20240630_142158_execution_report.md
```

## Error Handling

The CLI provides detailed error messages and exit codes:

- **Exit Code 0**: Success
- **Exit Code 1**: General error (API failure, missing dependencies, etc.)

## Integration with Existing Workflow

The CLI automatically integrates with your existing `test_execution.py` workflow and uses the same reporting system, storing results in the `reports/` directory.