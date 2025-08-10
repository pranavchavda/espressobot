#\!/usr/bin/env python3
"""Test memory search to see actual error"""

import asyncio
import sys
import os
import logging

# Set up logging to see debug messages
logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_search():
    """Test memory search"""
    
    # Set database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    from app.memory.shared_manager import get_shared_memory_manager
    
    # Get shared manager
    manager = await get_shared_memory_manager()
    
    # Search for memories
    print("Testing memory search...")
    try:
        results = await manager.search_memories(
            user_id="1",
            query="web access openai native tool",
            limit=5,
            similarity_threshold=0.2
        )
        
        print(f"Found {len(results)} memories")
        for result in results:
            print(f"  - Score: {result.similarity_score:.3f} | {result.memory.content[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())
