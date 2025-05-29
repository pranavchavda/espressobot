"""
Compatibility module for MCP memory server.
Redirects to the new services implementation.
"""
from services.compatibility import memory_server

# Provide the same interface as the original module
def get_mcp_memory_server():
    return memory_server

# Export the memory server instance directly
memory_service = memory_server
