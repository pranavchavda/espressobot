#!/usr/bin/env python3
"""
Debug script to test SkuVault API endpoints
"""

import os
import json
import requests
from skuvault_api import SkuVaultAPI

def test_direct_api_call(tenant_token, user_token, sku):
    """Test direct API calls to understand response format"""
    
    print(f"\nTesting direct API calls for SKU: {sku}")
    print("=" * 50)
    
    # Test getProducts
    print("\n1. Testing getProducts endpoint...")
    url = "https://app.skuvault.com/api/products/getProducts"
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "ProductSKUs": [sku]
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response Keys: {list(result.keys())}")
        
        if 'Products' in result and result['Products']:
            product = result['Products'][0]
            print(f"Product found: {product.get('Description', 'No description')}")
            print(f"Available fields: {list(product.keys())}")
        else:
            print("No products found in response")
            
        print(f"\nFull response: {json.dumps(result, indent=2)[:1000]}...")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test getInventoryByLocation
    print("\n\n2. Testing getInventoryByLocation endpoint...")
    url = "https://app.skuvault.com/api/inventory/getInventoryByLocation"
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response Keys: {list(result.keys())}")
        
        if 'Items' in result:
            print(f"Items found: {len(result['Items'])}")
            if result['Items']:
                item = result['Items'][0]
                print(f"Item fields: {list(item.keys())}")
        elif 'Products' in result:
            print(f"Products found: {len(result['Products'])}")
            if result['Products']:
                product = result['Products'][0]
                print(f"Product fields: {list(product.keys())}")
        
        print(f"\nFull response: {json.dumps(result, indent=2)[:1000]}...")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with the wrapper
    print("\n\n3. Testing with SkuVaultAPI wrapper...")
    try:
        api = SkuVaultAPI(tenant_token, user_token)
        locations = api.get_inventory_by_location([sku])
        print(f"Locations found: {len(locations)}")
        for loc in locations:
            print(f"  - {loc.location} ({loc.warehouse}): {loc.quantity_available} available")
    except Exception as e:
        print(f"Wrapper error: {e}")

def main():
    # Get credentials
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN environment variables")
        print("\nAlternatively, enter them here:")
        tenant_token = input("Tenant Token: ").strip()
        user_token = input("User Token: ").strip()
    
    # Test SKU
    test_sku = input("\nEnter a SKU to test (or press Enter for default): ").strip()
    if not test_sku:
        test_sku = "TEST-SKU"
    
    test_direct_api_call(tenant_token, user_token, test_sku)

if __name__ == "__main__":
    main()