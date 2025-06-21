#!/usr/bin/env python
"""Test script for EspressoBot v0.2 API"""

import requests
import json

# Test the API
def test_api():
    url = "http://localhost:8000/chat"
    
    # Initial connection
    print("Testing initial connection...")
    response = requests.post(url, json={"message": "", "conversation_id": None})
    if response.status_code == 200:
        data = response.json()
        conversation_id = data["conversation_id"]
        print(f"✅ Connected! Conversation ID: {conversation_id}")
        print(f"Current agent: {data['current_agent']}")
        print(f"Agents available: {len(data['agents'])}")
        for agent in data['agents']:
            print(f"  - {agent['name']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return
    
    # Test a simple query
    print("\nTesting product search...")
    response = requests.post(url, json={
        "message": "Find all Lavazza products",
        "conversation_id": conversation_id
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Response received!")
        print(f"Current agent: {data['current_agent']}")
        if data['messages']:
            print(f"Message: {data['messages'][0]['content'][:200]}...")
        if data['events']:
            print(f"Events: {len(data['events'])}")
            for event in data['events']:
                print(f"  - {event['type']}: {event['content']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_api()