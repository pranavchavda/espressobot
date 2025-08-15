#!/usr/bin/env python3
"""Test LangSmith API to see data format"""
import os
from langsmith import Client
from datetime import datetime, timedelta, timezone
import json

api_key = os.getenv('LANGSMITH_API_KEY')
if not api_key:
    print("Error: LANGSMITH_API_KEY not set")
    exit(1)

client = Client(api_key=api_key)

# Fetch recent runs
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(hours=2)

print("Fetching recent runs...")
for i, run in enumerate(client.list_runs(
    project_name="espressobot",
    start_time=start_time,
    end_time=end_time,
    limit=2,
    is_root=True
)):
    print(f"\n=== Run {i+1} ===")
    print(f"Type: {type(run)}")
    print(f"Dir: {[x for x in dir(run) if not x.startswith('_')][:10]}")
    
    # Try different ways to access data
    if hasattr(run, 'dict'):
        data = run.dict()
        print(f"Has dict() method")
    elif hasattr(run, '__dict__'):
        data = run.__dict__
        print(f"Using __dict__")
    else:
        data = vars(run)
        print(f"Using vars()")
    
    # Show sample fields
    print(f"Sample fields:")
    for key in list(data.keys())[:10]:
        value = data[key]
        if value is not None:
            print(f"  {key}: {type(value).__name__} = {str(value)[:100]}")
    
    # Check specific fields we need
    print(f"\nKey fields:")
    print(f"  id: {data.get('id')}")
    print(f"  name: {data.get('name')}")
    print(f"  start_time: {data.get('start_time')} (type: {type(data.get('start_time'))})")
    print(f"  end_time: {data.get('end_time')} (type: {type(data.get('end_time'))})")
    print(f"  total_tokens: {data.get('total_tokens')}")
    print(f"  status: {data.get('status')}")
    
    break  # Just check first one