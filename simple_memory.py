"""
Simplified memory module that doesn't require external MCP dependencies.
Provides the same interface as the MCP memory server for compatibility.
"""
import os
import json
import logging
import json # Added for serializing complex values for embedding
from typing import Dict, Any, Optional

from embedding_service import EmbeddingService
from vector_store import VectorStore

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
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        
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

            # Generate and store embedding
            try:
                text_to_embed = ""
                if isinstance(value, (dict, list)):
                    text_to_embed = json.dumps(value)
                elif isinstance(value, str):
                    text_to_embed = value
                else:
                    # For other types, convert to string, though this might not always be ideal for semantic meaning
                    text_to_embed = str(value)
                
                if text_to_embed:
                    embedding = self.embedding_service.get_embedding(text_to_embed)
                    if embedding:
                        self.vector_store.add_embedding(user_id, key, embedding)
                        logger.info(f"[MEMORY_VECTOR] Stored embedding for user {user_id}, key {key}")
                    else:
                        logger.warning(f"[MEMORY_VECTOR] Failed to generate embedding for user {user_id}, key {key}. Vector not stored.")
                else:
                    logger.warning(f"[MEMORY_VECTOR] Value for key {key} (user {user_id}) resulted in empty text_to_embed. Vector not stored.")
            except Exception as e_embed:
                logger.error(f"[MEMORY_VECTOR] Error processing or storing embedding for user {user_id}, key {key}: {e_embed}", exc_info=True)
            
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
            deleted_from_store = False
            if key in self.store[user_id]:
                # Delete the memory
                del self.store[user_id][key]
                deleted_from_store = True
            
            # Delete corresponding embedding
            if deleted_from_store: # Only attempt to delete from vector store if it was in the main store
                try:
                    delete_success = self.vector_store.delete_embedding(user_id, key)
                    if delete_success:
                        logger.info(f"[MEMORY_VECTOR] Deleted embedding for user {user_id}, key {key}")
                    else:
                        logger.warning(f"[MEMORY_VECTOR] Failed to delete or find embedding for user {user_id}, key {key} in vector store.")
                except Exception as e_embed_delete:
                    logger.error(f"[MEMORY_VECTOR] Error deleting embedding for user {user_id}, key {key}: {e_embed_delete}", exc_info=True)
            elif user_id in self.store: # Key wasn't in user's store, but user exists. Still try to cleanup vector store just in case of inconsistency.
                logger.info(f"[MEMORY_VECTOR] Key '{key}' not found in main store for user '{user_id}'. Attempting cleanup of vector store anyway.")
                self.vector_store.delete_embedding(user_id, key)
            
            return {
                "success": True,
                "key": memory_key,
                "message": f"Memory deletion processed for user {user_id}, key {key}."
            }
        except Exception as e:
            logger.error(f"[MEMORY] Error deleting memory: {e}")
            return {
                "success": False,
                "key": memory_key,
                "message": f"Error deleting memory: {str(e)}"
            }

    async def proactively_retrieve_memories(self, user_id: str, query_text: str, top_n: int = 5):
        user_id = str(user_id)
        """
        Proactively retrieves memories relevant to a query_text using vector similarity.
        """
        logger.info(f"[MEMORY_PROACTIVE] Attempting to retrieve memories for user {user_id} (top_n={top_n}) based on query: '{query_text[:50]}...'" )
        retrieved_memories_content = []
        try:
            query_embedding = self.embedding_service.get_embedding(query_text)
            if not query_embedding:
                logger.warning(f"[MEMORY_PROACTIVE] Could not generate embedding for query: '{query_text[:50]}...'. Skipping retrieval.")
                return []

            # Find similar memory keys from the vector store
            similar_memory_keys = self.vector_store.find_similar_embeddings(user_id, query_embedding, top_n=top_n)
            
            if not similar_memory_keys:
                logger.info(f"[MEMORY_PROACTIVE] No similar memory keys found for user {user_id} and query.")
                return []

            logger.info(f"[MEMORY_PROACTIVE] Found {len(similar_memory_keys)} similar memory keys: {similar_memory_keys}")

            # Retrieve the actual content of these memories
            for key in similar_memory_keys: # key here is a tuple (actual_key_str, similarity_score)
                memory_key_to_retrieve = key[0] # Extract the actual key string from the tuple
                memory_data_dict = await self.retrieve_user_memory(user_id, memory_key_to_retrieve) # retrieve_user_memory returns a dict
                if memory_data_dict and memory_data_dict.get("success") and "value" in memory_data_dict:
                    content_value = memory_data_dict["value"]
                    retrieved_memories_content.append(content_value) # Append the actual value
                    logger.debug(f"[MEMORY_PROACTIVE] Appended content for key '{key[0]}': '{str(content_value)[:70]}...'") 
                elif memory_data_dict and not memory_data_dict.get("success"):
                     logger.warning(f"[MEMORY_PROACTIVE] Failed to retrieve content for memory key {key[0]}: {memory_data_dict.get('message', 'Unknown error')}")
                else:
                    logger.warning(f"[MEMORY_PROACTIVE] No content found or unexpected structure for memory key {key[0]} when retrieving.")            
            logger.info(f"[MEMORY_PROACTIVE] Successfully retrieved content for {len(retrieved_memories_content)} memories.")
            return retrieved_memories_content

        except Exception as e:
            logger.error(f"[MEMORY_PROACTIVE] Error during proactive memory retrieval for user {user_id}: {e}", exc_info=True)
            return [] # Return empty list on error

MEMORY_BACKEND = os.environ.get("MEMORY_BACKEND", "simple").lower()

if MEMORY_BACKEND == "mcp":
    from mcp_memory import MCPMemoryServer
    memory_server = MCPMemoryServer()
else:
    memory_server = SimpleMemoryServer()