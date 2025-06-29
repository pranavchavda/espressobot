#!/usr/bin/env python3
"""
Manage variant links between related products (e.g., different colors of the same model).

This tool helps create and maintain the varLinks metafield that connects product variants
together, allowing customers to easily switch between color/style options.
"""

import os
import sys
import json
import requests
import argparse
from typing import List, Dict, Set

# Get Shopify credentials from environment
SHOPIFY_SHOP_URL = os.getenv('SHOPIFY_SHOP_URL')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')

if not all([SHOPIFY_SHOP_URL, SHOPIFY_ACCESS_TOKEN]):
    print("Error: Missing required environment variables (SHOPIFY_SHOP_URL, SHOPIFY_ACCESS_TOKEN)")
    sys.exit(1)

# GraphQL endpoint
GRAPHQL_URL = f"{SHOPIFY_SHOP_URL}/admin/api/2024-01/graphql.json"
HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

def get_product_info(product_id: str) -> Dict:
    """Get product title and current varLinks."""
    query = """
    query getProduct($id: ID!) {
        product(id: $id) {
            id
            title
            handle
            status
            metafield(namespace: "new", key: "varLinks") {
                id
                value
            }
        }
    }
    """
    
    # Handle different ID formats
    if not product_id.startswith('gid://'):
        product_id = f"gid://shopify/Product/{product_id}"
    
    response = requests.post(GRAPHQL_URL, headers=HEADERS, json={
        'query': query,
        'variables': {'id': product_id}
    })
    
    result = response.json()
    if 'errors' in result:
        print(f"Error fetching product {product_id}: {result['errors']}")
        return None
    
    return result.get('data', {}).get('product')

def update_variant_links(product_id: str, linked_products: List[str]) -> bool:
    """Update the varLinks metafield for a product."""
    mutation = """
    mutation setMetafield($input: MetafieldsSetInput!) {
        metafieldsSet(metafields: [$input]) {
            metafields {
                id
                namespace
                key
                value
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    # Ensure all IDs are in GID format
    formatted_ids = []
    for pid in linked_products:
        if not pid.startswith('gid://'):
            formatted_ids.append(f"gid://shopify/Product/{pid}")
        else:
            formatted_ids.append(pid)
    
    # Ensure product_id is in GID format
    if not product_id.startswith('gid://'):
        product_id = f"gid://shopify/Product/{product_id}"
    
    variables = {
        "input": {
            "ownerId": product_id,
            "namespace": "new",
            "key": "varLinks",
            "value": json.dumps(formatted_ids),
            "type": "list.product_reference"
        }
    }
    
    response = requests.post(GRAPHQL_URL, headers=HEADERS, json={
        'query': mutation,
        'variables': variables
    })
    
    result = response.json()
    
    if 'errors' in result:
        print(f"GraphQL errors: {result['errors']}")
        return False
    
    if result.get('data', {}).get('metafieldsSet', {}).get('userErrors'):
        print(f"Error updating {product_id}: {result['data']['metafieldsSet']['userErrors']}")
        return False
    
    return True

def link_products(product_ids: List[str], verbose: bool = False):
    """Link a group of products together."""
    print(f"\nLinking {len(product_ids)} products together...")
    print("-" * 50)
    
    # First, verify all products exist
    valid_products = []
    for pid in product_ids:
        product = get_product_info(pid)
        if product:
            valid_products.append(product['id'])
            if verbose:
                print(f"✓ Found: {product['title']}")
        else:
            print(f"✗ Not found: {pid}")
    
    if len(valid_products) < 2:
        print("\nError: Need at least 2 valid products to link")
        return
    
    print(f"\nLinking {len(valid_products)} valid products...")
    
    # Update all products with the complete list
    success_count = 0
    for product_id in valid_products:
        product = get_product_info(product_id)
        if update_variant_links(product_id, valid_products):
            success_count += 1
            print(f"✓ Updated: {product['title']}")
        else:
            print(f"✗ Failed: {product['title']}")
    
    print(f"\nSuccessfully linked {success_count}/{len(valid_products)} products")

def unlink_products(product_ids: List[str]):
    """Remove products from variant linking."""
    print(f"\nUnlinking {len(product_ids)} products...")
    print("-" * 50)
    
    for pid in product_ids:
        product = get_product_info(pid)
        if not product:
            print(f"✗ Not found: {pid}")
            continue
        
        # Remove varLinks by setting empty array
        if update_variant_links(product['id'], []):
            print(f"✓ Unlinked: {product['title']}")
        else:
            print(f"✗ Failed: {product['title']}")

def check_links(product_id: str):
    """Check variant links for a product."""
    product = get_product_info(product_id)
    if not product:
        print(f"Product not found: {product_id}")
        return
    
    print(f"\nProduct: {product['title']}")
    print(f"Handle: {product['handle']}")
    print(f"Status: {product['status']}")
    print("-" * 50)
    
    # Get current varLinks
    varlinks_metafield = product.get('metafield')
    if not varlinks_metafield or not varlinks_metafield.get('value'):
        print("No variant links found")
        return
    
    linked_ids = json.loads(varlinks_metafield['value'])
    print(f"Linked to {len(linked_ids)} products:")
    
    # Fetch details for each linked product
    for linked_id in linked_ids:
        linked_product = get_product_info(linked_id)
        if linked_product:
            status = "✓" if linked_product['id'] == product['id'] else " "
            print(f"{status} {linked_product['title']} ({linked_product['status']})")
        else:
            print(f"✗ {linked_id} (NOT FOUND)")

def sync_group(sample_product_id: str):
    """Sync all products in a variant group based on one product's links."""
    print(f"\nSyncing variant group based on: {sample_product_id}")
    print("-" * 50)
    
    # Get the sample product's links
    product = get_product_info(sample_product_id)
    if not product:
        print(f"Product not found: {sample_product_id}")
        return
    
    varlinks_metafield = product.get('metafield')
    if not varlinks_metafield or not varlinks_metafield.get('value'):
        print("No variant links found on sample product")
        return
    
    linked_ids = json.loads(varlinks_metafield['value'])
    print(f"Found {len(linked_ids)} products in group")
    
    # Update all products in the group
    link_products(linked_ids, verbose=True)

def audit_links(search_query: str = None):
    """Audit variant links for consistency issues."""
    print("\nAuditing variant links...")
    print("-" * 50)
    
    # Search for products
    query = """
    query searchProducts($query: String!) {
        products(first: 100, query: $query) {
            edges {
                node {
                    id
                    title
                    handle
                    metafields(first: 1, namespace: "new", key: "varLinks") {
                        edges {
                            node {
                                value
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    response = requests.post(GRAPHQL_URL, headers=HEADERS, json={
        'query': query,
        'variables': {'query': search_query or ''}
    })
    
    result = response.json()
    products = result.get('data', {}).get('products', {}).get('edges', [])
    
    # Group products by their varLinks
    link_groups = {}
    unlinked = []
    
    for edge in products:
        product = edge['node']
        varlinks_data = product.get('metafields', {}).get('edges', [])
        
        if not varlinks_data:
            unlinked.append(product)
        else:
            links = tuple(sorted(json.loads(varlinks_data[0]['node']['value'])))
            if links not in link_groups:
                link_groups[links] = []
            link_groups[links].append(product)
    
    # Report findings
    print(f"\nFound {len(products)} products")
    print(f"Variant groups: {len(link_groups)}")
    print(f"Unlinked products: {len(unlinked)}")
    
    # Show groups
    for i, (links, group_products) in enumerate(link_groups.items(), 1):
        print(f"\nGroup {i} ({len(group_products)} products, {len(links)} total links):")
        for p in group_products[:5]:  # Show first 5
            print(f"  - {p['title']}")
        if len(group_products) > 5:
            print(f"  ... and {len(group_products) - 5} more")
    
    # Show unlinked
    if unlinked:
        print(f"\nUnlinked products:")
        for p in unlinked[:10]:  # Show first 10
            print(f"  - {p['title']}")
        if len(unlinked) > 10:
            print(f"  ... and {len(unlinked) - 10} more")

def main():
    parser = argparse.ArgumentParser(description='Manage variant links between related products')
    parser.add_argument('--action', choices=['link', 'unlink', 'check', 'sync', 'audit'],
                        required=True, help='Action to perform')
    parser.add_argument('--products', help='Comma-separated list of product IDs')
    parser.add_argument('--file', help='File containing product IDs (one per line)')
    parser.add_argument('--product', help='Single product ID (for check/sync actions)')
    parser.add_argument('--search', help='Search query (for audit action)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Get product IDs based on input method
    product_ids = []
    if args.products:
        product_ids = [pid.strip() for pid in args.products.split(',')]
    elif args.file:
        with open(args.file, 'r') as f:
            product_ids = [line.strip() for line in f if line.strip()]
    elif args.product:
        product_ids = [args.product]
    
    # Execute action
    if args.action == 'link':
        if not product_ids or len(product_ids) < 2:
            print("Error: Link action requires at least 2 product IDs")
            sys.exit(1)
        link_products(product_ids, args.verbose)
    
    elif args.action == 'unlink':
        if not product_ids:
            print("Error: Unlink action requires product IDs")
            sys.exit(1)
        unlink_products(product_ids)
    
    elif args.action == 'check':
        if not args.product:
            print("Error: Check action requires --product")
            sys.exit(1)
        check_links(args.product)
    
    elif args.action == 'sync':
        if not args.product:
            print("Error: Sync action requires --product")
            sys.exit(1)
        sync_group(args.product)
    
    elif args.action == 'audit':
        audit_links(args.search)

if __name__ == '__main__':
    main()