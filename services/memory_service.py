"""
Memory service implementation for persistent user-specific memory storage.
Replaces the MCPMemoryServer with a direct implementation.
"""
import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import logging

from services.base_service import BaseService, ServiceError
from services.config import service_config

class MemoryServiceError(ServiceError):
    """Exception raised for memory service errors."""
    pass

class MemoryService(BaseService):
    """
    Direct implementation of memory service functionality.
    Provides persistent user-specific memory storage without MCP overhead.
    """
    def __init__(self):
        """Initialize the memory service."""
        super().__init__("memory")
        
        # Get storage path from config or use default
        self.storage_path = service_config.get(
            "memory", 
            "storage_path", 
            os.path.join(os.getcwd(), "storage", "memory")
        )
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # In-memory cache for faster access
        self.memory_cache = {}
        
        # Load existing memories
        self._load_memories()
    
    def _get_user_storage_path(self, user_id: str) -> str:
        """
        Get the storage path for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Path to user's memory storage file
        """
        return os.path.join(self.storage_path, f"user_{user_id}.json")
    
    def _load_memories(self) -> None:
        """Load all existing memories into the cache."""
        try:
            # Find all user memory files
            for filename in os.listdir(self.storage_path):
                if filename.startswith("user_") and filename.endswith(".json"):
                    # Extract user_id from filename
                    user_id = filename[5:-5]  # Remove "user_" prefix and ".json" suffix
                    
                    # Load user memories
                    file_path = os.path.join(self.storage_path, filename)
                    with open(file_path, 'r') as f:
                        self.memory_cache[user_id] = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading memories: {str(e)}")
            # Initialize empty cache if loading fails
            self.memory_cache = {}
    
    def _save_user_memories(self, user_id: str) -> None:
        """
        Save a user's memories to disk.
        
        Args:
            user_id: User identifier
        """
        try:
            file_path = self._get_user_storage_path(user_id)
            with open(file_path, 'w') as f:
                json.dump(self.memory_cache.get(user_id, {}), f, indent=2)
        except Exception as e:
            raise MemoryServiceError(f"Failed to save memories: {str(e)}")
    
    async def store_memory(self, user_id: str, key: str, value: Any) -> Dict[str, Any]:
        """
        Store a memory for a specific user.
        
        Args:
            user_id: User identifier
            key: Memory key
            value: Memory value (any JSON-serializable object)
            
        Returns:
            Success status and metadata
        """
        try:
            # Ensure user_id is a string
            user_id = str(user_id)
            
            # Initialize user memory if not exists
            if user_id not in self.memory_cache:
                self.memory_cache[user_id] = {}
            
            # Store memory
            self.memory_cache[user_id][key] = value
            
            # Save to disk
            self._save_user_memories(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "key": key
            }
        except Exception as e:
            raise MemoryServiceError(f"Failed to store memory: {str(e)}")
    
    async def retrieve_memory(self, user_id: str, key: str) -> Dict[str, Any]:
        """
        Retrieve a memory for a specific user.
        
        Args:
            user_id: User identifier
            key: Memory key
            
        Returns:
            Memory value and metadata
        """
        try:
            # Ensure user_id is a string
            user_id = str(user_id)
            
            # Check if user exists
            if user_id not in self.memory_cache:
                return {
                    "success": False,
                    "error": f"No memories found for user {user_id}"
                }
            
            # Check if key exists
            if key not in self.memory_cache[user_id]:
                return {
                    "success": False,
                    "error": f"Memory key '{key}' not found for user {user_id}"
                }
            
            # Return memory
            return {
                "success": True,
                "user_id": user_id,
                "key": key,
                "value": self.memory_cache[user_id][key]
            }
        except Exception as e:
            raise MemoryServiceError(f"Failed to retrieve memory: {str(e)}")
    
    async def delete_memory(self, user_id: str, key: str) -> Dict[str, Any]:
        """
        Delete a memory for a specific user.
        
        Args:
            user_id: User identifier
            key: Memory key
            
        Returns:
            Success status and metadata
        """
        try:
            # Ensure user_id is a string
            user_id = str(user_id)
            
            # Check if user exists
            if user_id not in self.memory_cache:
                return {
                    "success": False,
                    "error": f"No memories found for user {user_id}"
                }
            
            # Check if key exists
            if key not in self.memory_cache[user_id]:
                return {
                    "success": False,
                    "error": f"Memory key '{key}' not found for user {user_id}"
                }
            
            # Delete memory
            del self.memory_cache[user_id][key]
            
            # Save to disk
            self._save_user_memories(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "key": key
            }
        except Exception as e:
            raise MemoryServiceError(f"Failed to delete memory: {str(e)}")
    
    async def list_memories(self, user_id: str) -> Dict[str, Any]:
        """
        List all memories for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of memory keys and metadata
        """
        try:
            # Ensure user_id is a string
            user_id = str(user_id)
            
            # Check if user exists
            if user_id not in self.memory_cache:
                return {
                    "success": True,
                    "user_id": user_id,
                    "keys": []
                }
            
            # Return memory keys
            return {
                "success": True,
                "user_id": user_id,
                "keys": list(self.memory_cache[user_id].keys())
            }
        except Exception as e:
            raise MemoryServiceError(f"Failed to list memories: {str(e)}")

# Create a singleton instance
memory_service = MemoryService()
