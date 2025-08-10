#\!/usr/bin/env python3
"""Test searching for user's name"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_name_search():
    """Test name search"""
    
    # Set database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    from app.memory.shared_manager import get_shared_memory_manager
    
    # Get shared manager
    manager = await get_shared_memory_manager()
    
    # Search for name-related memories
    print("Searching for name memories...")
    try:
        results = await manager.search_memories(
            user_id="1",
            query="do you know my name",
            limit=10,
            similarity_threshold=0.2
        )
        
        print(f"Found {len(results)} memories:")
        for result in results:
            print(f"  - Score: {result.similarity_score:.3f} | {result.memory.content}")
            
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()
    
    # Also try direct query for Pranav memories
    print("\nDirect database query for 'Pranav' memories:")
    query = """
    SELECT id, content, category, importance_score, created_at
    FROM memories 
    WHERE user_id = $1 AND content ILIKE '%pranav%'
    ORDER BY importance_score DESC
    LIMIT 5
    """
    
    try:
        results = await manager._execute_query(query, "1")
        print(f"Found {len(results)} memories mentioning 'Pranav':")
        for row in results:
            print(f"  - {row['content']}")
    except Exception as e:
        print(f"Error in direct query: {e}")

if __name__ == "__main__":
    asyncio.run(test_name_search())
