"""
Module for handling MCP server connections for Shopify Dev MCP
"""
import os
import asyncio
from agents.mcp.server import MCPServerStdio
import httpx
from typing import Dict, Any, List, Optional

class ShopifyMCPServer:
    """
    A class to handle communication with a local Shopify Dev MCP server instance.
    This spawns an npx process running @shopify/dev-mcp to provide schema information
    and documentation search capabilities.
    """
    def __init__(self):
        # Params for local Shopify Dev MCP server
        self.params = {"command": "npx", "args": ["-y", "@shopify/dev-mcp@latest"]}
        self.cache = True
    
    async def introspect_admin_schema(self, query, filter_types=None):
        """Query the Shopify Admin API schema using the MCP server"""
        if filter_types is None:
            filter_types = ["all"]
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            return await server.call_tool(
                "introspect_admin_schema", {"query": query, "filter": filter_types}
            )
    
    async def search_dev_docs(self, prompt):
        """Search Shopify developer documentation using the MCP server"""
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            return await server.call_tool(
                "search_dev_docs", {"prompt": prompt}
            )
    
    def stop(self):
        """Stop the MCP server process (no-op; context manager handles teardown)"""
        pass

# Create a singleton instance
mcp_server = ShopifyMCPServer()
