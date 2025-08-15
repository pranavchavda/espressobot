#!/usr/bin/env python3
"""Test MCP tools directly without LangGraph"""
import asyncio
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_mcp_direct():
    """Test calling MCP server directly"""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    
    try:
        # Initialize MCP client
        client = MultiServerMCPClient({
            "products": {
                "command": "python3",
                "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-products-server.py"))],
                "transport": "stdio",
                "env": {
                    **os.environ,
                    "PYTHONPATH": "/home/pranav/espressobot/frontend/python-tools"
                }
            }
        })
        
        # Get tools
        tools = await client.get_tools()
        logger.info(f"Got {len(tools)} tools from MCP")
        
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description[:50]}...")
        
        # Try to call search_products
        search_tool = None
        for tool in tools:
            if tool.name == "search_products":
                search_tool = tool
                break
        
        if search_tool:
            logger.info("Found search_products tool, attempting to call...")
            try:
                result = await search_tool._arun(query="Breville Barista Express")
                logger.info(f"Result: {str(result)[:200]}...")
                return True
            except Exception as e:
                logger.error(f"Failed to call tool: {e}")
                return False
        else:
            logger.error("search_products tool not found!")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize MCP: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_direct())
    print(f"\n{'✅' if success else '❌'} Test {'passed' if success else 'failed'}")