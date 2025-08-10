#\!/usr/bin/env python3
"""Test memory search performance"""

import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_performance():
    """Test memory search performance"""
    
    # Set database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    from app.memory.shared_manager import get_shared_memory_manager
    
    # Get shared manager
    manager = await get_shared_memory_manager()
    
    # Test search performance
    queries = ["my name", "CEO", "video calendar", "coffee", "web access"]
    
    print("Testing memory search performance...")
    for query in queries:
        start = time.time()
        results = await manager.search_memories(
            user_id="1",
            query=query,
            limit=5,
            similarity_threshold=0.2
        )
        duration = (time.time() - start) * 1000
        print(f"  Query '{query}': {len(results)} results in {duration:.1f}ms")
    
    # Test concurrent searches
    print("\nTesting concurrent searches...")
    start = time.time()
    tasks = [
        manager.search_memories("1", query, 5, 0.2)
        for query in queries
    ]
    results = await asyncio.gather(*tasks)
    duration = (time.time() - start) * 1000
    print(f"  5 concurrent searches completed in {duration:.1f}ms")
    
    # Don't close the shared manager

if __name__ == "__main__":
    asyncio.run(test_performance())
