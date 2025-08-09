#!/usr/bin/env python3
"""Test Agent Management API"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_get_agents():
    """Test getting all agents"""
    print("\n1. Testing GET /api/agent-management/agents")
    response = requests.get(f"{BASE_URL}/api/agent-management/agents")
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get("success"):
        print(f"Found {len(data.get('agents', []))} agents")
        for agent in data.get('agents', [])[:3]:  # Show first 3
            print(f"  - {agent.get('agent_name')}: {agent.get('model_slug')}")
    else:
        print(f"Error: {data.get('error')}")
    return data

def test_get_models():
    """Test getting available models"""
    print("\n2. Testing GET /api/agent-management/models")
    response = requests.get(f"{BASE_URL}/api/agent-management/models")
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get("success"):
        print(f"Found {len(data.get('models', []))} models")
        print(f"Current provider: {data.get('provider')}")
        for model in data.get('models', [])[:5]:  # Show first 5
            print(f"  - {model.get('name')} ({model.get('provider')})")
    else:
        print(f"Error: {data.get('error')}")
    return data

def test_get_stats():
    """Test getting statistics"""
    print("\n3. Testing GET /api/agent-management/stats")
    response = requests.get(f"{BASE_URL}/api/agent-management/stats")
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get("success"):
        stats = data.get('stats', {})
        totals = stats.get('totals', {})
        print(f"Total agents: {totals.get('total_agents')}")
        print(f"Active agents: {totals.get('active_agents')}")
        print(f"Unique models: {totals.get('unique_models')}")
    else:
        print(f"Error: {data.get('error')}")
    return data

def test_update_agent():
    """Test updating an agent's model"""
    print("\n4. Testing PUT /api/agent-management/agents/products")
    
    # Update products agent to use GPT-5-mini
    update_data = {
        "model_slug": "gpt-5-mini"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/agent-management/agents/products",
        json=update_data
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get("success"):
        print(f"Success: {data.get('message')}")
    else:
        print(f"Error: {data.get('error')}")
    return data

def test_sync_agents():
    """Test syncing agents"""
    print("\n5. Testing POST /api/agent-management/sync")
    response = requests.post(f"{BASE_URL}/api/agent-management/sync")
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get("success"):
        print(f"Synced {data.get('synced')} agents")
    else:
        print(f"Error: {data.get('error')}")
    return data

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Agent Management API")
    print("=" * 60)
    
    # Run tests
    test_get_agents()
    test_get_models()
    test_get_stats()
    test_sync_agents()
    test_update_agent()
    
    # Verify the update worked
    print("\n6. Verifying update...")
    agents_data = test_get_agents()
    for agent in agents_data.get('agents', []):
        if agent.get('agent_name') == 'products':
            print(f"Products agent now uses: {agent.get('model_slug')}")
            break
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)