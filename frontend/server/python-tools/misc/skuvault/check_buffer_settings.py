#!/usr/bin/env python3
"""
Check if there's a way to retrieve buffer settings from SkuVault
"""

import json
import os
import sys
import requests

def check_product_details(sku: str):
    """Try to get detailed product info including buffer settings."""
    
    # Get credentials from environment
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials")
        sys.exit(1)
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Test 1: getProducts with specific SKU
    print("=== Test 1: getProducts ===")
    url = "https://app.skuvault.com/api/products/getProducts"
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "ProductSKUs": [sku],
        "IncludeKitLines": True
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get('Products'):
            product = data['Products'][0]
            print(f"Product found: {product.get('Sku')}")
            # Look for any buffer-related fields
            for key in product.keys():
                if any(term in key.lower() for term in ['buffer', 'cutoff', 'minimum', 'reserve']):
                    print(f"  {key}: {product[key]}")
            # Print all keys to see what's available
            print("\nAll available fields:")
            for key in sorted(product.keys()):
                print(f"  {key}")
    
    # Test 2: Try getAvailableQuantities
    print("\n\n=== Test 2: getAvailableQuantities ===")
    url = "https://app.skuvault.com/api/inventory/getAvailableQuantities"
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "ProductSKUs": [sku]
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test 3: Try getIntegrations to see channels
    print("\n\n=== Test 3: getIntegrations ===")
    url = "https://app.skuvault.com/api/integrations/getIntegrations"
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Check buffer settings')
    parser.add_argument('--sku', default='ECM-G1041-B', help='SKU to check')
    
    args = parser.parse_args()
    
    check_product_details(args.sku)