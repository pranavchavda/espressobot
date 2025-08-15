#!/usr/bin/env python3
"""
Fetch and analyze LangSmith traces programmatically
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

def format_tokens(count: int) -> str:
    """Format token count with color coding"""
    if count > 50000:
        return f"[red bold]{count:,}[/red bold]"
    elif count > 20000:
        return f"[yellow]{count:,}[/yellow]"
    else:
        return f"[green]{count:,}[/green]"

def format_latency(seconds: float) -> str:
    """Format latency with appropriate units"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = seconds / 60
        return f"{minutes:.1f}m"

def format_cost(cost: float) -> str:
    """Format cost with color coding"""
    if cost > 1.0:
        return f"[red bold]${cost:.4f}[/red bold]"
    elif cost > 0.1:
        return f"[yellow]${cost:.4f}[/yellow]"
    else:
        return f"[green]${cost:.4f}[/green]"

def build_trace_tree(run: Dict[str, Any], tree: Tree = None, level: int = 0) -> Tree:
    """Build a rich tree visualization of the trace"""
    if tree is None:
        # Root node
        name = run.get('name', 'Unknown')
        run_type = run.get('run_type', '')
        
        # Get token counts
        token_usage = run.get('token_usage', {})
        total_tokens = token_usage.get('total_tokens', 0)
        
        # Get latency
        start_time = run.get('start_time')
        end_time = run.get('end_time')
        latency = 0
        if start_time and end_time:
            # Handle both datetime objects and strings
            if isinstance(start_time, datetime):
                start_dt = start_time
            elif isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = None
                
            if isinstance(end_time, datetime):
                end_dt = end_time
            elif isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end_dt = None
                
            if start_dt and end_dt:
                latency = (end_dt - start_dt).total_seconds()
        
        root_text = f"[bold cyan]{name}[/bold cyan] ({run_type})"
        if total_tokens:
            root_text += f" - {format_tokens(total_tokens)} tokens"
        if latency:
            root_text += f" - {format_latency(latency)}"
        
        tree = Tree(root_text)
    
    # Process child runs
    child_runs = run.get('child_runs', [])
    for child in child_runs:
        name = child.get('name', 'Unknown')
        run_type = child.get('run_type', '')
        
        # Get token counts for this child
        token_usage = child.get('token_usage', {})
        total_tokens = token_usage.get('total_tokens', 0)
        
        # Get latency for this child
        start_time = child.get('start_time')
        end_time = child.get('end_time')
        latency = 0
        if start_time and end_time:
            # Handle both datetime objects and strings
            if isinstance(start_time, datetime):
                start_dt = start_time
            elif isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = None
                
            if isinstance(end_time, datetime):
                end_dt = end_time
            elif isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end_dt = None
                
            if start_dt and end_dt:
                latency = (end_dt - start_dt).total_seconds()
        
        # Color code by type
        if run_type == 'llm':
            icon = "🤖"
            color = "yellow"
        elif run_type == 'tool':
            icon = "🔧"
            color = "blue"
        elif run_type == 'chain':
            icon = "⛓️"
            color = "magenta"
        else:
            icon = "📦"
            color = "white"
        
        child_text = f"{icon} [{color}]{name}[/{color}]"
        if total_tokens:
            child_text += f" - {format_tokens(total_tokens)} tokens"
        if latency:
            child_text += f" - {format_latency(latency)}"
        
        # Add status
        status = child.get('status', '')
        if status == 'error':
            child_text += " [red]❌ ERROR[/red]"
        
        branch = tree.add(child_text)
        
        # Recursively add children
        if child.get('child_runs'):
            build_trace_tree(child, branch, level + 1)
    
    return tree

def analyze_trace(run: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a trace for token usage, costs, and performance"""
    analysis = {
        'total_tokens': 0,
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_latency': 0,
        'llm_calls': 0,
        'tool_calls': 0,
        'errors': [],
        'token_breakdown': {},
        'latency_breakdown': {},
        'estimated_cost': 0
    }
    
    def process_run(r: Dict[str, Any], path: str = ""):
        """Recursively process runs"""
        name = r.get('name', 'Unknown')
        current_path = f"{path}/{name}" if path else name
        
        # Token usage
        token_usage = r.get('token_usage', {})
        if token_usage:
            total = token_usage.get('total_tokens', 0)
            prompt = token_usage.get('prompt_tokens', 0)
            completion = token_usage.get('completion_tokens', 0)
            
            analysis['total_tokens'] += total
            analysis['prompt_tokens'] += prompt
            analysis['completion_tokens'] += completion
            
            if total > 0:
                analysis['token_breakdown'][current_path] = {
                    'total': total,
                    'prompt': prompt,
                    'completion': completion
                }
        
        # Latency
        start_time = r.get('start_time')
        end_time = r.get('end_time')
        if start_time and end_time:
            # Handle both datetime objects and strings
            if isinstance(start_time, datetime):
                start_dt = start_time
            elif isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = None
                
            if isinstance(end_time, datetime):
                end_dt = end_time
            elif isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end_dt = None
                
            if start_dt and end_dt:
                latency = (end_dt - start_dt).total_seconds()
                analysis['latency_breakdown'][current_path] = latency
        
        # Count calls
        run_type = r.get('run_type', '')
        if run_type == 'llm':
            analysis['llm_calls'] += 1
            
            # Estimate costs (rough estimates)
            model = r.get('extra', {}).get('invocation_params', {}).get('model', '')
            if 'gpt-4' in model:
                # GPT-4: ~$0.03/1k prompt, $0.06/1k completion
                cost = (prompt * 0.03 + completion * 0.06) / 1000
            elif 'gpt-3.5' in model:
                # GPT-3.5: ~$0.0015/1k prompt, $0.002/1k completion
                cost = (prompt * 0.0015 + completion * 0.002) / 1000
            else:
                # Default estimate
                cost = total * 0.002 / 1000
            analysis['estimated_cost'] += cost
            
        elif run_type == 'tool':
            analysis['tool_calls'] += 1
        
        # Errors
        if r.get('status') == 'error':
            error_info = {
                'name': name,
                'error': r.get('error', 'Unknown error'),
                'path': current_path
            }
            analysis['errors'].append(error_info)
        
        # Process children
        for child in r.get('child_runs', []):
            process_run(child, current_path)
    
    # Calculate total latency from root
    start_time = run.get('start_time')
    end_time = run.get('end_time')
    if start_time and end_time:
        # Handle both datetime objects and strings
        if isinstance(start_time, datetime):
            start_dt = start_time
        elif isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = None
            
        if isinstance(end_time, datetime):
            end_dt = end_time
        elif isinstance(end_time, str):
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_dt = None
            
        if start_dt and end_dt:
            analysis['total_latency'] = (end_dt - start_dt).total_seconds()
    
    process_run(run)
    return analysis

def fetch_recent_traces(client: Client, 
                       project_name: str = "espressobot",
                       limit: int = 10,
                       hours_back: int = 24) -> List[Dict[str, Any]]:
    """Fetch recent traces from LangSmith"""
    # Calculate time range
    from datetime import timezone
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)
    
    console.print(f"[cyan]Fetching traces from last {hours_back} hours...[/cyan]")
    
    runs = []
    for run in client.list_runs(
        project_name=project_name,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        is_root=True  # Only get root runs
    ):
        # Convert Run object to dict
        run_dict = run.dict() if hasattr(run, 'dict') else vars(run)
        runs.append(run_dict)
    
    return runs

def display_trace_summary(runs: List[Dict[str, Any]]):
    """Display a summary table of traces"""
    table = Table(title="Recent Traces", show_header=True, header_style="bold magenta")
    table.add_column("Time", style="cyan", width=20)
    table.add_column("Name", style="white", width=30)
    table.add_column("Tokens", justify="right", width=12)
    table.add_column("Latency", justify="right", width=10)
    table.add_column("Cost", justify="right", width=10)
    table.add_column("Status", justify="center", width=10)
    table.add_column("ID", style="dim", width=20)
    
    for run in runs:
        # Format time
        start_time = run.get('start_time')
        if start_time:
            # Handle both datetime objects and strings
            if isinstance(start_time, datetime):
                dt = start_time
            elif isinstance(start_time, str):
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                dt = None
            
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S') if dt else "Unknown"
        else:
            time_str = "Unknown"
        
        # Get token count (can be direct or nested)
        total_tokens = run.get('total_tokens', 0)
        if not total_tokens:
            token_usage = run.get('token_usage', {})
            total_tokens = token_usage.get('total_tokens', 0)
        tokens_str = format_tokens(total_tokens) if total_tokens else "-"
        
        # Get latency
        end_time = run.get('end_time')
        if start_time and end_time:
            # Handle both datetime objects and strings
            if isinstance(end_time, datetime):
                end_dt = end_time
                start_dt = start_time if isinstance(start_time, datetime) else datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            elif isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                start_dt = dt if dt else datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                end_dt = None
                start_dt = None
            
            if end_dt and start_dt:
                latency = (end_dt - start_dt).total_seconds()
                latency_str = format_latency(latency)
            else:
                latency_str = "-"
        else:
            latency_str = "-"
        
        # Estimate cost
        prompt_tokens = run.get('prompt_tokens', 0)
        completion_tokens = run.get('completion_tokens', 0)
        if not prompt_tokens:
            token_usage = run.get('token_usage', {})
            prompt_tokens = token_usage.get('prompt_tokens', 0)
            completion_tokens = token_usage.get('completion_tokens', 0)
        
        # Rough estimate - adjust based on your models
        cost = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000
        cost_str = format_cost(cost) if cost > 0 else "-"
        
        # Status
        status = run.get('status', 'unknown')
        if status == 'success':
            status_str = "[green]✓[/green]"
        elif status == 'error':
            status_str = "[red]✗[/red]"
        else:
            status_str = "[yellow]?[/yellow]"
        
        # Name
        name = run.get('name', 'Unknown')[:30]
        
        # ID (shortened)
        run_id = str(run.get('id', ''))[:20]
        
        table.add_row(time_str, name, tokens_str, latency_str, cost_str, status_str, run_id)
    
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description='Fetch and analyze LangSmith traces')
    parser.add_argument('--project', default='espressobot', help='Project name')
    parser.add_argument('--limit', type=int, default=10, help='Number of traces to fetch')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
    parser.add_argument('--trace-id', help='Specific trace ID to analyze')
    parser.add_argument('--detailed', action='store_true', help='Show detailed analysis')
    parser.add_argument('--tree', action='store_true', help='Show trace tree')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    # Initialize client
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY environment variable not set[/red]")
        sys.exit(1)
    
    client = Client(api_key=api_key)
    
    if args.trace_id:
        # Fetch specific trace
        console.print(f"[cyan]Fetching trace {args.trace_id}...[/cyan]")
        try:
            run = client.read_run(args.trace_id)
            # Convert Run object to dict
            run_dict = run.dict() if hasattr(run, 'dict') else vars(run)
            runs = [run_dict]
        except Exception as e:
            console.print(f"[red]Error fetching trace: {e}[/red]")
            sys.exit(1)
    else:
        # Fetch recent traces
        runs = fetch_recent_traces(client, args.project, args.limit, args.hours)
    
    if not runs:
        console.print("[yellow]No traces found[/yellow]")
        return
    
    # Display summary unless analyzing specific trace
    if not args.trace_id:
        display_trace_summary(runs)
        console.print(f"\n[cyan]Found {len(runs)} traces[/cyan]")
    
    # Detailed analysis
    if args.detailed or args.trace_id:
        for run in runs[:1] if not args.trace_id else runs:  # Only analyze first or specific
            console.print("\n" + "="*80)
            console.print(f"[bold]Analyzing Trace: {run.get('name', 'Unknown')}[/bold]")
            console.print(f"ID: {run.get('id', 'Unknown')}")
            console.print("="*80)
            
            # Analyze the trace
            analysis = analyze_trace(run)
            
            # Display analysis
            if args.json:
                print(json.dumps(analysis, indent=2, default=str))
            else:
                # Token usage panel
                token_panel = Panel(
                    f"""[bold]Token Usage[/bold]
Total: {format_tokens(analysis['total_tokens'])}
Prompt: {format_tokens(analysis['prompt_tokens'])}
Completion: {format_tokens(analysis['completion_tokens'])}
Estimated Cost: {format_cost(analysis['estimated_cost'])}""",
                    expand=False
                )
                console.print(token_panel)
                
                # Performance panel
                perf_panel = Panel(
                    f"""[bold]Performance[/bold]
Total Latency: {format_latency(analysis['total_latency'])}
LLM Calls: {analysis['llm_calls']}
Tool Calls: {analysis['tool_calls']}
Errors: {len(analysis['errors'])}""",
                    expand=False
                )
                console.print(perf_panel)
                
                # Top token users
                if analysis['token_breakdown']:
                    console.print("\n[bold]Top Token Users:[/bold]")
                    sorted_tokens = sorted(
                        analysis['token_breakdown'].items(), 
                        key=lambda x: x[1]['total'], 
                        reverse=True
                    )[:5]
                    for path, tokens in sorted_tokens:
                        console.print(f"  {path}: {format_tokens(tokens['total'])}")
                
                # Errors
                if analysis['errors']:
                    console.print("\n[bold red]Errors:[/bold red]")
                    for error in analysis['errors']:
                        console.print(f"  - {error['path']}: {error['error']}")
            
            # Show trace tree
            if args.tree:
                console.print("\n[bold]Trace Tree:[/bold]")
                tree = build_trace_tree(run)
                console.print(tree)

if __name__ == "__main__":
    main()