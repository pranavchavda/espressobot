"""
Memory service module for managing user-specific memories.

This service provides an interface for storing and retrieving user memories
using the MCP memory server.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Union
from mcp_memory import get_mcp_memory_server

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Ensure DEBUG messages are processed by this logger

class MemoryService:
    """
    Service for managing user memories using the MCPMemoryServer.
    """
    
    @staticmethod
    async def store_memory(user_id: int, key: str, value: Any) -> Dict[str, Any]:
        """
        Store a memory for a specific user using the MCP memory server.
        
        Args:
            user_id: The user's ID
            key: Memory key
            value: Memory value (will be JSON serialized if not a string)
            
        Returns:
            Dict with operation status from the MCP memory server.
        """
        current_value = value
        value_type_name = type(current_value).__name__
        logger.debug(f"MemoryService: store_memory for key '{key}', initial value type: {value_type_name}")

        # Phase 1: Attempt to extract primitive string if 'current_value' is a known OpenAI SDK text object.
        # Handles types like TextContent, TextContentBlock, Text by checking common attributes.
        if value_type_name in ["TextContent", "TextContentBlock", "Text"]:
            extracted_text_from_sdk_object = None
            if hasattr(current_value, 'text'):  # Common for TextContentBlock
                text_attr = current_value.text
                if hasattr(text_attr, 'value') and isinstance(text_attr.value, str):
                    extracted_text_from_sdk_object = text_attr.value
                elif isinstance(text_attr, str):
                    extracted_text_from_sdk_object = text_attr
            elif hasattr(current_value, 'value') and isinstance(current_value.value, str):  # Common for Text
                extracted_text_from_sdk_object = current_value.value
            
            if extracted_text_from_sdk_object is not None:
                logger.debug(f"Extracted string '{extracted_text_from_sdk_object}' from {value_type_name} for key '{key}'")
                current_value = extracted_text_from_sdk_object # current_value is now a string
            else:
                logger.warning(f"{value_type_name} for key '{key}' did not yield a primitive string via common paths. Will proceed with original object for serialization or stringification.")
                # current_value remains the original SDK object

        # Phase 2: Ensure 'final_value_as_string' is a string. This string will be passed to MCPMemoryServer.
        final_value_as_string = None
        if isinstance(current_value, str):
            final_value_as_string = current_value
        else:
            # current_value is not a string. It could be a dict/list (intended as JSON value),
            # or an unhandled complex object (e.g., an SDK object if Phase 1 didn't convert it).
            try:
                # This will succeed for basic types like dict, list, int, float, bool.
                # It will fail with TypeError for non-serializable objects like TextContent if it's still here.
                logger.debug(f"Value for key '{key}' (type: {type(current_value).__name__}) is not a string. Attempting json.dumps to store its JSON string representation.")
                final_value_as_string = json.dumps(current_value)
            except TypeError as te:
                logger.warning(f"json.dumps failed for key '{key}' (type: {type(current_value).__name__}): {te}. This usually means it's a non-JSON-serializable object. Falling back to str().")
                logger.debug(f"REPR of object causing json.dumps failure for key '{key}': {repr(current_value)}")
                final_value_as_string = str(current_value) # Ultimate fallback: string representation of the object.
            except Exception as e:
                logger.error(f"Unexpected error during json.dumps for key '{key}' (type: {type(current_value).__name__}): {e}. Falling back to str().")
                final_value_as_string = str(current_value)

        # Final check: Ensure it's unequivocally a string before sending to MCP layer.
        if not isinstance(final_value_as_string, str):
            logger.error(f"CRITICAL_MEMORY_SERVICE: final_value_as_string for key '{key}' is NOT a string (type: {type(final_value_as_string).__name__}) after all processing. Forcing to string. THIS IS UNEXPECTED.")
            final_value_as_string = str(final_value_as_string)

        logger.debug(f"MemoryService: final_value_as_string for key '{key}' (type: {type(final_value_as_string).__name__}) before sending to MCP: {final_value_as_string[:200]}")
        
        # Store in MCP memory server (which expects final_value_as_string to be a string)
        # Try to pass current Flask app if available
        try:
            from flask import current_app
            mcp_server = get_mcp_memory_server(flask_app=current_app)
        except:
            mcp_server = get_mcp_memory_server()
        mcp_result = await mcp_server.store_user_memory(str(user_id), key, final_value_as_string)
        
        # Directly return the result from MCP memory server call
        # The 'success', 'key', 'error', 'message' fields are expected from memory_mcp_server
        return mcp_result
    
    @staticmethod
    async def retrieve_memory(user_id: int, key: str, default: Any = None) -> Dict[str, Any]:
        """
        Retrieve a memory for a specific user from the MCP memory server.
        
        Args:
            user_id: The user's ID
            key: Memory key to retrieve
            default: Default value if memory not found
            
        Returns:
            Dict with memory value or default, and source as 'memory_server'.
        """
        # Retrieve from MCP memory server
        # Note: mcp_memory.get_user_memory does not take a 'default' argument.
        # Default handling is managed below based on the success and value from mcp_result.
        try:
            from flask import current_app
            mcp_server = get_mcp_memory_server(flask_app=current_app)
        except:
            mcp_server = get_mcp_memory_server()
        mcp_result = await mcp_server.get_user_memory(str(user_id), key)
        
        # The mcp_result should contain 'success', 'key', 'value', and optionally 'error' or 'message'.
        # We will add/ensure 'source' is present.
        
        response = {
            "success": mcp_result.get("success", False),
            "key": key,
            "value": mcp_result.get("value", default),
            "source": "memory_server" # Always from memory_server now
        }
        
        if not response["success"]:
            response["error"] = mcp_result.get("error") or mcp_result.get("message") or "Failed to retrieve from MCP memory server."
            if response["value"] is default and default is None: # If it failed and value is still default (None)
                response["source"] = "not_found"
        elif mcp_result.get("message"):
            response["message"] = mcp_result.get("message")
        
        # Attempt to parse JSON if value is a string that looks like JSON
        value_to_check = response["value"]
        if isinstance(value_to_check, str) and value_to_check.strip().startswith(("{", "[")):
            try:
                response["value"] = json.loads(value_to_check)
            except json.JSONDecodeError:
                # Not valid JSON, keep as string. No error needed, it's just a string value.
                pass
        
        return response
    
    @staticmethod
    async def list_memories(user_id: int) -> Dict[str, Any]:
        """
        List all memories for a user from the MCP memory server.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict with operation status and list of memory keys from the MCP memory server.
        """
        # List keys from MCP memory server
        try:
            from flask import current_app
            mcp_server = get_mcp_memory_server(flask_app=current_app)
        except:
            mcp_server = get_mcp_memory_server()
        return await mcp_server.list_user_memories(str(user_id))
        
    @staticmethod
    async def delete_memory(user_id: int, key: str) -> Dict[str, Any]:
        """
        Delete a memory for a user from the MCP memory server.
        
        Args:
            user_id: The user's ID
            key: Memory key to delete
            
        Returns:
            Dict with operation status from the MCP memory server.
        """
        # Delete from MCP memory server
        try:
            from flask import current_app
            mcp_server = get_mcp_memory_server(flask_app=current_app)
        except:
            mcp_server = get_mcp_memory_server()
        return await mcp_server.delete_user_memory(str(user_id), key)
    
    @staticmethod
    async def proactively_retrieve_memories(user_id: int, query_text: str, top_n: int = 5) -> List[str]:
        """
        Proactively retrieves relevant memories for a user based on query_text.
        
        Args:
            user_id: The user's ID.
            query_text: The text to find relevant memories for.
            top_n: The maximum number of memories to retrieve.
            
        Returns:
            A list of memory content strings.
        """
        logger.info(f"MemoryService: Proactively retrieving memories for user {user_id} based on query: '{query_text[:50]}...'" )
        try:
            try:
                from flask import current_app
                mcp_server = get_mcp_memory_server(flask_app=current_app)
            except:
                mcp_server = get_mcp_memory_server()
            retrieved_contents = await mcp_server.proactively_retrieve_memories(str(user_id), query_text, top_n)
            logger.info(f"MemoryService: Retrieved {len(retrieved_contents)} memories proactively for user {user_id}.")
            return retrieved_contents
        except Exception as e:
            logger.error(f"MemoryService: Error during proactive memory retrieval for user {user_id}: {e}", exc_info=True)
            return [] # Return empty list on error

# Create a singleton instance
memory_service = MemoryService()