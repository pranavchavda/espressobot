#\!/usr/bin/env python3
"""Test embedding format issue"""

import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_embedding_format():
    """Test embedding format"""
    
    # Set database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    from app.memory.shared_manager import get_shared_memory_manager
    from app.memory.embedding_service import get_embedding_service
    
    # Get services
    manager = await get_shared_memory_manager()
    embedding_service = get_embedding_service()
    
    # Generate embedding
    query = "do you know my name"
    result = await embedding_service.get_embedding(query)
    embedding = result.embedding
    
    print(f"Embedding type: {type(embedding)}")
    print(f"Embedding length: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
    
    # Try the actual query that the search_memories function uses
    search_query = """
    SELECT id, user_id, content, metadata, category, importance_score,
           access_count, last_accessed_at, created_at, updated_at,
           embedding,
           1 - (embedding <=> $2::vector) as similarity
    FROM memories 
    WHERE user_id = $1 
      AND 1 - (embedding <=> $2::vector) >= $3
    ORDER BY 
      (1 - (embedding <=> $2::vector)) * 0.6 + importance_score * 0.4 DESC
    LIMIT $4
    """
    
    # Test with string representation
    embedding_str = str(embedding)
    print(f"\nTesting with embedding string format...")
    
    try:
        results = await manager._execute_query(
            search_query, "1", embedding_str, 0.2, 10
        )
        print(f"Success\! Found {len(results)} results")
    except Exception as e:
        print(f"Failed with string format: {e}")
    
    # Test with JSON format
    embedding_json = json.dumps(embedding)
    print(f"\nTesting with JSON format...")
    
    try:
        results = await manager._execute_query(
            search_query, "1", embedding_json, 0.2, 10
        )
        print(f"Success\! Found {len(results)} results")
    except Exception as e:
        print(f"Failed with JSON format: {e}")

if __name__ == "__main__":
    asyncio.run(test_embedding_format())
