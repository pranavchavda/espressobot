#!/usr/bin/env python3
"""
Test script for the full LangGraph system with all agents and memory
"""

import asyncio
import os
import time
from typing import Dict, Any
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_orchestrator():
    """Test the full orchestrator with all agents"""
    from app.orchestrator import Orchestrator
    from app.state.graph_state import create_initial_state
    
    print("\n=== Testing LangGraph Orchestrator with All Agents ===\n")
    
    # Initialize orchestrator (this will load all 14 agents)
    print("Initializing orchestrator...")
    start_time = time.time()
    orchestrator = Orchestrator()
    init_time = time.time() - start_time
    print(f"✅ Orchestrator initialized in {init_time:.2f}s")
    print(f"   Loaded agents: {list(orchestrator.agents.keys())}")
    
    # Test cases for different agents
    test_cases = [
        {
            "message": "Hello, how are you?",
            "expected_agent": "general",
            "description": "General conversation"
        },
        {
            "message": "Find product with SKU ESP-001",
            "expected_agent": "products",
            "description": "Product search"
        },
        {
            "message": "Update the price of SKU TEST-001 to 99.99",
            "expected_agent": "pricing",
            "description": "Price management"
        },
        {
            "message": "Check inventory levels for all coffee products",
            "expected_agent": "inventory",
            "description": "Inventory management"
        },
        {
            "message": "What are the current MAP sales?",
            "expected_agent": "sales",
            "description": "Sales campaigns"
        },
        {
            "message": "Update product features for the espresso machine",
            "expected_agent": "features",
            "description": "Feature management"
        },
        {
            "message": "Add an image to product ABC-123",
            "expected_agent": "media",
            "description": "Media management"
        },
        {
            "message": "Send a review request to customer@example.com",
            "expected_agent": "integrations",
            "description": "External integrations"
        },
        {
            "message": "Create a new product bundle",
            "expected_agent": "product_mgmt",
            "description": "Product management"
        },
        {
            "message": "Search my memories for coffee preferences",
            "expected_agent": "utility",
            "description": "Memory operations"
        },
        {
            "message": "Execute this GraphQL query: { shop { name } }",
            "expected_agent": "graphql",
            "description": "GraphQL operations"
        },
        {
            "message": "Show me today's orders",
            "expected_agent": "orders",
            "description": "Order management"
        },
        {
            "message": "Check my Gmail inbox",
            "expected_agent": "google_workspace",
            "description": "Google Workspace"
        },
        {
            "message": "What's today's website traffic?",
            "expected_agent": "ga4_analytics",
            "description": "GA4 Analytics"
        }
    ]
    
    print(f"\n=== Running {len(test_cases)} Agent Routing Tests ===\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['description']}")
        print(f"  Message: '{test['message']}'")
        
        # Create initial state
        state = create_initial_state(
            user_message=test['message'],
            conversation_id=f"test-{i}",
            user_id="test_user"
        )
        
        # Route the request
        start_time = time.time()
        routed_state = await orchestrator.route_request(state)
        routing_time = time.time() - start_time
        
        selected_agent = routed_state.get("current_agent", "unknown")
        print(f"  Selected Agent: {selected_agent}")
        print(f"  Expected Agent: {test['expected_agent']}")
        print(f"  Routing Time: {routing_time:.3f}s")
        
        if selected_agent == test['expected_agent']:
            print(f"  ✅ PASSED")
        else:
            print(f"  ❌ FAILED - Wrong agent selected")
        
        print()
    
    print("=== Testing Complete ===\n")

async def test_memory_integration():
    """Test native memory integration"""
    print("\n=== Testing Native Memory Integration ===\n")
    
    try:
        from app.memory.native_memory_integration import NativeMemoryIntegration, MemoryType, ContextTier
        
        print("Initializing native memory system...")
        memory = NativeMemoryIntegration(
            memory_type=MemoryType.BUFFER,  # Start with simple buffer memory
            context_tier=ContextTier.STANDARD
        )
        
        await memory.initialize()
        print("✅ Memory system initialized")
        
        # Test adding a memory
        print("\nTesting memory operations...")
        from app.state.graph_state import create_initial_state
        
        state = create_initial_state(
            user_message="I prefer Ethiopian coffee",
            conversation_id="memory-test",
            user_id="test_user"
        )
        
        # Enhance state with memory
        start_time = time.time()
        enhanced_state = await memory.enhance_agent_state(state)
        memory_time = time.time() - start_time
        
        print(f"✅ State enhanced with memory in {memory_time:.3f}s")
        
        # Check if memory context was added
        if enhanced_state.get("memory_context"):
            print(f"   Memory context added: {len(enhanced_state['memory_context'])} items")
        
        # Test conversation memory
        print("\nTesting conversation memory...")
        conv_memory = memory.get_conversation_memory()
        if conv_memory:
            print("✅ Conversation memory available")
            
            # Add a message to memory
            conv_memory.add_user_message("Test user message")
            conv_memory.add_ai_message("Test AI response")
            
            # Get messages
            messages = conv_memory.chat_memory.messages
            print(f"   Stored {len(messages)} messages")
        
        print("\n✅ Memory integration test complete")
        
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_performance():
    """Test system performance and latency"""
    print("\n=== Testing System Performance ===\n")
    
    from app.orchestrator import Orchestrator
    from app.state.graph_state import create_initial_state
    
    orchestrator = Orchestrator()
    
    # Test simple query latency
    queries = [
        "Hello",
        "Find product ESP-001",
        "What's the price of coffee?",
        "Show me today's orders"
    ]
    
    print("Testing query latencies:")
    for query in queries:
        state = create_initial_state(query, "perf-test", "test_user")
        
        start_time = time.time()
        routed_state = await orchestrator.route_request(state)
        latency = time.time() - start_time
        
        print(f"  '{query[:30]}...': {latency*1000:.0f}ms")
    
    # Test streaming performance
    print("\nTesting streaming (first 5 tokens):")
    state = create_initial_state(
        "Tell me about coffee",
        "stream-test",
        "test_user"
    )
    
    token_times = []
    token_count = 0
    
    start_time = time.time()
    async for chunk in orchestrator.stream_response(state):
        if chunk.get("type") == "token" and token_count < 5:
            token_time = time.time() - start_time
            token_times.append(token_time)
            token_count += 1
            print(f"  Token {token_count}: {token_time*1000:.0f}ms")
        
        if token_count >= 5:
            break
    
    if token_times:
        avg_time = sum(token_times) / len(token_times)
        print(f"\n  Average time to token: {avg_time*1000:.0f}ms")
        print(f"  First token: {token_times[0]*1000:.0f}ms")
    
    print("\n✅ Performance testing complete")

async def main():
    """Run all tests"""
    print("=" * 60)
    print("LANGGRAPH FULL SYSTEM TEST")
    print("=" * 60)
    
    # Test orchestrator and agents
    await test_orchestrator()
    
    # Test memory integration
    await test_memory_integration()
    
    # Test performance
    await test_performance()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())