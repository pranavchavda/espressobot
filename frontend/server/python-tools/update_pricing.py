#!/usr/bin/env python3
"""Update product variant pricing."""

import sys
import argparse
from base import ShopifyClient, print_json, format_price


def update_variant_pricing(product_id: str, variant_id: str, price: str = None, 
                         compare_at_price: str = None, cost: str = None):
    """Update pricing for a product variant."""
    client = ShopifyClient()
    
    # Normalize IDs
    product_id = client.normalize_id(product_id)
    if not variant_id.startswith('gid://'):
        variant_id = f"gid://shopify/ProductVariant/{variant_id}"
    
    # Build variant input
    variant_input = {'id': variant_id}
    
    if price is not None:
        variant_input['price'] = format_price(price)
    
    if compare_at_price is not None:
        variant_input['compareAtPrice'] = format_price(compare_at_price) if compare_at_price else None
    
    # Execute mutation
    mutation = '''
    mutation updateVariantPricing($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            product {
                id
                title
            }
            productVariants {
                id
                title
                price
                compareAtPrice
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
        'variants': [variant_input]
    }
    
    result = client.execute_graphql(mutation, variables)
    
    # Check for errors
    if not client.check_user_errors(result, 'productVariantsBulkUpdate'):
        sys.exit(1)
    
    # Handle cost update separately if provided
    if cost is not None:
        cost_result = update_variant_cost(client, variant_id, cost)
        if cost_result:
            result['cost_update'] = cost_result
    
    return result


def update_variant_cost(client: ShopifyClient, variant_id: str, cost: str):
    """Update inventory item cost (separate mutation)."""
    # First get the inventory item ID
    query = '''
    query getInventoryItem($id: ID!) {
        productVariant(id: $id) {
            inventoryItem {
                id
            }
        }
    }
    '''
    
    inv_result = client.execute_graphql(query, {'id': variant_id})
    inventory_item = inv_result.get('data', {}).get('productVariant', {}).get('inventoryItem')
    
    if not inventory_item:
        print("Warning: Could not find inventory item for cost update", file=sys.stderr)
        return None
    
    # Update cost
    mutation = '''
    mutation updateCost($id: ID!, $input: InventoryItemInput!) {
        inventoryItemUpdate(id: $id, input: $input) {
            inventoryItem {
                id
                unitCost {
                    amount
                    currencyCode
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    '''
    
    variables = {
        'id': inventory_item['id'],
        'input': {
            'cost': format_price(cost)
        }
    }
    
    cost_result = client.execute_graphql(mutation, variables)
    
    if not client.check_user_errors(cost_result, 'inventoryItemUpdate'):
        return None
    
    return cost_result.get('data', {}).get('inventoryItemUpdate')


def main():
    parser = argparse.ArgumentParser(
        description='Update product variant pricing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Update price only
  python update_pricing.py --product-id 1234567890 --variant-id 9876543210 --price 29.99
  
  # Update price and compare-at price
  python update_pricing.py -p 1234567890 -v 9876543210 --price 29.99 --compare-at 39.99
  
  # Clear compare-at price
  python update_pricing.py -p 1234567890 -v 9876543210 --compare-at ""
  
  # Update all pricing
  python update_pricing.py -p 1234567890 -v 9876543210 --price 29.99 --compare-at 39.99 --cost 15.00
        '''
    )
    
    parser.add_argument('--product-id', '-p', required=True,
                       help='Product ID (numeric or GID format)')
    parser.add_argument('--variant-id', '-v', required=True,
                       help='Variant ID to update')
    parser.add_argument('--price', help='New price')
    parser.add_argument('--compare-at', '--compare-at-price',
                       help='Compare at price (use "" to clear)')
    parser.add_argument('--cost', help='Unit cost for inventory tracking')
    
    args = parser.parse_args()
    
    # Validate that at least one price field is provided
    if not any([args.price, args.compare_at, args.cost]):
        print("Error: Must provide at least one of --price, --compare-at, or --cost", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    # Update pricing
    result = update_variant_pricing(
        args.product_id,
        args.variant_id,
        args.price,
        args.compare_at,
        args.cost
    )
    
    # Display results
    update_data = result.get('data', {}).get('productVariantsBulkUpdate', {})
    
    if update_data.get('productVariants'):
        variant = update_data['productVariants'][0]
        print(f"✅ Successfully updated variant pricing")
        print(f"Product: {update_data['product']['title']}")
        print(f"Variant: {variant['title']}")
        print(f"Price: ${variant['price']}")
        if variant.get('compareAtPrice'):
            print(f"Compare at: ${variant['compareAtPrice']}")
        
        if 'cost_update' in result:
            cost_data = result['cost_update'].get('inventoryItem', {}).get('unitCost')
            if cost_data:
                print(f"Cost: ${cost_data['amount']}")
    else:
        print("No variants were updated", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()