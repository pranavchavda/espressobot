#!/usr/bin/env python3
"""Quick test to see model usage"""
import requests
import json
import time

# Test 1: Simple query
url = "http://localhost:8000/api/chat/message"
thread_id = f"quick_test_{int(time.time())}"

messages = [
    "What is the price of Profitec GO?",
    "Is it available in yellow?", 
    "What about the warranty?"
]

print(f"Thread ID: {thread_id}\n")

for i, msg in enumerate(messages, 1):
    print(f"\n[Message {i}]: {msg}")
    
    response = requests.post(url, json={
        "message": msg,
        "thread_id": thread_id,
        "use_orchestrator": "progressive"
    }, stream=True)
    
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

print(f"\n\nDone! Check traces for thread_id: {thread_id}")
print("Look in LangSmith for token usage breakdown")