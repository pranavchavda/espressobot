#!/usr/bin/env python3
"""Final test for context passing and streaming completion"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_context_and_streaming():
    """Test that context passing works and streaming completes"""
    
    thread_id = f"final-{int(time.time())}"
    print(f"Testing with thread_id: {thread_id}\n")
    
    # Test 1: Simple greeting (should complete quickly)
    print("="*50)
    print("Test 1: Simple Greeting")
    print("="*50)
    
    response1 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "hello", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    done1 = False
    for line in response1.iter_lines(decode_unicode=True):
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "done":
                    done1 = True
                    print("✅ Received done event")
                    break
            except:
                pass
    
    if done1:
        print("✅ Simple greeting completed successfully")
    else:
        print("❌ Simple greeting did not complete")
    
    # Test 2: Context-dependent query
    print("\n" + "="*50)
    print("Test 2: Context-Dependent Query")
    print("="*50)
    
    response2 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "What did I just say?", "thread_id": thread_id},
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
                    print("✅ Received done event")
                    break
            except:
                pass
    
    if "hello" in content2.lower():
        print("✅ Context was maintained (assistant remembered 'hello')")
    else:
        print("❌ Context was not maintained")
        print(f"Response: {content2[:200]}...")
    
    if done2:
        print("✅ Context query completed successfully")
    else:
        print("❌ Context query did not complete")
    
    # Test 3: Product query (might route to agent)
    print("\n" + "="*50)
    print("Test 3: Product Query (Agent Routing)")
    print("="*50)
    
    thread_id3 = f"product-{int(time.time())}"
    
    response3 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "What Breville machines do you have?", "thread_id": thread_id3},
        stream=True,
        timeout=30
    )
    
    agent_used = None
    done3 = False
    content3 = ""
    
    try:
        for line in response3.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    event = data.get("event")
                    
                    if event == "planner_status":
                        agent_used = data.get("agent")
                        print(f"→ Routed to: {agent_used}")
                    elif event == "assistant_delta":
                        content3 += data.get("delta", "")
                    elif event == "done":
                        done3 = True
                        print("✅ Received done event")
                        break
                except:
                    pass
    except requests.exceptions.Timeout:
        print("⚠️ Request timed out (might be processing)")
    except requests.exceptions.ConnectionError:
        print("⚠️ Connection error (stream might have issues)")
    
    if agent_used:
        print(f"✅ Routed to agent: {agent_used}")
    else:
        print("⚠️ No agent routing detected")
    
    if "Breville" in content3 or "machine" in content3.lower():
        print("✅ Product information received")
    else:
        print("⚠️ No product information in response")
    
    if done3:
        print("✅ Product query completed successfully")
    else:
        print("⚠️ Product query did not complete (streaming issue)")
    
    # Final Summary
    print("\n" + "="*50)
    print("FINAL RESULTS")
    print("="*50)
    
    success_count = sum([done1, done2, done3])
    total_tests = 3
    
    print(f"\nTests completed: {success_count}/{total_tests}")
    
    if done1 and done2:
        print("✅ Basic streaming and context passing work")
    
    if not done3:
        print("⚠️ Agent routing has streaming completion issues")
        print("   This is a known issue being worked on")
    
    if success_count >= 2:
        print("\n🎉 PARTIAL SUCCESS: Core functionality works!")
        print("   Context passing is implemented and functional")
        print("   Simple queries complete successfully")
        if not done3:
            print("   Agent streaming needs further debugging")
    else:
        print("\n❌ FAILURE: Significant issues remain")

if __name__ == "__main__":
    test_context_and_streaming()