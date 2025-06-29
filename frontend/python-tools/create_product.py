#!/usr/bin/env python3
"""Create new products in Shopify."""

import sys
import argparse
from base import ShopifyClient, parse_tags, format_price, print_json


def create_product(
    title: str,
    vendor: str,
    product_type: str,
    description: str = None,
    tags: list = None,
    price: str = "0.00",
    sku: str = None,
    barcode: str = None,
    weight: float = None,
    weight_unit: str = "KILOGRAMS",
    inventory_quantity: int = 0,
    track_inventory: bool = True,
    status: str = "DRAFT"
):
    """Create a new product with a single variant."""
    client = ShopifyClient()
    
    # Build product input
    product_input = {
        'title': title,
        'vendor': vendor,
        'productType': product_type,
        'status': status
    }
    
    if description:
        product_input['descriptionHtml'] = description.replace('\n', '<br>')
    
    if tags:
        product_input['tags'] = tags
    
    # Build variant
    variant_input = {
        'price': format_price(price),
        'inventoryQuantities': [{
            'availableQuantity': inventory_quantity,
            'locationId': get_default_location(client)
        }]
    }
    
    if sku:
        variant_input['sku'] = sku
    
    if barcode:
        variant_input['barcode'] = barcode
    
    if weight:
        variant_input['weight'] = weight
        variant_input['weightUnit'] = weight_unit
    
    if not track_inventory:
        variant_input['inventoryPolicy'] = 'CONTINUE'
        variant_input['inventoryManagement'] = None
    else:
        variant_input['inventoryManagement'] = 'SHOPIFY'
    
    product_input['variants'] = [variant_input]
    
    # Execute mutation
    mutation = '''
    mutation createProduct($input: ProductInput!) {
        productCreate(input: $input) {
            product {
                id
                title
                handle
                status
                tags
                variants(first: 1) {
                    edges {
                        node {
                            id
                            sku
                            price
                        }
                    }
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    '''
    
    result = client.execute_graphql(mutation, {'input': product_input})
    
    # Check for errors
    if not client.check_user_errors(result, 'productCreate'):
        sys.exit(1)
    
    return result.get('data', {}).get('productCreate', {}).get('product')


def get_default_location(client: ShopifyClient) -> str:
    """Get the default location ID for inventory."""
    query = '''
    {
        locations(first: 1) {
            edges {
                node {
                    id
                    name
                    isActive
                }
            }
        }
    }
    '''
    
    result = client.execute_graphql(query)
    locations = result.get('data', {}).get('locations', {}).get('edges', [])
    
    if not locations:
        print("Error: No locations found for inventory", file=sys.stderr)
        sys.exit(1)
    
    return locations[0]['node']['id']


def main():
    parser = argparse.ArgumentParser(
        description='Create new products in Shopify',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Simple product
  python create_product.py --title "Test Product" --vendor "Brand" --type "Category"
  
  # Full product details
  python create_product.py \\
    --title "DeLonghi Dedica Style EC685M" \\
    --vendor "DeLonghi" \\
    --type "Espresso Machines" \\
    --description "Compact espresso machine with professional features" \\
    --tags "espresso-machines,delonghi,consumer" \\
    --price 249.99 \\
    --sku "EC685M" \\
    --inventory 10 \\
    --status ACTIVE
  
  # Product without inventory tracking
  python create_product.py --title "Digital Gift Card" --vendor "Store" --type "Gift Cards" --no-track-inventory
        '''
    )
    
    parser.add_argument('--title', '-t', required=True,
                       help='Product title')
    parser.add_argument('--vendor', '-v', required=True,
                       help='Product vendor/brand')
    parser.add_argument('--type', '--product-type', required=True,
                       help='Product type/category')
    parser.add_argument('--description', '-d',
                       help='Product description')
    parser.add_argument('--tags',
                       help='Comma-separated list of tags')
    parser.add_argument('--price', '-p', default='0.00',
                       help='Product price (default: 0.00)')
    parser.add_argument('--sku', '-s',
                       help='Product SKU')
    parser.add_argument('--barcode', '-b',
                       help='Product barcode')
    parser.add_argument('--weight', '-w', type=float,
                       help='Product weight')
    parser.add_argument('--weight-unit', choices=['GRAMS', 'KILOGRAMS', 'OUNCES', 'POUNDS'],
                       default='KILOGRAMS', help='Weight unit (default: KILOGRAMS)')
    parser.add_argument('--inventory', '-i', type=int, default=0,
                       help='Initial inventory quantity (default: 0)')
    parser.add_argument('--no-track-inventory', action='store_true',
                       help='Disable inventory tracking')
    parser.add_argument('--status', choices=['DRAFT', 'ACTIVE', 'ARCHIVED'],
                       default='DRAFT', help='Product status (default: DRAFT)')
    
    args = parser.parse_args()
    
    # Parse tags
    tags = parse_tags(args.tags) if args.tags else None
    
    # Create product
    product = create_product(
        title=args.title,
        vendor=args.vendor,
        product_type=args.type,
        description=args.description,
        tags=tags,
        price=args.price,
        sku=args.sku,
        barcode=args.barcode,
        weight=args.weight,
        weight_unit=args.weight_unit,
        inventory_quantity=args.inventory,
        track_inventory=not args.no_track_inventory,
        status=args.status
    )
    
    if product:
        print(f"✅ Successfully created product")
        print(f"ID: {product['id']}")
        print(f"Title: {product['title']}")
        print(f"Handle: {product['handle']}")
        print(f"Status: {product['status']}")
        
        if product.get('variants', {}).get('edges'):
            variant = product['variants']['edges'][0]['node']
            print(f"Variant ID: {variant['id']}")
            if variant.get('sku'):
                print(f"SKU: {variant['sku']}")
            print(f"Price: ${variant['price']}")
        
        if tags:
            print(f"Tags: {', '.join(product['tags'])}")
    else:
        print("Failed to create product", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()