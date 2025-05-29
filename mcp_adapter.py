"""
Compatibility module for MCP adapter.
Redirects to the new services implementation.
"""
# This file provides compatibility with the old MCP adapter interface
# It's not needed for the new services architecture but is kept for backward compatibility

# Import all services from the compatibility layer
from services.compatibility import (
    memory_server,
    fetch_mcp_server,
    shopify_mcp_server,
    thinking_mcp_server,
    filesystem_mcp_server
)

# Provide the same interface as the original module
def get_mcp_adapter(adapter_type, *args, **kwargs):
    """
    Get an MCP adapter instance of the specified type.
    Redirects to the appropriate service in the compatibility layer.
    """
    if adapter_type == "memory":
        return memory_server
    elif adapter_type == "fetch":
        return fetch_mcp_server
    elif adapter_type == "shopify":
        return shopify_mcp_server
    elif adapter_type == "thinking":
        return thinking_mcp_server
    elif adapter_type == "filesystem":
        return filesystem_mcp_server
    else:
        raise ValueError(f"Unknown MCP adapter type: {adapter_type}")

# Add the missing normalized_memory_call function
def normalized_memory_call(user_id, key, value=None, operation="get"):
    """
    Normalized interface for memory operations.
    
    Args:
        user_id: User identifier
        key: Memory key
        value: Optional value for store operations
        operation: Operation type (get, store, delete, list)
        
    Returns:
        Operation result
    """
    import asyncio
    
    async def _async_memory_call():
        if operation == "get":
            return await memory_server.retrieve_memory(user_id, key)
        elif operation == "store":
            return await memory_server.store_memory(user_id, key, value)
        elif operation == "delete":
            return await memory_server.delete_memory(user_id, key)
        elif operation == "list":
            return await memory_server.list_memories(user_id)
        else:
            raise ValueError(f"Unknown memory operation: {operation}")
    
    # Run the async function in the event loop
    return asyncio.run(_async_memory_call())
