#!/usr/bin/env python3
"""
Check which models are consuming tokens in a trace
"""
import os
import sys
from langsmith import Client
from rich.console import Console
from rich.table import Table

console = Console()

def format_tokens(count: int) -> str:
    """Format token count with color"""
    if count > 50000:
        return f"[red bold]{count:,}[/red bold]"
    elif count > 20000:
        return f"[yellow]{count:,}[/yellow]"
    else:
        return f"[green]{count:,}[/green]"

def format_cost(cost: float) -> str:
    """Format cost with color"""
    if cost > 1.0:
        return f"[red bold]${cost:.4f}[/red bold]"
    elif cost > 0.1:
        return f"[yellow]${cost:.4f}[/yellow]"
    else:
        return f"[green]${cost:.4f}[/green]"

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost based on model"""
    # Pricing as of Aug 2025 (adjust as needed)
    pricing = {
        # GPT-5 models (hypothetical pricing - adjust based on actual)
        'gpt-5': (0.15, 0.30),  # $0.15/1k prompt, $0.30/1k completion
        'gpt-5-mini': (0.06, 0.12),
        'gpt-5-nano': (0.03, 0.06),
        
        # GPT-4 models
        'gpt-4o': (0.005, 0.015),  # $5/1M prompt, $15/1M completion
        'gpt-4o-mini': (0.00015, 0.0006),  # $0.15/1M prompt, $0.60/1M completion
        'gpt-4-turbo': (0.01, 0.03),
        'gpt-4': (0.03, 0.06),
        
        # GPT-3.5
        'gpt-3.5-turbo': (0.0005, 0.0015),
        
        # Claude models
        'claude-3-opus': (0.015, 0.075),
        'claude-3-sonnet': (0.003, 0.015),
        'claude-3-haiku': (0.00025, 0.00125),
    }
    
    # Find matching pricing
    model_lower = model.lower()
    for key, (prompt_price, completion_price) in pricing.items():
        if key in model_lower:
            return (prompt_tokens * prompt_price + completion_tokens * completion_price) / 1000
    
    # Default pricing if model not found
    return (prompt_tokens * 0.002 + completion_tokens * 0.002) / 1000

def analyze_model_usage(run_data, models_summary=None):
    """Recursively analyze model usage in a run"""
    if models_summary is None:
        models_summary = {}
    
    # Check if this is an LLM run
    run_type = run_data.get('run_type', '')
    if run_type == 'llm':
        # Get model info
        extra = run_data.get('extra', {})
        invocation_params = extra.get('invocation_params', {})
        model = invocation_params.get('model', 'unknown')
        
        # Get token counts
        total_tokens = run_data.get('total_tokens', 0)
        prompt_tokens = run_data.get('prompt_tokens', 0)
        completion_tokens = run_data.get('completion_tokens', 0)
        
        if total_tokens > 0:
            # Add to summary
            if model not in models_summary:
                models_summary[model] = {
                    'calls': 0,
                    'total_tokens': 0,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'estimated_cost': 0
                }
            
            models_summary[model]['calls'] += 1
            models_summary[model]['total_tokens'] += total_tokens
            models_summary[model]['prompt_tokens'] += prompt_tokens
            models_summary[model]['completion_tokens'] += completion_tokens
            models_summary[model]['estimated_cost'] += estimate_cost(model, prompt_tokens, completion_tokens)
    
    # Process child runs
    child_runs = run_data.get('child_runs')
    if child_runs:
        for child in child_runs:
            analyze_model_usage(child, models_summary)
    
    return models_summary

def main():
    trace_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not trace_id:
        console.print("[yellow]Usage: python check_model_usage.py <trace_id>[/yellow]")
        console.print("\nExample: python check_model_usage.py a4483bbb-baa3-4b07-9399-4527f3e32525")
        return
    
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        sys.exit(1)
    
    client = Client(api_key=api_key)
    
    console.print(f"[cyan]Fetching trace {trace_id}...[/cyan]\n")
    
    try:
        run = client.read_run(trace_id)
        run_data = run.dict()
        
        # Overall summary
        console.print(f"[bold]Trace: {run_data.get('name')}[/bold]")
        console.print(f"Total Tokens: {format_tokens(run_data.get('total_tokens', 0))}")
        console.print(f"Prompt Tokens: {format_tokens(run_data.get('prompt_tokens', 0))}")
        console.print(f"Completion Tokens: {format_tokens(run_data.get('completion_tokens', 0))}\n")
        
        # Analyze model usage
        models_summary = analyze_model_usage(run_data)
        
        if not models_summary:
            console.print("[yellow]No model usage found in this trace[/yellow]")
            return
        
        # Create table
        table = Table(title="Token Usage by Model", show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=20)
        table.add_column("Calls", justify="right", width=8)
        table.add_column("Total Tokens", justify="right", width=15)
        table.add_column("Prompt", justify="right", width=12)
        table.add_column("Completion", justify="right", width=12)
        table.add_column("Est. Cost", justify="right", width=12)
        
        # Sort by total tokens
        sorted_models = sorted(models_summary.items(), key=lambda x: x[1]['total_tokens'], reverse=True)
        
        total_cost = 0
        for model, stats in sorted_models:
            table.add_row(
                model,
                str(stats['calls']),
                format_tokens(stats['total_tokens']),
                format_tokens(stats['prompt_tokens']),
                format_tokens(stats['completion_tokens']),
                format_cost(stats['estimated_cost'])
            )
            total_cost += stats['estimated_cost']
        
        console.print(table)
        console.print(f"\n[bold]Total Estimated Cost: {format_cost(total_cost)}[/bold]")
        
        # Warnings
        console.print("\n[bold]Analysis:[/bold]")
        for model, stats in sorted_models:
            if 'gpt-5' in model.lower() and stats['total_tokens'] > 50000:
                console.print(f"[red]⚠️  WARNING: {model} used {stats['total_tokens']:,} tokens (${stats['estimated_cost']:.4f})[/red]")
                console.print(f"   This is expensive! Consider using gpt-4o-mini for this task.")
            elif 'gpt-4o-mini' in model.lower() and stats['total_tokens'] > 10000:
                console.print(f"[green]✓ {model} used {stats['total_tokens']:,} tokens (${stats['estimated_cost']:.4f})[/green]")
                console.print(f"   This is fine - gpt-4o-mini is cost-effective for compression.")
            elif stats['total_tokens'] > 20000:
                console.print(f"[yellow]⚠️  {model} used {stats['total_tokens']:,} tokens[/yellow]")
        
        # Check what the high-token model was doing
        console.print("\n[bold]Checking what consumed the most tokens...[/bold]")
        
        # Find the run with most tokens
        def find_highest_token_run(run_data, current_max=None):
            if current_max is None:
                current_max = {'tokens': 0, 'name': '', 'model': ''}
            
            tokens = run_data.get('total_tokens', 0)
            if tokens > current_max['tokens']:
                model = 'unknown'
                if run_data.get('run_type') == 'llm':
                    extra = run_data.get('extra', {})
                    invocation_params = extra.get('invocation_params', {})
                    model = invocation_params.get('model', 'unknown')
                
                current_max = {
                    'tokens': tokens,
                    'name': run_data.get('name', 'unknown'),
                    'model': model,
                    'inputs': run_data.get('inputs', {})
                }
            
            child_runs = run_data.get('child_runs')
            if child_runs:
                for child in child_runs:
                    current_max = find_highest_token_run(child, current_max)
            
            return current_max
        
        highest = find_highest_token_run(run_data)
        if highest['tokens'] > 0:
            console.print(f"\nHighest token consumer:")
            console.print(f"  Component: {highest['name']}")
            console.print(f"  Model: {highest['model']}")
            console.print(f"  Tokens: {format_tokens(highest['tokens'])}")
            
            # Check input size
            if highest['inputs']:
                input_str = str(highest['inputs'])
                console.print(f"  Input size: {len(input_str):,} characters")
                if 'message' in highest['inputs']:
                    console.print(f"  User message: {str(highest['inputs']['message'])[:100]}...")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()