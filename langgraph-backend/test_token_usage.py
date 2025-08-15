#!/usr/bin/env python3
"""
Test token usage with real API calls and follow-up tasks
"""
import asyncio
import aiohttp
import json
import time
import uuid
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()

async def send_message(session, message: str, thread_id: str, message_num: int):
    """Send a message to the API"""
    url = "http://localhost:8000/api/chat/message"
    
    payload = {
        "message": message,
        "thread_id": thread_id,
        "use_orchestrator": "progressive"
    }
    
    console.print(f"\n[cyan]Message {message_num}: {message}[/cyan]")
    console.print(f"[dim]Thread ID: {thread_id}[/dim]")
    
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                # Handle streaming response
                full_response = ""
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'content' in chunk:
                                full_response += chunk['content']
                                print(chunk['content'], end='', flush=True)
                        except json.JSONDecodeError:
                            pass
                
                console.print(f"\n[green]✓ Response received[/green]")
                return full_response
            else:
                error = await response.text()
                console.print(f"[red]Error {response.status}: {error}[/red]")
                return None
    except Exception as e:
        console.print(f"[red]Request failed: {e}[/red]")
        return None

async def run_test_conversation():
    """Run a test conversation with follow-ups"""
    
    # Generate unique thread ID for this test
    thread_id = f"test_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    console.print(f"[bold cyan]Starting Test Conversation[/bold cyan]")
    console.print(f"Thread ID: {thread_id}")
    console.print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print("=" * 80)
    
    # Test messages that require context and follow-ups
    test_messages = [
        "Check my recent emails from the last 24 hours",
        "Open the second email and show me its content",
        "Reply to that email saying I'll review it tomorrow",
        "Now check today's website traffic stats",
        "What was the conversion rate?",
        "Compare that to yesterday's traffic"
    ]
    
    async with aiohttp.ClientSession() as session:
        responses = []
        
        for i, message in enumerate(test_messages, 1):
            # Wait a bit between messages to simulate real usage
            if i > 1:
                await asyncio.sleep(2)
            
            response = await send_message(session, message, thread_id, i)
            responses.append({
                'message': message,
                'response': response,
                'timestamp': datetime.now()
            })
            
            if not response:
                console.print(f"[yellow]⚠ Stopping test due to error[/yellow]")
                break
        
        console.print("\n" + "=" * 80)
        console.print(f"[bold green]Test Completed[/bold green]")
        console.print(f"Messages sent: {len(responses)}")
        console.print(f"Thread ID: {thread_id}")
    
    return thread_id, responses

async def fetch_trace_for_thread(thread_id: str):
    """Fetch the most recent trace for this thread"""
    import os
    import sys
    from langsmith import Client
    from datetime import timezone, timedelta
    
    api_key = os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        return None
    
    client = Client(api_key=api_key)
    
    # Look for traces from the last hour
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=1)
    
    console.print(f"\n[cyan]Searching for traces with thread_id: {thread_id}[/cyan]")
    
    traces = []
    for run in client.list_runs(
        project_name="espressobot",
        start_time=start_time,
        end_time=end_time,
        limit=50,
        is_root=True
    ):
        run_dict = run.dict()
        # Check if this trace is from our test thread
        inputs = run_dict.get('inputs', {})
        if thread_id in str(inputs):
            traces.append(run_dict)
    
    if traces:
        console.print(f"[green]Found {len(traces)} traces for this thread[/green]")
        return traces
    else:
        console.print(f"[yellow]No traces found for thread {thread_id}[/yellow]")
        console.print("Try waiting a few seconds for traces to appear in LangSmith")
        return None

def analyze_model_usage(traces):
    """Analyze model usage from traces"""
    models_summary = {}
    
    def process_run(run_data):
        """Recursively process runs to find model usage"""
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
                if model not in models_summary:
                    models_summary[model] = {
                        'calls': 0,
                        'total_tokens': 0,
                        'prompt_tokens': 0,
                        'completion_tokens': 0
                    }
                
                models_summary[model]['calls'] += 1
                models_summary[model]['total_tokens'] += total_tokens
                models_summary[model]['prompt_tokens'] += prompt_tokens
                models_summary[model]['completion_tokens'] += completion_tokens
        
        # Process child runs
        child_runs = run_data.get('child_runs')
        if child_runs:
            for child in child_runs:
                process_run(child)
    
    # Process all traces
    for trace in traces:
        process_run(trace)
    
    return models_summary

async def main():
    """Main test function"""
    console.print("[bold magenta]Token Usage Test with Real API Calls[/bold magenta]\n")
    
    # Run the test conversation
    thread_id, responses = await run_test_conversation()
    
    # Wait a bit for traces to be recorded
    console.print("\n[yellow]Waiting 5 seconds for traces to be recorded...[/yellow]")
    await asyncio.sleep(5)
    
    # Fetch traces
    traces = await fetch_trace_for_thread(thread_id)
    
    if traces:
        # Analyze model usage
        console.print("\n[bold]Analyzing Token Usage by Model:[/bold]")
        models_summary = analyze_model_usage(traces)
        
        # Create summary table
        table = Table(title="Token Usage Summary", show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=25)
        table.add_column("Calls", justify="right", width=8)
        table.add_column("Total Tokens", justify="right", width=15)
        table.add_column("Prompt", justify="right", width=12)
        table.add_column("Completion", justify="right", width=12)
        
        total_tokens_all = 0
        for model, stats in sorted(models_summary.items(), key=lambda x: x[1]['total_tokens'], reverse=True):
            table.add_row(
                model,
                str(stats['calls']),
                f"{stats['total_tokens']:,}",
                f"{stats['prompt_tokens']:,}",
                f"{stats['completion_tokens']:,}"
            )
            total_tokens_all += stats['total_tokens']
        
        console.print(table)
        console.print(f"\n[bold]Total Tokens Across All Models: {total_tokens_all:,}[/bold]")
        
        # Analysis
        console.print("\n[bold]Analysis:[/bold]")
        if 'gpt-5' in models_summary:
            gpt5_tokens = models_summary['gpt-5']['total_tokens']
            console.print(f"GPT-5 (Orchestrator): {gpt5_tokens:,} tokens")
        
        if 'gpt-5-nano' in models_summary:
            nano_tokens = models_summary['gpt-5-nano']['total_tokens']
            console.print(f"GPT-5-nano (Compression): {nano_tokens:,} tokens")
            console.print("[green]✓ Using gpt-5-nano for compression[/green]")
        elif 'gpt-4o-mini' in models_summary:
            mini_tokens = models_summary['gpt-4o-mini']['total_tokens']
            console.print(f"GPT-4o-mini (Compression): {mini_tokens:,} tokens")
            console.print("[yellow]⚠ Still using gpt-4o-mini, should be gpt-5-nano[/yellow]")
        
        # Check for token reduction
        console.print(f"\n[bold]Token Efficiency:[/bold]")
        console.print(f"Messages sent: {len(responses)}")
        console.print(f"Average tokens per message: {total_tokens_all // len(responses):,}")
        
        if total_tokens_all > 50000:
            console.print(f"[red]⚠ High token usage detected[/red]")
        elif total_tokens_all < 20000:
            console.print(f"[green]✓ Efficient token usage[/green]")
        else:
            console.print(f"[yellow]Moderate token usage[/yellow]")
        
        # Save trace IDs for manual inspection
        trace_ids = [str(t['id']) for t in traces]
        console.print(f"\n[dim]Trace IDs for manual inspection:[/dim]")
        for tid in trace_ids[:3]:  # Show first 3
            console.print(f"  {tid}")
        
        # Save results to file
        results = {
            'thread_id': thread_id,
            'timestamp': datetime.now().isoformat(),
            'messages_sent': len(responses),
            'total_tokens': total_tokens_all,
            'model_usage': models_summary,
            'trace_ids': trace_ids
        }
        
        with open('token_usage_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        console.print(f"\n[green]Results saved to token_usage_test_results.json[/green]")
    else:
        console.print("\n[red]Could not fetch traces. Please check LangSmith manually.[/red]")
        console.print(f"Thread ID: {thread_id}")

if __name__ == "__main__":
    asyncio.run(main())