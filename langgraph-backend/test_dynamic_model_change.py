#!/usr/bin/env python3
"""Test that model changes take effect dynamically"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_model_change():
    print("=" * 60)
    print("Testing Dynamic Model Change")
    print("=" * 60)
    
    # 1. Check current model for inventory agent
    print("\n1. Current inventory agent model:")
    response = requests.get(f"{BASE_URL}/api/agent-management/agents")
    agents = response.json()["agents"]
    
    inventory_agent = next((a for a in agents if a["agent_name"] == "inventory"), None)
    if inventory_agent:
        print(f"   Current model: {inventory_agent['model_slug']}")
    
    # 2. Change inventory agent to use GPT-5-mini
    print("\n2. Changing inventory agent to GPT-5-mini...")
    update_data = {
        "model_slug": "gpt-5-mini"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/agent-management/agents/inventory",
        json=update_data
    )
    
    if response.json().get("success"):
        print("   ✅ Model updated successfully")
    else:
        print(f"   ❌ Failed: {response.json().get('error')}")
    
    # 3. Verify the change
    print("\n3. Verifying change...")
    response = requests.get(f"{BASE_URL}/api/agent-management/agents")
    agents = response.json()["agents"]
    
    inventory_agent = next((a for a in agents if a["agent_name"] == "inventory"), None)
    if inventory_agent:
        print(f"   New model: {inventory_agent['model_slug']}")
        if inventory_agent['model_slug'] == 'gpt-5-mini':
            print("   ✅ Model change verified!")
        else:
            print("   ❌ Model didn't change")
    
    # 4. Check persisted config
    print("\n4. Checking persisted configuration...")
    with open("app/config/agent_models.json", "r") as f:
        config = json.load(f)
    
    if "inventory" in config:
        print(f"   Persisted model: {config['inventory']['model_name']}")
        if config['inventory']['model_name'] == 'gpt-5-mini':
            print("   ✅ Configuration persisted!")
        else:
            print("   ❌ Configuration not persisted")
    
    # 5. Change it back to Claude
    print("\n5. Reverting to Claude 3.5 Haiku...")
    update_data = {
        "model_slug": "claude-3-5-haiku-20241022"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/agent-management/agents/inventory",
        json=update_data
    )
    
    if response.json().get("success"):
        print("   ✅ Reverted successfully")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_model_change()