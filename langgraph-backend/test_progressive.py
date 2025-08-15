#!/usr/bin/env python3
"""Test progressive orchestrator token usage"""
import requests
import json
import time

url = "http://localhost:8000/api/chat/message"
thread_id = f"test_prog_{int(time.time())}"

print(f"Testing PROGRESSIVE orchestrator")
print(f"Thread: {thread_id}\n")

# Simple messages that should work
messages = [
    "What is the price of Profitec GO?",
    "Is it in stock?",
    "What colors is it available in?"
]

for i, msg in enumerate(messages, 1):
    print(f"\nMessage {i}: {msg}")
    
    try:
        response = requests.post(url, json={
            "message": msg,
            "thread_id": thread_id,
            "use_orchestrator": "progressive"  # Use progressive orchestrator
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
        
        if full_response:
            print(f"Response: {full_response[:150]}...")
        else:
            print("No response received")
        
        time.sleep(2)
    except requests.Timeout:
        print("Request timed out!")
    except Exception as e:
        print(f"Error: {e}")

print(f"\n\nThread ID for LangSmith: {thread_id}")
print("\nNOTE: With progressive orchestrator using gpt-5-nano for compression,")
print("token usage should be significantly lower than direct orchestrator.")