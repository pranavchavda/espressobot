#!/usr/bin/env python
"""
Simple test for LangSmith tracing with orchestrator
"""
import os
import asyncio
import logging
from app.orchestrator_direct import DirectOrchestrator
from app.state.graph_state import GraphState
from langchain_core.messages import HumanMessage

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set environment variables
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "espressobot"

# Use a mock database URL to bypass PostgreSQL issues
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_espressobot.db"

async def test_orchestrator():
    print("\n" + "="*60)
    print("Testing Orchestrator with LangSmith Tracing")
    print("="*60)
    
    try:
        # Initialize orchestrator
        print("\n🔧 Initializing orchestrator...")
        orchestrator = DirectOrchestrator()
        print("✅ Orchestrator initialized")
        
        # Simple test message
        print("\n📝 Sending test message...")
        state = GraphState(
            messages=[HumanMessage(content="Hello! What's 2+2?")],
            thread_id="test-123",
            user_id="test-user"
        )
        
        # Process the request
        result = await orchestrator.process_request(state)
        
        # Show the response
        if result.get("messages"):
            last_msg = result["messages"][-1]
            print(f"\n📥 Response: {last_msg.content}")
        
        print("\n" + "="*60)
        print("✅ Test completed!")
        print("\n📊 View trace at:")
        print("https://smith.langchain.com/o/336cb8ba-b6ab-42fa-85a4-9c079014f4ce/projects/p/espressobot/runs")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orchestrator())