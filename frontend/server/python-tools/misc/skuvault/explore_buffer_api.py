#!/usr/bin/env python3
"""
Explore SkuVault API for buffer quantity functionality
This tool tests various potential endpoints for setting buffer quantities
"""

import json
import os
import sys
import requests
import argparse
from typing import Dict, Any

class SkuVaultBufferExplorer:
    def __init__(self):
        self.tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
        self.user_token = os.environ.get('SKUVAULT_USER_TOKEN')
        
        if not self.tenant_token or not self.user_token:
            print("Error: Missing SkuVault credentials. Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN")
            sys.exit(1)
        
        self.base_url = "https://app.skuvault.com/api"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to SkuVault API."""
        # Always include auth tokens
        payload["TenantToken"] = self.tenant_token
        payload["UserToken"] = self.user_token
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response": response.json() if response.text else {},
                "success": response.status_code == 200
            }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "status_code": 0,
                "response": {"error": str(e)},
                "success": False
            }
    
    def test_update_product_with_buffer(self, sku: str):
        """Test if updateProduct accepts buffer-related fields."""
        print("\n=== Testing updateProduct with buffer fields ===")
        
        # Try various potential field names
        test_payloads = [
            {
                "Sku": sku,
                "BufferQuantity": 5,
                "BufferMode": "cutoff"
            },
            {
                "Sku": sku,
                "QuantityBuffer": 5,
                "QuantityBufferMode": "cutoff"
            },
            {
                "Sku": sku,
                "LowQuantityCutoff": 5
            },
            {
                "Sku": sku,
                "MinimumQuantity": 5
            },
            {
                "Sku": sku,
                "ReserveQuantity": 5
            }
        ]
        
        for i, payload in enumerate(test_payloads, 1):
            print(f"\nTest {i}: {list(payload.keys())}")
            result = self.make_request("/products/updateProduct", payload)
            self.print_result(result)
    
    def test_channel_specific_endpoints(self, sku: str, channel: str = "Default"):
        """Test channel-specific endpoints."""
        print("\n=== Testing channel-specific endpoints ===")
        
        # Potential endpoints
        endpoints_to_test = [
            ("/inventory/setChannelQuantity", {
                "Sku": sku,
                "Channel": channel,
                "Quantity": 10,
                "BufferQuantity": 5
            }),
            ("/channels/setBuffer", {
                "Sku": sku,
                "Channel": channel,
                "BufferQuantity": 5,
                "BufferMode": "cutoff"
            }),
            ("/integrations/updateChannelSettings", {
                "Sku": sku,
                "ChannelName": channel,
                "Settings": {
                    "BufferQuantity": 5,
                    "BufferMode": "cutoff"
                }
            })
        ]
        
        for endpoint, payload in endpoints_to_test:
            print(f"\nTesting: {endpoint}")
            result = self.make_request(endpoint, payload)
            self.print_result(result)
    
    def test_integration_endpoints(self, sku: str):
        """Test integration-related endpoints."""
        print("\n=== Testing integration endpoints ===")
        
        # First, get integrations
        result = self.make_request("/integrations/getIntegrations", {})
        self.print_result(result)
        
        # Try updateIntegrations with buffer settings
        payload = {
            "ProductIntegrations": {
                "Products": [sku],
                "IntegrationName": "Default",
                "Settings": {
                    "BufferQuantity": 5,
                    "BufferMode": "cutoff"
                }
            }
        }
        
        print("\nTesting updateIntegrations with buffer settings:")
        result = self.make_request("/integrations/updateIntegrations", payload)
        self.print_result(result)
    
    def print_result(self, result: Dict[str, Any]):
        """Print API result in a formatted way."""
        if result['success']:
            print(f"✓ Success (Status: {result['status_code']})")
            if result['response']:
                print(f"Response: {json.dumps(result['response'], indent=2)}")
        else:
            print(f"✗ Failed (Status: {result['status_code']})")
            if result['response']:
                print(f"Error: {json.dumps(result['response'], indent=2)}")

def main():
    parser = argparse.ArgumentParser(
        description='Explore SkuVault API for buffer quantity functionality',
        epilog='This tool tests various potential endpoints to find buffer quantity settings'
    )
    
    parser.add_argument('--sku', required=True, help='Product SKU to test with')
    parser.add_argument('--channel', default='Default', help='Channel name (default: Default)')
    parser.add_argument('--test', choices=['all', 'product', 'channel', 'integration'], 
                       default='all', help='Which endpoints to test')
    
    args = parser.parse_args()
    
    explorer = SkuVaultBufferExplorer()
    
    print(f"Testing buffer functionality for SKU: {args.sku}")
    print("=" * 60)
    
    if args.test in ['all', 'product']:
        explorer.test_update_product_with_buffer(args.sku)
    
    if args.test in ['all', 'channel']:
        explorer.test_channel_specific_endpoints(args.sku, args.channel)
    
    if args.test in ['all', 'integration']:
        explorer.test_integration_endpoints(args.sku)
    
    print("\n" + "=" * 60)
    print("Testing complete. Check the results above to see which endpoints/fields work.")
    print("\nNote: This is an exploratory tool. Some endpoints may not exist or may")
    print("require different parameters than tested here.")

if __name__ == "__main__":
    main()