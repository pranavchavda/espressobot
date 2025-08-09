#!/usr/bin/env python3
"""Debug test for product streaming"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_product_stream():
    """Test product query streaming with detailed output"""
    
    thread_id = f"debug-{int(time.time())}"
    print(f"Testing product query with thread_id: {thread_id}\n")
    
    response = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={"message": "What Breville machines do you have?", "thread_id": thread_id},
        stream=True,
        timeout=30
    )
    
    events = []
    try:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    event_type = data.get("event")
                    events.append(event_type)
                    
                    if event_type == "planner_status":
                        print(f"[PLANNER] Routing to: {data.get('agent')}")
                    elif event_type == "assistant_delta":
                        print(f"[DELTA] Agent: {data.get('agent')}, Delta: {data.get('delta')[:50]}...")
                    elif event_type == "agent_complete":
                        print(f"[COMPLETE] Agent: {data.get('agent')}, Message length: {len(data.get('message', ''))}")
                    elif event_type == "done":
                        print(f"[DONE] Stream completed successfully")
                    elif event_type == "error":
                        print(f"[ERROR] {data.get('error')}")
                    else:
                        print(f"[{event_type}] {json.dumps(data)[:100]}...")
                        
                except json.JSONDecodeError as e:
                    print(f"[RAW] {line[:100]}...")
    except requests.exceptions.Timeout:
        print("[TIMEOUT] Request timed out")
    except requests.exceptions.ConnectionError as e:
        print(f"[CONNECTION ERROR] {e}")
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}")
    
    print(f"\nEvent summary: {events}")
    print(f"Total events: {len(events)}")
    
    if "done" in events:
        print("✅ Stream completed with done event")
    else:
        print("❌ Stream did not complete with done event")

if __name__ == "__main__":
    test_product_stream()