"""
Test script for ShopifyFeaturesMCPServer.
This script demonstrates how to use all available tools in the ShopifyFeaturesMCPServer.
"""
import asyncio
import os
import uuid
from datetime import datetime
from mcp_server import shopify_features_mcp_server
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def test_product_operations():
    print("\n=== Testing Product Operations ===")
    
    # Generate a unique product title
    test_suffix = str(uuid.uuid4())[:8]
    product_title = f"Test Product {test_suffix}"
    
    try:
        # 1. Create a new product
        print("\n1. Creating a new product...")
        new_product = await shopify_features_mcp_server.product_create(
            title=product_title,
            vendor="Test Vendor",
            productType="Test Type",
            bodyHtml="<p>This is a test product created via MCP server.</p>",
            tags=["test", "mcp-test"],
            variantPrice="19.99",
            variantSku=f"TEST-{test_suffix}",
            variantPreviewName="Default Title"
        )
        
        if not new_product or 'success' not in new_product or not new_product['success']:
            print(f"Failed to create product: {new_product}")
            return None
            
        product_id = new_product.get('product', {}).get('id')
        variant_id = new_product.get('product', {}).get('variants', [{}])[0].get('id')
        print(f"Created product ID: {product_id}, Variant ID: {variant_id}")
        
        # 2. Add tags to the product
        print("\n2. Adding tags to the product...")
        add_tags = await shopify_features_mcp_server.product_tags_add(
            productId=product_id,
            tags=["new-tag-1", "new-tag-2"]
        )
        print(f"Add tags result: {add_tags}")
        
        # 3. Update product details
        print("\n3. Updating product details...")
        update_result = await shopify_features_mcp_server.product_update(
            variantId=variant_id,
            title=f"Updated {product_title}",
            description="<p>This product has been updated via MCP server.</p>",
            price="24.99"
        )
        print(f"Update result: {update_result}")
        
        # 4. Remove one of the tags
        print("\n4. Removing a tag from the product...")
        remove_tags = await shopify_features_mcp_server.product_tags_remove(
            productId=product_id,
            tags=["new-tag-1"]
        )
        print(f"Remove tags result: {remove_tags}")
        
        return product_id
        
    except Exception as e:
        print(f"Error in product operations: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_feature_boxes(product_id):
    print("\n=== Testing Feature Box Operations ===")
    
    if not product_id:
        print("No product ID provided for feature box tests")
        return
        
    try:
        # 1. List existing feature boxes
        print("\n1. Listing feature boxes...")
        feature_boxes = await shopify_features_mcp_server.list_feature_boxes(product_id)
        print(f"Existing feature boxes: {feature_boxes}")
        
        # 2. Create a new feature box
        print("\n2. Creating a test feature box...")
        test_box = await shopify_features_mcp_server.create_feature_box(
            product_id=product_id,
            title="Premium Quality",
            text="This product is made with the finest materials.",
            image_url="https://cdn.shopify.com/s/files/1/0000/0000/files/example.jpg"
        )
        print(f"Created feature box: {test_box}")
        
        # 3. Verify the new feature box was added
        print("\n3. Verifying feature box was added...")
        updated_boxes = await shopify_features_mcp_server.list_feature_boxes(product_id)
        print(f"Updated feature boxes: {updated_boxes}")
        
    except Exception as e:
        print(f"Error in feature box operations: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_search_operations():
    print("\n=== Testing Search Operations ===")
    
    try:
        # 1. Search for products
        print("\n1. Searching for products...")
        search_results = await shopify_features_mcp_server.search_products("test")
        print(f"Search results count: {len(search_results.get('products', []))}")
        
        if search_results.get('products'):
            # 2. Get details of the first product
            product_id = search_results['products'][0]['id']
            print(f"\n2. Getting details for product ID: {product_id}")
            product_details = await shopify_features_mcp_server.get_product(product_id)
            print(f"Product title: {product_details.get('product', {}).get('title')}")
            
            return product_id
            
    except Exception as e:
        print(f"Error in search operations: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return None

async def test_shopify_features_mcp():
    print("=== Starting Shopify Features MCP Server Tests ===")
    
    # Test product creation and manipulation
    product_id = await test_product_operations()
    
    # Test feature boxes with the created product
    await test_feature_boxes(product_id)
    
    # Test search and retrieval operations
    await test_search_operations()
    
    print("\n=== Test Sequence Completed ===")

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["SHOPIFY_ACCESS_TOKEN", "SHOPIFY_SHOP_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file and try again.")
    else:
        asyncio.run(test_shopify_features_mcp())
