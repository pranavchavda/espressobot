#!/usr/bin/env python3
"""Test the API with native tools."""

import requests
import json

# Test the API
url = "http://localhost:8000/chat"

# Start a new conversation
response = requests.post(url, json={
    "message": "search for coffee machines"
})

if response.status_code == 200:
    data = response.json()
    print("✓ API call successful!")
    print(f"Conversation ID: {data['conversation_id']}")
    print(f"Current Agent: {data['current_agent']}")
    print(f"Messages: {len(data['messages'])}")
    for msg in data['messages']:
        print(f"  - {msg['agent']}: {msg['content'][:100]}...")
else:
    print(f"✗ API call failed with status {response.status_code}")
    print(response.text)