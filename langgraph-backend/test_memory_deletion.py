#!/usr/bin/env python3
"""Test memory deletion functionality"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.memory.postgres_memory_manager import PostgresMemoryManager

async def test_deletion():
    """Test memory deletion with real data"""
    
    # Set the database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    # Initialize manager
    manager = PostgresMemoryManager()
    await manager.initialize()
    
    # Test with a real memory ID
    memory_id = "0b096923-78ca-4a42-8194-5780f8103671"
    user_id = "test_user_1"
    
    print(f"Testing deletion of memory {memory_id} for user {user_id}")
    
    # Try to delete
    success = await manager.delete_memory(memory_id, user_id)
    
    if success:
        print("✅ Memory deleted successfully!")
    else:
        print("❌ Memory deletion failed (may not exist)")
    
    await manager.close()
    
    return success

if __name__ == "__main__":
    result = asyncio.run(test_deletion())
    sys.exit(0 if result else 1)