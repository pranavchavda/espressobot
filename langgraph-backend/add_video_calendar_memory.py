#\!/usr/bin/env python3
"""Add video calendar memory for testing"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.memory.shared_manager import get_shared_memory_manager
from app.memory.postgres_memory_manager import Memory

async def add_memory():
    """Add video calendar memory"""
    
    # Set database URL
    os.environ['DATABASE_URL'] = 'postgresql://espressobot:localdev123@localhost/espressobot_dev'
    
    # Get shared manager
    manager = await get_shared_memory_manager()
    
    # Add video calendar memory
    memory = Memory(
        user_id="1",
        content="There is a Video Calendar Google Doc that tracks all upcoming video productions and release schedules for iDrinkCoffee.com",
        category="facts",
        importance_score=0.8,
        metadata={"type": "document", "source": "google_drive", "topic": "video_production"}
    )
    
    memory_id = await manager.store_memory(memory)
    print(f"✅ Added video calendar memory with ID: {memory_id}")
    
    # Don't close the shared manager

if __name__ == "__main__":
    asyncio.run(add_memory())
