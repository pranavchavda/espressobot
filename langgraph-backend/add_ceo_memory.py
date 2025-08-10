#\!/usr/bin/env python3
"""Add CEO memory for testing"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.memory.postgres_memory_manager import PostgresMemoryManager, Memory

async def add_ceo_memory():
    """Add CEO memory"""
    
    # Set the database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    # Initialize manager
    manager = PostgresMemoryManager()
    await manager.initialize()
    
    # Add CEO memory with high importance
    ceo_memory = Memory(
        user_id="1",
        content="Slawek Janicki is the CEO and founder of iDrinkCoffee.com",
        category="facts",
        importance_score=1.0,
        metadata={"entity": "person", "role": "CEO", "company": "iDrinkCoffee.com"}
    )
    
    memory_id = await manager.store_memory(ceo_memory)
    print(f"✅ Added CEO memory with ID: {memory_id}")
    
    await manager.close()

if __name__ == "__main__":
    asyncio.run(add_ceo_memory())
