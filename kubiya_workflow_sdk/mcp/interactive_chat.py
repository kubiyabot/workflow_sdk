"""Interactive chat interface for Kubiya MCP Server."""

import asyncio
import os
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint

from mcp_use import MCPClient, MCPAgent
from .test_agent import get_llm

console = Console()


class InteractiveChat:
    """Interactive chat session with Kubiya MCP Server."""
    
    def __init__(self, agent: MCPAgent):
        self.agent = agent
        self.history = []
        self.commands = {
            "help": self.show_help,
            "history": self.show_history,
            "clear": self.clear_history,
            "workflows": self.list_workflows,
            "runners": self.list_runners,
            "export": self.export_workflow,
            "status": self.check_status
        }
    
    async def show_help(self):
        """Show available commands."""
        help_text = """
# Available Commands

- **help** - Show this help message
- **history** - Show conversation history
- **clear** - Clear conversation history
- **workflows** - List all workflows
- **runners** - List available runners
- **export <name>** - Export workflow as YAML
- **status <id>** - Check execution status
- **exit/quit** - End the chat

# Example Prompts

- "Create a workflow that backs up a database"
- "List all workflows and show their descriptions"
- "Execute the backup-database workflow with production parameters"
- "Create a CI/CD pipeline for a Node.js application"
- "Add error handling to the last workflow"
"""
        console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))
    
    async def show_history(self):
        """Show conversation history."""
        if not self.history:
            console.print("[yellow]No conversation history yet[/yellow]")
            return
        
        for i, (timestamp, role, message) in enumerate(self.history, 1):
            time_str = timestamp.strftime("%H:%M:%S")
            if role == "user":
                console.print(f"[dim]{time_str}[/dim] [blue]You:[/blue] {message}")
            else:
                console.print(f"[dim]{time_str}[/dim] [green]Assistant:[/green] {message[:100]}...")
    
    async def clear_history(self):
        """Clear conversation history."""
        self.history = []
        console.print("[yellow]Conversation history cleared[/yellow]")
    
    async def list_workflows(self):
        """List all workflows."""
        response = await self.agent.run("List all workflows with their descriptions")
        console.print(Panel(str(response), title="Workflows", border_style="green"))
    
    async def list_runners(self):
        """List available runners."""
        response = await self.agent.run("List all available Kubiya runners")
        console.print(Panel(str(response), title="Runners", border_style="green"))
    
    async def export_workflow(self, name: str = None):
        """Export a workflow as YAML."""
        if not name:
            console.print("[red]Usage: export <workflow-name>[/red]")
            return
        
        response = await self.agent.run(f"Export the {name} workflow as YAML")
        console.print(Panel(str(response), title=f"Export: {name}", border_style="green"))
    
    async def check_status(self, execution_id: str = None):
        """Check execution status."""
        if not execution_id:
            console.print("[red]Usage: status <execution-id>[/red]")
            return
        
        response = await self.agent.run(f"Check the status of execution {execution_id}")
        console.print(Panel(str(response), title=f"Status: {execution_id}", border_style="green"))
    
    async def process_command(self, user_input: str) -> bool:
        """Process a command. Returns True if should continue, False to exit."""
        parts = user_input.strip().split(maxsplit=1)
        if not parts:
            return True
        
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None
        
        # Check for exit
        if command in ["exit", "quit"]:
            return False
        
        # Check for built-in command
        if command in self.commands:
            handler = self.commands[command]
            if args and command in ["export", "status"]:
                await handler(args)
            else:
                await handler()
            return True
        
        # Not a command, process as regular prompt
        return None
    
    async def run(self):
        """Run the interactive chat loop."""
        await self.show_help()
        
        while True:
            try:
                # Get user input
                user_input = console.input("\n[bold cyan]You:[/bold cyan] ")
                
                # Check for commands
                result = await self.process_command(user_input)
                if result is False:
                    break
                elif result is True:
                    continue
                
                # Add to history
                self.history.append((datetime.now(), "user", user_input))
                
                # Get AI response
                console.print("[dim]Thinking...[/dim]", end="\r")
                response = await self.agent.run(user_input)
                
                # Clear thinking message and show response
                console.print(" " * 20, end="\r")  # Clear line
                console.print(Panel(
                    str(response),
                    title="[green]Assistant[/green]",
                    border_style="green",
                    expand=False
                ))
                
                # Add to history
                self.history.append((datetime.now(), "assistant", str(response)))
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' or 'quit' to end the chat[/yellow]")
            except Exception as e:
                console.print(f"\n[red]Error: {str(e)}[/red]")


async def run_interactive_chat(
    provider: str,
    model: str,
    api_key: Optional[str] = None
) -> None:
    """Run interactive chat with specified LLM provider."""
    
    try:
        # Create MCP client
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
        llm = get_llm(provider, model, api_key)
        
        # Create agent
        agent = MCPAgent(llm=llm, client=client)
        
        # Create and run chat
        chat = InteractiveChat(agent)
        await chat.run()
        
        console.print("\n[green]Thanks for using Kubiya MCP Chat![/green]")
        
    except Exception as e:
        console.print(f"\n[red]Chat error: {str(e)}[/red]")
        raise


if __name__ == "__main__":
    # Test the module directly
    import sys
    
    if len(sys.argv) > 1:
        provider = sys.argv[1]
        model = sys.argv[2] if len(sys.argv) > 2 else None
        
        asyncio.run(run_interactive_chat(provider, model))
    else:
        print("Usage: python interactive_chat.py <provider> [model]") 