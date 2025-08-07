#!/usr/bin/env python3
"""
Simple test to verify basic system functionality
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_basic():
    """Basic test of the orchestrator"""
    print("\n=== Basic System Test ===\n")
    
    # Import here to catch any import errors
    try:
        from app.orchestrator_simple import SimpleOrchestrator
        print("✅ SimpleOrchestrator imported successfully")
    except Exception as e:
        print(f"❌ Failed to import SimpleOrchestrator: {e}")
        return
    
    try:
        from app.orchestrator import Orchestrator
        print("✅ Full Orchestrator imported successfully")
    except Exception as e:
        print(f"❌ Failed to import full Orchestrator: {e}")
        print("   This might be due to missing agent files or dependencies")
    
    # Test creating simple orchestrator
    try:
        orchestrator = SimpleOrchestrator()
        print(f"✅ SimpleOrchestrator created with {len(orchestrator.agents)} agents")
        print(f"   Agents: {list(orchestrator.agents.keys())}")
    except Exception as e:
        print(f"❌ Failed to create SimpleOrchestrator: {e}")
    
    # Test a simple query
    try:
        from app.state.graph_state import create_initial_state
        
        state = create_initial_state(
            user_message="Hello, how are you?",
            conversation_id="test-1",
            user_id="test_user"
        )
        
        result = await orchestrator.run(
            message="Hello",
            conversation_id="test-simple",
            user_id="test_user"
        )
        
        if result.get("success"):
            print("✅ Simple query executed successfully")
            print(f"   Last agent: {result.get('last_agent')}")
        else:
            print(f"❌ Query failed: {result.get('error')}")
    except Exception as e:
        print(f"❌ Failed to run query: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_basic()

if __name__ == "__main__":
    asyncio.run(main())