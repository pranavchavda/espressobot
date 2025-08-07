"""
Example of MCP (Model Context Protocol) integration with LangGraph.
Shows how to connect to existing MCP servers and use them in agents.
"""

import asyncio
import json
from typing import Dict, List, Any
from pathlib import Path
from langchain_community.tools import MCPClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages connections to all MCP servers"""
    
    def __init__(self):
        self.base_path = Path("/home/pranav/espressobot/frontend/python-tools")
        self.servers = {}
        self.tools_by_server = {}
        
        # Define all MCP servers
        self.server_configs = {
            "products": "mcp-products-server.py",
            "pricing": "mcp-pricing-server.py",
            "inventory": "mcp-inventory-server.py",
            "sales": "mcp-sales-server.py",
            "features": "mcp-features-server.py",
            "media": "mcp-media-server.py",
            "integrations": "mcp-integrations-server.py",
            "product_management": "mcp-product-management-server.py",
            "utility": "mcp-utility-server.py",
            "graphql": "mcp-graphql-server.py",
            "orders": "mcp-orders-server.py",
            "price_monitor": "mcp-price-monitor-server.py",
        }
        
    async def initialize_all(self):
        """Initialize all MCP servers"""
        
        logger.info("Initializing MCP servers...")
        
        for name, server_file in self.server_configs.items():
            try:
                await self.initialize_server(name, server_file)
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {e}")
                # Continue with other servers even if one fails
                
        logger.info(f"Initialized {len(self.servers)} MCP servers")
        
    async def initialize_server(self, name: str, server_file: str):
        """Initialize a single MCP server"""
        
        server_path = self.base_path / server_file
        
        if not server_path.exists():
            raise FileNotFoundError(f"MCP server not found: {server_path}")
            
        # Create MCP client
        client = MCPClient(f"stdio://{server_path}")
        
        # Initialize and test connection
        await client.initialize()
        
        # Get available tools
        tools = await client.get_tools()
        
        self.servers[name] = client
        self.tools_by_server[name] = tools
        
        logger.info(f"Initialized {name} with {len(tools)} tools")
        
    async def call_tool(self, server_name: str, tool_name: str, params: Dict[str, Any]):
        """Call a tool on a specific MCP server"""
        
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not initialized")
            
        client = self.servers[server_name]
        
        try:
            result = await client.call_tool(tool_name, params)
            return result
        except Exception as e:
            logger.error(f"Tool call failed: {server_name}.{tool_name} - {e}")
            raise
            
    def get_tools_for_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get all tools available on a server"""
        return self.tools_by_server.get(server_name, [])
        
    def find_tool(self, tool_name: str) -> tuple[str, Dict[str, Any]]:
        """Find which server has a specific tool"""
        
        for server_name, tools in self.tools_by_server.items():
            for tool in tools:
                if tool["name"] == tool_name:
                    return server_name, tool
                    
        return None, None
        
    async def close_all(self):
        """Close all MCP server connections"""
        
        for name, client in self.servers.items():
            try:
                await client.close()
                logger.info(f"Closed connection to {name}")
            except Exception as e:
                logger.error(f"Error closing {name}: {e}")


# Example: Tool Router for LangGraph
class MCPToolRouter:
    """Routes tool calls to appropriate MCP servers"""
    
    def __init__(self, mcp_manager: MCPServerManager):
        self.mcp_manager = mcp_manager
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool by finding the right server"""
        
        # Find which server has this tool
        server_name, tool = self.mcp_manager.find_tool(tool_name)
        
        if not server_name:
            raise ValueError(f"Tool {tool_name} not found in any MCP server")
            
        # Execute the tool
        result = await self.mcp_manager.call_tool(server_name, tool_name, params)
        
        return {
            "server": server_name,
            "tool": tool_name,
            "result": result
        }


# Example: Using MCP in a LangGraph Agent
class MCPEnabledAgent:
    """An agent that can use any MCP tool"""
    
    def __init__(self, mcp_manager: MCPServerManager):
        self.mcp_manager = mcp_manager
        self.router = MCPToolRouter(mcp_manager)
        
    async def process_request(self, request: str) -> str:
        """Process a request using MCP tools"""
        
        # This is simplified - in production, use an LLM to:
        # 1. Understand the request
        # 2. Select appropriate tools
        # 3. Extract parameters
        
        # Example: Handle a product search request
        if "search" in request.lower() and "product" in request.lower():
            result = await self.router.execute_tool(
                "search_products",
                {"query": request}
            )
            return f"Found products: {result}"
            
        # Example: Handle a price update request
        elif "update price" in request.lower():
            # Extract SKU and price from request (simplified)
            result = await self.router.execute_tool(
                "update_pricing",
                {
                    "product_id": "123",
                    "variant_id": "456",
                    "price": 99.99
                }
            )
            return f"Price updated: {result}"
            
        return "Request not understood"


# Example usage
async def main():
    """Example of using MCP servers with LangGraph"""
    
    # Initialize MCP manager
    mcp_manager = MCPServerManager()
    await mcp_manager.initialize_all()
    
    # Show available tools
    print("\nAvailable MCP Servers and Tools:")
    for server_name, tools in mcp_manager.tools_by_server.items():
        print(f"\n{server_name}:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    
    # Create an agent
    agent = MCPEnabledAgent(mcp_manager)
    
    # Process some requests
    test_requests = [
        "Search for espresso machines",
        "Update price for SKU ESP-001 to 699.99",
        "Check inventory for all products"
    ]
    
    print("\nProcessing test requests:")
    for request in test_requests:
        print(f"\nRequest: {request}")
        response = await agent.process_request(request)
        print(f"Response: {response}")
    
    # Cleanup
    await mcp_manager.close_all()


if __name__ == "__main__":
    asyncio.run(main())