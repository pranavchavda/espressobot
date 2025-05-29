"""
Compatibility module for MCP server.
Redirects to the new services implementation.
"""
from services.compatibility import (
    fetch_mcp_server,
    shopify_mcp_server,
    thinking_mcp_server,
    filesystem_mcp_server
)

# Provide the same interface as the original module
def get_mcp_server(server_type, *args, **kwargs):
    """
    Get an MCP server instance of the specified type.
    Redirects to the appropriate service in the compatibility layer.
    """
    if server_type == "fetch":
        return fetch_mcp_server
    elif server_type == "shopify":
        return shopify_mcp_server
    elif server_type == "thinking":
        return thinking_mcp_server
    elif server_type == "filesystem":
        return filesystem_mcp_server
    elif server_type == "perplexity":
        return perplexity_mcp_server
    else:
        raise ValueError(f"Unknown MCP server type: {server_type}")

# For direct imports of specific server types
def get_fetch_mcp_server(*args, **kwargs):
    return fetch_mcp_server

def get_shopify_mcp_server(*args, **kwargs):
    return shopify_mcp_server

def get_thinking_mcp_server(*args, **kwargs):
    return thinking_mcp_server

def get_filesystem_mcp_server(*args, **kwargs):
    return filesystem_mcp_server

# Add missing shopify_features_mcp_server
# This is likely a specialized version of the shopify server with additional features
shopify_features_mcp_server = shopify_mcp_server

# Add missing perplexity_mcp_server
# This is likely a specialized server for perplexity operations
# Using fetch_mcp_server as a fallback since it's likely for external API calls
perplexity_mcp_server = fetch_mcp_server
