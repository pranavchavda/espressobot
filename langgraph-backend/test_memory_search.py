#\!/usr/bin/env python3
"""Test memory search functionality"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.memory.postgres_memory_manager import PostgresMemoryManager

async def test_search():
    """Test memory search"""
    
    # Set the database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    # Initialize manager
    manager = PostgresMemoryManager()
    await manager.initialize()
    
    # Search for CEO-related memories
    print("Searching for CEO memories...")
    results = await manager.search_memories(
        user_id="1",
        query="CEO of iDrinkCoffee",
        limit=5,
        similarity_threshold=0.3
    )
    
    print(f"Found {len(results)} memories:")
    for result in results:
        print(f"  - Score: {result.similarity_score:.3f} | {result.memory.content[:100]}...")
    
    await manager.close()
    
    return len(results) > 0

if __name__ == "__main__":
    success = asyncio.run(test_search())
    sys.exit(0 if success else 1)
