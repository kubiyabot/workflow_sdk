#!/usr/bin/env python3
"""
Incident Response Workflow CLI

A comprehensive CLI tool for managing incident response workflows with:
- Preflight checks for Kubiya platform dependencies
- Test webhook execution with parameters
- Workflow compilation to JSON/YAML formats
- Workflow execution and monitoring
"""

import os
import sys
import json
import yaml
import click
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Add paths for SDK access
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent.parent))

from kubiya_workflow_sdk.client import KubiyaClient
from kubiya_workflow_sdk.dsl import Workflow, Step


class WorkflowCLI:
    """Main CLI class for workflow management."""
    
    def __init__(self):
        self.kubiya_api_key = os.getenv('KUBIYA_API_KEY')
        self.kubiya_base_url = os.getenv('KUBIYA_BASE_URL', 'https://api.kubiya.ai')
        
    def get_client(self) -> KubiyaClient:
        """Get configured Kubiya client."""
        if not self.kubiya_api_key:
            raise click.ClickException("KUBIYA_API_KEY environment variable is required")
        
        return KubiyaClient(
            api_key=self.kubiya_api_key,
            base_url=self.kubiya_base_url,
            timeout=300
        )
    
    def check_api_connectivity(self) -> Dict[str, Any]:
        """Check API connectivity and authentication."""
        try:
            headers = {
                'Authorization': f'Bearer {self.kubiya_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.kubiya_base_url}/api/v1/health",
                headers=headers,
                timeout=10
            )
            
            return {
                'status': 'success' if response.status_code == 200 else 'failed',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'error': None if response.status_code == 200 else response.text
            }
        except Exception as e:
            return {
                'status': 'failed',
                'status_code': None,
                'response_time': None,
                'error': str(e)
            }
    
    def check_integrations(self) -> Dict[str, Any]:
        """Check required integrations (Slack, etc.)."""
        try:
            headers = {
                'Authorization': f'Bearer {self.kubiya_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Check Slack integration
            slack_response = requests.get(
                f"{self.kubiya_base_url}/api/v1/integrations/slack",
                headers=headers,
                timeout=10
            )
            
            return {
                'slack': {
                    'status': 'available' if slack_response.status_code == 200 else 'unavailable',
                    'status_code': slack_response.status_code,
                    'configured': slack_response.status_code == 200
                }
            }
        except Exception as e:
            return {
                'slack': {
                    'status': 'error',
                    'status_code': None,
                    'configured': False,
                    'error': str(e)
                }
            }
    
    def check_secrets(self) -> Dict[str, Any]:
        """Check required secrets availability."""
        try:
            headers = {
                'Authorization': f'Bearer {self.kubiya_api_key}',
                'Content-Type': 'application/json'
            }
            
            secrets_to_check = ['ANTHROPIC_API_KEY', 'SLACK_BOT_TOKEN']
            results = {}
            
            for secret_name in secrets_to_check:
                try:
                    response = requests.get(
                        f"{self.kubiya_base_url}/api/v1/secret/get_secret_value/{secret_name}",
                        headers=headers,
                        timeout=10
                    )
                    
                    results[secret_name] = {
                        'status': 'available' if response.status_code == 200 else 'unavailable',
                        'status_code': response.status_code,
                        'configured': response.status_code == 200
                    }
                except Exception as e:
                    results[secret_name] = {
                        'status': 'error',
                        'status_code': None,
                        'configured': False,
                        'error': str(e)
                    }
            
            return results
        except Exception as e:
            return {'error': str(e)}
    
    def load_workflow_definition(self, workflow_file: str = None) -> Workflow:
        """Load workflow definition from Python file."""
        if not workflow_file:
            # Try to find test_execution.py
            workflow_file = current_dir / "test_execution.py"
        else:
            workflow_file = Path(workflow_file)
        
        if not workflow_file.exists():
            raise click.ClickException(f"Workflow file not found: {workflow_file}")
        
        # Import and execute the workflow file
        import importlib.util
        spec = importlib.util.spec_from_file_location("workflow_module", workflow_file)
        workflow_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workflow_module)
        
        # Look for workflow creation function
        if hasattr(workflow_module, 'create_incident_response_workflow'):
            return workflow_module.create_incident_response_workflow()
        elif hasattr(workflow_module, 'create_workflow'):
            return workflow_module.create_workflow()
        else:
            raise click.ClickException("No workflow creation function found in file")


@click.group()
@click.pass_context
def cli(ctx):
    """Incident Response Workflow CLI"""
    ctx.ensure_object(dict)
    ctx.obj['workflow_cli'] = WorkflowCLI()


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def preflight(ctx, verbose):
    """Run preflight checks for workflow dependencies."""
    workflow_cli = ctx.obj['workflow_cli']
    
    click.echo("🔍 Running preflight checks for incident response workflow...")
    click.echo("=" * 60)
    
    # Check 1: API Connectivity
    click.echo("1. Checking Kubiya API connectivity...")
    api_check = workflow_cli.check_api_connectivity()
    
    if api_check['status'] == 'success':
        click.echo(f"   ✅ API connectivity: OK ({api_check['response_time']:.2f}s)")
    else:
        click.echo(f"   ❌ API connectivity: FAILED")
        if verbose and api_check['error']:
            click.echo(f"      Error: {api_check['error']}")
    
    # Check 2: Integrations
    click.echo("2. Checking required integrations...")
    integrations = workflow_cli.check_integrations()
    
    for integration, details in integrations.items():
        if details['status'] == 'available':
            click.echo(f"   ✅ {integration.title()} integration: Available")
        else:
            click.echo(f"   ❌ {integration.title()} integration: Unavailable")
            if verbose and 'error' in details:
                click.echo(f"      Error: {details['error']}")
    
    # Check 3: Secrets
    click.echo("3. Checking required secrets...")
    secrets = workflow_cli.check_secrets()
    
    if 'error' in secrets:
        click.echo(f"   ❌ Secrets check failed: {secrets['error']}")
    else:
        for secret_name, details in secrets.items():
            if details['configured']:
                click.echo(f"   ✅ {secret_name}: Available")
            else:
                click.echo(f"   ❌ {secret_name}: Missing")
                if verbose and 'error' in details:
                    click.echo(f"      Error: {details['error']}")
    
    # Check 4: Environment Variables
    click.echo("4. Checking environment variables...")
    required_env_vars = ['KUBIYA_API_KEY']
    
    for env_var in required_env_vars:
        if os.getenv(env_var):
            click.echo(f"   ✅ {env_var}: Set")
        else:
            click.echo(f"   ❌ {env_var}: Missing")
    
    click.echo("=" * 60)
    click.echo("✅ Preflight checks completed")


@cli.command()
@click.option('--incident-id', default='CLI-TEST-001', help='Incident ID for testing')
@click.option('--severity', default='critical', help='Incident severity')
@click.option('--title', default='CLI Test Incident', help='Incident title')
@click.option('--source', default='cli', help='Incident source')
@click.option('--url', default='https://example.com/incident', help='Incident URL')
@click.option('--channel', default='#incident-test', help='Slack channel')
@click.option('--dry-run', is_flag=True, help='Show webhook payload without sending')
@click.pass_context
def test_webhook(ctx, incident_id, severity, title, source, url, channel, dry_run):
    """Execute test webhook with custom parameters."""
    workflow_cli = ctx.obj['workflow_cli']
    
    # Create test incident payload
    test_payload = {
        "id": incident_id,
        "title": title,
        "severity": severity,
        "description": f"Test incident created via CLI at {datetime.now(timezone.utc).isoformat()}",
        "source": source,
        "url": url,
        "slack_channel": channel,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tags": ["test", "cli", "incident-response"],
        "metadata": {
            "created_by": "workflow-cli",
            "test_execution": True
        }
    }
    
    click.echo("🚀 Test Webhook Execution")
    click.echo("=" * 40)
    click.echo(f"📋 Incident ID: {incident_id}")
    click.echo(f"🚨 Severity: {severity}")
    click.echo(f"📝 Title: {title}")
    click.echo(f"📡 Source: {source}")
    click.echo(f"💬 Channel: {channel}")
    click.echo()
    
    if dry_run:
        click.echo("🔍 DRY RUN - Webhook payload:")
        click.echo(json.dumps(test_payload, indent=2))
        return
    
    try:
        client = workflow_cli.get_client()
        
        click.echo("⏳ Executing workflow with test payload...")
        
        # Execute the workflow
        result = client.execute_workflow(
            workflow_name="incident-response-e2e-test",
            event=test_payload,
            stream=True
        )
        
        click.echo("✅ Workflow execution initiated successfully")
        click.echo(f"📊 Execution ID: {result.get('execution_id', 'N/A')}")
        
        if result.get('stream_url'):
            click.echo(f"🔗 Stream URL: {result['stream_url']}")
        
    except Exception as e:
        click.echo(f"❌ Workflow execution failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--format', type=click.Choice(['json', 'yaml']), default='json', help='Output format')
@click.option('--output', '-o', help='Output file path')
@click.option('--workflow-file', help='Python workflow file to compile')
@click.option('--pretty', is_flag=True, help='Pretty print output')
@click.pass_context
def compile(ctx, format, output, workflow_file, pretty):
    """Compile workflow definition to JSON/YAML."""
    workflow_cli = ctx.obj['workflow_cli']
    
    click.echo(f"🔧 Compiling workflow to {format.upper()}...")
    
    try:
        # Load workflow definition
        workflow = workflow_cli.load_workflow_definition(workflow_file)
        
        # Convert to dictionary
        workflow_dict = {
            "name": workflow.name,
            "description": workflow.description,
            "type": workflow.type,
            "runner": workflow.runner,
            "steps": []
        }
        
        # Add steps
        for step in workflow.steps:
            step_dict = {
                "name": step.name,
                "data": step.data
            }
            workflow_dict["steps"].append(step_dict)
        
        # Format output
        if format == 'json':
            output_content = json.dumps(workflow_dict, indent=2 if pretty else None)
        else:  # yaml
            output_content = yaml.dump(workflow_dict, default_flow_style=False, indent=2)
        
        # Output
        if output:
            output_path = Path(output)
            output_path.write_text(output_content)
            click.echo(f"✅ Workflow compiled to: {output_path}")
        else:
            click.echo(output_content)
            
    except Exception as e:
        click.echo(f"❌ Compilation failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--workflow-file', help='Python workflow file to execute')
@click.option('--incident-id', default='CLI-EXEC-001', help='Incident ID')
@click.option('--stream', is_flag=True, default=True, help='Stream execution output')
@click.option('--timeout', default=300, help='Execution timeout in seconds')
@click.pass_context
def execute(ctx, workflow_file, incident_id, stream, timeout):
    """Execute workflow with real-time monitoring."""
    workflow_cli = ctx.obj['workflow_cli']
    
    # Create execution payload
    execution_payload = {
        "id": incident_id,
        "title": f"CLI Execution - {incident_id}",
        "severity": "high",
        "description": f"Workflow execution initiated via CLI at {datetime.now(timezone.utc).isoformat()}",
        "source": "cli-execution",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    click.echo("🚀 Executing Incident Response Workflow")
    click.echo("=" * 50)
    click.echo(f"📋 Incident ID: {incident_id}")
    click.echo(f"📡 Streaming: {'Enabled' if stream else 'Disabled'}")
    click.echo(f"⏱️  Timeout: {timeout}s")
    click.echo()
    
    try:
        client = workflow_cli.get_client()
        
        # Execute workflow
        if stream:
            click.echo("📊 Starting workflow execution with streaming...")
            
            # Use existing test_execution.py logic for streaming
            from test_execution import main as execute_test
            execute_test()
        else:
            click.echo("📊 Starting workflow execution...")
            result = client.execute_workflow(
                workflow_name="incident-response-e2e-test",
                event=execution_payload,
                stream=False
            )
            
            click.echo("✅ Workflow execution completed")
            click.echo(f"📊 Result: {json.dumps(result, indent=2)}")
            
    except Exception as e:
        click.echo(f"❌ Execution failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show workflow and platform status."""
    workflow_cli = ctx.obj['workflow_cli']
    
    click.echo("📊 Incident Response Workflow Status")
    click.echo("=" * 40)
    
    # Check API status
    api_check = workflow_cli.check_api_connectivity()
    click.echo(f"🌐 API Status: {api_check['status'].title()}")
    
    if api_check['status'] == 'success':
        click.echo(f"   Response Time: {api_check['response_time']:.2f}s")
    
    # Check integrations
    integrations = workflow_cli.check_integrations()
    click.echo(f"🔗 Integrations:")
    for name, details in integrations.items():
        status_icon = "✅" if details['configured'] else "❌"
        click.echo(f"   {status_icon} {name.title()}: {details['status'].title()}")
    
    # Check recent executions (if available)
    reports_dir = Path("reports")
    if reports_dir.exists():
        recent_reports = sorted(reports_dir.glob("*_execution_report.md"))[-3:]
        if recent_reports:
            click.echo(f"📈 Recent Executions:")
            for report in recent_reports:
                click.echo(f"   📄 {report.name}")


if __name__ == '__main__':
    cli()