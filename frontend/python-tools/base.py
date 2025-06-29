#!/usr/bin/env python3
"""Base utilities for Shopify API interaction."""

import os
import sys
import json
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse


class ShopifyClient:
    """Base client for Shopify Admin API GraphQL operations."""
    
    def __init__(self):
        self.shop_url = os.environ.get('SHOPIFY_SHOP_URL')
        self.access_token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
        self.debug = os.environ.get('DEBUG', '').lower() == 'true'
        
        if not self.shop_url or not self.access_token:
            print("Error: Missing required environment variables", file=sys.stderr)
            print("Please set SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN", file=sys.stderr)
            sys.exit(1)
        
        # Normalize shop URL
        self.shop_url = self.shop_url.rstrip('/')
        if not self.shop_url.startswith('https://'):
            self.shop_url = f'https://{self.shop_url}'
        
        self.graphql_url = f"{self.shop_url}/admin/api/2025-07/graphql.json"
        self.session = requests.Session()
        self.session.headers.update({
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        })
    
    def execute_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query or mutation."""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        if self.debug:
            print(f"GraphQL Request: {json.dumps(payload, indent=2)}", file=sys.stderr)
        
        try:
            response = self.session.post(self.graphql_url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if self.debug:
                print(f"GraphQL Response: {json.dumps(result, indent=2)}", file=sys.stderr)
            
            # Check for GraphQL errors
            if 'errors' in result:
                print(f"GraphQL Errors: {json.dumps(result['errors'], indent=2)}", file=sys.stderr)
                sys.exit(1)
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}", file=sys.stderr)
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)
    
    def check_user_errors(self, data: Dict[str, Any], operation: str) -> bool:
        """Check for userErrors in mutation response."""
        for key in data.get('data', {}).values():
            if isinstance(key, dict) and 'userErrors' in key:
                errors = key['userErrors']
                if errors:
                    print(f"User Errors in {operation}:", file=sys.stderr)
                    for error in errors:
                        print(f"  - {error.get('field', 'General')}: {error.get('message', 'Unknown error')}", file=sys.stderr)
                    return False
        return True
    
    def normalize_id(self, identifier: str) -> str:
        """Normalize ID to GID format if needed."""
        if identifier.startswith('gid://'):
            return identifier
        if identifier.isdigit():
            return f"gid://shopify/Product/{identifier}"
        return identifier
    
    def resolve_product_id(self, identifier: str) -> Optional[str]:
        """Resolve product by ID, handle, SKU, or title."""
        # Try as direct ID first
        if identifier.startswith('gid://') or identifier.isdigit():
            return self.normalize_id(identifier)
        
        # Try by handle
        query = '''
        query getProductByHandle($handle: String!) {
            productByHandle(handle: $handle) {
                id
            }
        }
        '''
        result = self.execute_graphql(query, {'handle': identifier})
        if result.get('data', {}).get('productByHandle'):
            return result['data']['productByHandle']['id']
        
        # Try by SKU or title
        search_query = f'sku:"{identifier}" OR title:"{identifier}"'
        query = '''
        query searchProduct($query: String!) {
            products(first: 1, query: $query) {
                edges {
                    node {
                        id
                        title
                        variants(first: 10) {
                            edges {
                                node {
                                    sku
                                }
                            }
                        }
                    }
                }
            }
        }
        '''
        result = self.execute_graphql(query, {'query': search_query})
        edges = result.get('data', {}).get('products', {}).get('edges', [])
        
        if edges:
            product = edges[0]['node']
            # Verify SKU match if searching by SKU
            if identifier.upper() in search_query.upper():
                for variant in product.get('variants', {}).get('edges', []):
                    if variant['node'].get('sku', '').upper() == identifier.upper():
                        return product['id']
            # Otherwise return first match
            return product['id']
        
        return None


def parse_tags(tags_input: str) -> List[str]:
    """Parse comma-separated tags into a list."""
    if not tags_input:
        return []
    return [tag.strip() for tag in tags_input.split(',') if tag.strip()]


def format_price(price: str) -> str:
    """Ensure price is formatted as string with 2 decimal places."""
    try:
        return f"{float(price):.2f}"
    except (ValueError, TypeError):
        return price


def print_json(data: Any, indent: int = 2):
    """Print JSON data in a formatted way."""
    print(json.dumps(data, indent=indent))


if __name__ == '__main__':
    # Test connection
    client = ShopifyClient()
    result = client.execute_graphql('{ shop { name currencyCode } }')
    print("Connection successful!")
    print(f"Shop: {result['data']['shop']['name']}")
    print(f"Currency: {result['data']['shop']['currencyCode']}")