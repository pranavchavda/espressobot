#!/usr/bin/env python3
"""Test script for A2A context passing"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
THREAD_ID = f"test-context-{int(time.time())}"

def test_context_passing():
    print(f"Testing with thread_id: {THREAD_ID}")
    
    # First message - ask about a product
    print("\n1. Sending initial product query...")
    response1 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "I am looking for information about the Breville Barista Express in black",
            "thread_id": THREAD_ID
        },
        stream=True
    )
    
    print("Response 1:")
    full_response1 = ""
    for line in response1.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "assistant_delta":
                    full_response1 += data.get("delta", "")
                    print(data.get("delta", ""), end="", flush=True)
                elif data.get("event") == "planner_status":
                    print(f"\n[Routing to: {data.get('agent')}]", flush=True)
            except json.JSONDecodeError:
                pass
    
    print("\n\n" + "="*50)
    time.sleep(2)  # Give the system a moment
    
    # Second message - requires context from first
    print("\n2. Sending follow-up requiring context...")
    response2 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "What is the price of that model?",
            "thread_id": THREAD_ID
        },
        stream=True
    )
    
    print("Response 2:")
    full_response2 = ""
    for line in response2.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "assistant_delta":
                    full_response2 += data.get("delta", "")
                    print(data.get("delta", ""), end="", flush=True)
                elif data.get("event") == "planner_status":
                    print(f"\n[Routing to: {data.get('agent')}]", flush=True)
            except json.JSONDecodeError:
                pass
    
    print("\n\n" + "="*50)
    time.sleep(2)
    
    # Third message - test cross-agent context
    print("\n3. Sending cross-agent query...")
    response3 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "Is it currently on sale or at regular price?",
            "thread_id": THREAD_ID
        },
        stream=True
    )
    
    print("Response 3:")
    full_response3 = ""
    for line in response3.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "assistant_delta":
                    full_response3 += data.get("delta", "")
                    print(data.get("delta", ""), end="", flush=True)
                elif data.get("event") == "planner_status":
                    print(f"\n[Routing to: {data.get('agent')}]", flush=True)
            except json.JSONDecodeError:
                pass
    
    print("\n\n" + "="*50)
    print("\nContext Passing Test Complete!")
    print(f"\nAnalysis:")
    print(f"- Response 1 mentioned: {'Breville' in full_response1 and 'Express' in full_response1}")
    print(f"- Response 2 understood context: {'price' in full_response2.lower() or '$' in full_response2}")
    print(f"- Response 3 checked sale status: {'sale' in full_response3.lower() or 'regular' in full_response3.lower()}")

if __name__ == "__main__":
    test_context_passing()