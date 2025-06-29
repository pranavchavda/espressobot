#!/usr/bin/env python3
"""
Test bulk update endpoint for buffer settings
"""

import json
import os
import sys
import requests

def test_bulk_update(sku: str, buffer_quantity: int):
    """Test updateProducts bulk endpoint."""
    
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
    
    # Test 1: updateProducts endpoint
    print("=== Test 1: updateProducts bulk endpoint ===")
    url = "https://app.skuvault.com/api/products/updateProducts"
    
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "Products": [
            {
                "Sku": sku,
                "BufferQuantity": buffer_quantity,
                "LowQuantityCutoff": buffer_quantity,
                "MinimumQuantity": buffer_quantity,
                "BufferMode": "cutoff"
            }
        ]
    }
    
    print(f"Request payload (auth tokens hidden):")
    print(json.dumps({"Products": payload["Products"]}, indent=2))
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test 2: Try setQuantity endpoint
    print("\n\n=== Test 2: setQuantity endpoint ===")
    url = "https://app.skuvault.com/api/inventory/setQuantity"
    
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "Sku": sku,
        "WarehouseCode": "MAIN",  # Adjust if needed
        "Quantity": 100,  # Just testing
        "BufferQuantity": buffer_quantity,
        "BufferMode": "cutoff"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test 3: Check if there's a setBufferQuantity endpoint
    print("\n\n=== Test 3: Trying setBufferQuantity endpoint ===")
    url = "https://app.skuvault.com/api/inventory/setBufferQuantity"
    
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "Sku": sku,
        "BufferQuantity": buffer_quantity,
        "Mode": "cutoff"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Test bulk update for buffers')
    parser.add_argument('--sku', default='ECM-G1041-B', help='SKU to test')
    parser.add_argument('--buffer', type=int, default=3, help='Buffer quantity')
    
    args = parser.parse_args()
    
    test_bulk_update(args.sku, args.buffer)