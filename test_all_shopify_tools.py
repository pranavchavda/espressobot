"""
Test script for all Shopify Features MCP tools.
"""
import asyncio
import json
import os
from dotenv import load_dotenv
from mcp_server import shopify_features_mcp_server

# Load environment variables
load_dotenv()

async def test_all_tools():
    print("=== Testing All Shopify Features MCP Tools ===\n")
    product_id_for_cleanup = None
    
    try:
        # Test 1: Create a new product
        print("1. Testing product_create...")
        product_title_suffix = os.urandom(4).hex()
        product_sku_suffix = os.urandom(4).hex()
        new_product_payload = {
            "title": f"Test Product {product_title_suffix}",
            "vendor": "Test Vendor",
            "productType": "Test Type",
            "bodyHtml": "<p>This is a test product created via MCP server.</p>",
            "tags": ["test", "mcp-test"],
            "variantPrice": "19.99",
            "variantSku": f"TEST-{product_sku_suffix}",
            "variantPreviewName": "Default Title"
        }
        new_product = await shopify_features_mcp_server.product_create(**new_product_payload)
        print(f"Response from product_create: {json.dumps(new_product, indent=2)}")
        
        if not new_product or not new_product.get('success') or not new_product.get('data'):
            print("❌ Failed to create product or invalid response format.")
            return
        
        product_data = new_product['data']
        product_id = product_data.get('productId')
        # The product_create response gives productId like "gid://shopify/Product/NUMBER"
        # Other tools might expect just the NUMBER part.
        # Let's extract the number if it's in GID format for future use.
        if product_id and product_id.startswith("gid://shopify/Product/"):
            product_id_numeric = product_id.split('/')[-1]
        else:
            product_id_numeric = product_id # Assume it's already numeric if not GID
            
        variant_id = product_data.get('variantId')
        product_id_for_cleanup = product_id_numeric # For potential cleanup later

        if not product_id_numeric or not variant_id:
            print("❌ Missing product_id_numeric or variant_id in response from product_create.")
            return
        print(f"✅ product_create successful! Product ID (Numeric): {product_id_numeric}, Variant ID: {variant_id}")

        # Test 2: Get the created product
        print("\n2. Testing get_product...")
        retrieved_product = await shopify_features_mcp_server.get_product(product_id_numeric)
        print(f"Response from get_product: {json.dumps(retrieved_product, indent=2)}")
        if not retrieved_product or not retrieved_product.get('success') or not retrieved_product.get('data'):
            print("❌ Failed to get product or invalid response format.")
            # Continue to other tests if this fails
        else:
            print("✅ get_product successful!")
            assert retrieved_product['data']['id'] == product_id # Check if GIDs match
            assert retrieved_product['data']['title'] == new_product_payload['title']

        # Test 3: Add tags to the product
        print("\n3. Testing product_tags_add...")
        add_tags_result = await shopify_features_mcp_server.product_tags_add(
            productId=product_id_numeric,
            tags=["test-tag-1", "test-tag-2"]
        )
        print(f"Response from product_tags_add: {json.dumps(add_tags_result, indent=2)}")
        if not add_tags_result or not add_tags_result.get('success'):
            print("❌ Failed to add tags.")
        else:
            print("✅ product_tags_add successful!")

        # Test 4: Remove one of the tags
        print("\n4. Testing product_tags_remove...")
        remove_tags_result = await shopify_features_mcp_server.product_tags_remove(
            productId=product_id_numeric,
            tags=["test-tag-1"]
        )
        print(f"Response from product_tags_remove: {json.dumps(remove_tags_result, indent=2)}")
        if not remove_tags_result or not remove_tags_result.get('success'):
            print("❌ Failed to remove tags.")
        else:
            print("✅ product_tags_remove successful!")

        # Test 5: Update the product
        print("\n5. Testing product_update...")
        updated_product_title = f"Updated Product {os.urandom(4).hex()}"
        update_payload = {
            "variantId": variant_id.split('/')[-1] if variant_id and variant_id.startswith("gid://shopify/ProductVariant/") else variant_id,
            "title": updated_product_title,
            "price": "24.99",
            "status": "ACTIVE" # Ensure this is a valid status
        }
        update_result = await shopify_features_mcp_server.product_update(**update_payload)
        print(f"Response from product_update: {json.dumps(update_result, indent=2)}")
        if not update_result or not update_result.get('success'):
            print("❌ Failed to update product.")
        else:
            print("✅ product_update successful!")
            # Verify with get_product again
            print("Verifying update with get_product...")
            verify_product = await shopify_features_mcp_server.get_product(product_id_numeric)
            if verify_product and verify_product.get('success') and verify_product.get('data'):
                assert verify_product['data']['title'] == updated_product_title
                assert verify_product['data']['status'].lower() == 'active'
                # Price check might need to look into variants
                print("✅ Product update verified!")
            else:
                print("⚠️ Could not verify product update via get_product.")

        # Test 6: Create a feature box for the product
        print("\n6. Testing create_feature_box...")
        feature_box_result = await shopify_features_mcp_server.create_feature_box(
            product_id=product_id_numeric,
            title="Premium Quality Feature",
            text="This product boasts premium quality, tested rigorously.",
            image_url="https://cdn.shopify.com/s/files/1/0000/0000/files/example_feature.jpg"
        )
        print(f"Response from create_feature_box: {json.dumps(feature_box_result, indent=2)}")
        if not feature_box_result or not feature_box_result.get('success'):
            print("❌ Failed to create feature box.")
        else:
            print("✅ create_feature_box successful!")
            
        # Test 7: Search for the product
        print("\n7. Testing search_products...")
        search_results = await shopify_features_mcp_server.search_products(query=updated_product_title) # Search by updated title
        print(f"Response from search_products: {json.dumps(search_results, indent=2)}")
        found = False
        if search_results and search_results.get('success') and search_results.get('data'):
            for product in search_results['data']:
                if product.get('id') == product_id:
                    found = True
                    break
        if found:
            print(f"✅ search_products successful! Found product {product_id}.")
        else:
            print(f"⚠️ search_products did not find the product {product_id} by its new title, or error in search.")

        print("\n🎉🎉🎉 All tests completed! 🎉🎉🎉")
        
    except Exception as e:
        print(f"❌ An unexpected error occurred during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Optional: Add cleanup logic here if needed, e.g., delete the test product
        # For now, we'll just note the ID if a product was created.
        if product_id_for_cleanup:
            print(f"\nℹ️ Test product created with ID (Numeric): {product_id_for_cleanup}. Manual cleanup might be needed.")

if __name__ == "__main__":
    asyncio.run(test_all_tools())
