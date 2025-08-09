#!/usr/bin/env python
"""Test memory database connection and extraction"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

async def test_connection():
    from app.memory.postgres_memory_manager import PostgresMemoryManager
    from app.memory.memory_persistence import MemoryPersistenceNode
    from langchain_core.messages import HumanMessage, AIMessage
    
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
    print(f"OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    
    # Test database connection
    print("\n1. Testing database connection...")
    manager = PostgresMemoryManager()
    await manager.initialize()
    print("✅ Connected to database")
    
    # Test memory extraction
    print("\n2. Testing memory extraction...")
    node = MemoryPersistenceNode()
    await node.initialize()
    
    # Create test messages
    messages = [
        HumanMessage(content="I prefer dark roast coffee from Ethiopia"),
        AIMessage(content="Great choice! Ethiopian dark roasts have wonderful fruity notes."),
        HumanMessage(content="Yes, and I usually order 2 bags per month for my office"),
        AIMessage(content="I'll help you find the perfect Ethiopian dark roast for your monthly office supply.")
    ]
    
    # Extract memories
    memories = await node.extraction_service.extract_memories_from_conversation(
        messages, user_id="test_user_1"
    )
    
    print(f"✅ Extracted {len(memories)} memories:")
    for mem in memories:
        print(f"  - [{mem.category}] {mem.content} (importance: {mem.importance_score})")
    
    # Test storing memories
    print("\n3. Testing memory storage...")
    stored_count = 0
    for memory in memories:
        memory_id = await manager.store_memory(memory)
        if memory_id:
            stored_count += 1
            print(f"  ✅ Stored memory {memory_id}")
    
    print(f"\n✅ Successfully stored {stored_count}/{len(memories)} memories")
    
    # Cleanup
    await manager.close()
    await node.close()
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_connection())