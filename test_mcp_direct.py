"""
Direct test of the Shopify Features MCP server.
"""
import os
import asyncio
from dotenv import load_dotenv
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

# Load environment variables
load_dotenv()

async def test_mcp_server():
    print("=== Testing MCP Server Directly ===")
    
    # Get environment variables
    shopify_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    shop_url = os.getenv("SHOPIFY_SHOP_URL")
    
    if not shopify_token or not shop_url:
        print("Error: Missing required environment variables")
        return
    
    # Set up MCP server parameters
    params = {
        "command": "npx",
        "args": ["-y", "@pranavchavda/shopify-feature-box-mcp"],
        "env": {
            "SHOPIFY_ACCESS_TOKEN": shopify_token,
            "SHOPIFY_SHOP_URL": shop_url
        }
    }
    
    try:
        print("Starting MCP server...")
        async with stdio_client(StdioServerParameters(**params)) as client:
            session = ClientSession(client)
            
            # List available tools
            print("\nListing available tools...")
            tools = await client.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")
            
            # Test search_products
            print("\nTesting search_products...")
            result = await session.call_tool(
                "search_products",
                {"query": "test"}
            )
            print(f"Search results: {result}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
