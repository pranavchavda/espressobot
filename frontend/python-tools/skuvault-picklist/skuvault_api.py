#!/usr/bin/env python3
"""
SkuVault API wrapper for picklist application
"""

import requests
import json
from typing import List, Dict, Any, Optional
import time
from dataclasses import dataclass

@dataclass
class ProductLocation:
    sku: str
    code: str
    description: str
    location: str
    warehouse: str
    quantity_available: int
    quantity_on_hand: int

class SkuVaultAPI:
    def __init__(self, tenant_token: str, user_token: str):
        self.tenant_token = tenant_token
        self.user_token = user_token
        self.base_url = "https://app.skuvault.com/api"
        self.last_request_time = 0
        self.request_count = 0
        
    def _rate_limit(self):
        """Handle rate limiting - 10 requests per minute"""
        current_time = time.time()
        
        # Reset counter if more than 60 seconds have passed
        if current_time - self.last_request_time > 60:
            self.request_count = 0
            
        # If we've made 10 requests, wait until 60 seconds have passed
        if self.request_count >= 10:
            wait_time = 60 - (current_time - self.last_request_time)
            if wait_time > 0:
                time.sleep(wait_time)
            self.request_count = 0
            
        self.request_count += 1
        self.last_request_time = current_time
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with authentication and error handling"""
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add auth tokens to payload
        payload["TenantToken"] = self.tenant_token
        payload["UserToken"] = self.user_token
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e.response, 'text'):
                error_msg += f"\nResponse: {e.response.text}"
            raise Exception(f"API request failed: {error_msg}")
    
    def get_products(self, skus: List[str]) -> List[Dict[str, Any]]:
        """Get product details for given SKUs"""
        payload = {
            "ProductSKUs": skus,
            "IncludeKitLines": True
        }
        
        result = self._make_request("products/getProducts", payload)
        
        if result.get('Status') != 'OK' and 'Products' not in result:
            raise Exception(f"API error: {result.get('Status', 'Unknown error')}")
            
        return result.get('Products', [])
    
    def get_inventory_by_location(self, skus: List[str]) -> List[ProductLocation]:
        """Get inventory locations for given SKUs"""
        # First get product details
        products = self.get_products(skus)
        product_map = {p['Sku']: p for p in products}
        
        # If no products found, return empty list
        if not products:
            return []
        
        # Then get location data
        payload = {
            "ProductSKUs": skus,
            "IncludeKitLines": False
        }
        
        print(f"Fetching inventory locations for: {skus}")
        result = self._make_request("inventory/getInventoryByLocation", payload)
        print(f"Inventory API response keys: {list(result.keys())}")
        
        # Check various possible response formats
        if 'Items' not in result and 'Products' not in result:
            print(f"Unexpected response format: {result}")
            # Try to return basic info from products if location API fails
            locations = []
            for product in products:
                locations.append(ProductLocation(
                    sku=product.get('Sku', ''),
                    code=product.get('Code', ''),
                    description=product.get('Description', 'Unknown Product'),
                    location='Check SkuVault',
                    warehouse='Main',
                    quantity_available=product.get('QuantityAvailable', 0),
                    quantity_on_hand=product.get('QuantityOnHand', 0)
                ))
            return locations
        
        locations = []
        
        # Try different response formats
        items = result.get('Items', result.get('Products', []))
        
        for item in items:
            # Handle different SKU field names
            sku = item.get('SKU', item.get('Sku', item.get('ProductSKU', '')))
            product = product_map.get(sku, {})
            
            # Extract location info - try multiple formats
            location_data = item.get('LocationDetails', [])
            
            # If no LocationDetails, try other formats
            if not location_data:
                if 'Location' in item or 'WarehouseLocation' in item:
                    # Single location format
                    location_data = [{
                        'Location': item.get('Location', item.get('WarehouseLocation', 'Unknown')),
                        'Warehouse': item.get('Warehouse', item.get('WarehouseName', 'Main')),
                        'Quantity': item.get('Quantity', 0),
                        'QuantityAvailable': item.get('QuantityAvailable', item.get('Quantity', 0)),
                        'QuantityOnHand': item.get('QuantityOnHand', item.get('Quantity', 0))
                    }]
                elif 'Warehouses' in item:
                    # Multiple warehouse format
                    location_data = []
                    for wh in item.get('Warehouses', []):
                        location_data.append({
                            'Location': wh.get('Location', 'Unknown'),
                            'Warehouse': wh.get('WarehouseName', wh.get('Name', 'Main')),
                            'QuantityAvailable': wh.get('QuantityAvailable', 0),
                            'QuantityOnHand': wh.get('QuantityOnHand', 0)
                        })
            
            # If still no location data, create a default entry
            if not location_data:
                location_data = [{
                    'Location': 'No Location Data',
                    'Warehouse': 'Main',
                    'QuantityAvailable': product.get('QuantityAvailable', 0),
                    'QuantityOnHand': product.get('QuantityOnHand', 0)
                }]
            
            for loc in location_data:
                locations.append(ProductLocation(
                    sku=sku,
                    code=product.get('Code', ''),
                    description=product.get('Description', 'Unknown Product'),
                    location=loc.get('Location', 'Unknown'),
                    warehouse=loc.get('Warehouse', 'Main'),
                    quantity_available=loc.get('QuantityAvailable', loc.get('Quantity', 0)),
                    quantity_on_hand=loc.get('QuantityOnHand', loc.get('Quantity', 0))
                ))
        
        if not locations:
            print(f"No locations found in response. Full response: {json.dumps(result, indent=2)[:500]}...")
        
        return locations
    
    def search_products(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for products by term"""
        # SkuVault doesn't have a direct search endpoint, so we'll need to get all products
        # and filter locally. In a real implementation, you might want to cache this data.
        # For now, we'll return empty list and require exact SKUs
        return []
    
    def pick_items_bulk(self, picks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Record bulk picks in SkuVault"""
        payload = {
            "Picks": picks
        }
        
        result = self._make_request("inventory/pickItemBulk", payload)
        return result