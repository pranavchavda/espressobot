#!/usr/bin/env python3
"""Wrapper for update_pricing that handles identifier resolution."""

import sys
import argparse
from update_pricing import update_variant_pricing
from get_product import get_product


def update_pricing_by_identifier(identifier: str, price: str = None, 
                                compare_at_price: str = None, cost: str = None):
    """Update pricing for a product using any identifier (SKU, handle, ID, etc)."""
    
    # First, get the product details
    product = get_product(identifier)
    
    if not product:
        print(f"Error: Product not found with identifier: {identifier}", file=sys.stderr)
        sys.exit(1)
    
    # Extract product and variant IDs
    product_id = product['id'].split('/')[-1]  # Extract numeric ID from GID
    
    # Get the first variant (or the one matching the SKU if provided)
    variant = None
    variants = product.get('variants', {}).get('edges', [])
    
    if variants:
        # If identifier is a SKU, find matching variant
        for edge in variants:
            v = edge['node']
            if v.get('sku') == identifier:
                variant = v
                break
        
        # Otherwise use first variant
        if not variant and variants:
            variant = variants[0]['node']
    
    if not variant:
        print(f"Error: No variant found for product: {identifier}", file=sys.stderr)
        sys.exit(1)
    
    variant_id = variant['id'].split('/')[-1]  # Extract numeric ID from GID
    
    # Call the original update function
    result = update_variant_pricing(product_id, variant_id, price, compare_at_price, cost)
    
    # Add some helpful info to the result
    print(f"✅ Successfully updated pricing for {product['title']} (SKU: {variant.get('sku', 'N/A')})")
    if price:
        print(f"   New price: ${price}")
    if compare_at_price is not None:
        print(f"   Compare at price: ${compare_at_price if compare_at_price else 'Cleared'}")
    if cost:
        print(f"   Cost: ${cost}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Update product pricing by identifier (SKU, handle, ID, or title)'
    )
    
    parser.add_argument('identifier', 
                       help='Product identifier (SKU, handle, product ID, or title)')
    parser.add_argument('--price', '-p',
                       help='New price')
    parser.add_argument('--compare-at', '--compare-at-price', '-c',
                       help='Compare at price (use "" to clear)')
    parser.add_argument('--cost',
                       help='Unit cost for inventory tracking')
    
    args = parser.parse_args()
    
    if not any([args.price, args.compare_at, args.cost]):
        parser.error("At least one of --price, --compare-at, or --cost must be specified")
    
    update_pricing_by_identifier(
        args.identifier,
        args.price,
        args.compare_at,
        args.cost
    )


if __name__ == '__main__':
    main()