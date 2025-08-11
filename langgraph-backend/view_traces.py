#!/usr/bin/env python3
"""
Simple script to view recent LangSmith traces from CLI
"""
import os
import sys
from datetime import datetime, timedelta
from langsmith import Client
import json

def main():
    import argparse
    parser = argparse.ArgumentParser(description="View LangSmith traces")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch traces in real-time")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Number of traces to show")
    args = parser.parse_args()
    
    # Initialize LangSmith client
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ LANGSMITH_API_KEY not found in environment")
        return
    
    try:
        client = Client(api_key=api_key)
        
        # Get project name from env or use default
        project_name = os.getenv("LANGSMITH_PROJECT", "espressobot")
        
        if args.watch:
            print(f"👁️  Watching traces from project: {project_name} (Press Ctrl+C to stop)")
            print("="*60)
            last_seen = set()
            
            while True:
                # Get runs from the last 5 minutes
                cutoff_time = datetime.now() - timedelta(minutes=5)
                
                runs = list(client.list_runs(
                    project_name=project_name,
                    limit=args.limit,
                    start_time=cutoff_time
                ))
                
                for run in runs:
                    if run.id not in last_seen:
                        print(f"\n🆕 NEW TRACE: {run.name}")
                        print(f"   ID: {run.id}")
                        print(f"   Status: {run.status}")
                        print(f"   Time: {run.start_time}")
                        if run.error:
                            print(f"   ❌ Error: {run.error}")
                        if hasattr(run, 'inputs') and run.inputs:
                            inputs_str = str(run.inputs)
                            if 'messages' in inputs_str:
                                print(f"   📥 Message: {inputs_str[:150]}...")
                        if hasattr(run, 'outputs') and run.outputs:
                            outputs_str = str(run.outputs)
                            if 'text' in outputs_str:
                                print(f"   📤 Response: {outputs_str[:150]}...")
                        print("-" * 50)
                        last_seen.add(run.id)
                
                import time
                time.sleep(2)
        else:
            print(f"🔍 Fetching recent traces from project: {project_name}")
            print("="*50)
            
            # Get runs from the last hour
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            # List recent runs
            runs = list(client.list_runs(
                project_name=project_name,
                limit=args.limit,
                start_time=cutoff_time
            ))
            
            if not runs:
                print("📭 No recent traces found in the last hour")
                return
                
            print(f"📊 Found {len(runs)} recent traces:")
            print()
            
            for i, run in enumerate(runs, 1):
                print(f"🔄 Trace {i}:")
                print(f"   ID: {run.id}")
                print(f"   Name: {run.name}")
                print(f"   Status: {run.status}")
                print(f"   Start Time: {run.start_time}")
                print(f"   End Time: {run.end_time}")
                if run.error:
                    print(f"   ❌ Error: {run.error}")
                if hasattr(run, 'inputs') and run.inputs:
                    print(f"   📥 Inputs: {str(run.inputs)[:100]}...")
                if hasattr(run, 'outputs') and run.outputs:
                    print(f"   📤 Outputs: {str(run.outputs)[:100]}...")
                print()
            
    except KeyboardInterrupt:
        print("\n👋 Stopping trace monitoring...")
    except Exception as e:
        print(f"❌ Error fetching traces: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()