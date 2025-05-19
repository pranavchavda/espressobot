"""
Memory service module for managing user-specific memories.

This service provides an interface for storing and retrieving user memories,
using both the MCP memory server for in-memory storage and the database
for persistence.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Union

from models import UserMemory
from extensions import db
from mcp_server import memory_mcp_server

# Configure logging
logger = logging.getLogger(__name__)

class MemoryService:
    """
    Service for managing user memories with both in-memory and database persistence.
    """
    
    @staticmethod
    async def store_memory(user_id: int, key: str, value: Any, persist: bool = True) -> Dict[str, Any]:
        """
        Store a memory for a specific user.
        
        Args:
            user_id: The user's ID
            key: Memory key
            value: Memory value (will be JSON serialized if not a string)
            persist: Whether to also persist to database (default: True)
            
        Returns:
            Dict with operation status
        """
        # Convert value to string if it's not already
        if not isinstance(value, str):
            try:
                value_str = json.dumps(value)
            except Exception as e:
                value_str = str(value)
                logger.warning(f"Failed to JSON serialize value for {key}, using str() instead: {e}")
        else:
            value_str = value
            
        # Store in MCP memory server
        mcp_result = await memory_mcp_server.store_memory(user_id, key, value_str)
        
        # Persist to database if requested
        db_result = {"persisted": False}
        if persist:
            try:
                # Check if memory already exists
                existing_memory = UserMemory.query.filter_by(
                    user_id=user_id, key=key
                ).first()
                
                if existing_memory:
                    # Update existing memory
                    existing_memory.value = value_str
                    db.session.commit()
                else:
                    # Create new memory
                    memory = UserMemory(
                        user_id=user_id,
                        key=key,
                        value=value_str
                    )
                    db.session.add(memory)
                    db.session.commit()
                    
                db_result = {"persisted": True}
            except Exception as e:
                logger.error(f"Error persisting memory to database: {e}")
                db_result = {"persisted": False, "error": str(e)}
                
        return {
            "success": mcp_result.get("success", False),
            "key": key,
            "persisted": db_result.get("persisted", False),
            "message": mcp_result.get("message", "")
        }
    
    @staticmethod
    async def retrieve_memory(user_id: int, key: str, default: Any = None) -> Dict[str, Any]:
        """
        Retrieve a memory for a specific user.
        
        Args:
            user_id: The user's ID
            key: Memory key to retrieve
            default: Default value if memory not found
            
        Returns:
            Dict with memory value or default
        """
        # First try MCP memory server
        mcp_result = await memory_mcp_server.retrieve_memory(user_id, key)
        
        # If successful, return the result
        if mcp_result.get("success", False) and mcp_result.get("value") is not None:
            value = mcp_result.get("value")
            # Try to parse as JSON if it looks like JSON
            if isinstance(value, str) and value.strip().startswith(("{", "[")):
                try:
                    parsed_value = json.loads(value)
                    return {
                        "success": True,
                        "key": key,
                        "value": parsed_value,
                        "source": "memory_server"
                    }
                except json.JSONDecodeError:
                    # Not valid JSON, return as string
                    pass
                    
            return {
                "success": True,
                "key": key,
                "value": value,
                "source": "memory_server"
            }
        
        # If not in memory server, check database
        try:
            memory = UserMemory.query.filter_by(
                user_id=user_id, key=key
            ).first()
            
            if memory:
                value = memory.value
                # Try to parse as JSON if it looks like JSON
                if value.strip().startswith(("{", "[")):
                    try:
                        parsed_value = json.loads(value)
                        
                        # Also store this back in the memory server for next time
                        await memory_mcp_server.store_memory(user_id, key, value)
                        
                        return {
                            "success": True,
                            "key": key,
                            "value": parsed_value,
                            "source": "database"
                        }
                    except json.JSONDecodeError:
                        # Not valid JSON, return as string
                        pass
                
                # Also store this back in the memory server for next time
                await memory_mcp_server.store_memory(user_id, key, value)
                
                return {
                    "success": True,
                    "key": key,
                    "value": value,
                    "source": "database"
                }
        except Exception as e:
            logger.error(f"Error retrieving memory from database: {e}")
        
        # If not found anywhere, return default
        return {
            "success": False,
            "key": key,
            "value": default,
            "source": "default"
        }
    
    @staticmethod
    async def list_memories(user_id: int) -> Dict[str, Any]:
        """
        List all memories for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict with list of memory keys
        """
        # Get keys from MCP memory server
        mcp_result = await memory_mcp_server.list_memories(user_id)
        mcp_keys = set(mcp_result.get("keys", []))
        
        # Get keys from database
        try:
            db_memories = UserMemory.query.filter_by(user_id=user_id).all()
            db_keys = {memory.key for memory in db_memories}
        except Exception as e:
            logger.error(f"Error listing memories from database: {e}")
            db_keys = set()
        
        # Combine unique keys from both sources
        all_keys = list(mcp_keys.union(db_keys))
        
        return {
            "success": True,
            "keys": all_keys,
            "count": len(all_keys),
            "sources": {
                "memory_server": list(mcp_keys),
                "database": list(db_keys)
            }
        }
    
    @staticmethod
    async def delete_memory(user_id: int, key: str) -> Dict[str, Any]:
        """
        Delete a memory for a user.
        
        Args:
            user_id: The user's ID
            key: Memory key to delete
            
        Returns:
            Dict with operation status
        """
        # Delete from MCP memory server
        mcp_result = await memory_mcp_server.delete_memory(user_id, key)
        
        # Delete from database
        db_result = {"deleted": False}
        try:
            memory = UserMemory.query.filter_by(
                user_id=user_id, key=key
            ).first()
            
            if memory:
                db.session.delete(memory)
                db.session.commit()
                db_result = {"deleted": True}
        except Exception as e:
            logger.error(f"Error deleting memory from database: {e}")
            db_result = {"deleted": False, "error": str(e)}
        
        return {
            "success": mcp_result.get("success", False) or db_result.get("deleted", False),
            "key": key,
            "memory_server_deleted": mcp_result.get("success", False),
            "database_deleted": db_result.get("deleted", False),
            "message": f"Memory {key} deleted for user {user_id}"
        }

# Create a singleton instance
memory_service = MemoryService()