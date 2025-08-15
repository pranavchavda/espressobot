#!/usr/bin/env python3
"""Simple test for product search through the API"""
import requests
import json
import time

def test_product_search():
    """Test the product search endpoint"""
    url = "http://localhost:8000/api/agent/message"
    headers = {"Content-Type": "application/json"}
    
    # Test 1: Simple hello
    print("Test 1: Simple hello...")
    data = {
        "message": "hello",
        "conversation_id": "test-api-1",
        "thread_id": "test-api-1"
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"Response: {response.json()['response'][:100]}...")
        print("✅ Hello test passed\n")
    except Exception as e:
        print(f"❌ Hello test failed: {e}\n")
    
    # Test 2: Product search
    print("Test 2: Product search...")
    data = {
        "message": "find breville barista express", 
        "conversation_id": "test-api-2",
        "thread_id": "test-api-2"
    }
    try:
        start = time.time()
        response = requests.post(url, json=data, headers=headers, timeout=90)
        elapsed = time.time() - start
        result = response.json()
        print(f"Response ({elapsed:.1f}s): {result['response'][:200]}...")
        print("✅ Product search completed\n")
    except requests.Timeout:
        print("❌ Product search timed out after 90 seconds\n")
    except Exception as e:
        print(f"❌ Product search failed: {e}\n")

if __name__ == "__main__":
    test_product_search()