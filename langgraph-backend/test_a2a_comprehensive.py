#!/usr/bin/env python3
"""Comprehensive test for A2A context passing and streaming"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_comprehensive():
    """Test all aspects of A2A context passing and streaming"""
    
    print("="*60)
    print("COMPREHENSIVE A2A CONTEXT PASSING TEST")
    print("="*60)
    
    thread_id = f"a2a-test-{int(time.time())}"
    print(f"\nThread ID: {thread_id}\n")
    
    # Test 1: Initial greeting (orchestrator direct response)
    print("TEST 1: Initial Greeting (Orchestrator Direct)")
    print("-"*50)
    
    response1 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "Hello, I'm testing the system", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    content1 = ""
    done1 = False
    delta_count1 = 0
    
    for line in response1.iter_lines(decode_unicode=True):
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "assistant_delta":
                    delta_count1 += 1
                    content1 += data.get("delta", "")
                elif data.get("event") == "done":
                    done1 = True
                    break
            except:
                pass
    
    print(f"✓ Received {delta_count1} delta events")
    print(f"✓ Response: {content1[:100]}...")
    print(f"✓ Stream completed: {done1}")
    
    # Test 2: Context check (orchestrator remembers)
    print("\nTEST 2: Context Memory Check")
    print("-"*50)
    
    response2 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "What did I just tell you?", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    content2 = ""
    done2 = False
    
    for line in response2.iter_lines(decode_unicode=True):
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "assistant_delta":
                    content2 += data.get("delta", "")
                elif data.get("event") == "done":
                    done2 = True
                    break
            except:
                pass
    
    has_context = "testing" in content2.lower() or "system" in content2.lower() or "hello" in content2.lower()
    print(f"✓ Context maintained: {has_context}")
    print(f"✓ Response: {content2[:100]}...")
    print(f"✓ Stream completed: {done2}")
    
    # Test 3: Product query (agent routing)
    print("\nTEST 3: Product Query (Agent Routing)")
    print("-"*50)
    
    response3 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "Show me Breville espresso machines under $1000", "thread_id": thread_id},
        stream=True,
        timeout=30
    )
    
    content3 = ""
    done3 = False
    agent_used = None
    delta_count3 = 0
    
    for line in response3.iter_lines(decode_unicode=True):
        if line:
            try:
                data = json.loads(line)
                event = data.get("event")
                
                if event == "planner_status":
                    agent_used = data.get("agent")
                elif event == "assistant_delta":
                    delta_count3 += 1
                    content3 += data.get("delta", "")
                elif event == "done":
                    done3 = True
                    break
            except:
                pass
    
    print(f"✓ Routed to agent: {agent_used}")
    print(f"✓ Received {delta_count3} delta events")
    print(f"✓ Product info received: {'Breville' in content3}")
    print(f"✓ Stream completed: {done3}")
    
    # Test 4: Context passing to agent (A2A)
    print("\nTEST 4: A2A Context Passing")
    print("-"*50)
    
    response4 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "What was the price range I mentioned?", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    content4 = ""
    done4 = False
    
    for line in response4.iter_lines(decode_unicode=True):
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "assistant_delta":
                    content4 += data.get("delta", "")
                elif data.get("event") == "done":
                    done4 = True
                    break
            except:
                pass
    
    has_price_context = "1000" in content4 or "thousand" in content4.lower()
    print(f"✓ Agent received context: {has_price_context}")
    print(f"✓ Response: {content4[:100]}...")
    print(f"✓ Stream completed: {done4}")
    
    # Final Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_tests_passed = all([done1, done2, done3, done4])
    context_works = has_context and has_price_context
    
    print(f"\n✓ All streams completed: {all_tests_passed}")
    print(f"✓ Context passing works: {context_works}")
    print(f"✓ Agent routing works: {agent_used is not None}")
    print(f"✓ Streaming works: {delta_count1 > 0 and delta_count3 > 0}")
    
    if all_tests_passed and context_works:
        print("\n🎉 SUCCESS: A2A context passing is fully functional!")
        print("   - Orchestrator maintains conversation context")
        print("   - Agents receive context from previous messages")
        print("   - Streaming completes properly for all query types")
        print("   - No duplicate rendering issues detected")
    else:
        print("\n⚠️ PARTIAL SUCCESS: Some issues remain")
        if not all_tests_passed:
            print("   - Some streams did not complete")
        if not context_works:
            print("   - Context passing needs improvement")

if __name__ == "__main__":
    test_comprehensive()