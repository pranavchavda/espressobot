
"""
Test script to directly query MCP servers and see their raw output
"""
import asyncio
import json
import sys
from mcp_server import mcp_server, perplexity_mcp_server

async def test_shopify_dev_docs(query):
    """Test the Shopify dev docs search"""
    print(f"Testing search_dev_docs with query: {query}")
    try:
        result = await mcp_server.search_dev_docs(query)
        print("\nRaw result type:", type(result))
        print("Raw result attributes:", dir(result))
        
        # Print the raw result
        print("\n--- Raw Result ---")
        print(result)
        
        # Convert to dictionary if needed
        if hasattr(result, 'meta') or hasattr(result, 'content'):
            print("\n--- Converting to Dictionary ---")
            res = {}
            if hasattr(result, 'meta'):
                res["meta"] = result.meta
                print("Meta:", result.meta)
            if hasattr(result, 'content'):
                print("\nContent items:", len(result.content))
                res["content"] = []
                for i, c in enumerate(result.content):
                    print(f"\nContent item {i}:")
                    print(f"  Type: {getattr(c, 'type', None)}")
                    print(f"  Text length: {len(getattr(c, 'text', ''))} chars")
                    print(f"  Text snippet: {getattr(c, 'text', '')[:100]}...")
                    res["content"].append({
                        "type": getattr(c, "type", None),
                        "text": getattr(c, "text", None),
                        "annotations": getattr(c, "annotations", None)
                    })
            if hasattr(result, 'isError'):
                res["isError"] = result.isError
                print("isError:", result.isError)
            
            # Try to convert to JSON
            try:
                json_str = json.dumps(res)
                print("\nJSON serialization successful")
                print(f"JSON length: {len(json_str)} characters")
            except Exception as e:
                print(f"\nJSON serialization failed: {e}")
    except Exception as e:
        print(f"Error testing search_dev_docs: {e}")

async def test_introspect_admin_schema(query):
    """Test the introspect admin schema tool"""
    print(f"Testing introspect_admin_schema with query: {query}")
    try:
        result = await mcp_server.introspect_admin_schema(query)
        print("\nRaw result type:", type(result))
        print("Raw result attributes:", dir(result))
        
        # Print the raw result
        print("\n--- Raw Result ---")
        print(result)
        
        # Convert to dictionary if needed
        if hasattr(result, 'meta') or hasattr(result, 'content'):
            print("\n--- Converting to Dictionary ---")
            res = {}
            if hasattr(result, 'meta'):
                res["meta"] = result.meta
                print("Meta:", result.meta)
            if hasattr(result, 'content'):
                print("\nContent items:", len(result.content))
                res["content"] = []
                for i, c in enumerate(result.content):
                    print(f"\nContent item {i}:")
                    print(f"  Type: {getattr(c, 'type', None)}")
                    print(f"  Text length: {len(getattr(c, 'text', ''))} chars")
                    print(f"  Text snippet: {getattr(c, 'text', '')[:100]}...")
                    res["content"].append({
                        "type": getattr(c, "type", None),
                        "text": getattr(c, "text", None),
                        "annotations": getattr(c, "annotations", None)
                    })
            if hasattr(result, 'isError'):
                res["isError"] = result.isError
                print("isError:", result.isError)
            
            # Try to convert to JSON
            try:
                json_str = json.dumps(res)
                print("\nJSON serialization successful")
                print(f"JSON length: {len(json_str)} characters")
            except Exception as e:
                print(f"\nJSON serialization failed: {e}")
    except Exception as e:
        print(f"Error testing introspect_admin_schema: {e}")

async def test_perplexity(query):
    """Test the Perplexity Ask tool"""
    print(f"Testing perplexity_ask with query: {query}")
    try:
        messages = [{"role": "user", "content": query}]
        result = await perplexity_mcp_server.perplexity_ask(messages)
        print("\nRaw result type:", type(result))
        print("Raw result attributes:", dir(result))
        
        # Print the raw result
        print("\n--- Raw Result ---")
        print(result)
        
        # Convert to dictionary if needed
        if hasattr(result, 'meta') or hasattr(result, 'content'):
            print("\n--- Converting to Dictionary ---")
            res = {}
            if hasattr(result, 'meta'):
                res["meta"] = result.meta
                print("Meta:", result.meta)
            if hasattr(result, 'content'):
                print("\nContent items:", len(result.content))
                res["content"] = []
                for i, c in enumerate(result.content):
                    print(f"\nContent item {i}:")
                    print(f"  Type: {getattr(c, 'type', None)}")
                    print(f"  Text length: {len(getattr(c, 'text', ''))} chars")
                    print(f"  Text snippet: {getattr(c, 'text', '')[:100]}...")
                    res["content"].append({
                        "type": getattr(c, "type", None),
                        "text": getattr(c, "text", None),
                        "annotations": getattr(c, "annotations", None)
                    })
            if hasattr(result, 'isError'):
                res["isError"] = result.isError
                print("isError:", result.isError)
            
            # Try to convert to JSON
            try:
                json_str = json.dumps(res)
                print("\nJSON serialization successful")
                print(f"JSON length: {len(json_str)} characters")
            except Exception as e:
                print(f"\nJSON serialization failed: {e}")
    except Exception as e:
        print(f"Error testing perplexity_ask: {e}")

async def main():
    if len(sys.argv) < 3:
        print("Usage: python test_mcp.py [tool] [query]")
        print("Tools: search_dev_docs, introspect_admin_schema, perplexity_ask")
        return
    
    tool = sys.argv[1]
    query = sys.argv[2]
    
    if tool == "search_dev_docs":
        await test_shopify_dev_docs(query)
    elif tool == "introspect_admin_schema":
        await test_introspect_admin_schema(query)
    elif tool == "perplexity_ask":
        await test_perplexity(query)
    else:
        print(f"Unknown tool: {tool}")
        print("Available tools: search_dev_docs, introspect_admin_schema, perplexity_ask")

if __name__ == "__main__":
    asyncio.run(main())
