"""Shared memory manager singleton instance"""

import asyncio
from typing import Optional
from .postgres_memory_manager_v2 import SimpleMemoryManager

_manager_instance: Optional[SimpleMemoryManager] = None
_lock = asyncio.Lock()

async def get_shared_memory_manager() -> SimpleMemoryManager:
    """Get or create the shared memory manager instance"""
    global _manager_instance
    
    async with _lock:
        if _manager_instance is None:
            _manager_instance = SimpleMemoryManager()
            await _manager_instance.initialize()
        return _manager_instance

async def close_shared_manager():
    """Close the shared memory manager"""
    global _manager_instance
    
    async with _lock:
        if _manager_instance is not None:
            await _manager_instance.close()
            _manager_instance = None