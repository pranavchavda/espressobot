"""
Script to test available tools in the Shopify Features MCP server.
"""
import asyncio
import os
from mcp_server import shopify_features_mcp_server
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def list_available_tools():
    print("=== Testing MCP Server Connection ===")
    
    try:
        # Try to get the list of available tools
        print("\nAttempting to list available tools...")
        
        # We'll use the search_products method as a test
        print("\n1. Testing search_products...")
        search_results = await shopify_features_mcp_server.search_products("test")
        print(f"Search results: {search_results}")
        
        if search_results.get('products'):
            product_id = search_results['products'][0]['id']
            print(f"\n2. Found product ID: {product_id}")
            
            # Test get_product
            print("\n3. Testing get_product...")
            product_details = await shopify_features_mcp_server.get_product(product_id)
            print(f"Product details: {product_details}")
            
            # Test list_feature_boxes
            print("\n4. Testing list_feature_boxes...")
            feature_boxes = await shopify_features_mcp_server.list_feature_boxes(product_id)
            print(f"Feature boxes: {feature_boxes}")
            
            # Test create_feature_box
            print("\n5. Testing create_feature_box...")
            try:
                new_box = await shopify_features_mcp_server.create_feature_box(
                    product_id=product_id,
                    title="Test Feature Box",
                    text="This is a test feature box.",
                    image_url="https://cdn.shopify.com/s/files/1/0000/0000/files/example.jpg"
                )
                print(f"Created feature box: {new_box}")
            except Exception as e:
                print(f"Error creating feature box: {e}")
                
            # List feature boxes again to confirm
            print("\n6. Listing feature boxes after creation...")
            updated_boxes = await shopify_features_mcp_server.list_feature_boxes(product_id)
            print(f"Updated feature boxes: {updated_boxes}")
        
    except Exception as e:
        print(f"Error testing MCP server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["SHOPIFY_ACCESS_TOKEN", "SHOPIFY_SHOP_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file and try again.")
    else:
        asyncio.run(list_available_tools())
