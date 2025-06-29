#!/usr/bin/env python3
"""
Tool to manage inventory policy (oversell settings) for products.

Usage:
    python tools/manage_inventory_policy.py --identifier "SKU123" --policy deny
    python tools/manage_inventory_policy.py --identifier "product-handle" --policy allow
    python tools/manage_inventory_policy.py --identifier "gid://shopify/Product/123" --policy deny
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, Any, Optional, List

# Get credentials from environment
SHOP_URL = os.getenv('SHOPIFY_SHOP_URL', '').rstrip('/')
ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN', '')

if not SHOP_URL or not ACCESS_TOKEN:
    print("Error: SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN environment variables are required")
    sys.exit(1)

GRAPHQL_URL = f"{SHOP_URL}/admin/api/2024-01/graphql.json"

def make_graphql_request(query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
    """Make a GraphQL request to Shopify."""
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': ACCESS_TOKEN
    }
    
    payload = {'query': query}
    if variables:
        payload['variables'] = variables
    
    response = requests.post(GRAPHQL_URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()

def find_product(identifier: str) -> Optional[Dict[str, Any]]:
    """Find a product by various identifiers."""
    # Try different query approaches
    queries = []
    
    # If it's a GID
    if identifier.startswith('gid://'):
        query = '''
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                variants(first: 100) {
                    edges {
                        node {
                            id
                            sku
                            title
                            inventoryPolicy
                            price
                        }
                    }
                }
            }
        }
        '''
        result = make_graphql_request(query, {'id': identifier})
        if result.get('data', {}).get('product'):
            return result['data']['product']
    
    # Try as SKU
    sku_query = '''
    query findBySku($query: String!) {
        productVariants(first: 10, query: $query) {
            edges {
                node {
                    id
                    sku
                    inventoryPolicy
                    product {
                        id
                        title
                        handle
                        variants(first: 100) {
                            edges {
                                node {
                                    id
                                    sku
                                    title
                                    inventoryPolicy
                                    price
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    '''
    
    result = make_graphql_request(sku_query, {'query': f'sku:{identifier}'})
    variants = result.get('data', {}).get('productVariants', {}).get('edges', [])
    if variants:
        return variants[0]['node']['product']
    
    # Try as handle or title
    product_query = '''
    query findProduct($query: String!) {
        products(first: 10, query: $query) {
            edges {
                node {
                    id
                    title
                    handle
                    variants(first: 100) {
                        edges {
                            node {
                                id
                                sku
                                title
                                inventoryPolicy
                                price
                            }
                        }
                    }
                }
            }
        }
    }
    '''
    
    # Try as handle
    result = make_graphql_request(product_query, {'query': f'handle:{identifier}'})
    products = result.get('data', {}).get('products', {}).get('edges', [])
    if products:
        return products[0]['node']
    
    # Try as title
    result = make_graphql_request(product_query, {'query': f'title:"{identifier}"'})
    products = result.get('data', {}).get('products', {}).get('edges', [])
    if products:
        return products[0]['node']
    
    return None

def update_inventory_policy(product_id: str, variant_id: str, policy: str) -> Dict[str, Any]:
    """Update the inventory policy for a variant."""
    mutation = '''
    mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants {
                id
                sku
                inventoryPolicy
            }
            userErrors {
                field
                message
            }
        }
    }
    '''
    
    variables = {
        'productId': product_id,
        'variants': [{
            'id': variant_id,
            'inventoryPolicy': policy.upper()
        }]
    }
    
    return make_graphql_request(mutation, variables)

def main():
    parser = argparse.ArgumentParser(description='Manage inventory policy (oversell settings) for products')
    parser.add_argument('--identifier', '-i', required=True,
                      help='Product identifier (SKU, handle, title, or Shopify GID)')
    parser.add_argument('--policy', '-p', required=True, 
                      choices=['allow', 'deny', 'ALLOW', 'DENY', 'continue', 'CONTINUE'],
                      help='Inventory policy: allow/continue (can oversell) or deny (cannot oversell)')
    parser.add_argument('--dry-run', action='store_true',
                      help='Show what would be changed without making updates')
    
    args = parser.parse_args()
    
    # Normalize policy - convert 'allow' to 'continue' for Shopify API
    policy = args.policy.upper()
    if policy == 'ALLOW':
        policy = 'CONTINUE'
    
    # Find the product
    print(f"Searching for product: {args.identifier}")
    product = find_product(args.identifier)
    
    if not product:
        print(f"Error: Could not find product with identifier '{args.identifier}'")
        sys.exit(1)
    
    print(f"\nFound product: {product['title']}")
    print(f"Handle: {product['handle']}")
    print(f"Product ID: {product['id']}")
    
    # Get all variants
    variants = product.get('variants', {}).get('edges', [])
    if not variants:
        print("Error: Product has no variants")
        sys.exit(1)
    
    print(f"\nVariants to update:")
    for edge in variants:
        variant = edge['node']
        current_policy = variant['inventoryPolicy']
        # Display user-friendly names
        current_display = "ALLOW" if current_policy == "CONTINUE" else current_policy
        policy_display = "ALLOW" if policy == "CONTINUE" else policy
        status = "→ Will update" if current_policy != policy else "✓ Already set"
        print(f"  - {variant['sku'] or 'No SKU'} ({variant['title']}): {current_display} → {policy_display} [{status}]")
    
    if args.dry_run:
        print("\nDry run mode - no changes made")
        return
    
    # Update each variant
    policy_display = "ALLOW" if policy == "CONTINUE" else policy
    print(f"\nUpdating inventory policy to {policy_display}...")
    success_count = 0
    error_count = 0
    
    for edge in variants:
        variant = edge['node']
        if variant['inventoryPolicy'] == policy:
            policy_display = "ALLOW" if policy == "CONTINUE" else policy
            print(f"  ✓ {variant['sku'] or 'No SKU'}: Already set to {policy_display}")
            success_count += 1
            continue
        
        result = update_inventory_policy(product['id'], variant['id'], policy)
        
        if result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
            errors = result['data']['productVariantsBulkUpdate']['userErrors']
            print(f"  ✗ {variant['sku'] or 'No SKU'}: Error - {errors}")
            error_count += 1
        else:
            updated_variants = result.get('data', {}).get('productVariantsBulkUpdate', {}).get('productVariants', [])
            if updated_variants:
                updated_policy = updated_variants[0].get('inventoryPolicy', policy)
                updated_display = "ALLOW" if updated_policy == "CONTINUE" else updated_policy
                print(f"  ✓ {variant['sku'] or 'No SKU'}: Updated to {updated_display}")
                success_count += 1
            else:
                print(f"  ✗ {variant['sku'] or 'No SKU'}: No response from update")
                error_count += 1
    
    print(f"\nSummary:")
    print(f"  - Successfully updated: {success_count} variants")
    if error_count > 0:
        print(f"  - Errors: {error_count} variants")
    
    if error_count > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()