#!/usr/bin/env python3
"""
Test script to verify SkuVault API connection
"""

import os
from skuvault_api import SkuVaultAPI

def test_connection():
    # Get credentials from environment
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing credentials. Please set:")
        print("  export SKUVAULT_TENANT_TOKEN='your_token'")
        print("  export SKUVAULT_USER_TOKEN='your_token'")
        return False
    
    print("Testing SkuVault API connection...")
    
    try:
        api = SkuVaultAPI(tenant_token, user_token)
        
        # Test with a sample SKU
        test_sku = input("Enter a test SKU (or press Enter to skip): ").strip()
        
        if test_sku:
            print(f"\nFetching data for SKU: {test_sku}")
            products = api.get_products([test_sku])
            
            if products:
                product = products[0]
                print(f"✓ Found product: {product.get('Description', 'No description')}")
                print(f"  Code: {product.get('Code', 'N/A')}")
                print(f"  Quantity Available: {product.get('QuantityAvailable', 0)}")
                
                # Test location lookup
                print("\nFetching location data...")
                locations = api.get_inventory_by_location([test_sku])
                
                if locations:
                    for loc in locations:
                        print(f"✓ Location: {loc.location}")
                        print(f"  Warehouse: {loc.warehouse}")
                        print(f"  Quantity: {loc.quantity_available}")
                else:
                    print("✗ No location data found")
            else:
                print(f"✗ Product not found: {test_sku}")
        else:
            print("✓ API connection successful!")
        
        return True
        
    except Exception as e:
        print(f"✗ API Error: {str(e)}")
        return False

if __name__ == "__main__":
    if test_connection():
        print("\n✓ All tests passed! Ready to build the application.")
    else:
        print("\n✗ Tests failed. Please check your credentials and try again.")