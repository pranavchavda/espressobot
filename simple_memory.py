"""
Simplified memory module that doesn't require external MCP dependencies.
Provides the same interface as the MCP memory server for compatibility.
"""
import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# In-memory storage
memory_store = {}

class SimpleMemoryServer:
    """
    A simple in-memory implementation of the memory server interface.
    """
    
    def __init__(self):
        """Initialize the simple memory server."""
        self.store = memory_store
        
    async def store_user_memory(self, user_id, key, value):
        """
        Store a memory for a specific user.
        
        Args:
            user_id: The user's ID to namespace the memory
            key: The memory key
            value: The value to store
            
        Returns:
            Dictionary with storage status
        """
        memory_key = f"user_{user_id}:{key}"
        logger.info(f"[MEMORY] Storing memory for user {user_id}: {key}")
        
        try:
            # Store the value
            if not isinstance(self.store, dict):
                self.store = {}
                
            # Initialize user dict if needed
            if user_id not in self.store:
                self.store[user_id] = {}
                
            # Store the memory
            self.store[user_id][key] = value
            
            return {
                "success": True,
                "key": memory_key,
                "message": f"Memory stored successfully for user {user_id}"
            }
        except Exception as e:
            logger.error(f"[MEMORY] Error storing memory: {e}")
            return {
                "success": False,
                "key": memory_key,
                "message": f"Error storing memory: {str(e)}"
            }
    
    async def retrieve_user_memory(self, user_id, key, default=None):
        """
        Retrieve a memory for a specific user.
        
        Args:
            user_id: The user's ID to namespace the memory
            key: The memory key to retrieve
            default: Default value if memory not found
            
        Returns:
            Dictionary with the retrieved memory or error
        """
        memory_key = f"user_{user_id}:{key}"
        logger.info(f"[MEMORY] Retrieving memory for user {user_id}: {key}")
        
        try:
            # Check if user exists
            if user_id not in self.store:
                return {
                    "success": False,
                    "key": memory_key,
                    "message": "Memory not found",
                    "value": default
                }
            
            # Check if key exists
            if key not in self.store[user_id]:
                return {
                    "success": False,
                    "key": memory_key,
                    "message": "Memory not found",
                    "value": default
                }
            
            # Return the value
            return {
                "success": True,
                "key": memory_key,
                "value": self.store[user_id][key]
            }
        except Exception as e:
            logger.error(f"[MEMORY] Error retrieving memory: {e}")
            return {
                "success": False,
                "key": memory_key,
                "message": f"Error retrieving memory: {str(e)}",
                "value": default
            }
    
    async def list_user_memories(self, user_id):
        """
        List all memories for a specific user.
        
        Args:
            user_id: The user's ID to namespace the memories
            
        Returns:
            Dictionary with the list of memory keys for the user
        """
        logger.info(f"[MEMORY] Listing memories for user {user_id}")
        
        try:
            # Check if user exists
            if user_id not in self.store:
                return {
                    "success": True,
                    "keys": [],
                    "count": 0
                }
            
            # Return all keys
            keys = list(self.store[user_id].keys())
            
            return {
                "success": True,
                "keys": keys,
                "count": len(keys)
            }
        except Exception as e:
            logger.error(f"[MEMORY] Error listing memories: {e}")
            return {
                "success": False,
                "keys": [],
                "message": f"Error listing memories: {str(e)}",
                "count": 0
            }
    
    async def delete_user_memory(self, user_id, key):
        """
        Delete a specific memory for a user.
        
        Args:
            user_id: The user's ID to namespace the memory
            key: The memory key to delete
            
        Returns:
            Dictionary with deletion status
        """
        memory_key = f"user_{user_id}:{key}"
        logger.info(f"[MEMORY] Deleting memory for user {user_id}: {key}")
        
        try:
            # Check if user exists
            if user_id not in self.store:
                return {
                    "success": True,
                    "key": memory_key,
                    "message": f"Memory deleted successfully for user {user_id}"
                }
            
            # Check if key exists
            if key in self.store[user_id]:
                # Delete the memory
                del self.store[user_id][key]
            
            return {
                "success": True,
                "key": memory_key,
                "message": f"Memory deleted successfully for user {user_id}"
            }
        except Exception as e:
            logger.error(f"[MEMORY] Error deleting memory: {e}")
            return {
                "success": False,
                "key": memory_key,
                "message": f"Error deleting memory: {str(e)}"
            }

# Create singleton instance
memory_server = SimpleMemoryServer()