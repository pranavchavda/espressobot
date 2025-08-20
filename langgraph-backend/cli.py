#!/usr/bin/env python3
"""
EspressoBot LangGraph Backend - Interactive CLI
A rich terminal interface for testing and interacting with the backend
"""

import asyncio
import httpx
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.shortcuts import CompleteStyle
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False
from rich.live import Live
from rich.layout import Layout
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
import click

console = Console()

class EspressoBotCLI:
    def __init__(self, base_url: str = "http://localhost:8000", config_file: Optional[str] = None):
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Use config values or defaults
        self.base_url = self.config.get("base_url", base_url)
        self.default_user_id = self.config.get("default_user_id", "1")
        self.timeout = self.config.get("timeout", 300.0)  # 5 minutes for long-running operations
        self.max_retries = self.config.get("max_retries", 3)
        self.access_token = self.config.get("access_token")  # Store OAuth token
        
        # Set up HTTP client with auth headers if available
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        self.conversation_id = f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Define available commands for autocomplete
        self.commands = [
            "/help", "/agents", "/clear", "/export", "/stream", "/conv", "/new", "/quit",
            "/memory", "/memory-search", "/memory-delete", "/memory-export",
            "/sales", "/orders", "/revenue",
            "/product", "/products", "/pricing",
            "/system-health", "/system-status", "/config", "/debug",
            "/agents-config", "/orchestrator-status", "/logs",
            "/login", "/get-token", "/logout", "/auth-status"
        ]
        
        # Create completer for commands (if prompt-toolkit is available)
        if PROMPT_TOOLKIT_AVAILABLE:
            self.command_completer = WordCompleter(self.commands, ignore_case=True)
        else:
            self.command_completer = None
    
    def get_user_input(self, prompt_text: str = "You: ") -> str:
        """Get user input with helpful command list"""
        try:
            # Show available commands hint for commands starting with /
            clean_prompt = prompt_text.rstrip(': ')
            
            # Show command hint on first use or when user types just "/"
            hint_shown = getattr(self, '_hint_shown', False)
            if not hint_shown:
                console.print("[dim]💡 Tip: Type [cyan]/help[/cyan] for commands, or [cyan]/[/cyan] to see available commands[/dim]")
                self._hint_shown = True
            
            # Use rich prompt with enhanced formatting
            user_input = Prompt.ask(f"[bold blue]{clean_prompt}[/bold blue]")
            
            # If user types just "/", show available commands
            if user_input.strip() == "/":
                console.print("\n[cyan]Available commands:[/cyan]")
                # Group commands by category
                command_groups = {
                    "Chat": ["/help", "/agents", "/clear", "/quit", "/new"],
                    "Memory": ["/memory", "/memory-search", "/memory-delete"],
                    "Analytics": ["/sales", "/orders"],
                    "Products": ["/product", "/products"],
                    "System": ["/system-status", "/config", "/debug"],
                    "Auth": ["/login", "/logout", "/auth-status"]
                }
                
                for category, commands in command_groups.items():
                    console.print(f"\n[bold]{category}:[/bold]")
                    for cmd in commands:
                        console.print(f"  [cyan]{cmd}[/cyan]")
                
                console.print("\n[dim]Type any command above, or start chatting![/dim]")
                # Recursive call to get actual input
                return self.get_user_input(prompt_text)
            
            return user_input
            
        except (EOFError, KeyboardInterrupt):
            return ""
        
    def load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file"""
        if config_file is None:
            # Look for config in common locations
            config_paths = [
                Path.cwd() / "espressobot-cli.json",
                Path.home() / ".espressobot" / "cli.json",
                Path.home() / ".config" / "espressobot" / "cli.json"
            ]
            
            for path in config_paths:
                if path.exists():
                    config_file = str(path)
                    break
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                console.print(f"[dim]Loaded config from {config_file}[/dim]")
                return config
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load config file {config_file}: {e}[/yellow]")
        
        return {}
    
    def save_config(self, config_file: Optional[str] = None) -> bool:
        """Save current configuration to file"""
        if config_file is None:
            config_dir = Path.home() / ".config" / "espressobot"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = str(config_dir / "cli.json")
        
        config = {
            "base_url": self.base_url,
            "default_user_id": self.default_user_id,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "access_token": self.access_token
        }
        
        try:
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            console.print(f"[green]✓[/green] Configuration saved to {config_file}")
            return True
        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
            return False
    
    async def make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic and better error handling"""
        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    response = await self.client.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = await self.client.post(url, **kwargs)
                elif method.upper() == "DELETE":
                    response = await self.client.delete(url, **kwargs)
                else:
                    return {"error": f"Unsupported HTTP method: {method}"}
                
                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg += f": {error_data['error']}"
                        elif "detail" in error_data:
                            error_msg += f": {error_data['detail']}"
                    except:
                        error_msg += f": {response.text[:100]}"
                    
                    return {"error": error_msg}
                
                return response.json()
                
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    console.print(f"[yellow]Request timeout, retrying... (attempt {attempt + 1}/{self.max_retries})[/yellow]")
                    continue
                return {"error": f"Request timeout after {self.max_retries} attempts"}
            except httpx.ConnectError:
                return {"error": "Could not connect to backend. Is it running?"}
            except Exception as e:
                return {"error": f"Request failed: {str(e)}"}
        
        return {"error": "Max retries exceeded"}
        
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
            # Try the agent management endpoint first
            response = await self.client.get(f"{self.base_url}/api/agent-management/agents")
            if response.status_code == 200:
                data = response.json()
                
                # Handle the response format
                agents_list = []
                if isinstance(data, dict) and "agents" in data:
                    agents_data = data["agents"]
                elif isinstance(data, list):
                    agents_data = data
                else:
                    agents_data = []
                
                # Convert agents to expected format
                for agent in agents_data:
                    name = agent.get("agent_name") or agent.get("id") or agent.get("name", "unknown")
                    description = agent.get("description", "No description")
                    model_info = agent.get("model_slug", "")
                    provider = agent.get("model_provider", "")
                    
                    # Add model info to description if available
                    if model_info and provider:
                        description += f" (Model: {provider}/{model_info})"
                    elif model_info:
                        description += f" (Model: {model_info})"
                    
                    agents_list.append({
                        "name": name,
                        "description": description
                    })
                
                return agents_list
            
            # Fallback to dynamic agents endpoint
            response = await self.client.get(f"{self.base_url}/api/dynamic-agents/")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return [{"name": agent.get("name", agent.get("id", "unknown")), 
                            "description": agent.get("description", "Dynamic agent")} for agent in data]
                return []
                
        except Exception as e:
            console.print(f"[dim]Debug: Failed to get agents: {e}[/dim]")
            return []
    
    # Memory Management Methods
    async def get_memories(self, user_id: str = "1", limit: int = 20, category: Optional[str] = None) -> Dict[str, Any]:
        """Get user memories with optional filtering"""
        try:
            params = {"limit": limit}
            if category:
                params["category"] = category
            response = await self.client.get(f"{self.base_url}/api/memory/list/{user_id}", params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def search_memories(self, user_id: str, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search memories by semantic similarity"""
        try:
            payload = {"query": query, "limit": limit}
            response = await self.client.post(f"{self.base_url}/api/memory/search/{user_id}", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_memories(self, user_id: str, memory_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple memories"""
        try:
            payload = {"memory_ids": memory_ids}
            response = await self.client.delete(f"{self.base_url}/api/memory/bulk/{user_id}", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # Analytics Methods  
    async def get_daily_sales(self, date: str = "today") -> Dict[str, Any]:
        """Get daily sales summary"""
        try:
            params = {"date": date}
            response = await self.client.get(f"{self.base_url}/api/analytics/daily-sales", params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_order_analytics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get order analytics for date range"""
        try:
            params = {"start_date": start_date, "end_date": end_date}
            response = await self.client.get(f"{self.base_url}/api/analytics/orders", params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # Product Management Methods
    async def search_products(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search products"""
        try:
            params = {"query": query, "limit": limit}
            response = await self.client.get(f"{self.base_url}/api/products/search", params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_product(self, identifier: str) -> Dict[str, Any]:
        """Get product by SKU, handle, or ID"""
        try:
            response = await self.client.get(f"{self.base_url}/api/products/{identifier}")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # Admin Methods
    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get orchestrator status and configuration"""
        try:
            response = await self.client.get(f"{self.base_url}/api/orchestrator/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Combine multiple status checks
            health = await self.check_health()
            agents = await self.get_agents()
            
            status = {
                "backend_health": health,
                "agent_count": len(agents),
                "agents": [agent["name"] for agent in agents],
                "timestamp": datetime.now().isoformat()
            }
            
            # Try to get orchestrator status
            orch_status = await self.get_orchestrator_status()
            if "error" not in orch_status:
                status["orchestrator"] = orch_status
                
            return status
        except Exception as e:
            return {"error": str(e)}
    
    async def get_agent_config(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get agent configuration"""
        try:
            if agent_name:
                response = await self.client.get(f"{self.base_url}/api/orchestrator/agents/{agent_name}")
            else:
                response = await self.client.get(f"{self.base_url}/api/orchestrator/agents")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # Enhanced logging and monitoring
    async def get_conversation_logs(self) -> Dict[str, Any]:
        """Get recent conversation logs"""
        try:
            response = await self.client.get(f"{self.base_url}/api/agent/logs")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # Authentication Methods
    async def start_oauth_flow(self, provider: str = "google") -> Dict[str, Any]:
        """Start OAuth authentication flow"""
        try:
            response = await self.client.post(f"{self.base_url}/api/auth/oauth/{provider}/start")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def complete_oauth_flow(self, code: str, state: str, provider: str = "google") -> Dict[str, Any]:
        """Complete OAuth flow with authorization code"""
        try:
            payload = {"code": code, "state": state}
            response = await self.client.post(f"{self.base_url}/api/auth/oauth/{provider}/callback", json=payload)
            result = response.json()
            
            # Store access token if successful
            if "access_token" in result:
                self.access_token = result["access_token"]
                # Update client headers
                self.client.headers["Authorization"] = f"Bearer {self.access_token}"
                console.print("[green]✓[/green] Authentication successful!")
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    async def check_auth_status(self) -> Dict[str, Any]:
        """Check current authentication status"""
        try:
            response = await self.client.get(f"{self.base_url}/api/auth/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def logout(self) -> bool:
        """Logout and clear stored tokens"""
        try:
            if self.access_token:
                await self.client.post(f"{self.base_url}/api/auth/logout")
            
            # Clear stored token
            self.access_token = None
            if "Authorization" in self.client.headers:
                del self.client.headers["Authorization"]
            
            # Clear from config
            self.config["access_token"] = None
            self.save_config()
            
            console.print("[green]✓[/green] Logged out successfully")
            return True
        except Exception as e:
            console.print(f"[red]Logout error: {e}[/red]")
            return False
    
    def open_browser_for_auth(self, auth_url: str):
        """Open browser for OAuth authentication"""
        import webbrowser
        console.print(f"[cyan]Opening browser for authentication...[/cyan]")
        console.print(f"[dim]URL: {auth_url}[/dim]")
        
        try:
            webbrowser.open(auth_url)
            console.print("[green]✓[/green] Browser opened. Please complete authentication.")
        except Exception as e:
            console.print(f"[yellow]Could not open browser automatically: {e}[/yellow]")
            console.print(f"[cyan]Please manually open this URL in your browser:[/cyan]")
            console.print(f"[blue]{auth_url}[/blue]")
    
    async def interactive_login_web(self, provider: str = "google") -> bool:
        """OAuth login via web interface (uses existing Google OAuth registration)"""
        console.print(f"[bold]Starting {provider.title()} OAuth Authentication via Web Interface[/bold]")
        
        # Use the web interface URL that's already registered with Google
        web_auth_url = f"http://localhost:5173/auth/login?provider={provider}&cli=true"
        
        console.print("[cyan]Opening web interface for authentication...[/cyan]")
        console.print("[dim]This uses the existing Google OAuth registration from the web interface[/dim]")
        
        # Open browser to web interface
        self.open_browser_for_auth(web_auth_url)
        
        console.print("\n[yellow]Complete the authentication in your browser.[/yellow]")
        console.print("[yellow]After successful login, you'll see a CLI token on the page.[/yellow]")
        
        # Get the CLI token from user
        cli_token = Prompt.ask("[cyan]Enter the CLI token from the web page")
        
        if not cli_token:
            console.print("[red]No CLI token provided[/red]")
            return False
        
        # Validate the CLI token with the backend
        with console.status("[cyan]Validating CLI token...", spinner="dots"):
            result = await self.validate_cli_token(cli_token)
        
        if "error" in result:
            console.print(f"[red]Token validation failed: {result['error']}[/red]")
            return False
        
        # Store the validated token
        if "access_token" in result:
            self.access_token = result["access_token"]
            self.client.headers["Authorization"] = f"Bearer {self.access_token}"
            
            # Display user info if available
            user_email = result.get("user_email", "Unknown")
            console.print(f"[green]✓[/green] Authentication successful!")
            console.print(f"[cyan]Logged in as:[/cyan] {user_email}")
            
            # Save configuration with new token
            self.save_config()
            return True
        
        console.print("[red]No access token received[/red]")
        console.print(f"[dim]Response: {json.dumps(result, indent=2)}[/dim]")
        return False
    
    async def validate_cli_token(self, cli_token: str) -> Dict[str, Any]:
        """Validate CLI token obtained from web interface"""
        try:
            payload = {"cli_token": cli_token}
            response = await self.client.post(f"{self.base_url}/api/auth/cli/validate", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def interactive_login(self, provider: str = "google") -> bool:
        """Interactive OAuth login flow - uses web interface by default"""
        return await self.interactive_login_web(provider)
    
    def requires_auth(self, message: str) -> bool:
        """Check if a message requires authentication"""
        auth_keywords = [
            "email", "gmail", "calendar", "drive", "google workspace", 
            "send email", "check email", "schedule meeting", "ga4", "analytics"
        ]
        return any(keyword in message.lower() for keyword in auth_keywords)
    
    async def ensure_authenticated(self, message: str) -> bool:
        """Ensure user is authenticated for OAuth-required operations"""
        if not self.requires_auth(message):
            return True  # No auth needed
            
        if self.access_token:
            # If we have a JWT token, check if it's still valid
            if self.access_token.startswith('eyJ'):
                try:
                    import jwt
                    decoded = jwt.decode(self.access_token, options={"verify_signature": False})
                    exp_timestamp = decoded.get('exp')
                    if exp_timestamp:
                        from datetime import datetime
                        if datetime.utcnow().timestamp() < exp_timestamp:
                            return True  # Token is still valid
                        else:
                            console.print("[yellow]⚠️  Authentication token has expired.[/yellow]")
                    else:
                        return True  # No expiry, assume valid
                except:
                    pass  # Token parsing failed, proceed with re-auth
            else:
                # Non-JWT token, assume it's valid
                return True
        
        # Prompt for authentication
        console.print("[yellow]⚠️  This operation requires authentication with Google services.[/yellow]")
        console.print("Commands that require auth: email, calendar, drive, GA4 analytics")
        
        if Confirm.ask("Would you like to authenticate now?"):
            success = await self.interactive_login("google")
            if success:
                console.print("[green]✓[/green] Authentication successful! You can now use Google services.")
                return True
            else:
                console.print("[red]❌[/red] Authentication failed. Some features may not work.")
                return False
        else:
            console.print("[yellow]Skipping authentication. Some features may not be available.[/yellow]")
            return False
    
    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message to the backend"""
        # Extract user ID from JWT token if available
        user_id = self.default_user_id  # Default fallback
        if self.access_token and self.access_token.startswith('eyJ'):
            try:
                import jwt
                decoded = jwt.decode(self.access_token, options={"verify_signature": False})
                user_id = str(decoded.get('id', decoded.get('sub', self.default_user_id)))
            except:
                pass  # Use default if JWT parsing fails
        
        payload = {
            "message": message,
            "conversation_id": self.conversation_id,
            "user_id": user_id
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/agent/message",
            json=payload
        )
        
        return response.json()
    
    async def stream_message(self, message: str):
        """Stream a message response"""
        # Extract user ID from JWT token if available
        user_id = self.default_user_id  # Default fallback
        if self.access_token and self.access_token.startswith('eyJ'):
            try:
                import jwt
                decoded = jwt.decode(self.access_token, options={"verify_signature": False})
                user_id = str(decoded.get('id', decoded.get('sub', self.default_user_id)))
            except:
                pass  # Use default if JWT parsing fails
        
        payload = {
            "message": message,
            "conversation_id": self.conversation_id,
            "user_id": user_id
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
    
    def display_memories(self, memories_data):
        """Display memories in a formatted table"""
        # Handle both dict and list responses
        if isinstance(memories_data, dict):
            if "error" in memories_data:
                console.print(f"[red]Error: {memories_data['error']}[/red]")
                return
            memories = memories_data.get("memories", [])
        else:
            # If it's already a list, use it directly
            memories = memories_data if isinstance(memories_data, list) else []
        
        if not memories:
            console.print("[yellow]No memories found[/yellow]")
            return
        
        table = Table(title="Memories", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Category", style="cyan", width=12)
        table.add_column("Content", style="white", width=50)
        table.add_column("Created", style="dim", width=12)
        
        for memory in memories:
            created = memory.get("created_at", "")[:10]  # Show just date
            content = memory.get("content", "")[:80] + "..." if len(memory.get("content", "")) > 80 else memory.get("content", "")
            table.add_row(
                str(memory.get("id", ""))[:8],
                memory.get("category", ""),
                content,
                created
            )
        
        console.print(table)
    
    def display_sales_summary(self, sales_data: Dict[str, Any]):
        """Display daily sales summary"""
        if "error" in sales_data:
            console.print(f"[red]Error: {sales_data['error']}[/red]")
            return
        
        summary = sales_data.get("summary", {})
        
        panel_content = f"""
[bold]Daily Sales Summary[/bold]
[green]Revenue:[/green] ${summary.get('total_revenue', 0):,.2f}
[cyan]Orders:[/cyan] {summary.get('order_count', 0)}
[yellow]Average Order Value:[/yellow] ${summary.get('average_order_value', 0):,.2f}
        """.strip()
        
        console.print(Panel(panel_content, title="Sales", border_style="green"))
    
    def display_products(self, products_data: Dict[str, Any]):
        """Display products in a table"""
        if "error" in products_data:
            console.print(f"[red]Error: {products_data['error']}[/red]")
            return
        
        products = products_data.get("products", [])
        if not products:
            console.print("[yellow]No products found[/yellow]")
            return
        
        table = Table(title="Products", show_header=True, header_style="bold magenta")
        table.add_column("SKU", style="cyan", width=15)
        table.add_column("Title", style="white", width=40)
        table.add_column("Price", style="green", width=10)
        table.add_column("Status", style="yellow", width=10)
        
        for product in products:
            variants = product.get("variants", [])
            price = f"${variants[0].get('price', 0)}" if variants else "N/A"
            title = product.get("title", "")[:35] + "..." if len(product.get("title", "")) > 35 else product.get("title", "")
            
            table.add_row(
                variants[0].get("sku", "") if variants else "",
                title,
                price,
                product.get("status", "").lower()
            )
        
        console.print(table)
    
    def display_system_status(self, status_data: Dict[str, Any]):
        """Display comprehensive system status"""
        if "error" in status_data:
            console.print(f"[red]Error: {status_data['error']}[/red]")
            return
        
        panel_content = f"""
[bold]System Status[/bold]
[green]Backend Health:[/green] {'✓ Healthy' if status_data.get('backend_health') else '❌ Down'}
[cyan]Agent Count:[/cyan] {status_data.get('agent_count', 0)}
[yellow]Agents:[/yellow] {', '.join(status_data.get('agents', []))}
[dim]Last Check:[/dim] {status_data.get('timestamp', 'Unknown')[:19]}
        """.strip()
        
        if "orchestrator" in status_data:
            orch = status_data["orchestrator"]
            panel_content += f"\n\n[bold]Orchestrator:[/bold] {orch.get('status', 'Unknown')}"
        
        console.print(Panel(panel_content, title="System Status", border_style="blue"))
    
    def display_agent_config(self, config_data: Dict[str, Any]):
        """Display agent configuration"""
        if "error" in config_data:
            console.print(f"[red]Error: {config_data['error']}[/red]")
            return
        
        if "agents" in config_data:  # List of agents
            table = Table(title="Agent Configuration", show_header=True, header_style="bold magenta")
            table.add_column("Agent", style="cyan", width=15)
            table.add_column("Model", style="green", width=20)
            table.add_column("Provider", style="yellow", width=15)
            table.add_column("Status", style="white", width=10)
            
            for agent in config_data["agents"]:
                table.add_row(
                    agent.get("name", ""),
                    agent.get("model", "default"),
                    agent.get("provider", "openai"),
                    agent.get("status", "active")
                )
            console.print(table)
        else:  # Single agent
            agent_name = config_data.get("name", "Unknown")
            model = config_data.get("model", "default")
            provider = config_data.get("provider", "openai")
            console.print(f"[bold]{agent_name}[/bold]: {provider}/{model}")
    
    def display_message(self, role: str, content: str, agent: Optional[str] = None):
        """Display a message with formatting"""
        if role == "user":
            console.print(Panel(content, title="[bold blue]You[/bold blue]", border_style="blue"))
        else:
            title = f"[bold green]{agent or 'Assistant'}[/bold green]"
            # Improve markdown rendering and newline handling
            try:
                # Pre-process content for better formatting
                processed_content = self._process_message_content(content)
                formatted = Markdown(processed_content, code_theme="monokai")
                console.print(Panel(formatted, title=title, border_style="green", padding=(1, 2)))
            except Exception as e:
                # Fallback: just process newlines and display as plain text
                processed_content = self._process_message_content(content)
                console.print(Panel(processed_content, title=title, border_style="green", padding=(1, 2)))
    
    def _process_message_content(self, content: str) -> str:
        """Process message content for better formatting"""
        # Handle various newline patterns
        content = content.replace('\\n', '\n')  # Convert literal \n to actual newlines
        content = content.replace('\r\n', '\n')  # Normalize Windows line endings
        
        # Improve list formatting
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Add proper spacing around headers
            if line.strip().startswith('#'):
                if processed_lines and processed_lines[-1].strip():
                    processed_lines.append('')  # Add blank line before headers
                processed_lines.append(line)
                processed_lines.append('')  # Add blank line after headers
            # Improve bullet point formatting
            elif line.strip().startswith(('- ', '* ', '+ ')):
                processed_lines.append(line)
            # Improve numbered list formatting
            elif line.strip() and line.strip().split('.')[0].isdigit():
                processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        # Remove excessive blank lines (more than 2 consecutive)
        result_lines = []
        blank_count = 0
        for line in processed_lines:
            if line.strip() == '':
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def display_help(self):
        """Display help information"""
        help_text = """
[bold]Chat Commands:[/bold]
  [cyan]/help[/cyan]         - Show this help message
  [cyan]/agents[/cyan]       - List available agents
  [cyan]/clear[/cyan]        - Clear conversation history
  [cyan]/export[/cyan]       - Export conversation to file
  [cyan]/stream[/cyan]       - Toggle streaming mode
  [cyan]/conv[/cyan]         - Show conversation ID
  [cyan]/new[/cyan]          - Start new conversation
  [cyan]/quit[/cyan]         - Exit the CLI

[bold]Memory Commands:[/bold]
  [cyan]/memory[/cyan]       - List user memories
  [cyan]/memory-search[/cyan] <query> - Search memories
  [cyan]/memory-delete[/cyan] <ids> - Delete memories by ID
  [cyan]/memory-export[/cyan] - Export memories to file

[bold]Analytics Commands:[/bold]
  [cyan]/sales[/cyan]        - Today's sales summary
  [cyan]/sales[/cyan] <date> - Sales for specific date (YYYY-MM-DD)
  [cyan]/orders[/cyan] <start> <end> - Order analytics for date range
  [cyan]/revenue[/cyan] <start> <end> - Revenue report for date range

[bold]Product Commands:[/bold]
  [cyan]/product[/cyan] <sku/id> - Get product details
  [cyan]/products[/cyan] <query> - Search products
  [cyan]/pricing[/cyan] <sku> <price> - Update product price

[bold]System Commands:[/bold]
  [cyan]/system-health[/cyan] - Check system health
  [cyan]/system-status[/cyan] - Full system status
  [cyan]/config[/cyan]       - Show configuration
  [cyan]/config save[/cyan]  - Save current configuration
  [cyan]/debug[/cyan]        - Debug information

[bold]Admin Commands:[/bold]  
  [cyan]/agents-config[/cyan] [agent] - Agent configuration
  [cyan]/orchestrator-status[/cyan] - Orchestrator status
  [cyan]/logs[/cyan]         - Recent conversation logs

[bold]Authentication Commands:[/bold]
  [cyan]/login[/cyan] [provider] - OAuth login (default: google)
  [cyan]/get-token[/cyan]    - Extract token from web interface (easier!)
  [cyan]/logout[/cyan]       - Logout and clear tokens
  [cyan]/auth-status[/cyan]  - Check authentication status
  
[bold]Examples:[/bold]
  /memory-search coffee preferences
  /sales 2025-01-15
  /orders 2025-01-01 2025-01-31  
  /product BES870XL
  /products Breville espresso
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
                # Get user input with command help
                message = self.get_user_input("[bold blue]You[/bold blue]: ")
                
                if not message:
                    continue
                
                # Handle commands
                if message.startswith("/"):
                    command_parts = message[1:].split()
                    command = command_parts[0].lower()
                    args = command_parts[1:] if len(command_parts) > 1 else []
                    
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
                    
                    # Memory commands
                    elif command == "memory":
                        with console.status("[cyan]Loading memories...", spinner="dots"):
                            memories = await self.get_memories()
                        self.display_memories(memories)
                    elif command == "memory-search":
                        if not args:
                            console.print("[red]Usage: /memory-search <query>[/red]")
                            continue
                        query = " ".join(args)
                        with console.status(f"[cyan]Searching memories for: {query}...", spinner="dots"):
                            results = await self.search_memories("1", query)
                        self.display_memories(results)
                    elif command == "memory-delete":
                        if not args:
                            console.print("[red]Usage: /memory-delete <id1> [id2] ...[/red]")
                            continue
                        with console.status("[cyan]Deleting memories...", spinner="dots"):
                            result = await self.delete_memories("1", args)
                        if "error" in result:
                            console.print(f"[red]Error: {result['error']}[/red]")
                        else:
                            console.print(f"[green]✓[/green] Deleted {len(args)} memories")
                    elif command == "memory-export":
                        with console.status("[cyan]Exporting memories...", spinner="dots"):
                            memories = await self.get_memories("1", limit=1000)
                        if "error" not in memories:
                            filename = f"memories-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
                            with open(filename, "w") as f:
                                json.dump(memories, f, indent=2)
                            console.print(f"[green]✓[/green] Memories exported to {filename}")
                        else:
                            console.print(f"[red]Error: {memories['error']}[/red]")
                    
                    # Analytics commands
                    elif command == "sales":
                        date = args[0] if args else "today"
                        with console.status(f"[cyan]Loading sales for {date}...", spinner="dots"):
                            sales = await self.get_daily_sales(date)
                        self.display_sales_summary(sales)
                    elif command == "orders":
                        if len(args) < 2:
                            console.print("[red]Usage: /orders <start_date> <end_date>[/red]")
                            continue
                        with console.status(f"[cyan]Loading orders from {args[0]} to {args[1]}...", spinner="dots"):
                            orders = await self.get_order_analytics(args[0], args[1])
                        if "error" in orders:
                            console.print(f"[red]Error: {orders['error']}[/red]")
                        else:
                            console.print(f"[green]Orders:[/green] {orders.get('order_count', 0)}")
                            console.print(f"[green]Revenue:[/green] ${orders.get('total_revenue', 0):,.2f}")
                    
                    # Product commands
                    elif command == "product":
                        if not args:
                            console.print("[red]Usage: /product <sku/id>[/red]")
                            continue
                        with console.status(f"[cyan]Loading product {args[0]}...", spinner="dots"):
                            product = await self.get_product(args[0])
                        if "error" in product:
                            console.print(f"[red]Error: {product['error']}[/red]")
                        else:
                            title = product.get("title", "Unknown")
                            status = product.get("status", "unknown").lower()
                            console.print(f"[bold]{title}[/bold] ([{status}])")
                    elif command == "products":
                        if not args:
                            console.print("[red]Usage: /products <search query>[/red]")
                            continue
                        query = " ".join(args)
                        with console.status(f"[cyan]Searching products: {query}...", spinner="dots"):
                            products = await self.search_products(query)
                        self.display_products(products)
                    
                    # System commands
                    elif command == "system-health":
                        with console.status("[cyan]Checking system health...", spinner="dots"):
                            healthy = await self.check_health()
                        if healthy:
                            console.print("[green]✓[/green] System is healthy")
                        else:
                            console.print("[red]❌[/red] System is not responding")
                    elif command == "system-status":
                        with console.status("[cyan]Getting system status...", spinner="dots"):
                            status = await self.get_system_status()
                        self.display_system_status(status)
                    elif command == "config":
                        if args and args[0] == "save":
                            self.save_config()
                        else:
                            console.print(f"[cyan]Base URL:[/cyan] {self.base_url}")
                            console.print(f"[cyan]User ID:[/cyan] {self.default_user_id}")
                            console.print(f"[cyan]Timeout:[/cyan] {self.timeout}s")
                            console.print(f"[cyan]Max Retries:[/cyan] {self.max_retries}")
                            console.print(f"[cyan]Conversation ID:[/cyan] {self.conversation_id}")
                            console.print(f"[cyan]Streaming:[/cyan] {'enabled' if streaming else 'disabled'}")
                            console.print("[dim]Use '/config save' to save current settings[/dim]")
                    
                    # Admin commands
                    elif command == "agents-config":
                        agent_name = args[0] if args else None
                        with console.status("[cyan]Getting agent configuration...", spinner="dots"):
                            config = await self.get_agent_config(agent_name)
                        self.display_agent_config(config)
                    elif command == "orchestrator-status":
                        with console.status("[cyan]Getting orchestrator status...", spinner="dots"):
                            status = await self.get_orchestrator_status()
                        if "error" in status:
                            console.print(f"[red]Error: {status['error']}[/red]")
                        else:
                            console.print(f"[green]Orchestrator Status:[/green] {status.get('status', 'Unknown')}")
                            if "version" in status:
                                console.print(f"[cyan]Version:[/cyan] {status['version']}")
                    elif command == "logs":
                        with console.status("[cyan]Getting conversation logs...", spinner="dots"):
                            logs = await self.get_conversation_logs()
                        if "error" in logs:
                            console.print(f"[red]Error: {logs['error']}[/red]")
                        else:
                            console.print("[bold]Recent Conversation Logs:[/bold]")
                            for log in logs.get("logs", [])[:10]:  # Show last 10
                                timestamp = log.get("timestamp", "")[:19]
                                message = log.get("message", "")[:100]
                                console.print(f"[dim]{timestamp}[/dim] {message}")
                    
                    # Authentication commands
                    elif command == "login":
                        provider = args[0] if args else "google"
                        success = await self.interactive_login(provider)
                        if not success:
                            console.print("[red]Login failed[/red]")
                    elif command == "get-token":
                        console.print("[cyan]Getting JWT token from web interface...[/cyan]")
                        console.print("[dim]This will open your browser to extract the token[/dim]")
                        
                        # Create a simple HTML page that extracts the token
                        html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>CLI Token Extractor</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .token { background: #f0f0f0; padding: 10px; word-break: break-all; border-radius: 4px; margin: 10px 0; }
        .copy-btn { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔑 CLI Authentication Token</h2>
        <p>Your CLI authentication token:</p>
        <div id="token" class="token">Loading...</div>
        <button class="copy-btn" onclick="copyToken()">Copy Token</button>
        <p id="status"></p>
        
        <h3>Instructions:</h3>
        <ol>
            <li>Copy the token above</li>
            <li>Return to your CLI terminal</li>
            <li>Paste the token when prompted</li>
            <li>Close this window</li>
        </ol>
    </div>
    
    <script>
        function getToken() {
            const token = localStorage.getItem('authToken');
            const tokenDiv = document.getElementById('token');
            
            if (token) {
                tokenDiv.textContent = token;
                document.getElementById('status').innerHTML = '<span class="success">✓ Token found!</span>';
            } else {
                tokenDiv.textContent = 'No token found. Please log in to the web interface first.';
                document.getElementById('status').innerHTML = '<span class="error">❌ Please log in to the web interface</span>';
            }
        }
        
        function copyToken() {
            const token = document.getElementById('token').textContent;
            navigator.clipboard.writeText(token).then(() => {
                document.getElementById('status').innerHTML = '<span class="success">✓ Token copied to clipboard!</span>';
            });
        }
        
        // Get token when page loads
        window.onload = getToken;
    </script>
</body>
</html>
                        '''
                        
                        # Write HTML to temporary file
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                            f.write(html_content)
                            temp_file = f.name
                        
                        # Open in browser
                        import webbrowser
                        file_url = f"file://{temp_file}"
                        webbrowser.open(file_url)
                        
                        console.print(f"[green]✓[/green] Opened token extractor in browser")
                        console.print("[yellow]Copy the token from the browser and paste it below:[/yellow]")
                        
                        # Get token from user
                        token = Prompt.ask("[cyan]Paste your JWT token here")
                        
                        if token and token.startswith('eyJ'):
                            # Validate and store token
                            with console.status("[cyan]Validating token...", spinner="dots"):
                                result = await self.validate_cli_token(token)
                            
                            if "access_token" in result:
                                self.access_token = result["access_token"]
                                self.client.headers["Authorization"] = f"Bearer {self.access_token}"
                                self.save_config()
                                
                                user_email = result.get("user_email", "Unknown")
                                console.print(f"[green]✓[/green] Authentication successful!")
                                console.print(f"[cyan]Logged in as:[/cyan] {user_email}")
                            else:
                                console.print(f"[red]Token validation failed: {result.get('error', 'Unknown error')}[/red]")
                        else:
                            console.print("[red]Invalid token format[/red]")
                        
                        # Clean up temp file
                        import os
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                    elif command == "logout":
                        await self.logout()
                    elif command == "auth-status":
                        with console.status("[cyan]Checking authentication...", spinner="dots"):
                            status = await self.check_auth_status()
                        if "error" in status:
                            console.print(f"[red]Error: {status['error']}[/red]")
                        else:
                            is_auth = status.get("authenticated", False)
                            user_email = status.get("user_email", "Unknown")
                            console.print(f"[green]Authenticated:[/green] {'✓' if is_auth else '❌'}")
                            if is_auth:
                                console.print(f"[cyan]Email:[/cyan] {user_email}")
                    
                    # Debug commands
                    elif command == "debug":
                        console.print("[bold]Debug Information:[/bold]")
                        console.print(f"[cyan]Python Version:[/cyan] {sys.version}")
                        console.print(f"[cyan]CLI Version:[/cyan] 2.0.0-enhanced")
                        console.print(f"[cyan]Base URL:[/cyan] {self.base_url}")
                        console.print(f"[cyan]HTTP Client:[/cyan] {type(self.client).__name__}")
                        console.print(f"[cyan]Conversation History:[/cyan] {len(self.conversation_history)} messages")
                        console.print(f"[cyan]Authenticated:[/cyan] {'✓' if self.access_token else '❌'}")
                    
                    else:
                        console.print(f"[red]Unknown command: /{command}[/red]")
                        console.print("Type [cyan]/help[/cyan] to see available commands")
                    continue
                
                # Add to history
                self.conversation_history.append({"role": "user", "content": message})
                
                # Check if authentication is required
                auth_required = await self.ensure_authenticated(message)
                if not auth_required and self.requires_auth(message):
                    console.print("[yellow]Proceeding without authentication - some features may not work[/yellow]")
                
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
                        
                        # Handle orchestrator response format
                        if "error" in result:
                            console.print(f"[red]Error: {result['error']}[/red]")
                        elif "response" in result:
                            # Direct orchestrator response format
                            agent = result.get("agent", "orchestrator")
                            response_content = result["response"]
                            self.display_message("assistant", response_content, agent)
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": response_content,
                                "agent": agent
                            })
                        elif "messages" in result:
                            # Message array format
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
                            console.print(f"[red]Unexpected response format: {result}[/red]")
                
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
        
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
        elif "response" in result:
            # Handle direct response format
            agent = result.get("agent", "bot")
            self.display_message("assistant", result["response"], agent)
        elif "success" in result and result["success"]:
            # Get only the last assistant message (the new response)
            assistant_messages = [msg for msg in result["messages"] if msg["role"] == "assistant"]
            if assistant_messages:
                msg = assistant_messages[-1]
                agent = msg.get("metadata", {}).get("agent", "bot")
                self.display_message("assistant", msg["content"], agent)
        elif "messages" in result:
            # Handle message array response
            messages = result["messages"]
            if messages:
                last_msg = messages[-1]
                if last_msg.get("role") == "assistant":
                    agent = last_msg.get("metadata", {}).get("agent", "bot")
                    self.display_message("assistant", last_msg["content"], agent)
        else:
            console.print(f"[red]Unexpected response format: {result}[/red]")
    
    async def close(self):
        """Clean up"""
        await self.client.aclose()

@click.command()
@click.option('--url', default='http://localhost:8000', help='Backend URL')
@click.option('--message', '-m', help='Send a single message and exit')
@click.option('--agents', '-a', is_flag=True, help='List available agents and exit')
@click.option('--health', '-h', is_flag=True, help='Check backend health and exit')
@click.option('--memory', is_flag=True, help='List user memories and exit')
@click.option('--memory-search', help='Search memories and exit')
@click.option('--sales', help='Get sales summary (today/YYYY-MM-DD) and exit')
@click.option('--product', help='Get product details by SKU/ID and exit')
@click.option('--products', help='Search products and exit')
@click.option('--system-status', is_flag=True, help='Show system status and exit')
@click.option('--user-id', default='1', help='User ID for memory operations (default: 1)')
@click.option('--config', help='Configuration file path')
@click.option('--save-config', is_flag=True, help='Save configuration and exit')
@click.option('--login', help='OAuth login with provider (google, microsoft)')
@click.option('--logout', is_flag=True, help='Logout and clear stored tokens')
@click.option('--auth-status', is_flag=True, help='Check authentication status')
def main(url: str, message: Optional[str], agents: bool, health: bool, 
         memory: bool, memory_search: Optional[str], sales: Optional[str], 
         product: Optional[str], products: Optional[str], system_status: bool, 
         user_id: str, config: Optional[str], save_config: bool,
         login: Optional[str], logout: bool, auth_status: bool):
    """EspressoBot LangGraph Backend - Interactive CLI"""
    
    async def run():
        cli = EspressoBotCLI(url, config_file=config)
        
        try:
            # Handle save config first
            if save_config:
                cli.save_config(config)
                return
            
            # Handle authentication commands first
            if login:
                success = await cli.interactive_login(login)
                if not success:
                    console.print("[red]Login failed[/red]")
                return
            
            if logout:
                await cli.logout()
                return
            
            if auth_status:
                status = await cli.check_auth_status()
                if "error" in status:
                    console.print(f"[red]Error: {status['error']}[/red]")
                else:
                    is_auth = status.get("authenticated", False)
                    user_email = status.get("user_email", "Unknown")
                    console.print(f"[green]Authenticated:[/green] {'✓' if is_auth else '❌'}")
                    if is_auth:
                        console.print(f"[cyan]Email:[/cyan] {user_email}")
                return
            
            # Check backend health for all operations
            if not any([health, agents, message, memory, memory_search, sales, product, products, system_status]):
                # Interactive mode - health check in run_interactive
                await cli.run_interactive()
                return
            
            # For non-interactive operations, check health first
            if not await cli.check_health():
                console.print("[red]❌ Backend is not running![/red]")
                console.print("Start the backend with: [cyan]uvicorn app.main:app --reload[/cyan]")
                return
            
            # Handle non-interactive commands
            if health:
                console.print("[green]✓[/green] Backend is healthy")
            
            elif agents:
                agents_list = await cli.get_agents()
                cli.display_agents(agents_list)
            
            elif memory:
                memories = await cli.get_memories(user_id)
                cli.display_memories(memories)
                
            elif memory_search:
                results = await cli.search_memories(user_id, memory_search)
                cli.display_memories(results)
                
            elif sales:
                sales_data = await cli.get_daily_sales(sales)
                cli.display_sales_summary(sales_data)
                
            elif product:
                product_data = await cli.get_product(product)
                if "error" in product_data:
                    console.print(f"[red]Error: {product_data['error']}[/red]")
                else:
                    title = product_data.get("title", "Unknown")
                    status = product_data.get("status", "unknown").lower()
                    vendor = product_data.get("vendor", "")
                    console.print(f"[bold]{title}[/bold]")
                    console.print(f"[cyan]Vendor:[/cyan] {vendor}")
                    console.print(f"[yellow]Status:[/yellow] {status}")
                    
                    variants = product_data.get("variants", [])
                    if variants:
                        console.print(f"[green]Price:[/green] ${variants[0].get('price', 0)}")
                        console.print(f"[cyan]SKU:[/cyan] {variants[0].get('sku', 'N/A')}")
                        
            elif products:
                products_data = await cli.search_products(products)
                cli.display_products(products_data)
                
            elif system_status:
                status = await cli.get_system_status()
                cli.display_system_status(status)
            
            elif message:
                await cli.run_single_command(message)
        
        finally:
            await cli.close()
    
    asyncio.run(run())

if __name__ == "__main__":
    main()