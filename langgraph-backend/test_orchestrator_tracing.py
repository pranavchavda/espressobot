#!/usr/bin/env python
"""
Test LangSmith tracing with the DirectOrchestrator
"""
import os
import asyncio
import logging
from app.orchestrator_direct import DirectOrchestrator
from app.state.graph_state import GraphState
from langchain_core.messages import HumanMessage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "espressobot"

async def test_orchestrator_tracing():
    """Test LangSmith tracing with DirectOrchestrator"""
    
    print("\n" + "="*60)
    print("Testing DirectOrchestrator with LangSmith Tracing")
    print("="*60)
    
    try:
        # Initialize orchestrator
        print("\n🔧 Initializing DirectOrchestrator...")
        orchestrator = DirectOrchestrator()
        print("✅ Orchestrator initialized")
        
        # Test 1: Simple greeting
        print("\n📝 Test 1: Simple greeting")
        state = GraphState(
            messages=[HumanMessage(content="Hello! My name is Pranav.")],
            thread_id="test-greeting-123",
            user_id="1"
        )
        
        result = await orchestrator.process_request(state)
        last_message = result["messages"][-1]
        print(f"   Response: {last_message.content[:100]}...")
        
        # Test 2: Product query (should route to products agent)
        print("\n📝 Test 2: Product query")
        state = GraphState(
            messages=[HumanMessage(content="What espresso machines do you have under $1000?")],
            thread_id="test-products-456",
            user_id="1"
        )
        
        result = await orchestrator.process_request(state)
        last_message = result["messages"][-1]
        print(f"   Response: {last_message.content[:100]}...")
        print(f"   Routed to: {result.get('current_agent', 'orchestrator')}")
        
        # Test 3: Memory context query
        print("\n📝 Test 3: Memory context query")
        state = GraphState(
            messages=[HumanMessage(content="What was my name again?")],
            thread_id="test-memory-789",
            user_id="1"
        )
        
        result = await orchestrator.process_request(state)
        last_message = result["messages"][-1]
        print(f"   Response: {last_message.content[:100]}...")
        
        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("\n📊 Check your traces at:")
        print(f"https://smith.langchain.com/projects/p/espressobot/runs")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orchestrator_tracing())