#!/usr/bin/env python3
"""
Manage Miele MAP sales based on the 2025 calendar.
Automatically applies and reverts sale prices and tags according to approved MAP windows.
"""

import os
import sys
import json
import requests
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional

# Get Shopify credentials from environment
SHOPIFY_SHOP_URL = os.environ.get('SHOPIFY_SHOP_URL')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')

if not SHOPIFY_SHOP_URL or not SHOPIFY_ACCESS_TOKEN:
    print("Error: Missing SHOPIFY_SHOP_URL or SHOPIFY_ACCESS_TOKEN environment variables")
    sys.exit(1)

# GraphQL endpoint
GRAPHQL_URL = f"{SHOPIFY_SHOP_URL}/admin/api/2024-10/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# Product definitions with variants
MIELE_PRODUCTS = {
    "CM5310": {
        "product_id": "gid://shopify/Product/6973208133666",
        "regular_price": "1849.99",
        "variants": [
            {"id": "gid://shopify/ProductVariant/40299653726242", "sku": "MIL-CM5310"}
        ]
    },
    "CM6160": {
        "product_id": "gid://shopify/Product/6976161841186",
        "regular_price": "2599.99",
        "variants": [
            {"id": "gid://shopify/ProductVariant/40309728018466", "sku": "MIL-CM6160"}
        ]
    },
    "CM6360_CleanSteel": {
        "product_id": "gid://shopify/Product/7022600486946",
        "regular_price": "2999.99",
        "variants": [
            {"id": "gid://shopify/ProductVariant/40471828889634", "sku": "MIL-CM6360-S"}
        ]
    },
    "CM6360_LotusWhite": {
        "product_id": "gid://shopify/Product/7188667498530",
        "regular_price": "2999.99",
        "variants": [
            {"id": "gid://shopify/ProductVariant/41052773253154", "sku": "MIL-CM6360-W"}
        ]
    },
    "CM7750": {
        "product_id": "gid://shopify/Product/6976240844834",
        "regular_price": "5999.99",
        "variants": [
            {"id": "gid://shopify/ProductVariant/40309899755554", "sku": "MIL-CM7750"}
        ]
    }
}

# Sale windows for 2025
SALE_WINDOWS = [
    # Format: (start_date, end_date, product_prices)
    # New Year Sale
    ("2024-12-27", "2025-01-02", {
        "CM5310": "1449.99",
        "CM6160": "2049.99"
    }),
    # January sales
    ("2025-01-10", "2025-01-16", {
        "CM5310": "1499.99",
        "CM6360": "2499.99",
        "CM7750": "5499.99"
    }),
    ("2025-01-17", "2025-01-23", {
        "CM6160": "2099.99"
    }),
    ("2025-01-30", "2025-02-06", {
        "CM5310": "1449.99",
        "CM6160": "2099.99",
        "CM7750": "5499.99"
    }),
    # Valentine's Day
    ("2025-02-07", "2025-02-13", {
        "CM5310": "1449.99",
        "CM6360": "2399.99"
    }),
    ("2025-02-14", "2025-02-20", {
        "CM5310": "1449.99"
    }),
    ("2025-02-21", "2025-03-06", {
        "CM6160": "2099.99",
        "CM7750": "5499.99"
    }),
    # March sales
    ("2025-03-14", "2025-03-27", {
        "CM5310": "1499.99",
        "CM6360": "2499.99"
    }),
    # Easter
    ("2025-04-04", "2025-04-17", {
        "CM6160": "2049.99",
        "CM7750": "5499.99"
    }),
    ("2025-04-18", "2025-04-24", {
        "CM5310": "1449.99",
        "CM6160": "2049.99",
        "CM6360": "2399.99",
        "CM7750": "5499.99"
    }),
    # Mother's Day
    ("2025-05-09", "2025-05-15", {
        "CM6160": "2049.99",
        "CM7750": "5499.99"
    }),
    # Summer sales
    ("2025-05-30", "2025-06-12", {
        "CM5310": "1449.99",
        "CM6360": "2399.99"
    }),
    ("2025-06-20", "2025-06-26", {
        "CM6160": "2099.99",
        "CM7750": "5499.99"
    }),
    # Canada Day
    ("2025-06-27", "2025-07-03", {
        "CM5310": "1499.99",
        "CM6360": "2499.99"
    }),
    # July sales
    ("2025-07-25", "2025-07-31", {
        "CM7750": "5499.99"
    }),
    # Civic Holiday
    ("2025-08-01", "2025-08-07", {
        "CM6160": "2099.99",
        "CM7750": "5499.99"
    }),
    # August sales
    ("2025-08-22", "2025-08-28", {
        "CM5310": "1499.99",
        "CM6360": "2499.99"
    }),
    # Labour Day/Back to School
    ("2025-09-05", "2025-09-18", {
        "CM6160": "2099.99",
        "CM7750": "5499.99"
    }),
    ("2025-09-19", "2025-09-25", {
        "CM5310": "1499.99",
        "CM6360": "2499.99"
    })
]

def get_product_variants(product_id: str) -> List[Dict]:
    """Get all variants for a product."""
    query = f'''{{
        product(id: "{product_id}") {{
            variants(first: 10) {{
                edges {{
                    node {{
                        id
                        sku
                        price
                        compareAtPrice
                    }}
                }}
            }}
        }}
    }}'''
    
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    data = response.json()
    
    if 'errors' in data:
        print(f"Error getting variants: {data['errors']}")
        return []
    
    variants = []
    edges = data.get('data', {}).get('product', {}).get('variants', {}).get('edges', [])
    for edge in edges:
        node = edge['node']
        variants.append({
            'id': node['id'],
            'sku': node['sku'],
            'price': node['price']
        })
    
    return variants

def update_variant_price(product_id: str, variant_id: str, price: str, compare_at: Optional[str] = None) -> bool:
    """Update variant pricing."""
    mutation = """
    mutation updateProductVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants {
                id
                price
                compareAtPrice
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variant_input = {
        "id": variant_id,
        "price": price
    }
    
    if compare_at:
        variant_input["compareAtPrice"] = compare_at
    else:
        variant_input["compareAtPrice"] = None
    
    variables = {
        "productId": product_id,
        "variants": [variant_input]
    }
    
    response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    result = response.json()
    
    if 'errors' in result:
        print(f"GraphQL Error: {result['errors']}")
        return False
    
    user_errors = result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors', [])
    if user_errors:
        print(f"User Errors: {user_errors}")
        return False
    
    return True

def update_product_tags(product_id: str, tags_to_add: List[str] = None, tags_to_remove: List[str] = None) -> bool:
    """Add or remove tags from a product."""
    operations = []
    
    if tags_to_add:
        operations.append(f'''
            tagsAdd(id: "{product_id}", tags: {json.dumps(tags_to_add)}) {{
                node {{ id }}
                userErrors {{ field message }}
            }}
        ''')
    
    if tags_to_remove:
        operations.append(f'''
            tagsRemove(id: "{product_id}", tags: {json.dumps(tags_to_remove)}) {{
                node {{ id }}
                userErrors {{ field message }}
            }}
        ''')
    
    if not operations:
        return True
    
    mutation = f"mutation updateTags {{ {' '.join(operations)} }}"
    
    response = requests.post(GRAPHQL_URL, json={"query": mutation}, headers=HEADERS)
    result = response.json()
    
    if 'errors' in result:
        print(f"GraphQL Error: {result['errors']}")
        return False
    
    return True

def get_active_sales(check_date: date) -> Dict[str, str]:
    """Get all products that should be on sale for a given date."""
    active_sales = {}
    
    for start_str, end_str, prices in SALE_WINDOWS:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        
        if start_date <= check_date <= end_date:
            active_sales.update(prices)
    
    return active_sales

def process_sales(dry_run: bool = False):
    """Process all Miele products and update prices/tags based on current date."""
    today = date.today()
    active_sales = get_active_sales(today)
    
    print(f"\n{'=' * 60}")
    print(f"Miele MAP Sales Management - {today}")
    print(f"{'=' * 60}\n")
    
    if active_sales:
        print(f"Active sales found for {len(active_sales)} products:")
        for product, price in active_sales.items():
            print(f"  - {product}: ${price}")
    else:
        print("No active sales for today.")
    
    print(f"\n{'Processing Products:':^60}")
    print(f"{'-' * 60}")
    
    updates_made = 0
    
    for product_key, product_info in MIELE_PRODUCTS.items():
        product_id = product_info['product_id']
        regular_price = product_info['regular_price']
        
        # Skip CM6360 variants for now - handle base products
        base_key = product_key.split('_')[0]
        
        # Determine if product should be on sale
        should_be_on_sale = base_key in active_sales
        sale_price = active_sales.get(base_key) if should_be_on_sale else None
        
        print(f"\n{product_key}:")
        print(f"  Regular price: ${regular_price}")
        
        if should_be_on_sale:
            print(f"  Should be on sale: YES (${sale_price})")
        else:
            print(f"  Should be on sale: NO")
        
        # Get variants if not already loaded or refresh to get current prices
        if not product_info['variants'] or 'price' not in product_info['variants'][0]:
            product_info['variants'] = get_product_variants(product_id)
        
        # Update each variant
        for variant in product_info['variants']:
            current_price = variant.get('price', '0')
            needs_price_update = False
            
            if should_be_on_sale and current_price != sale_price:
                needs_price_update = True
                print(f"  Variant {variant['sku']}: ${current_price} → ${sale_price}")
            elif not should_be_on_sale and current_price != regular_price:
                needs_price_update = True
                print(f"  Variant {variant['sku']}: ${current_price} → ${regular_price}")
            else:
                print(f"  Variant {variant['sku']}: Price correct (${current_price})")
            
            if needs_price_update and not dry_run:
                new_price = sale_price if should_be_on_sale else regular_price
                compare_at = regular_price if should_be_on_sale else None
                
                if update_variant_price(product_id, variant['id'], new_price, compare_at):
                    print(f"    ✓ Price updated")
                    updates_made += 1
                else:
                    print(f"    ✗ Price update failed")
        
        # Update tags (only for main products, not variants)
        if '_' not in product_key:  # Skip variant products
            if should_be_on_sale:
                if not dry_run and update_product_tags(product_id, tags_to_add=["mielesale"]):
                    print(f"  ✓ Added mielesale tag")
                    updates_made += 1
            else:
                if not dry_run and update_product_tags(product_id, tags_to_remove=["mielesale"]):
                    print(f"  ✓ Removed mielesale tag")
                    updates_made += 1
    
    print(f"\n{'=' * 60}")
    print(f"Summary: {updates_made} updates made")
    if dry_run:
        print("(DRY RUN - no actual changes were made)")
    print(f"{'=' * 60}\n")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Manage Miele MAP sales based on the 2025 calendar'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be changed without making updates')
    parser.add_argument('--date', type=str,
                        help='Check sales for a specific date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.date:
        # Override today's date for testing
        import datetime
        date_parts = args.date.split('-')
        test_date = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
        # Monkey patch the date
        date.today = lambda: test_date
    
    process_sales(dry_run=args.dry_run)

if __name__ == '__main__':
    main()