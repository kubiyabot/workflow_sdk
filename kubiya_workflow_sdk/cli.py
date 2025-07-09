"""
Kubiya Workflow SDK CLI - Command line interface for MCP server and agent management.
"""

import click
import sys
import os
from rich.console import Console
from rich.panel import Panel
import logging

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--sentry-dsn", envvar="KUBIYA_SENTRY_DSN", help="Sentry DSN for error tracking")
@click.option("--sentry-env", envvar="KUBIYA_SENTRY_ENVIRONMENT", default="development", help="Sentry environment")
@click.option("--with-sentry", is_flag=True, envvar="KUBIYA_SENTRY_ENABLED", help="Enable Sentry error tracking")
@click.pass_context
def cli(ctx, debug, sentry_dsn, sentry_env, with_sentry):
    """Kubiya Workflow SDK - MCP Server and Agent Management."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["sentry_dsn"] = sentry_dsn
    ctx.obj["sentry_env"] = sentry_env
    ctx.obj["enable_sentry"] = with_sentry
    
    # Initialize Sentry if enabled and DSN is available
    # DSN can come from CLI flag or environment variable
    effective_dsn = sentry_dsn or os.getenv("KUBIYA_SENTRY_DSN")
    should_enable_sentry = with_sentry or os.getenv("KUBIYA_SENTRY_ENABLED", "").lower() == "true"
    
    if should_enable_sentry and effective_dsn:
        try:
            from kubiya_workflow_sdk import initialize_sentry
            success = initialize_sentry(
                dsn=effective_dsn,
                environment=sentry_env,
                enabled=True
            )
            if success:
                console.print(f"[green]✅ Sentry initialized for environment: {sentry_env}[/green]")
            else:
                console.print("[yellow]⚠️  Failed to initialize Sentry[/yellow]")
        except ImportError:
            console.print("[yellow]⚠️  Sentry SDK not available[/yellow]")
    elif should_enable_sentry:
        console.print("[yellow]⚠️  Sentry enabled but no DSN provided[/yellow]")


@cli.group()
def mcp():
    """MCP (Model Context Protocol) server commands."""
    pass


@mcp.command()
@click.option("--stdio", is_flag=True, default=True, help="Use stdio transport (default)")
@click.option("--api-key", envvar="KUBIYA_API_KEY", help="Kubiya API key")
@click.option("--base-url", default="https://api.kubiya.ai", help="Kubiya API base URL")
def server(stdio, api_key, base_url):
    """Start the Kubiya MCP server for tool integration."""
    import subprocess
    import sys
    
    if api_key:
        os.environ["KUBIYA_API_KEY"] = api_key
    if base_url:
        os.environ["KUBIYA_BASE_URL"] = base_url
    
    # Run the MCP server
    cmd = [sys.executable, "-m", "kubiya_workflow_sdk.mcp.server"]
    
    console.print("[green]🚀 Starting Kubiya MCP Server...[/green]")
    console.print(f"[blue]Transport: stdio[/blue]")
    console.print(f"[blue]Base URL: {base_url}[/blue]")
    
    if not api_key:
        console.print("[yellow]⚠️  No KUBIYA_API_KEY set - workflow execution will be limited[/yellow]")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@mcp.command()
@click.option("--provider", "-p", 
              type=click.Choice(["openai", "anthropic", "together", "groq"]),
              default="together",
              help="LLM provider to use")
@click.option("--model", "-m", help="Model name (uses provider default if not specified)")
@click.option("--api-key", help="LLM provider API key (or set via environment)")
@click.option("--kubiya-key", envvar="KUBIYA_API_KEY", help="Kubiya API key")
@click.option("--port", "-P", default=8000, type=int, help="Server port")
@click.option("--host", "-H", default="0.0.0.0", help="Server host")
def agent(provider, model, api_key, kubiya_key, port, host):
    """Start a production AI agent server with Kubiya MCP integration.
    
    This starts a full HTTP server that:
    - Provides OpenAI-compatible chat endpoint (/v1/chat/completions)
    - Streams responses in Vercel AI SDK format
    - Integrates with Kubiya MCP for workflow execution
    - Supports discovery endpoint for frontend integration
    
    Examples:
    
        # Start with Together AI (recommended)
        kubiya mcp agent --provider together --port 8000
        
        # Start with OpenAI GPT-4
        kubiya mcp agent -p openai -m gpt-4 --api-key sk-...
        
        # Start with Anthropic Claude
        kubiya mcp agent -p anthropic -m claude-3-opus-20240229
    """
    from kubiya_workflow_sdk.mcp.agent_server import run_server
    
    # Set environment variables
    if kubiya_key:
        os.environ["KUBIYA_API_KEY"] = kubiya_key
    
    # Get API keys
    kubiya_key = os.getenv("KUBIYA_API_KEY")
    provider_key = os.getenv(f"{provider.upper()}_API_KEY")
    
    # Display startup banner
    console.print(Panel(
        f"[bold]Kubiya MCP Agent Server[/bold]\n\n"
        f"Provider: {provider}\n"
        f"Model: {model or 'default'}\n"
        f"Endpoint: http://{host}:{port}\n"
        f"Kubiya API: {'✅ Configured' if kubiya_key else '⚠️ Not configured'}",
        title="Starting Agent Server",
        border_style="cyan"
    ))
    
    console.print(f"[cyan]Available endpoints:[/cyan]")
    console.print(f"  Chat:     http://{host}:{port}/v1/chat/completions")
    console.print(f"  Discover: http://{host}:{port}/discover")
    console.print(f"  Health:   http://{host}:{port}/health")
    console.print("\n[yellow]Press Ctrl+C to stop the server[/yellow]")
    
    try:
        run_server(
            provider=provider,
            model=model,
            api_key=provider_key,
            host=host,
            port=port
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        sys.exit(1)


@mcp.command()
@click.option("--provider", "-p", 
              type=click.Choice(["openai", "anthropic", "together", "groq"]),
              required=True,
              help="LLM provider")
@click.option("--model", "-m", help="Model name")
@click.option("--api-key", help="LLM provider API key")
@click.option("--kubiya-key", envvar="KUBIYA_API_KEY", help="Kubiya API key")
def chat(provider, model, api_key, kubiya_key):
    """Interactive chat with Kubiya MCP server."""
    import asyncio
    from kubiya_workflow_sdk.mcp.interactive_chat import run_interactive_chat
    
    if kubiya_key:
        os.environ["KUBIYA_API_KEY"] = kubiya_key
    
    # Default models
    default_models = {
        "openai": "gpt-4",
        "anthropic": "claude-3-opus-20240229", 
        "together": "deepseek-ai/DeepSeek-V3",
        "groq": "llama-3.1-70b-versatile"
    }
    
    if not model:
        model = default_models.get(provider, "gpt-4")  # fallback to gpt-4 if provider not found
    
    console.print(f"[green]💬 Starting interactive chat with {provider}/{model}[/green]")
    console.print("[yellow]Type 'exit' or 'quit' to end the conversation[/yellow]")
    console.print("[yellow]Type 'help' for available commands[/yellow]\n")
    
    try:
        asyncio.run(run_interactive_chat(
            provider=provider,
            model=model,
            api_key=api_key
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Chat ended[/yellow]")
    except Exception as e:
        console.print(f"[red]Chat error: {e}[/red]")
        sys.exit(1)


@mcp.command()
@click.option("--provider", "-p", 
              type=click.Choice(["openai", "anthropic", "together", "groq", "ollama"]),
              default="together",
              help="LLM provider to use")
@click.option("--model", "-m", help="Model name (provider-specific)")
@click.option("--api-key", help="LLM provider API key")
@click.option("--kubiya-key", envvar="KUBIYA_API_KEY", help="Kubiya API key")
@click.option("--scenario", "-s",
              type=click.Choice(["basic", "cicd", "data", "security", "custom"]),
              default="basic",
              help="Test scenario to run")
@click.option("--interactive", "-i", is_flag=True, help="Interactive conversation mode")
@click.option("--output", "-o", help="Save conversation log to file")
def test(provider, model, api_key, kubiya_key, scenario, interactive, output):
    """Test MCP server with an AI agent."""
    import asyncio
    from kubiya_workflow_sdk.mcp.test_agent import run_mcp_test
    
    # Set up environment
    if kubiya_key:
        os.environ["KUBIYA_API_KEY"] = kubiya_key
    
    # Default models per provider
    default_models = {
        "openai": "gpt-4",
        "anthropic": "claude-3-opus-20240229",
        "together": "deepseek-ai/DeepSeek-V3",
        "groq": "llama-3.1-70b-versatile",
        "ollama": "llama3.1:70b"
    }
    
    if not model:
        model = default_models.get(provider, "gpt-4")
    
    console.print(f"[green]🤖 Testing MCP server with {provider}/{model}[/green]")
    console.print(f"[blue]Scenario: {scenario}[/blue]")
    
    try:
        asyncio.run(run_mcp_test(
            provider=provider,
            model=model,
            api_key=api_key,
            scenario=scenario,
            interactive=interactive,
            output_file=output
        ))
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    from .__version__ import __version__
    
    console.print(Panel(
        f"[bold]Kubiya Workflow SDK[/bold]\n\n"
        f"Version: {__version__}\n"
        f"Python: {sys.version.split()[0]}\n"
        f"Platform: {sys.platform}",
        title="Version Information",
        border_style="blue"
    ))


@cli.command()
@click.option("--full", is_flag=True, help="Show full documentation")
def help(full):
    """Show help and usage examples."""
    
    help_text = """
[bold]Kubiya Workflow SDK CLI[/bold]

The Kubiya CLI provides tools for running MCP servers and AI agents that can create
and execute workflows through natural language.

[bold]Quick Start:[/bold]

1. Start an AI agent server (for web apps):
   [cyan]kubiya mcp agent --provider together --port 8000[/cyan]

2. Start an MCP server (for Claude Desktop):
   [cyan]kubiya mcp server[/cyan]

3. Interactive chat:
   [cyan]kubiya mcp chat --provider openai[/cyan]

[bold]Common Commands:[/bold]

• [cyan]kubiya mcp agent[/cyan] - Start HTTP agent server for Vercel AI SDK
• [cyan]kubiya mcp server[/cyan] - Start MCP server for Claude Desktop
• [cyan]kubiya mcp chat[/cyan] - Interactive chat with workflows
• [cyan]kubiya mcp test[/cyan] - Test MCP integration
• [cyan]kubiya version[/cyan] - Show version info

[bold]Environment Variables:[/bold]

• KUBIYA_API_KEY - Your Kubiya API key for workflow execution
• TOGETHER_API_KEY - Together AI API key
• OPENAI_API_KEY - OpenAI API key
• ANTHROPIC_API_KEY - Anthropic API key
• GROQ_API_KEY - Groq API key
"""

    if full:
        help_text += """
[bold]Agent Server Details:[/bold]

The agent server provides a production-ready HTTP API that:
- Implements OpenAI-compatible chat completions endpoint
- Streams responses in Vercel AI SDK format
- Integrates with Kubiya MCP for workflow tools
- Supports multiple LLM providers

[bold]Example Integration:[/bold]

In your Next.js app with Vercel AI SDK:

```typescript
const { messages, input, handleSubmit } = useChat({
  api: 'http://localhost:8000/v1/chat/completions',
});
```

[bold]Available Providers:[/bold]

• together - Best cost/performance ratio (recommended)
• openai - GPT-4 and GPT-3.5
• anthropic - Claude 3 models
• groq - Fast inference with open models

[bold]Test Scenarios:[/bold]

• basic - Simple workflow creation and execution
• cicd - CI/CD pipeline workflows
• data - Data processing workflows
• security - Security scanning workflows
• custom - Define your own test prompts
"""

    console.print(Panel(help_text, title="Help", border_style="green"))
    
    if not full:
        console.print("\n[dim]Use --full for complete documentation[/dim]")


if __name__ == "__main__":
    cli()


__all__ = ["cli"]
