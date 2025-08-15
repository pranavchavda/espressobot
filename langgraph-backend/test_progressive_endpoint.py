#!/usr/bin/env python3
"""Test the ACTUAL progressive orchestrator endpoint"""
import requests
import json
import time

# Use the CORRECT endpoint for progressive orchestrator
url = "http://localhost:8000/api/agent/message"  # Progressive is at /api/agent
thread_id = f"test_prog_{int(time.time())}"

print(f"Testing PROGRESSIVE orchestrator at correct endpoint")
print(f"URL: {url}")
print(f"Thread: {thread_id}\n")

messages = [
    "What is the price of Profitec GO?",
    "Is it in stock?", 
    "What colors is it available in?"
]

for i, msg in enumerate(messages, 1):
    print(f"\n[Message {i}]: {msg}")
    
    try:
        response = requests.post(url, json={
            "message": msg,
            "thread_id": thread_id
        }, timeout=120)  # 2 minutes for GPT-5 thinking model
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data.get('response', 'No response')[:200]}...")
        else:
            print(f"Error {response.status_code}: {response.text}")
        
        time.sleep(2)
    except requests.Timeout:
        print("Request timed out!")
    except Exception as e:
        print(f"Error: {e}")

print(f"\n\nThread ID for LangSmith: {thread_id}")
print("\nNOTE: This uses the progressive orchestrator with gpt-4.1-mini for compression")
print("Check server logs for 'Starting compression' to verify langextract is working")