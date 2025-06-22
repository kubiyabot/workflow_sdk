"""
Kubiya Workflow SDK CLI - Command line interface for workflow management.

This module provides a rich CLI experience for creating, validating, testing,
and executing workflows.
"""

import click
import json
import yaml
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich import print as rprint
import logging

from .dsl_v2 import FlowWorkflow, step, flow
from .client_v2 import create_streaming_client
from .runner import WorkflowRunner
from .executor_registry import validate_workflow
from .visualization import workflow_to_mermaid

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--api-token', envvar='KUBIYA_API_TOKEN', help='Kubiya API token')
@click.option('--base-url', default='https://api.kubiya.ai', help='API base URL')
@click.pass_context
def cli(ctx, debug, api_token, base_url):
    """Kubiya Workflow SDK - Build and execute enterprise workflows."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        
    ctx.ensure_object(dict)
    ctx.obj['api_token'] = api_token
    ctx.obj['base_url'] = base_url
    
    if not api_token and ctx.invoked_subcommand not in ['init', 'validate', 'visualize']:
        console.print("[yellow]Warning: No API token found. Set KUBIYA_API_TOKEN or use --api-token[/yellow]")


@cli.command()
@click.argument('name')
@click.option('--template', type=click.Choice(['basic', 'docker', 'kubernetes', 'data-pipeline']), 
              default='basic', help='Workflow template to use')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: {name}.py)')
def init(name, template, output):
    """Initialize a new workflow from template."""
    templates = {
        'basic': '''from kubiya_workflow_sdk import flow, step

@flow(name="{name}", version="1.0.0", description="TODO: Add description")
def {func_name}(ctx):
    return (
        step("validate", "Validate inputs")
            .python(lambda: print("Validating..."))
            .output("validation_result")
        >>
        step("process", "Process data")
            .python(lambda: print("Processing..."))
            .output("result")
        >>
        step("notify", "Send notification")
            .shell("echo 'Workflow completed!'")
    )

if __name__ == "__main__":
    # Test locally
    workflow = {func_name}()
    print(workflow.to_yaml())
''',
        'docker': '''from kubiya_workflow_sdk import flow, step

@flow(name="{name}", version="1.0.0", description="Docker-based workflow")
def {func_name}(ctx):
    return (
        step("build", "Build Docker image")
            .docker("docker:latest")
            .command("docker build -t myapp:{{{{ctx.param('version', 'latest')}}}} .")
            .output("image_id")
        >>
        step("test", "Run tests in container")
            .docker("myapp:{{{{ctx.param('version', 'latest')}}}}")
            .command("pytest /app/tests")
            .output("test_results")
        >>
        step("push", "Push to registry")
            .docker("docker:latest")
            .command("docker push myapp:{{{{ctx.param('version', 'latest')}}}}")
            .env(DOCKER_REGISTRY="{{{{ctx.param('registry', 'docker.io')}}}}")
    )
''',
        'kubernetes': '''from kubiya_workflow_sdk import flow, step

@flow(name="{name}", version="1.0.0", description="Kubernetes deployment workflow")  
def {func_name}(ctx):
    return (
        step("validate_manifest", "Validate K8s manifests")
            .tool("kubectl", action="apply", args=["--dry-run=client", "-f", "k8s/"])
            .output("validation")
        >>
        step("deploy", "Deploy to Kubernetes")
            .tool("kubectl", action="apply", args=["-f", "k8s/"])
            .retry(max_attempts=3, delay=30)
            .output("deployment_result")
        >>
        step("wait_ready", "Wait for pods to be ready")
            .tool("kubectl", action="wait", 
                  args=["--for=condition=ready", "pod", "-l", "app={{{{ctx.param('app_name')}}}}"])
            .timeout(300)
    )
''',
        'data-pipeline': '''from kubiya_workflow_sdk import flow, step

@flow(name="{name}", version="1.0.0", description="Data processing pipeline")
def {func_name}(ctx):
    extract = step("extract", "Extract data from source")
        .python(extract_data)
        .env(SOURCE_URL="{{{{ctx.param('source_url')}}}}")
        .output("raw_data")
        
    transform = step("transform", "Transform data")
        .python(transform_data)
        .output("processed_data")
        
    load = step("load", "Load data to destination")
        .python(load_data)
        .env(DEST_URL="{{{{ctx.param('destination_url')}}}}")
        .output("load_result")
        
    return extract >> transform >> load

def extract_data():
    import pandas as pd
    # TODO: Implement extraction logic
    return {"record_count": 1000}
    
def transform_data():
    # TODO: Implement transformation logic
    return {"transformed_count": 950}
    
def load_data():
    # TODO: Implement loading logic
    return {"loaded_count": 950}
'''
    }
    
    # Generate function name from workflow name
    func_name = name.lower().replace('-', '_').replace(' ', '_')
    
    # Format template
    content = templates[template].format(name=name, func_name=func_name)
    
    # Determine output file
    if not output:
        output = f"{name}.py"
        
    # Write file
    Path(output).write_text(content)
    
    console.print(f"[green]✅ Created workflow '{name}' from template '{template}'[/green]")
    console.print(f"[blue]📄 File: {output}[/blue]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Edit the workflow file to add your logic")
    console.print(f"2. Validate: [cyan]kubiya validate {output}[/cyan]")
    console.print(f"3. Execute: [cyan]kubiya run {output}[/cyan]")


@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['summary', 'detailed', 'json']), 
              default='summary', help='Output format')
def validate(workflow_file, format):
    """Validate a workflow file."""
    try:
        # Load workflow
        workflow = _load_workflow(workflow_file)
        
        # Validate
        result = validate_workflow(workflow)
        
        if format == 'json':
            click.echo(json.dumps({
                'valid': result.valid,
                'errors': result.errors,
                'warnings': result.warnings
            }, indent=2))
        elif format == 'detailed':
            console.print(Panel(f"[bold]Validation Report: {workflow_file}[/bold]"))
            
            if result.valid:
                console.print("[green]✅ Workflow is valid![/green]")
            else:
                console.print("[red]❌ Workflow has errors[/red]")
                
            if result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in result.errors:
                    console.print(f"  • {error}")
                    
            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  • {warning}")
        else:
            # Summary format
            if result.valid:
                console.print(f"[green]✅ {workflow_file} is valid[/green]")
            else:
                console.print(f"[red]❌ {workflow_file} has {len(result.errors)} error(s)[/red]")
                for error in result.errors[:3]:
                    console.print(f"   {error}")
                if len(result.errors) > 3:
                    console.print(f"   ... and {len(result.errors) - 3} more")
                    
        sys.exit(0 if result.valid else 1)
        
    except Exception as e:
        console.print(f"[red]Error loading workflow: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--params', '-p', multiple=True, help='Parameters as key=value')
@click.option('--params-file', type=click.Path(exists=True), help='JSON/YAML file with parameters')
@click.option('--step', '-s', help='Execute only this step')
@click.option('--dry-run', is_flag=True, help='Show what would be executed')
@click.option('--no-stream', is_flag=True, help='Disable streaming output')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text', help='Output format')
@click.pass_context
def run(ctx, workflow_file, params, params_file, step, dry_run, no_stream, output):
    """Execute a workflow."""
    try:
        # Load workflow
        workflow = _load_workflow(workflow_file)
        
        # Parse parameters
        params_dict = {}
        for param in params:
            key, value = param.split('=', 1)
            # Try to parse as JSON, fallback to string
            try:
                params_dict[key] = json.loads(value)
            except:
                params_dict[key] = value
                
        # Load params from file
        if params_file:
            file_params = _load_params_file(params_file)
            params_dict.update(file_params)
            
        # Create client
        client = create_streaming_client(
            api_token=ctx.obj['api_token'],
            base_url=ctx.obj['base_url']
        )
        
        # Configure output
        print_events = output == 'text' and not no_stream
        
        # Execute
        if dry_run:
            console.print("[yellow]🏃 Running in dry-run mode[/yellow]")
            result = client.test_workflow_stream(
                workflow=workflow.to_dict(),
                test_params=params_dict,
                dry_run=True,
                print_events=print_events
            )
        else:
            console.print(f"[green]🚀 Executing workflow: {workflow.name}[/green]")
            
            # Handle selective step execution
            if step:
                runner = WorkflowRunner(client=client)
                result = runner.run_step(workflow, step, params=params_dict)
            else:
                result = client.execute_workflow(
                    workflow=workflow.to_dict(),
                    params=params_dict,
                    stream=not no_stream,
                    print_events=print_events
                )
                
        # Output results
        if output == 'json':
            click.echo(json.dumps({
                'execution_id': result.execution_id,
                'status': result.status.value,
                'duration': result.duration_seconds,
                'outputs': result.outputs,
                'errors': result.errors
            }, indent=2))
        else:
            if hasattr(result, 'print_summary'):
                result.print_summary()
            else:
                console.print(f"\n[bold]Execution ID:[/bold] {result.execution_id}")
                console.print(f"[bold]Status:[/bold] {result.status.value}")
                if result.duration_seconds:
                    console.print(f"[bold]Duration:[/bold] {result.duration_seconds:.2f}s")
                    
    except Exception as e:
        console.print(f"[red]Execution failed: {e}[/red]")
        if ctx.obj.get('debug'):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file (default: stdout)')  
@click.option('--format', '-f', type=click.Choice(['mermaid', 'dot', 'png', 'svg']), 
              default='mermaid', help='Output format')
@click.option('--open', 'open_file', is_flag=True, help='Open generated file')
def visualize(workflow_file, output, format, open_file):
    """Generate workflow visualization."""
    try:
        # Load workflow
        workflow = _load_workflow(workflow_file)
        
        if format == 'mermaid':
            # Generate Mermaid diagram
            diagram = workflow_to_mermaid(workflow)
            
            if output:
                Path(output).write_text(diagram)
                console.print(f"[green]✅ Saved Mermaid diagram to {output}[/green]")
            else:
                console.print(Panel(diagram, title="Mermaid Diagram", expand=False))
                
            if open_file and output:
                import webbrowser
                mermaid_url = f"https://mermaid.live/edit#pako:{_encode_mermaid(diagram)}"
                webbrowser.open(mermaid_url)
                
        else:
            console.print(f"[red]Format '{format}' not implemented yet[/red]")
            
    except Exception as e:
        console.print(f"[red]Error generating visualization: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['json', 'yaml']), help='Output format')
def export(workflow_file, format):
    """Export workflow to JSON or YAML."""
    try:
        workflow = _load_workflow(workflow_file)
        
        if format == 'json' or (not format and workflow_file.endswith('.py')):
            output = workflow.to_json()
        else:
            output = workflow.to_yaml()
            
        click.echo(output)
        
    except Exception as e:
        console.print(f"[red]Error exporting workflow: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--runner', '-r', help='List executions for specific runner')
@click.option('--status', '-s', type=click.Choice(['pending', 'running', 'completed', 'failed']),
              help='Filter by status')
@click.option('--limit', '-l', default=10, help='Number of executions to show')
@click.pass_context  
def list(ctx, runner, status, limit):
    """List recent workflow executions."""
    try:
        client = create_streaming_client(
            api_token=ctx.obj['api_token'],
            base_url=ctx.obj['base_url']
        )
        
        # Would need to implement list_executions in streaming client
        console.print("[yellow]List command not fully implemented[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error listing executions: {e}[/red]")
        sys.exit(1)


def _load_workflow(file_path: str) -> FlowWorkflow:
    """Load workflow from Python file."""
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("workflow", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Find workflow in module
    for name, obj in vars(module).items():
        if hasattr(obj, '_flow_metadata'):
            # It's a flow decorator
            return obj()
            
    raise ValueError("No workflow found in file. Use @flow decorator.")


def _load_params_file(file_path: str) -> Dict[str, Any]:
    """Load parameters from JSON or YAML file."""
    content = Path(file_path).read_text()
    
    if file_path.endswith(('.yaml', '.yml')):
        return yaml.safe_load(content)
    else:
        return json.loads(content)


def _encode_mermaid(diagram: str) -> str:
    """Encode Mermaid diagram for live editor URL."""
    import base64
    import zlib
    
    # Compress and encode
    compressed = zlib.compress(diagram.encode('utf-8'), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode('utf-8')
    return encoded


if __name__ == '__main__':
    cli()


__all__ = ['cli'] 