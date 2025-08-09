#\!/usr/bin/env python3
import asyncio
import os
from app.memory.postgres_memory_manager import PostgresMemoryManager

async def test_memory_search():
    """Test memory search directly"""
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost:5432/espressobot_dev'
    
    manager = PostgresMemoryManager()
    await manager.initialize()
    
    # Test search with different queries
    test_queries = [
        "coffee",
        "Pranav",
        "preferences",
        "name"
    ]
    
    for query in test_queries:
        results = await manager.search_memories(
            query=query,
            user_id="1",
            limit=5,
            similarity_threshold=0.3  # Lower threshold for testing
        )
        print(f"\nQuery: '{query}' - Found {len(results)} memories:")
        for r in results[:3]:
            print(f"  - {r.memory.content[:60]}... (similarity: {r.similarity_score:.2f})")
    
    await manager.close()

asyncio.run(test_memory_search())
