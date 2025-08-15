#!/usr/bin/env python3
"""
Simplified trace analyzer for LangSmith traces
Focuses on finding where the tokens are being consumed
"""
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()

def format_tokens(count: int) -> str:
    """Format token count with color"""
    if count > 50000:
        return f"[red bold]{count:,}[/red bold]"
    elif count > 20000:
        return f"[yellow]{count:,}[/yellow]"
    else:
        return f"[green]{count:,}[/green]"

def format_time(seconds: float) -> str:
    """Format time duration"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        return f"{seconds/60:.1f}m"

def analyze_run_tokens(run_data, depth=0, parent_path=""):
    """Recursively analyze token usage in a run"""
    indent = "  " * depth
    name = run_data.get('name', 'Unknown')
    run_type = run_data.get('run_type', '')
    path = f"{parent_path}/{name}" if parent_path else name
    
    # Get token counts
    total_tokens = run_data.get('total_tokens', 0)
    prompt_tokens = run_data.get('prompt_tokens', 0)
    completion_tokens = run_data.get('completion_tokens', 0)
    
    # Print if this run has tokens
    if total_tokens > 0:
        console.print(f"{indent}[cyan]{name}[/cyan] ({run_type})")
        console.print(f"{indent}  Total: {format_tokens(total_tokens)}")
        console.print(f"{indent}  Prompt: {format_tokens(prompt_tokens)}")
        console.print(f"{indent}  Completion: {format_tokens(completion_tokens)}")
        
        # Check for input/output to understand what's consuming tokens
        inputs = run_data.get('inputs', {})
        outputs = run_data.get('outputs', {})
        
        if inputs:
            # Show a sample of the input
            input_str = str(inputs)
            if len(input_str) > 200:
                console.print(f"{indent}  Input preview: {input_str[:200]}...")
            console.print(f"{indent}  Input size: ~{len(str(inputs))} chars")
            
        if outputs:
            output_str = str(outputs)
            if len(output_str) > 200:
                console.print(f"{indent}  Output preview: {output_str[:200]}...")
            console.print(f"{indent}  Output size: ~{len(str(outputs))} chars")
        
        console.print()
    
    # Process child runs
    child_runs = run_data.get('child_runs')
    if child_runs:
        for child in child_runs:
            analyze_run_tokens(child, depth + 1, path)

def fetch_recent_traces(limit=10, hours=24):
    """Fetch recent traces"""
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        return []
    
    client = Client(api_key=api_key)
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    traces = []
    for run in client.list_runs(
        project_name="espressobot",
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        is_root=True
    ):
        traces.append(run.dict())
    
    return traces

def main():
    parser = argparse.ArgumentParser(description='Analyze LangSmith trace tokens')
    parser.add_argument('--trace-id', help='Specific trace ID to analyze')
    parser.add_argument('--limit', type=int, default=5, help='Number of recent traces to show')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
    
    args = parser.parse_args()
    
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        sys.exit(1)
    
    client = Client(api_key=api_key)
    
    if args.trace_id:
        # Analyze specific trace
        console.print(f"[cyan]Fetching trace {args.trace_id}...[/cyan]\n")
        try:
            run = client.read_run(args.trace_id)
            run_data = run.dict()
            
            # Show summary
            console.print(f"[bold]Trace: {run_data.get('name')}[/bold]")
            console.print(f"Total Tokens: {format_tokens(run_data.get('total_tokens', 0))}")
            console.print(f"Prompt Tokens: {format_tokens(run_data.get('prompt_tokens', 0))}")
            console.print(f"Completion Tokens: {format_tokens(run_data.get('completion_tokens', 0))}")
            
            # Calculate duration
            start_time = run_data.get('start_time')
            end_time = run_data.get('end_time')
            if start_time and end_time:
                if isinstance(start_time, datetime):
                    duration = (end_time - start_time).total_seconds()
                else:
                    duration = 0
                console.print(f"Duration: {format_time(duration)}")
            
            console.print("\n[bold]Token Breakdown by Component:[/bold]\n")
            
            # Analyze token usage
            analyze_run_tokens(run_data)
            
            # Check for large inputs
            inputs = run_data.get('inputs', {})
            if inputs:
                input_size = len(str(inputs))
                if input_size > 10000:
                    console.print(f"\n[yellow]⚠️  Large input detected: {input_size:,} characters[/yellow]")
                    
                    # Try to identify what's in the input
                    if 'messages' in inputs:
                        messages = inputs['messages']
                        console.print(f"   Contains {len(messages)} messages")
                        
                        # Check for large messages
                        for i, msg in enumerate(messages[:5]):  # First 5 messages
                            if isinstance(msg, dict):
                                content = msg.get('content', '')
                                if len(content) > 1000:
                                    console.print(f"   Message {i}: {len(content):,} chars")
                    
                    if 'context' in inputs:
                        context_size = len(str(inputs['context']))
                        console.print(f"   Context field: {context_size:,} chars")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
    
    else:
        # Show recent traces
        console.print(f"[cyan]Fetching traces from last {args.hours} hours...[/cyan]\n")
        traces = fetch_recent_traces(args.limit, args.hours)
        
        if not traces:
            console.print("[yellow]No traces found[/yellow]")
            return
        
        # Create summary table
        table = Table(title="Recent Traces", show_header=True)
        table.add_column("Time", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Tokens", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("ID", style="dim")
        
        for trace in traces:
            start_time = trace.get('start_time')
            if isinstance(start_time, datetime):
                time_str = start_time.strftime('%H:%M:%S')
            else:
                time_str = "Unknown"
            
            name = trace.get('name', 'Unknown')[:30]
            total_tokens = trace.get('total_tokens', 0)
            tokens_str = format_tokens(total_tokens) if total_tokens else "-"
            
            # Duration
            end_time = trace.get('end_time')
            if start_time and end_time:
                if isinstance(start_time, datetime):
                    duration = (end_time - start_time).total_seconds()
                    duration_str = format_time(duration)
                else:
                    duration_str = "-"
            else:
                duration_str = "-"
            
            trace_id = str(trace.get('id', ''))[:20] + "..."
            
            table.add_row(time_str, name, tokens_str, duration_str, trace_id)
        
        console.print(table)
        console.print(f"\n[dim]To analyze a specific trace, use: --trace-id <id>[/dim]")

if __name__ == "__main__":
    main()