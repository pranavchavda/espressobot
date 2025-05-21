"""
Adapter layer for normalizing responses from the memory MCP server to ensure consistent agent behavior.
"""
import asyncio
from typing import Any, Callable, Awaitable, Dict

# Utility: Normalize memory MCP server responses to a standard format
async def normalized_memory_call(method: Callable[..., Awaitable[Any]], *args, **kwargs) -> Dict:
    """
    Calls the given memory MCP server method, normalizing the result to always provide a 'content' field like other MCPs.
    """
    try:
        result = await method(*args, **kwargs)
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Memory MCP error: {str(e)}"
            }],
            "isError": True
        }

    # If already in the expected format, return as-is
    if isinstance(result, dict) and "content" in result:
        return result

    # If it's a known memory MCP structure with 'success' and 'error'
    if isinstance(result, dict):
        if not result.get("success", True):
            text = result.get("error") or "Unknown memory MCP error."
            return {
                "content": [{"type": "text", "text": text}],
                "isError": True
            }
        # If it's a memory value
        if "value" in result:
            return {
                "content": [{"type": "text", "text": str(result["value"])}],
                "isError": False
            }
        # If it's a list of keys or similar
        if "keys" in result:
            text = ", ".join(result["keys"])
            return {
                "content": [{"type": "text", "text": text}],
                "isError": False
            }
    # Fallback: dump the result as text
    return {
        "content": [{"type": "text", "text": str(result)}],
        "isError": False
    }
