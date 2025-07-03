#!/usr/bin/env python3
"""
Search for products using Shopify's search syntax.

This script allows searching for products on a Shopify store
using various criteria and provides output in different formats.
"""

import sys
import argparse
from base import ShopifyClient, print_json


def search_products(query: str, limit: int = 50, fields: list = None, status: str = "active"):
    """Search for products on Shopify.

    Args:
        query (str): The search query using Shopify's search syntax.
        limit (int): The maximum number of products to return.
        fields (list): A list of fields to return for each product.
        status (str): The product status to filter by (e.g., "active", "draft", "archived").
                      If a status is provided, it will be added to the query if not already present.

    Returns:
        dict: A dictionary containing the search results from Shopify.
    """
    client = ShopifyClient()
    
    # Default fields if not specified
    if not fields:
        fields = ['id', 'title', 'handle', 'vendor', 'status', 'tags', 'price']
    
    # Build field selection based on requested fields
    field_selections = []
    
    # Always include basic fields
    basic_fields = ['id', 'title', 'handle', 'vendor', 'status', 'tags', 'productType']
    field_selections.extend([f for f in basic_fields if f in fields or 'all' in fields])
    
    # Add price information
    if 'price' in fields or 'all' in fields:
        field_selections.append('''
            priceRangeV2 {
                minVariantPrice {
                    amount
                    currencyCode
                }
            }
        ''')
    
    # Add inventory
    if 'inventory' in fields or 'all' in fields:
        field_selections.append('totalInventory')
    
    # Add variants
    if 'variants' in fields or 'all' in fields:
        field_selections.append('''
            variants(first: 5) {
                edges {
                    node {
                        id
                        title
                        sku
                        price
                        inventoryQuantity
                        compareAtPrice
                    }
                }
            }
        ''')
    
    # Add SEO
    if 'seo' in fields or 'all' in fields:
        field_selections.append('''
            seo {
                title
                description
            }
        ''')
    
    # Build query
    graphql_query = f'''
    query searchProducts($query: String!, $first: Int!) {{
        products(first: $first, query: $query) {{
            edges {{
                node {{
                    {' '.join(field_selections)}
                }}
            }}
            pageInfo {{
                hasNextPage
            }}
        }}
    }}
    '''
    
    # Apply status filter if specified
    if status:
        if "status:" not in query:
            query = f"{query} status:{status}"
    
    variables = {
        'query': query,
        'first': limit
    }
    
    result = client.execute_graphql(graphql_query, variables)
    
    return result.get('data', {}).get('products', {})


def main():
    parser = argparse.ArgumentParser(
        description='Search products using Shopify search syntax',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Search syntax examples:
  - Basic: "coffee" or "espresso machine"
  - Tags: "tag:sale" or "tag:featured tag:new"
  - Type/Vendor: "product_type:Electronics" or "vendor:Apple"
  - Price: "price:>50" or "price:10..100"
  - Status: "status:active" or "status:draft"
  - Inventory: "inventory_quantity:>0"
  - SKU/Handle: "sku:ESP-001" or "handle:delonghi-espresso"
  - Combinations: "coffee tag:premium price:>100"
  - Negative: "coffee -decaf" or "tag:sale -tag:clearance"

Examples:
  python search_products.py "tag:sale status:active"
  python search_products.py "vendor:DeLonghi" --limit 20
  python search_products.py "price:>100" --fields all
        '''
    )
    
    parser.add_argument('query', help='Search query using Shopify syntax')
    parser.add_argument('--limit', '-l', type=int, default=50, 
                       help='Number of products to return (default: 50)')
    parser.add_argument('--fields', '-f', nargs='+', 
                       choices=['id', 'title', 'handle', 'vendor', 'status', 'tags', 'productType',
                               'price', 'inventory', 'variants', 'seo', 'all'],
                       default=['id', 'title', 'handle', 'vendor', 'status', 'tags', 'price', 'productType'],
                       help='Fields to include in results')
    parser.add_argument('--output', '-o', choices=['json', 'table', 'csv'], 
                       default='json', help='Output format (default: json)')
    parser.add_argument('--status', '-s', choices=['active', 'draft', 'archived', ''],
                       default='active', help='Filter by status (default: active, empty string for no filter)')
    
    args = parser.parse_args()

    # For JSON output, ensure 'variants' field is included
    if args.output == 'json' and 'variants' not in args.fields and 'all' not in args.fields:
        args.fields.append('variants')
    
    # Perform search
    results = search_products(args.query, args.limit, args.fields, args.status)
    
    products = [edge['node'] for edge in results.get('edges', [])]
    
    if not products:
        print("No products found matching your search criteria.")
        sys.exit(0)
    
    # Output results
    if args.output == 'json':
        # Flatten the data for a non-nested JSON output
        flat_products = []
        for p in products:
            product_info = {
                'product_id': p['id'].split('/')[-1],
                'product_title': p['title'],
                'handle': p.get('handle'),
                'vendor': p.get('vendor'),
                'status': p.get('status'),
                'tags': ', '.join(p.get('tags', [])),
                'product_type': p.get('productType')
            }

            variants = p.get('variants', {}).get('edges', [])
            if variants:
                for v_edge in variants:
                    v = v_edge['node']
                    variant_info = product_info.copy()
                    variant_info.update({
                        'variant_id': v['id'].split('/')[-1],
                        'variant_title': v['title'],
                        'sku': v.get('sku'),
                        'price': v.get('price'),
                        'compare_at_price': v.get('compareAtPrice'),
                        'inventory_quantity': v.get('inventoryQuantity')
                    })
                    flat_products.append(variant_info)
            else:
                # If no variants, add product info with empty variant fields
                product_info.update({
                    'variant_id': None,
                    'variant_title': None,
                    'sku': None,
                    'price': p.get('priceRangeV2', {}).get('minVariantPrice', {}).get('amount'),
                    'compare_at_price': None,
                    'inventory_quantity': p.get('totalInventory')
                })
                flat_products.append(product_info)
        
        print_json(flat_products)
    elif args.output == 'table':
        # Display results in a structured table
        cols = [
            ('ID', 15), ('Title', 40), ('Vendor', 20), ('Status', 10), 
            ('Price', 20), ('Tags', 30)
        ]
        
        print(f"Found {len(products)} products:")
        
        # Print header
        header_line = ' '.join([f'{name:<{width}}' for name, width in cols])
        print(header_line)
        print('-' * len(header_line))

        for p in products:
            price = p.get('priceRangeV2', {}).get('minVariantPrice', {})
            price_str = f"{price.get('currencyCode', '')} {price.get('amount', 'N/A')}" if price else 'N/A'
            
            row_values = {
                'ID': p['id'].split('/')[-1],
                'Title': p['title'],
                'Vendor': p.get('vendor', 'N/A'),
                'Status': p.get('status', 'N/A'),
                'Price': price_str,
                'Tags': ', '.join(p.get('tags', []))
            }

            row_line_items = []
            for name, width in cols:
                value = str(row_values.get(name, ''))
                if len(value) > width:
                    value = value[:width-4] + '...'
                row_line_items.append(f'{value:<{width}}')
            
            print(' '.join(row_line_items))
    else:  # csv
        import csv
        import io
        output = io.StringIO()
        
        # Determine columns
        columns = ['id', 'title', 'handle', 'vendor', 'status', 'tags']
        if any('price' in args.fields or 'all' in args.fields for _ in [1]):
            columns.append('price')
        
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        
        for p in products:
            row = {
                'id': p['id'].split('/')[-1],
                'title': p['title'],
                'handle': p.get('handle', ''),
                'vendor': p.get('vendor', ''),
                'status': p.get('status', ''),
                'tags': ', '.join(p.get('tags', []))
            }
            
            if 'price' in columns:
                price = p.get('priceRangeV2', {}).get('minVariantPrice', {})
                row['price'] = price.get('amount', '') if price else ''
            
            writer.writerow(row)
        
        print(output.getvalue())
    
    # Show if more results available
    if results.get('pageInfo', {}).get('hasNextPage'):
        print(f"\nNote: More results available. Use --limit to see more.", file=sys.stderr)


if __name__ == '__main__':
    main()