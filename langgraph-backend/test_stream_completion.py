#!/usr/bin/env python3
"""Test that streaming completes properly"""

import requests
import json
import time

def test_stream_completion():
    """Test that the stream sends done event and completes"""
    
    url = "http://localhost:8000/api/agent/stream"
    thread_id = f"test-{int(time.time())}"
    
    print(f"Testing with thread_id: {thread_id}")
    
    # Test 1: Simple greeting
    print("\nTest 1: Simple greeting (should complete quickly)")
    response = requests.post(
        url,
        json={"message": "hello", "thread_id": thread_id},
        stream=True,
        timeout=10
    )
    
    events = []
    done_received = False
    
    try:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    event = data.get("event")
                    events.append(event)
                    
                    if event == "done":
                        done_received = True
                        print("✓ Received 'done' event")
                        break
                    elif event == "title_generated":
                        print(f"✓ Title generated: {data.get('title')}")
                    elif event == "graph_complete":
                        print("✓ Graph completed")
                    elif event == "conversation_id":
                        print(f"✓ Conversation ID: {data.get('conv_id')}")
                        
                except json.JSONDecodeError:
                    pass
                    
    except requests.exceptions.Timeout:
        print("✗ Stream timed out")
    except requests.exceptions.ConnectionError as e:
        if "Read timed out" in str(e):
            print("✗ Stream read timed out")
        else:
            raise
    
    print(f"\nEvents received: {set(events)}")
    print(f"Done event received: {done_received}")
    
    if done_received:
        print("\n✅ SUCCESS: Stream completed properly!")
    else:
        print("\n❌ FAILURE: Stream did not complete")
    
    time.sleep(2)
    
    # Test 2: Product query
    print("\n" + "="*50)
    print("Test 2: Product query (may take longer)")
    
    thread_id_2 = f"test-product-{int(time.time())}"
    response2 = requests.post(
        url,
        json={"message": "Tell me about the Breville Barista Express", "thread_id": thread_id_2},
        stream=True,
        timeout=30
    )
    
    events2 = []
    done_received2 = False
    agent_used = None
    
    try:
        for line in response2.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    event = data.get("event")
                    events2.append(event)
                    
                    if event == "done":
                        done_received2 = True
                        print("✓ Received 'done' event")
                        break
                    elif event == "planner_status":
                        agent_used = data.get("agent")
                        print(f"✓ Routed to agent: {agent_used}")
                    elif event == "agent_complete":
                        print(f"✓ Agent completed: {data.get('agent')}")
                        
                except json.JSONDecodeError:
                    pass
                    
    except requests.exceptions.Timeout:
        print("✗ Stream timed out")
    except requests.exceptions.ConnectionError as e:
        if "Read timed out" in str(e):
            print("✗ Stream read timed out")
        else:
            raise
    
    print(f"\nEvents received: {set(events2)}")
    print(f"Agent used: {agent_used}")
    print(f"Done event received: {done_received2}")
    
    if done_received2:
        print("\n✅ SUCCESS: Product query stream completed properly!")
    else:
        print("\n❌ FAILURE: Product query stream did not complete")
    
    # Overall result
    print("\n" + "="*50)
    print("OVERALL RESULT:")
    if done_received and done_received2:
        print("✅ ALL TESTS PASSED: Streaming is working correctly!")
    else:
        print("❌ SOME TESTS FAILED: Streaming has issues")
        print(f"  - Simple greeting: {'✓' if done_received else '✗'}")
        print(f"  - Product query: {'✓' if done_received2 else '✗'}")

if __name__ == "__main__":
    test_stream_completion()