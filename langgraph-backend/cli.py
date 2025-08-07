#!/usr/bin/env python3
"""
EspressoBot LangGraph Backend - Interactive CLI
A rich terminal interface for testing and interacting with the backend
"""

import asyncio
import httpx
import json
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.layout import Layout
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
import click

console = Console()

class EspressoBotCLI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.conversation_id = f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.conversation_history: List[Dict[str, Any]] = []
        
    async def check_health(self) -> bool:
        """Check if backend is running"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    async def get_agents(self) -> List[Dict[str, str]]:
        """Get list of available agents"""
        try:
            response = await self.client.get(f"{self.base_url}/api/agent/agents")
            return response.json()["agents"]
        except:
            return []
    
    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message to the backend"""
        payload = {
            "message": message,
            "conversation_id": self.conversation_id,
            "user_id": "cli-user"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/agent/message",
            json=payload
        )
        
        return response.json()
    
    async def stream_message(self, message: str):
        """Stream a message response"""
        payload = {
            "message": message,
            "conversation_id": self.conversation_id
        }
        
        with console.status("[cyan]Thinking...", spinner="dots"):
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/agent/sse",
                json=payload,
                headers={"Accept": "text/event-stream"}
            ) as response:
                buffer = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "message" in data:
                                buffer = data["message"]
                                # Update status with current agent
                                agent = data.get("agent", "bot")
                                console.print(f"[dim]Agent: {agent}[/dim]")
                        except:
                            pass
                
                if buffer:
                    return {"content": buffer, "agent": "bot"}
        
        return None
    
    def display_welcome(self):
        """Display welcome message"""
        welcome = Panel.fit(
            "[bold cyan]🤖 EspressoBot LangGraph Backend CLI[/bold cyan]\n"
            "[dim]Interactive testing interface for the new backend[/dim]",
            border_style="cyan"
        )
        console.print(welcome)
    
    def display_agents(self, agents: List[Dict[str, str]]):
        """Display available agents in a table"""
        table = Table(title="Available Agents", show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan", width=20)
        table.add_column("Description", style="white")
        
        for agent in agents:
            table.add_row(agent["name"], agent["description"])
        
        console.print(table)
    
    def display_message(self, role: str, content: str, agent: Optional[str] = None):
        """Display a message with formatting"""
        if role == "user":
            console.print(Panel(content, title="[bold blue]You[/bold blue]", border_style="blue"))
        else:
            title = f"[bold green]{agent or 'Assistant'}[/bold green]"
            # Try to render as markdown for better formatting
            try:
                formatted = Markdown(content)
                console.print(Panel(formatted, title=title, border_style="green"))
            except:
                console.print(Panel(content, title=title, border_style="green"))
    
    def display_help(self):
        """Display help information"""
        help_text = """
[bold]Commands:[/bold]
  [cyan]/help[/cyan]     - Show this help message
  [cyan]/agents[/cyan]   - List available agents
  [cyan]/clear[/cyan]    - Clear conversation history
  [cyan]/export[/cyan]   - Export conversation to file
  [cyan]/stream[/cyan]   - Toggle streaming mode
  [cyan]/conv[/cyan]     - Show conversation ID
  [cyan]/new[/cyan]      - Start new conversation
  [cyan]/quit[/cyan]     - Exit the CLI
  
[bold]Tips:[/bold]
  • Ask about products: "Find product SKU ESP-001"
  • Check prices: "What's the price of Breville machines?"
  • Inventory queries: "Check stock levels"
  • Sales operations: "Start a MAP sale"
        """
        console.print(Panel(help_text, title="[bold]Help[/bold]", border_style="yellow"))
    
    async def export_conversation(self):
        """Export conversation to JSON file"""
        filename = f"conversation-{self.conversation_id}.json"
        with open(filename, "w") as f:
            json.dump({
                "conversation_id": self.conversation_id,
                "timestamp": datetime.now().isoformat(),
                "messages": self.conversation_history
            }, f, indent=2)
        console.print(f"[green]✓[/green] Conversation exported to {filename}")
    
    async def run_interactive(self):
        """Run interactive chat mode"""
        self.display_welcome()
        
        # Check backend health
        with console.status("[cyan]Connecting to backend...", spinner="dots"):
            if not await self.check_health():
                console.print("[red]❌ Backend is not running![/red]")
                console.print("Start the backend with: [cyan]uvicorn app.main:app --reload[/cyan]")
                return
        
        console.print("[green]✓[/green] Connected to backend\n")
        
        # Get and display agents
        agents = await self.get_agents()
        if agents:
            self.display_agents(agents)
            console.print()
        
        console.print("Type [cyan]/help[/cyan] for commands or start chatting!\n")
        
        streaming = False
        
        while True:
            try:
                # Get user input
                message = Prompt.ask("[bold blue]You[/bold blue]")
                
                if not message:
                    continue
                
                # Handle commands
                if message.startswith("/"):
                    command = message[1:].lower()
                    
                    if command == "quit":
                        if Confirm.ask("Are you sure you want to quit?"):
                            break
                    elif command == "help":
                        self.display_help()
                    elif command == "agents":
                        agents = await self.get_agents()
                        self.display_agents(agents)
                    elif command == "clear":
                        self.conversation_history = []
                        console.clear()
                        self.display_welcome()
                        console.print("[green]✓[/green] Conversation cleared\n")
                    elif command == "export":
                        await self.export_conversation()
                    elif command == "stream":
                        streaming = not streaming
                        mode = "enabled" if streaming else "disabled"
                        console.print(f"[yellow]Streaming {mode}[/yellow]")
                    elif command == "conv":
                        console.print(f"Conversation ID: [cyan]{self.conversation_id}[/cyan]")
                    elif command == "new":
                        self.conversation_id = f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                        self.conversation_history = []
                        console.print(f"[green]✓[/green] New conversation: {self.conversation_id}")
                    else:
                        console.print(f"[red]Unknown command: /{command}[/red]")
                    continue
                
                # Add to history
                self.conversation_history.append({"role": "user", "content": message})
                
                # Send message
                try:
                    if streaming:
                        response = await self.stream_message(message)
                        if response:
                            self.display_message("assistant", response["content"], response.get("agent"))
                            self.conversation_history.append({
                                "role": "assistant", 
                                "content": response["content"],
                                "agent": response.get("agent")
                            })
                    else:
                        with console.status("[cyan]Thinking...", spinner="dots"):
                            result = await self.send_message(message)
                        
                        if result["success"]:
                            # Get only the last assistant message (the new response)
                            assistant_messages = [msg for msg in result["messages"] if msg["role"] == "assistant"]
                            if assistant_messages:
                                # Display only the last (newest) assistant message
                                msg = assistant_messages[-1]
                                agent = msg.get("metadata", {}).get("agent", "bot")
                                self.display_message("assistant", msg["content"], agent)
                                self.conversation_history.append({
                                    "role": "assistant",
                                    "content": msg["content"],
                                    "agent": agent
                                })
                        else:
                            console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
                
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                
                console.print()  # Add spacing
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /quit to exit[/yellow]")
            except EOFError:
                break
        
        console.print("\n[cyan]👋 Goodbye![/cyan]")
    
    async def run_single_command(self, message: str):
        """Run a single command and exit"""
        if not await self.check_health():
            console.print("[red]❌ Backend is not running![/red]")
            return
        
        with console.status("[cyan]Processing...", spinner="dots"):
            result = await self.send_message(message)
        
        if result["success"]:
            # Get only the last assistant message (the new response)
            assistant_messages = [msg for msg in result["messages"] if msg["role"] == "assistant"]
            if assistant_messages:
                msg = assistant_messages[-1]
                agent = msg.get("metadata", {}).get("agent", "bot")
                self.display_message("assistant", msg["content"], agent)
        else:
            console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
    
    async def close(self):
        """Clean up"""
        await self.client.aclose()

@click.command()
@click.option('--url', default='http://localhost:8000', help='Backend URL')
@click.option('--message', '-m', help='Send a single message and exit')
@click.option('--agents', '-a', is_flag=True, help='List available agents and exit')
@click.option('--health', '-h', is_flag=True, help='Check backend health and exit')
def main(url: str, message: Optional[str], agents: bool, health: bool):
    """EspressoBot LangGraph Backend - Interactive CLI"""
    
    async def run():
        cli = EspressoBotCLI(url)
        
        try:
            if health:
                # Check health
                if await cli.check_health():
                    console.print("[green]✓[/green] Backend is healthy")
                else:
                    console.print("[red]❌[/red] Backend is not responding")
            
            elif agents:
                # List agents
                if not await cli.check_health():
                    console.print("[red]❌ Backend is not running![/red]")
                    return
                
                agents_list = await cli.get_agents()
                cli.display_agents(agents_list)
            
            elif message:
                # Single message
                await cli.run_single_command(message)
            
            else:
                # Interactive mode
                await cli.run_interactive()
        
        finally:
            await cli.close()
    
    asyncio.run(run())

if __name__ == "__main__":
    main()