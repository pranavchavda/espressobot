#!/usr/bin/env python3
"""
Test buffer quantity API with raw response output
"""

import json
import os
import sys
import requests

def test_buffer_update(sku: str, buffer_quantity: int, channel: str = None):
    """Test buffer quantity update and show raw response."""
    
    # Get credentials from environment
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials")
        sys.exit(1)
    
    # API endpoint
    url = "https://app.skuvault.com/api/products/updateProduct"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Test 1: Basic buffer fields only
    print("=== Test 1: Basic buffer fields ===")
    payload1 = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "Sku": sku,
        "BufferQuantity": buffer_quantity,
        "BufferMode": "cutoff"
    }
    
    print(f"Request payload (auth tokens hidden):")
    print(json.dumps({k: v for k, v in payload1.items() if k not in ['TenantToken', 'UserToken']}, indent=2))
    
    response = requests.post(url, json=payload1, headers=headers)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    # Test 2: With channel fields
    if channel:
        print("\n\n=== Test 2: With channel fields ===")
        payload2 = {
            "TenantToken": tenant_token,
            "UserToken": user_token,
            "Sku": sku,
            "BufferQuantity": buffer_quantity,
            "BufferMode": "cutoff",
            "Channel": channel,
            "ChannelName": channel,
            "IntegrationName": channel
        }
        
        print(f"Request payload (auth tokens hidden):")
        print(json.dumps({k: v for k, v in payload2.items() if k not in ['TenantToken', 'UserToken']}, indent=2))
        
        response = requests.post(url, json=payload2, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Test buffer API with raw response')
    parser.add_argument('--sku', default='ECM-G1041-B', help='SKU to test')
    parser.add_argument('--buffer', type=int, default=3, help='Buffer quantity')
    parser.add_argument('--channel', help='Channel name to test')
    
    args = parser.parse_args()
    
    test_buffer_update(args.sku, args.buffer, args.channel)