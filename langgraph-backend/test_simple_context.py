#!/usr/bin/env python3
"""Simple test for context passing verification"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def simple_context_test():
    thread_id = f"simple-test-{int(time.time())}"
    print(f"Testing with thread_id: {thread_id}\n")
    
    # Message 1: Ask about a specific product
    print("1. Asking about Breville...")
    r1 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "Tell me about the Breville Barista Express", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    agent1 = None
    response1 = ""
    for line in r1.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status" and not agent1:
                    agent1 = data.get("agent")
                elif data.get("event") == "assistant_delta":
                    response1 += data.get("delta", "")
            except:
                pass
    
    print(f"   → Agent used: {agent1}")
    print(f"   → Response mentioned Breville: {'Breville' in response1}")
    
    time.sleep(1)
    
    # Message 2: Follow-up that needs context
    print("\n2. Asking for price (needs context)...")
    r2 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "What's the price?", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    agent2 = None
    response2 = ""
    for line in r2.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status" and not agent2:
                    agent2 = data.get("agent")
                elif data.get("event") == "assistant_delta":
                    response2 += data.get("delta", "")
            except:
                pass
    
    print(f"   → Agent used: {agent2}")
    print(f"   → Response has price: {'$' in response2 or 'price' in response2.lower()}")
    print(f"   → Context maintained: {'Breville' in response2 or 'Barista' in response2 or agent2 == agent1}")
    
    # Check if context from orchestrator is being used
    print("\n3. Context Analysis:")
    print(f"   → Same agent handled both: {agent1 == agent2}")
    print(f"   → Agents involved: {agent1}, {agent2}")
    
    # Show snippet of response
    if response2:
        print(f"\n   Response snippet: {response2[:200]}...")
    
    print("\n✅ Context passing test complete!")

if __name__ == "__main__":
    simple_context_test()