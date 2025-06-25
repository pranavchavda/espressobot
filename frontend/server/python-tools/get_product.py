#!/usr/bin/env python3
"""Get detailed information about a specific product."""

import sys
import argparse
from base import ShopifyClient, print_json


def get_product(identifier: str, include_metafields: bool = False):
    """Get product details by ID, handle, SKU, or title."""
    client = ShopifyClient()
    
    # Resolve product ID
    product_id = client.resolve_product_id(identifier)
    if not product_id:
        print(f"Error: Product not found with identifier: {identifier}", file=sys.stderr)
        sys.exit(1)
    
    # Build query with optional metafields
    metafield_query = ''
    if include_metafields:
        metafield_query = '''
            metafields(first: 20) {
                edges {
                    node {
                        namespace
                        key
                        value
                        type
                    }
                }
            }
        '''
    
    query = f'''
    query getProduct($id: ID!) {{
        product(id: $id) {{
            id
            title
            handle
            description
            descriptionHtml
            vendor
            productType
            status
            tags
            createdAt
            updatedAt
            publishedAt
            seo {{
                title
                description
            }}
            priceRangeV2 {{
                minVariantPrice {{
                    amount
                    currencyCode
                }}
                maxVariantPrice {{
                    amount
                    currencyCode
                }}
            }}
            totalInventory
            tracksInventory
            featuredImage {{
                url
                altText
            }}
            images(first: 5) {{
                edges {{
                    node {{
                        url
                        altText
                    }}
                }}
            }}
            variants(first: 100) {{
                edges {{
                    node {{
                        id
                        title
                        sku
                        barcode
                        price
                        compareAtPrice
                        inventoryQuantity
                        availableForSale
                        inventoryItem {{
                            id
                            unitCost {{
                                amount
                            }}
                            measurement {{
                                weight {{
                                    value
                                    unit
                                }}
                            }}
                        }}
                        selectedOptions {{
                            name
                            value
                        }}
                    }}
                }}
            }}
            options {{
                name
                values
            }}
            collections(first: 10) {{
                edges {{
                    node {{
                        id
                        title
                        handle
                    }}
                }}
            }}
            {metafield_query}
        }}
    }}
    '''
    
    result = client.execute_graphql(query, {'id': product_id})
    return result.get('data', {}).get('product')


def main():
    parser = argparse.ArgumentParser(
        description='Get detailed product information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # By product ID
  python get_product.py 1234567890
  python get_product.py "gid://shopify/Product/1234567890"
  
  # By handle
  python get_product.py "delonghi-dedica-style"
  
  # By SKU
  python get_product.py "EC685M"
  
  # Include metafields
  python get_product.py "EC685M" --metafields
        '''
    )
    
    parser.add_argument('identifier', help='Product ID, handle, SKU, or title')
    parser.add_argument('--metafields', '-m', action='store_true',
                       help='Include metafields in output')
    parser.add_argument('--field', '-f', help='Extract specific field (dot notation)')
    
    args = parser.parse_args()
    
    # Get product
    product = get_product(args.identifier, args.metafields)
    
    if not product:
        print("Product not found", file=sys.stderr)
        sys.exit(1)
    
    # Extract specific field if requested
    if args.field:
        # Navigate through nested fields
        result = product
        for part in args.field.split('.'):
            if isinstance(result, dict):
                result = result.get(part)
            else:
                result = None
                break
        
        if result is not None:
            if isinstance(result, (dict, list)):
                print_json(result)
            else:
                print(result)
        else:
            print(f"Field '{args.field}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        # Format output
        output = {
            'id': product['id'],
            'title': product['title'],
            'handle': product['handle'],
            'vendor': product['vendor'],
            'type': product['productType'],
            'status': product['status'],
            'tags': product['tags'],
            'description': product['description'],
            'seo': product['seo'],
            'price_range': product['priceRangeV2'],
            'total_inventory': product['totalInventory'],
            'variants_count': len(product.get('variants', {}).get('edges', [])),
            'variants': [
                {
                    'id': v['node']['id'],
                    'title': v['node']['title'],
                    'sku': v['node']['sku'],
                    'price': v['node']['price'],
                    'inventory': v['node']['inventoryQuantity']
                }
                for v in product.get('variants', {}).get('edges', [])
            ],
            'collections': [
                {
                    'id': c['node']['id'],
                    'title': c['node']['title'],
                    'handle': c['node']['handle']
                }
                for c in product.get('collections', {}).get('edges', [])
            ]
        }
        
        if args.metafields and 'metafields' in product:
            output['metafields'] = [
                {
                    'namespace': m['node']['namespace'],
                    'key': m['node']['key'],
                    'value': m['node']['value'],
                    'type': m['node']['type']
                }
                for m in product.get('metafields', {}).get('edges', [])
            ]
        
        print_json(output)


if __name__ == '__main__':
    main()