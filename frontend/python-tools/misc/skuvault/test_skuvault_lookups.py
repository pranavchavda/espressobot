#!/usr/bin/env python3
"""
Test script to explore SkuVault API endpoints for valid Classification and Supplier values
"""

import os
import json
import requests
from typing import Dict, Any

def make_skuvault_request(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Make a request to SkuVault API"""
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials")
        return {}
    
    # Add auth tokens
    payload["TenantToken"] = tenant_token
    payload["UserToken"] = user_token
    
    url = f"https://app.skuvault.com/api/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return {
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except Exception as e:
        return {"error": str(e)}

def test_lookup_endpoints():
    """Test various potential endpoints for getting lookup values"""
    
    # List of potential endpoints to try
    endpoints = [
        # Classifications
        "classifications/getClassifications",
        "products/getClassifications",
        "lookups/getClassifications",
        "reference/getClassifications",
        
        # Suppliers
        "suppliers/getSuppliers",
        "products/getSuppliers",
        "lookups/getSuppliers",
        "reference/getSuppliers",
        
        # General lookups
        "lookups/getLookups",
        "reference/getReferenceLists",
        "products/getProductLookups",
        
        # Settings/configuration
        "settings/getSettings",
        "configuration/getConfiguration",
        "account/getAccountInfo"
    ]
    
    print("Testing SkuVault API endpoints for lookup values...\n")
    
    for endpoint in endpoints:
        print(f"Testing: {endpoint}")
        result = make_skuvault_request(endpoint, {})
        
        if "error" in result:
            print(f"  Error: {result['error']}")
        elif result["status_code"] == 200:
            print(f"  ✓ Success! Response:")
            print(f"  {json.dumps(result['response'], indent=2)[:500]}...")
        else:
            print(f"  Status: {result['status_code']}")
            if isinstance(result['response'], dict):
                print(f"  Response: {json.dumps(result['response'], indent=2)[:200]}...")
            else:
                print(f"  Response: {result['response'][:200]}...")
        print()

def test_create_with_values():
    """Test creating a product with different Classification and Supplier values"""
    
    test_values = [
        # Common classification values to try
        {"Classification": "Consumer Goods", "Supplier": "Direct"},
        {"Classification": "Electronics", "Supplier": "Manufacturer"},
        {"Classification": "Food & Beverage", "Supplier": "Distributor"},
        {"Classification": "Retail", "Supplier": "Vendor"},
        {"Classification": "Equipment", "Supplier": "Wholesale"},
        {"Classification": "Accessories", "Supplier": "Import"},
        {"Classification": "Parts", "Supplier": "OEM"},
        {"Classification": "Merchandise", "Supplier": "Supplier"},
        {"Classification": "", "Supplier": ""},  # Try empty strings
        {"Classification": None, "Supplier": None},  # Try null values
    ]
    
    print("\nTesting different Classification and Supplier values...\n")
    
    base_product = {
        "Sku": "TEST-SKU-DELETE-ME",
        "Description": "Test Product - Delete Me",
        "Cost": 0.01,
        "SalePrice": 0.01,
        "RetailPrice": 0.01
    }
    
    for values in test_values:
        product_data = {**base_product, **values}
        print(f"Testing: Classification='{values['Classification']}', Supplier='{values['Supplier']}'")
        
        result = make_skuvault_request("products/createProduct", product_data)
        
        if result.get("status_code") == 200:
            print(f"  ✓ Success! These values work!")
            # Try to delete the test product
            delete_result = make_skuvault_request("products/removeProduct", {"Sku": "TEST-SKU-DELETE-ME"})
            if delete_result.get("status_code") == 200:
                print("  (Test product deleted)")
        else:
            if isinstance(result.get('response'), dict):
                errors = result['response'].get('ErrorMessages', [])
                if errors:
                    print(f"  ✗ Failed: {errors}")
                else:
                    print(f"  ✗ Failed: {result['response']}")
            else:
                print(f"  ✗ Failed: Status {result.get('status_code')}")
        print()

def main():
    """Main function"""
    print("SkuVault API Lookup Value Explorer\n")
    print("=" * 50)
    
    # First try to find lookup endpoints
    test_lookup_endpoints()
    
    print("\n" + "=" * 50 + "\n")
    
    # Then test different values
    test_create_with_values()

if __name__ == "__main__":
    main()