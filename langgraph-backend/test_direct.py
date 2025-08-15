#!/usr/bin/env python3
"""Test DIRECT orchestrator to see model usage"""
import requests
import json
import time

url = "http://localhost:8000/api/chat/message"
thread_id = f"test_direct_{int(time.time())}"

print(f"Testing with thread: {thread_id}\n")

messages = [
    "What's the price of Profitec GO espresso machine?",
    "Is it available in stock?",
    "What warranty does it come with?"
]

for i, msg in enumerate(messages, 1):
    print(f"\nMessage {i}: {msg}")
    
    try:
        response = requests.post(url, json={
            "message": msg,
            "thread_id": thread_id,
            "use_orchestrator": "direct"  # Use DIRECT since progressive times out
        }, stream=True, timeout=30)
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data != '[DONE]':
                        try:
                            chunk = json.loads(data)
                            if 'content' in chunk:
                                full_response += chunk['content']
                        except:
                            pass
        
        print(f"Response: {full_response[:200]}...")
        time.sleep(2)
    except requests.Timeout:
        print("Request timed out!")
    except Exception as e:
        print(f"Error: {e}")

print(f"\n\nThread ID for LangSmith: {thread_id}")