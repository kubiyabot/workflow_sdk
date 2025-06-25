"""MCP Test Agent - Multi-provider LLM testing for Kubiya MCP Server."""

import asyncio
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from mcp_use import MCPClient, MCPAgent
from langchain_core.language_models import BaseChatModel

console = Console()


def get_llm(provider: str, model: Optional[str], api_key: Optional[str] = None) -> BaseChatModel:
    """Get LLM instance for the specified provider."""
    
    # Default models for each provider
    default_models = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "together": "deepseek-ai/DeepSeek-V3",
        "groq": "llama-3.3-70b-versatile",
        "ollama": "llama3.2"
    }
    
    # Use default model if none specified
    if model is None:
        model = default_models.get(provider)
        if not model:
            raise ValueError(f"No default model for provider {provider}")
    
    # Get API key from environment if not provided
    if not api_key:
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "together": "TOGETHER_API_KEY",
            "groq": "GROQ_API_KEY",
            "ollama": None  # Ollama doesn't need API key
        }
        
        env_var = env_vars.get(provider)
        if env_var:
            api_key = os.getenv(env_var)
            if not api_key:
                raise ValueError(f"No API key provided. Set {env_var} or use --api-key")
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=api_key)
    
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=api_key)
    
    elif provider == "together":
        from langchain_together import ChatTogether
        return ChatTogether(model=model, api_key=api_key)
    
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, api_key=api_key)
    
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model)
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_test_scenarios() -> Dict[str, List[str]]:
    """Get predefined test scenarios."""
    return {
        "basic": [
            "Create a simple hello world workflow that prints a greeting",
            "List all the workflows we have created",
            "Execute the hello world workflow",
            "Check the execution status"
        ],
        
        "cicd": [
            "Create a CI/CD workflow that builds a Docker image, runs tests, and deploys to Kubernetes",
            "Add parallel testing for Python, JavaScript, and Go to the workflow",
            "Add a manual approval step before production deployment",
            "Validate the workflow and show me the YAML",
            "Execute the workflow with dry_run mode"
        ],
        
        "data": [
            "Create a data processing workflow that downloads CSV files from S3",
            "Add a step to process the data with pandas and generate statistics",
            "Add error handling and retry logic for the S3 operations",
            "Add a final step to send results via email",
            "List available runners and execute on a GPU runner if available"
        ],
        
        "security": [
            "Create a security scanning workflow for a Git repository",
            "Add SAST scanning with Semgrep",
            "Add dependency vulnerability scanning",
            "Add container image scanning if Dockerfile exists",
            "Add a step to generate a security report and fail if critical issues found",
            "Validate and export the workflow as YAML"
        ],
        
        "custom": []  # Will be filled interactively
    }


async def run_mcp_test(
    provider: str,
    model: str,
    api_key: Optional[str],
    scenario: str,
    interactive: bool,
    output_file: Optional[str]
) -> None:
    """Run MCP test with specified configuration."""
    
    # Initialize conversation log
    conversation_log = {
        "provider": provider,
        "model": model,
        "scenario": scenario,
        "start_time": datetime.now().isoformat(),
        "messages": []
    }
    
    try:
        # Create MCP client
        console.print("[yellow]Initializing MCP client...[/yellow]")
        client = MCPClient.from_dict({
            "mcpServers": {
                "kubiya": {
                    "command": "python3",
                    "args": ["-m", "kubiya_workflow_sdk.mcp.server"],
                    "env": {
                        "KUBIYA_API_KEY": os.getenv("KUBIYA_API_KEY", ""),
                        "KUBIYA_BASE_URL": os.getenv("KUBIYA_BASE_URL", "https://api.kubiya.ai")
                    }
                }
            }
        })
        
        # Create LLM
        console.print(f"[yellow]Initializing {provider} LLM...[/yellow]")
        llm = get_llm(provider, model, api_key)
        
        # Create agent
        agent = MCPAgent(llm=llm, client=client)
        
        # Get test prompts
        scenarios = get_test_scenarios()
        prompts = scenarios.get(scenario, [])
        
        if scenario == "custom" or interactive:
            console.print("\n[green]Enter your test prompts (empty line to finish):[/green]")
            custom_prompts = []
            while True:
                prompt = console.input("[cyan]> [/cyan]")
                if not prompt:
                    break
                custom_prompts.append(prompt)
            
            if scenario == "custom":
                prompts = custom_prompts
            else:
                prompts.extend(custom_prompts)
        
        # Run test conversation
        console.print(f"\n[green]Starting {scenario} scenario with {len(prompts)} prompts[/green]")
        console.print("="*60)
        
        for i, prompt in enumerate(prompts, 1):
            console.print(f"\n[bold blue]Prompt {i}/{len(prompts)}:[/bold blue] {prompt}")
            
            # Log user message
            conversation_log["messages"].append({
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().isoformat()
            })
            
            # Get response
            try:
                response = await agent.run(prompt)
                
                # Display response
                console.print(Panel(
                    str(response),
                    title=f"[green]{provider}/{model} Response[/green]",
                    border_style="green"
                ))
                
                # Log assistant message
                conversation_log["messages"].append({
                    "role": "assistant", 
                    "content": str(response),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                console.print(f"[red]{error_msg}[/red]")
                
                conversation_log["messages"].append({
                    "role": "error",
                    "content": error_msg,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Summary
        console.print("\n" + "="*60)
        console.print("[green]Test completed![/green]")
        
        # Show execution summary
        await show_test_summary(agent, conversation_log)
        
        # Save conversation log if requested
        if output_file:
            conversation_log["end_time"] = datetime.now().isoformat()
            with open(output_file, "w") as f:
                json.dump(conversation_log, f, indent=2)
            console.print(f"\n[green]Conversation saved to: {output_file}[/green]")
    
    except Exception as e:
        console.print(f"\n[red]Test failed: {str(e)}[/red]")
        raise


async def show_test_summary(agent: MCPAgent, log: Dict[str, Any]) -> None:
    """Show test execution summary."""
    
    # Try to get workflow information
    try:
        # Get list of workflows
        result = await agent.run("List all workflows in JSON format")
        
        # Create summary table
        table = Table(title="Test Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Provider", log["provider"])
        table.add_row("Model", log["model"])
        table.add_row("Scenario", log["scenario"])
        table.add_row("Total Prompts", str(len([m for m in log["messages"] if m["role"] == "user"])))
        table.add_row("Errors", str(len([m for m in log["messages"] if m["role"] == "error"])))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[yellow]Could not generate full summary: {e}[/yellow]")


if __name__ == "__main__":
    # Test the module directly
    import sys
    
    if len(sys.argv) > 1:
        provider = sys.argv[1]
        model = sys.argv[2] if len(sys.argv) > 2 else None
        
        asyncio.run(run_mcp_test(
            provider=provider,
            model=model,
            api_key=None,
            scenario="basic",
            interactive=False,
            output_file=None
        ))
    else:
        print("Usage: python test_agent.py <provider> [model]") 