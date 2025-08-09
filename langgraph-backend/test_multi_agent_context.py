#!/usr/bin/env python3
"""Test multi-agent context passing and collaboration"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
THREAD_ID = f"test-multi-{int(time.time())}"

def test_multi_agent_context():
    print(f"Testing multi-agent collaboration with thread_id: {THREAD_ID}")
    
    # Test 1: Product → Inventory → Pricing flow
    print("\n" + "="*50)
    print("TEST 1: Product → Inventory → Pricing flow")
    print("="*50)
    
    print("\n1. Initial product query...")
    response1 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "Find me the Sanremo YOU espresso machine",
            "thread_id": THREAD_ID
        },
        stream=True
    )
    
    agents_used = []
    for line in response1.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status":
                    agent = data.get('agent')
                    if agent not in agents_used:
                        agents_used.append(agent)
                        print(f"→ Routing to: {agent}")
                elif data.get("event") == "assistant_delta":
                    pass  # Silent for brevity
            except json.JSONDecodeError:
                pass
    
    print(f"Agents involved: {agents_used}")
    
    print("\n2. Check inventory (should remember product)...")
    response2 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "How many units do we have in stock?",
            "thread_id": THREAD_ID
        },
        stream=True
    )
    
    agents_used = []
    for line in response2.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status":
                    agent = data.get('agent')
                    if agent not in agents_used:
                        agents_used.append(agent)
                        print(f"→ Routing to: {agent}")
            except json.JSONDecodeError:
                pass
    
    print(f"Agents involved: {agents_used}")
    
    print("\n3. Check if on sale (should remember product context)...")
    response3 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "Is there any discount or MAP sale on this?",
            "thread_id": THREAD_ID
        },
        stream=True
    )
    
    agents_used = []
    for line in response3.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status":
                    agent = data.get('agent')
                    if agent not in agents_used:
                        agents_used.append(agent)
                        print(f"→ Routing to: {agent}")
            except json.JSONDecodeError:
                pass
    
    print(f"Agents involved: {agents_used}")
    
    # Test 2: Complex multi-agent query
    print("\n" + "="*50)
    print("TEST 2: Complex multi-agent query")
    print("="*50)
    
    THREAD_ID_2 = f"test-complex-{int(time.time())}"
    
    print("\n4. Complex query requiring multiple agents...")
    response4 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "I need a grinder to go with a Breville espresso machine. What do you recommend around $500, and do we have any in stock?",
            "thread_id": THREAD_ID_2
        },
        stream=True
    )
    
    agents_used = []
    full_response = ""
    for line in response4.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status":
                    agent = data.get('agent')
                    if agent not in agents_used:
                        agents_used.append(agent)
                        print(f"→ Routing to: {agent}")
                elif data.get("event") == "assistant_delta":
                    full_response += data.get("delta", "")
            except json.JSONDecodeError:
                pass
    
    print(f"Agents involved: {agents_used}")
    print(f"\nResponse mentioned:")
    print(f"- Grinder: {'grinder' in full_response.lower()}")
    print(f"- Price/Budget: {'500' in full_response or 'price' in full_response.lower()}")
    print(f"- Stock/Inventory: {'stock' in full_response.lower() or 'available' in full_response.lower()}")
    
    # Test 3: GraphQL custom query with context
    print("\n" + "="*50)
    print("TEST 3: GraphQL with context")
    print("="*50)
    
    THREAD_ID_3 = f"test-graphql-{int(time.time())}"
    
    print("\n5. Ask about a product first...")
    response5 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "Tell me about the Eureka Mignon Specialita grinder",
            "thread_id": THREAD_ID_3
        },
        stream=True
    )
    
    for line in response5.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status":
                    print(f"→ Routing to: {data.get('agent')}")
            except json.JSONDecodeError:
                pass
    
    print("\n6. GraphQL query requiring context...")
    response6 = requests.post(
        f"{BASE_URL}/api/agent/stream",
        json={
            "message": "Can you run a GraphQL query to get all the metafields for that product?",
            "thread_id": THREAD_ID_3
        },
        stream=True
    )
    
    agents_used = []
    for line in response6.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("event") == "planner_status":
                    agent = data.get('agent')
                    if agent not in agents_used:
                        agents_used.append(agent)
                        print(f"→ Routing to: {agent}")
            except json.JSONDecodeError:
                pass
    
    print(f"Agents involved: {agents_used}")
    print(f"GraphQL agent was used: {'graphql' in agents_used}")
    
    print("\n" + "="*50)
    print("Multi-Agent Context Passing Test Complete!")
    print("="*50)

if __name__ == "__main__":
    test_multi_agent_context()