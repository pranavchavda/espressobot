#!/usr/bin/env python3
"""Final test for A2A context passing"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_context():
    thread_id = f"final-test-{int(time.time())}"
    print(f"Testing context passing with thread_id: {thread_id}\n")
    
    # Test 1: Initial query
    print("=" * 50)
    print("TEST 1: Initial Product Query")
    print("=" * 50)
    
    response1 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "Tell me about the Breville Barista Express", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    agent1 = None
    content1 = ""
    events1 = []
    
    try:
        for line in response1.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    events1.append(data.get("event"))
                    
                    if data.get("event") == "planner_status":
                        agent1 = data.get("agent")
                        print(f"→ Routed to: {agent1}")
                    elif data.get("event") == "assistant_delta":
                        content1 += data.get("delta", "")
                    elif data.get("event") == "done":
                        print("✓ Stream completed")
                        break
                    elif data.get("event") == "agent_complete":
                        print(f"✓ Agent {data.get('agent')} completed")
                except json.JSONDecodeError:
                    pass
    except requests.exceptions.ReadTimeout:
        print("⚠ Timeout but got some response")
    
    print(f"\nContent preview: {content1[:150]}...")
    print(f"Response mentions Breville: {'Breville' in content1}")
    
    time.sleep(2)
    
    # Test 2: Context-dependent query
    print("\n" + "=" * 50)
    print("TEST 2: Context-Dependent Query")
    print("=" * 50)
    
    response2 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "What is the price?", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    agent2 = None
    content2 = ""
    events2 = []
    
    try:
        for line in response2.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    events2.append(data.get("event"))
                    
                    if data.get("event") == "planner_status":
                        agent2 = data.get("agent")
                        print(f"→ Routed to: {agent2}")
                    elif data.get("event") == "assistant_delta":
                        content2 += data.get("delta", "")
                    elif data.get("event") == "done":
                        print("✓ Stream completed")
                        break
                    elif data.get("event") == "agent_complete":
                        print(f"✓ Agent {data.get('agent')} completed")
                except json.JSONDecodeError:
                    pass
    except requests.exceptions.ReadTimeout:
        print("⚠ Timeout but got some response")
    
    print(f"\nContent preview: {content2[:150]}...")
    print(f"Response has price info: {'$' in content2 or 'price' in content2.lower()}")
    print(f"Context maintained (mentions product): {'Breville' in content2 or 'Barista' in content2 or '1149' in content2}")
    
    # Summary
    print("\n" + "=" * 50)
    print("CONTEXT PASSING TEST RESULTS")
    print("=" * 50)
    
    print(f"\nTest 1 - Initial Query:")
    print(f"  ✓ Agent used: {agent1}")
    print(f"  ✓ Found product: {'Breville' in content1}")
    
    print(f"\nTest 2 - Context Query:")
    print(f"  ✓ Agent used: {agent2}")
    print(f"  ✓ Price mentioned: {'$' in content2 or 'price' in content2.lower()}")
    print(f"  ✓ Context passed: {'Breville' in content2 or 'Barista' in content2 or '1149' in content2}")
    
    if agent2 and ('$' in content2 or 'price' in content2.lower()) and ('Breville' in content2 or 'Barista' in content2 or '1149' in content2):
        print("\n🎉 SUCCESS: Context passing is working!")
    else:
        print("\n⚠ PARTIAL: Context passing needs investigation")
        print(f"  Events seen in response 1: {set(events1)}")
        print(f"  Events seen in response 2: {set(events2)}")

if __name__ == "__main__":
    test_context()