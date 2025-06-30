#!/usr/bin/env python3
"""
Production deployment script for incident response workflow.
This script sets up the workflow for production use with proper configuration.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add SDK path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from workflows.real_slack_incident_workflow import create_real_slack_incident_workflow


def validate_environment():
    """Validate that all required environment variables are set."""
    
    print("🔍 Validating environment...")
    
    required_vars = {
        'KUBIYA_API_KEY': 'Kubiya API key for workflow execution',
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  ❌ {var}: {description}")
        else:
            print(f"  ✅ {var}: Set")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(var)
        print(f"\nPlease set these variables and try again.")
        return False
    
    return True


def test_slack_integration(api_key):
    """Test Slack integration connectivity."""
    
    print("🔍 Testing Slack integration...")
    
    # Create a simple test workflow to check Slack token
    from kubiya_workflow_sdk.dsl import Workflow, Step
    
    test_workflow = Workflow("slack-integration-test")
    test_workflow.data = {
        "name": "slack-integration-test",
        "description": "Test Slack integration connectivity",
        "type": "chain",
        "runner": "core-testing-2",
        "steps": [
            {
                "name": "test-slack-token",
                "executor": {
                    "type": "kubiya",
                    "config": {
                        "url": "api/v1/integration/slack/token/1",
                        "method": "GET"
                    }
                },
                "output": "SLACK_TOKEN"
            },
            {
                "name": "validate-token",
                "executor": {
                    "type": "tool",
                    "config": {
                        "tool_def": {
                            "name": "validate_slack_token",
                            "description": "Validate Slack token",
                            "type": "docker",
                            "image": "curlimages/curl:latest",
                            "content": '''#!/bin/sh
echo "🔑 Validating Slack token..."
TOKEN=$(echo "$slack_token" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "✅ Slack token retrieved successfully"
    echo "🔑 Token preview: ${TOKEN:0:20}..."
    
    # Test auth
    AUTH_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "https://slack.com/api/auth.test")
    if echo "$AUTH_RESPONSE" | grep -q '"ok":true'; then
        echo "✅ Slack authentication successful"
        USER=$(echo "$AUTH_RESPONSE" | grep -o '"user":"[^"]*"' | cut -d'"' -f4)
        TEAM=$(echo "$AUTH_RESPONSE" | grep -o '"team":"[^"]*"' | cut -d'"' -f4)
        echo "👤 Bot user: $USER"
        echo "🏢 Team: $TEAM"
        echo "SLACK_INTEGRATION_STATUS=success"
    else
        echo "❌ Slack authentication failed"
        echo "$AUTH_RESPONSE"
        echo "SLACK_INTEGRATION_STATUS=auth_failed"
    fi
else
    echo "❌ No Slack token available"
    echo "SLACK_INTEGRATION_STATUS=no_token"
fi'''
                        },
                        "args": {
                            "slack_token": "${SLACK_TOKEN}"
                        }
                    }
                },
                "depends": ["test-slack-token"],
                "output": "VALIDATION_RESULT"
            }
        ]
    }
    
    client = KubiyaClient(api_key=api_key, timeout=120)
    
    try:
        events = client.execute_workflow(
            workflow_definition=test_workflow.to_dict(),
            parameters={},
            stream=True
        )
        
        for event in events:
            if isinstance(event, str) and event.strip():
                try:
                    parsed = json.loads(event)
                    event_type = parsed.get('type', '')
                    
                    if 'step_complete' in event_type:
                        step = parsed.get('step', {})
                        if step.get('name') == 'validate-token':
                            output = step.get('output', '')
                            if 'SLACK_INTEGRATION_STATUS=success' in output:
                                print("  ✅ Slack integration working correctly")
                                return True
                            elif 'SLACK_INTEGRATION_STATUS=auth_failed' in output:
                                print("  ❌ Slack authentication failed")
                                return False
                            elif 'SLACK_INTEGRATION_STATUS=no_token' in output:
                                print("  ❌ No Slack token available")
                                return False
                    
                    elif 'workflow_complete' in event_type:
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        print("  ⚠️ Could not determine Slack integration status")
        return False
        
    except Exception as e:
        print(f"  ❌ Slack integration test failed: {e}")
        return False


def deploy_to_production(api_key, config):
    """Deploy the workflow to production with the given configuration."""
    
    print(f"🚀 Deploying incident response workflow to production...")
    print(f"=" * 60)
    
    # Production configuration
    production_params = {
        "incident_event": json.dumps({
            "id": "PLACEHOLDER-WILL-BE-REPLACED",
            "title": "Production Incident",
            "severity": "critical",
            "description": "Production incident requiring immediate response"
        }),
        "slack_users": config.get('slack_users', 'admin@company.com'),
        "create_real_channel": "true",
        "auto_assign": "true"
    }
    
    print(f"📋 Production Configuration:")
    print(f"  👥 Default users: {production_params['slack_users']}")
    print(f"  📱 Real channels: {production_params['create_real_channel']}")
    print(f"  🎯 Auto-assign: {production_params['auto_assign']}")
    
    # Create workflow definition
    workflow = create_real_slack_incident_workflow()
    
    print(f"\n✅ Workflow definition created:")
    print(f"  📋 Name: {workflow.data['name']}")
    print(f"  📝 Description: {workflow.data['description']}")
    print(f"  🔧 Steps: {len(workflow.data['steps'])}")
    
    # Save workflow definition to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workflow_file = Path(__file__).parent / f"production_workflow_{timestamp}.json"
    
    with open(workflow_file, 'w') as f:
        json.dump(workflow.to_dict(), f, indent=2)
    
    print(f"  💾 Saved to: {workflow_file}")
    
    # Create deployment script
    deploy_script = Path(__file__).parent / f"deploy_incident_response.sh"
    
    script_content = f'''#!/bin/bash
# Production Incident Response Workflow Deployment Script
# Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

set -e

echo "🚀 Kubiya Incident Response Workflow"
echo "=================================="

# Check environment
if [ -z "$KUBIYA_API_KEY" ]; then
    echo "❌ KUBIYA_API_KEY environment variable is required"
    exit 1
fi

# Default parameters (can be overridden)
INCIDENT_ID="${{1:-PROD-$(date +%Y%m%d)-001}}"
INCIDENT_TITLE="${{2:-Production System Alert}}"
INCIDENT_SEVERITY="${{3:-critical}}"
SLACK_USERS="${{4:-{config.get('slack_users', 'admin@company.com')}}}"

echo "📋 Incident Parameters:"
echo "  🆔 ID: $INCIDENT_ID"
echo "  📝 Title: $INCIDENT_TITLE"
echo "  🚨 Severity: $INCIDENT_SEVERITY"
echo "  👥 Users: $SLACK_USERS"

# Build incident event JSON
INCIDENT_EVENT=$(cat << EOF
{{
  "id": "$INCIDENT_ID",
  "title": "$INCIDENT_TITLE", 
  "severity": "$INCIDENT_SEVERITY",
  "description": "Production incident requiring immediate attention"
}}
EOF
)

echo ""
echo "🚀 Executing incident response workflow..."

# Execute using the CLI generator
cd "{Path(__file__).parent}"
python generate_workflow.py --deploy \\
    --incident-id "$INCIDENT_ID" \\
    --incident-title "$INCIDENT_TITLE" \\
    --severity "$INCIDENT_SEVERITY" \\
    --users "$SLACK_USERS"

echo ""
echo "✅ Incident response workflow completed!"
echo "👀 Check your Slack workspace for the incident channel"
'''
    
    with open(deploy_script, 'w') as f:
        f.write(script_content)
    
    os.chmod(deploy_script, 0o755)
    
    print(f"  📜 Deployment script: {deploy_script}")
    
    # Create quick-start guide
    readme_file = Path(__file__).parent / "PRODUCTION_DEPLOYMENT.md"
    
    readme_content = f'''# Production Incident Response Workflow

## Quick Start

### 1. Environment Setup
```bash
export KUBIYA_API_KEY="your-api-key-here"
```

### 2. Test Integration
```bash
python deploy_production.py --test-only
```

### 3. Deploy Workflow
```bash
# Using the deployment script
./deploy_incident_response.sh

# Or with custom parameters
./deploy_incident_response.sh "PROD-20240630-001" "Database Outage" "critical" "oncall@company.com,devops@company.com"
```

### 4. Using the CLI Generator
```bash
# Interactive mode
python generate_workflow.py --interactive

# Quick deploy
python generate_workflow.py --deploy --users "your-email@company.com"

# Custom incident
python generate_workflow.py --deploy \\
    --incident-id "PROD-001" \\
    --severity high \\
    --users "user1@company.com,user2@company.com"
```

## Configuration

### Slack Users
- Use email addresses for better user resolution
- Comma-separated list: `user1@company.com,user2@company.com`
- The workflow will resolve emails to Slack user IDs automatically

### Incident Severities
- `critical`: Highest priority, immediate response
- `high`: High priority, urgent attention
- `medium`: Medium priority, scheduled response  
- `low`: Low priority, monitored response

### Environment Variables
- `KUBIYA_API_KEY`: Required for workflow execution

## Workflow Steps

1. **Parse Incident Event** - Validates and processes incident data
2. **Setup Slack Integration** - Retrieves Slack API token
3. **Resolve Slack Users** - Converts emails to Slack user IDs
4. **Create War Room** - Creates incident channel with Block Kit message
5. **Technical Investigation** - Performs automated investigation
6. **Update Slack Thread** - Posts investigation results as threaded reply
7. **Final Summary** - Generates comprehensive incident summary

## Files Generated

- `{workflow_file.name}`: Workflow definition JSON
- `{deploy_script.name}`: Deployment script
- `PRODUCTION_DEPLOYMENT.md`: This documentation

## Monitoring

Each workflow execution provides:
- Real-time step completion status
- Slack channel creation details
- User resolution results
- Investigation confidence scores
- Overall success metrics

Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
'''
    
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    print(f"  📚 Documentation: {readme_file}")
    
    print(f"\n🎉 PRODUCTION DEPLOYMENT COMPLETE!")
    print(f"=" * 60)
    print(f"✅ Workflow definition: {workflow_file}")
    print(f"✅ Deployment script: {deploy_script}")
    print(f"✅ Documentation: {readme_file}")
    print(f"\n🚀 To deploy an incident:")
    print(f"  ./deploy_incident_response.sh")
    print(f"\n🔧 To use interactively:")
    print(f"  python generate_workflow.py --interactive")
    
    return True


def main():
    """Main deployment function."""
    
    parser = argparse.ArgumentParser(description="Deploy incident response workflow to production")
    parser.add_argument('--test-only', action='store_true', help='Only test integrations, do not deploy')
    parser.add_argument('--skip-validation', action='store_true', help='Skip environment validation')
    parser.add_argument('--slack-users', default='admin@company.com', help='Default Slack users for notifications')
    parser.add_argument('--api-key', help='Kubiya API key (or set KUBIYA_API_KEY env var)')
    
    args = parser.parse_args()
    
    print("🏭 PRODUCTION DEPLOYMENT SETUP")
    print("=" * 50)
    
    # Get API key
    api_key = args.api_key or os.getenv('KUBIYA_API_KEY')
    if not api_key:
        print("❌ API key required. Set KUBIYA_API_KEY env var or use --api-key")
        return 1
    
    # Validate environment
    if not args.skip_validation:
        if not validate_environment():
            return 1
    
    # Test Slack integration
    print(f"\n🔍 Testing integrations...")
    slack_ok = test_slack_integration(api_key)
    
    if not slack_ok:
        print(f"\n⚠️ Slack integration test failed!")
        print(f"Please check:")
        print(f"  • Slack integration is configured in Kubiya")
        print(f"  • Bot has necessary permissions")
        print(f"  • API key has access to integrations")
        
        if not args.test_only:
            proceed = input(f"\nProceed with deployment anyway? (y/N): ").strip().lower()
            if proceed != 'y':
                return 1
    
    if args.test_only:
        print(f"\n✅ Integration tests completed!")
        return 0
    
    # Deploy to production
    config = {
        'slack_users': args.slack_users
    }
    
    success = deploy_to_production(api_key, config)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())