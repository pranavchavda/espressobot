#!/usr/bin/env python3
"""Search for products using Shopify's search syntax."""

import sys
import argparse
from base import ShopifyClient, print_json


def search_products(query: str, limit: int = 10, fields: list = None):
    """Search products and return results."""
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
    parser.add_argument('--limit', '-l', type=int, default=10, 
                       help='Number of products to return (default: 10)')
    parser.add_argument('--fields', '-f', nargs='+', 
                       choices=['id', 'title', 'handle', 'vendor', 'status', 'tags', 
                               'price', 'inventory', 'variants', 'seo', 'all'],
                       default=['id', 'title', 'handle', 'vendor', 'status', 'tags', 'price'],
                       help='Fields to include in results')
    parser.add_argument('--output', '-o', choices=['json', 'table', 'csv'], 
                       default='json', help='Output format')
    
    args = parser.parse_args()
    
    # Perform search
    results = search_products(args.query, args.limit, args.fields)
    
    products = [edge['node'] for edge in results.get('edges', [])]
    
    if not products:
        print("No products found matching your search criteria.")
        sys.exit(0)
    
    # Output results
    if args.output == 'json':
        print_json(products)
    elif args.output == 'table':
        # Simple table output
        print(f"Found {len(products)} products:")
        print("-" * 80)
        for p in products:
            price = p.get('priceRangeV2', {}).get('minVariantPrice', {})
            price_str = f"{price.get('currencyCode', '')} {price.get('amount', 'N/A')}" if price else 'N/A'
            print(f"ID: {p['id'].split('/')[-1]}")
            print(f"Title: {p['title']}")
            print(f"Vendor: {p.get('vendor', 'N/A')}")
            print(f"Status: {p.get('status', 'N/A')}")
            print(f"Price: {price_str}")
            print(f"Tags: {', '.join(p.get('tags', []))}")
            print("-" * 80)
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