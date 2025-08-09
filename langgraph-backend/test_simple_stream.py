#!/usr/bin/env python3
"""Simple test to find where streaming hangs"""

import requests
import json
import time

def test_simple():
    url = "http://localhost:8000/api/agent/stream"
    
    # Test with product query
    print("Testing product query...")
    thread_id = f"debug-{int(time.time())}"
    
    response = requests.post(
        url,
        json={"message": "Tell me about Breville", "thread_id": thread_id},
        stream=True,
        timeout=15
    )
    
    print(f"Thread ID: {thread_id}")
    print("\nReceiving events:")
    
    event_count = 0
    try:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    event = data.get("event")
                    event_count += 1
                    print(f"{event_count}. {event}")
                    
                    if event == "done":
                        print("✅ SUCCESS: Received done event!")
                        break
                        
                except json.JSONDecodeError:
                    print(f"Failed to parse: {line[:50]}...")
                    
    except requests.exceptions.Timeout:
        print(f"\n❌ TIMEOUT after {event_count} events")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ CONNECTION ERROR after {event_count} events: {e}")
    
    print(f"\nTotal events received: {event_count}")

if __name__ == "__main__":
    test_simple()