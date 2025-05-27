"""
Simple test script for the Shopify Features MCP server.
"""
import os
import asyncio
import json
from mcp_server import shopify_features_mcp_server
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_mcp_server():
    print("=== Simple MCP Server Test ===")
    
    # Print environment variables for debugging
    print("Environment variables:")
    print(f"SHOPIFY_ACCESS_TOKEN: {'*' * 10}{os.getenv('SHOPIFY_ACCESS_TOKEN')[-4:] if os.getenv('SHOPIFY_ACCESS_TOKEN') else 'Not set'}")
    print(f"SHOPIFY_SHOP_URL: {os.getenv('SHOPIFY_SHOP_URL') or 'Not set'}")
    
    try:
        # Test search_products
        print("\n1. Testing search_products...")
        search_results = await shopify_features_mcp_server.search_products("test")
        print("Search results:")
        print(json.dumps(search_results, indent=2))
        
        if search_results.get('products'):
            product_id = search_results['products'][0]['id']
            print(f"\nFound product ID: {product_id}")
            
            # Test get_product
            print("\n2. Testing get_product...")
            product_details = await shopify_features_mcp_server.get_product(product_id)
            print("Product details:")
            print(json.dumps(product_details, indent=2))
            
            # Test list_feature_boxes
            print("\n3. Testing list_feature_boxes...")
            feature_boxes = await shopify_features_mcp_server.list_feature_boxes(product_id)
            print("Feature boxes:")
            print(json.dumps(feature_boxes, indent=2))
            
            # Test create_feature_box
            print("\n4. Testing create_feature_box...")
            new_box = await shopify_features_mcp_server.create_feature_box(
                product_id=product_id,
                title="Test Feature Box",
                text="This is a test feature box created via MCP server.",
                image_url="https://cdn.shopify.com/s/files/1/0000/0000/files/example.jpg"
            )
            print("Created feature box:")
            print(json.dumps(new_box, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
