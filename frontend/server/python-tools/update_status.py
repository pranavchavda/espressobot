#!/usr/bin/env python3
"""Update product status (ACTIVE, DRAFT, or ARCHIVED)."""

import sys
import argparse
from base import ShopifyClient, print_json


def update_status(identifier: str, status: str, dry_run: bool = False):
    """Update product status."""
    client = ShopifyClient()
    
    # Resolve product ID
    product_id = client.resolve_product_id(identifier)
    if not product_id:
        print(f"Error: Product not found with identifier: {identifier}", file=sys.stderr)
        sys.exit(1)
    
    # Get current status first
    query = '''
    query getProductStatus($id: ID!) {
        product(id: $id) {
            id
            title
            status
        }
    }
    '''
    
    result = client.execute_graphql(query, {'id': product_id})
    product = result.get('data', {}).get('product')
    
    if not product:
        print(f"Error: Could not retrieve product", file=sys.stderr)
        sys.exit(1)
    
    current_status = product['status']
    
    # Check if status is already set
    if current_status == status:
        print(f"Product '{product['title']}' is already {status}")
        return product
    
    if dry_run:
        print(f"Would update product '{product['title']}' from {current_status} to {status}")
        return product
    
    # Update status
    mutation = '''
    mutation updateProductStatus($input: ProductInput!) {
        productUpdate(input: $input) {
            product {
                id
                title
                status
            }
            userErrors {
                field
                message
            }
        }
    }
    '''
    
    variables = {
        'input': {
            'id': product_id,
            'status': status
        }
    }
    
    result = client.execute_graphql(mutation, variables)
    
    # Check for errors
    if not client.check_user_errors(result, 'productUpdate'):
        sys.exit(1)
    
    return result.get('data', {}).get('productUpdate', {}).get('product')


def bulk_update_status(query_string: str, status: str, dry_run: bool = False):
    """Update status for multiple products matching a query."""
    client = ShopifyClient()
    
    # Search for products
    search_query = '''
    query searchProducts($query: String!, $first: Int!) {
        products(first: $first, query: $query) {
            edges {
                node {
                    id
                    title
                    status
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    '''
    
    all_products = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        variables = {
            'query': query_string,
            'first': 50
        }
        if cursor:
            variables['after'] = cursor
            
        result = client.execute_graphql(search_query, variables)
        products_data = result.get('data', {}).get('products', {})
        
        edges = products_data.get('edges', [])
        all_products.extend([edge['node'] for edge in edges])
        
        page_info = products_data.get('pageInfo', {})
        has_next_page = page_info.get('hasNextPage', False)
        cursor = page_info.get('endCursor')
    
    if not all_products:
        print(f"No products found matching query: {query_string}")
        return []
    
    # Filter products that need status update
    products_to_update = [p for p in all_products if p['status'] != status]
    
    if not products_to_update:
        print(f"All {len(all_products)} products are already {status}")
        return []
    
    print(f"Found {len(products_to_update)} products to update (out of {len(all_products)} total)")
    
    if dry_run:
        print("\nProducts that would be updated:")
        for product in products_to_update:
            print(f"  - {product['title']} ({product['status']} → {status})")
        return products_to_update
    
    # Update each product
    updated = []
    failed = []
    
    for i, product in enumerate(products_to_update, 1):
        print(f"\n[{i}/{len(products_to_update)}] Updating {product['title']}...")
        
        try:
            result = update_status(product['id'], status)
            if result:
                updated.append(result)
                print(f"  ✅ Updated from {product['status']} to {status}")
            else:
                failed.append(product)
                print(f"  ❌ Failed to update")
        except Exception as e:
            failed.append(product)
            print(f"  ❌ Error: {str(e)}")
    
    # Summary
    print(f"\n\nSummary:")
    print(f"  ✅ Successfully updated: {len(updated)}")
    print(f"  ❌ Failed: {len(failed)}")
    
    if failed:
        print("\nFailed products:")
        for product in failed:
            print(f"  - {product['title']}")
    
    return updated


def main():
    parser = argparse.ArgumentParser(
        description='Update product status (ACTIVE, DRAFT, or ARCHIVED)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Update single product to DRAFT
  python update_status.py --product "1234567890" --status DRAFT
  python update_status.py -p "delonghi-dedica" -s DRAFT
  
  # Update single product to ACTIVE
  python update_status.py --product "EC685M" --status ACTIVE
  
  # Archive a product
  python update_status.py --product "old-product" --status ARCHIVED
  
  # Bulk update by query
  python update_status.py --query "vendor:Pesado tag:portafilter" --status DRAFT
  python update_status.py --query "title:*Discontinued*" --status ARCHIVED
  
  # Dry run to preview changes
  python update_status.py --query "tag:sale" --status ACTIVE --dry-run
  
  # Check current status
  python update_status.py --product "1234567890" --check
        '''
    )
    
    # Product identifier group
    product_group = parser.add_mutually_exclusive_group(required=True)
    product_group.add_argument('--product', '-p',
                             help='Product ID, handle, SKU, or title')
    product_group.add_argument('--query', '-q',
                             help='Search query for bulk update')
    
    # Status argument
    parser.add_argument('--status', '-s', 
                       choices=['ACTIVE', 'DRAFT', 'ARCHIVED'],
                       help='New status to set')
    
    # Options
    parser.add_argument('--check', '-c', action='store_true',
                       help='Just check current status')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Preview changes without updating')
    
    args = parser.parse_args()
    
    # Handle check mode
    if args.check:
        if args.query:
            print("Error: --check can only be used with --product", file=sys.stderr)
            sys.exit(1)
            
        client = ShopifyClient()
        product_id = client.resolve_product_id(args.product)
        if not product_id:
            print(f"Error: Product not found with identifier: {args.product}", file=sys.stderr)
            sys.exit(1)
        
        query = '''
        query getProductStatus($id: ID!) {
            product(id: $id) {
                id
                title
                status
                handle
                vendor
            }
        }
        '''
        
        result = client.execute_graphql(query, {'id': product_id})
        product = result.get('data', {}).get('product')
        
        if product:
            print(f"Product: {product['title']}")
            print(f"Vendor: {product['vendor']}")
            print(f"Handle: {product['handle']}")
            print(f"Status: {product['status']}")
        sys.exit(0)
    
    # Validate status argument
    if not args.status:
        print("Error: --status is required (unless using --check)", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    # Perform update
    if args.query:
        # Bulk update
        bulk_update_status(args.query, args.status, args.dry_run)
    else:
        # Single product update
        result = update_status(args.product, args.status, args.dry_run)
        
        if result and not args.dry_run:
            print(f"✅ Successfully updated product status")
            print(f"Product: {result['title']}")
            print(f"Status: {result['status']}")


if __name__ == '__main__':
    main()