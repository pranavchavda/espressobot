#\!/usr/bin/env python3
"""Create a test memory for deletion testing"""

import asyncio
import sys
import os
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.memory.postgres_memory_manager import PostgresMemoryManager, Memory

async def create_test_memory():
    """Create a test memory"""
    
    # Set the database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    # Initialize manager
    manager = PostgresMemoryManager()
    await manager.initialize()
    
    # Create a test memory
    test_memory = Memory(
        user_id="1",  # User ID 1 for testing with the UI
        content=f"Test memory for deletion - {uuid.uuid4().hex[:8]}",
        category="general",
        importance_score=0.5,
        metadata={"test": True, "created_for": "deletion_testing"}
    )
    
    memory_id = await manager.store_memory(test_memory)
    print(f"✅ Created test memory with ID: {memory_id}")
    print(f"   Content: {test_memory.content}")
    print(f"   User: {test_memory.user_id}")
    
    await manager.close()
    
    return memory_id

if __name__ == "__main__":
    memory_id = asyncio.run(create_test_memory())
    print(f"\nYou can now test deleting this memory from the admin UI")
