#!/usr/bin/env python3
"""
Update SkuVault CSV with current prices from Shopify
"""

import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add current directory to path to import base
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Shopify client from base
from base import ShopifyClient

def get_products_by_skus(skus: List[str], batch_size: int = 50) -> Dict[str, Dict[str, float]]:
    """
    Fetch products from Shopify by SKUs in batches
    Returns dict mapping SKU to price info
    """
    client = ShopifyClient()
    prices = {}
    failed_skus = []
    
    # Process in batches to avoid query limits
    for i in range(0, len(skus), batch_size):
        batch = skus[i:i+batch_size]
        
        # Build query for this batch
        print(f"Fetching batch {i//batch_size + 1} of {(len(skus) + batch_size - 1)//batch_size}...")
        
        # Try batch query first
        batch_success = False
        try:
            # Escape special characters in SKUs for GraphQL
            escaped_skus = []
            for sku in batch:
                # Skip empty SKUs
                if not sku or not sku.strip():
                    continue
                # Escape backslashes first, then quotes
                escaped_sku = sku.replace('\\', '\\\\').replace('"', '\\"')
                escaped_skus.append(f'sku:"{escaped_sku}"')
            
            if not escaped_skus:
                continue
                
            sku_query = " OR ".join(escaped_skus)
            
            query = f'''
            {{
                products(first: 250, query: "{sku_query}") {{
                    edges {{
                        node {{
                            id
                            title
                            status
                            variants(first: 100) {{
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
                    }}
                }}
            }}
            '''
            
            result = client.execute_graphql(query)
            
            if result and 'data' in result:
                batch_success = True
                for edge in result['data'].get('products', {}).get('edges', []):
                    product = edge['node']
                    for variant_edge in product.get('variants', {}).get('edges', []):
                        variant = variant_edge['node']
                        if variant.get('sku'):
                            prices[variant['sku']] = {
                                'price': float(variant.get('price', 0)),
                                'compare_at_price': float(variant.get('compareAtPrice', 0)) if variant.get('compareAtPrice') else None,
                                'product_title': product.get('title', ''),
                                'status': product.get('status', '')
                            }
        except Exception as e:
            print(f"  Batch query failed: {e}")
            batch_success = False
        
        # If batch failed, try individual SKUs
        if not batch_success:
            print(f"  Trying individual SKUs for failed batch...")
            for sku in batch:
                if not sku or not sku.strip():
                    continue
                    
                try:
                    # Try exact SKU match first
                    query = '''
                    query($sku: String!) {
                        productVariants(first: 10, query: $sku) {
                            edges {
                                node {
                                    id
                                    sku
                                    price
                                    compareAtPrice
                                    product {
                                        id
                                        title
                                        status
                                    }
                                }
                            }
                        }
                    }
                    '''
                    
                    result = client.execute_graphql(query, {'sku': f'sku:{sku}'})
                    
                    if result and 'data' in result:
                        for edge in result['data'].get('productVariants', {}).get('edges', []):
                            variant = edge['node']
                            if variant.get('sku') == sku:  # Exact match
                                prices[sku] = {
                                    'price': float(variant.get('price', 0)),
                                    'compare_at_price': float(variant.get('compareAtPrice', 0)) if variant.get('compareAtPrice') else None,
                                    'product_title': variant.get('product', {}).get('title', ''),
                                    'status': variant.get('product', {}).get('status', '')
                                }
                                break
                except Exception as e:
                    failed_skus.append(sku)
                    continue
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < len(skus):
            time.sleep(0.2)
    
    if failed_skus:
        print(f"\nFailed to fetch {len(failed_skus)} SKUs")
    
    return prices

def update_csv_with_prices(input_file: str, output_file: str) -> Tuple[int, int]:
    """
    Read CSV, fetch prices from Shopify, and write updated CSV
    Returns (total_rows, found_count)
    """
    # Read the CSV and extract SKUs
    skus = []
    rows = []
    
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames.copy()
        
        for row in reader:
            sku = row.get('SKU', '').strip()
            if sku:
                skus.append(sku)
            rows.append(row)
    
    if not rows:
        print("No data found in CSV")
        return 0, 0
    
    # Add new columns if they don't exist
    new_columns = ['Shopify Price', 'Shopify Compare At Price', 'Shopify Status']
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)
    
    # Fetch prices from Shopify
    print(f"Fetching prices for {len(skus)} SKUs from Shopify...")
    price_data = get_products_by_skus(skus)
    
    # Update rows with Shopify data
    found_count = 0
    for row in rows:
        sku = row.get('SKU', '').strip()
        if sku and sku in price_data:
            data = price_data[sku]
            row['Shopify Price'] = f"${data['price']:.2f}"
            row['Shopify Compare At Price'] = f"${data['compare_at_price']:.2f}" if data['compare_at_price'] else 'N/A'
            row['Shopify Status'] = data['status']
            found_count += 1
        else:
            row['Shopify Price'] = 'N/A'
            row['Shopify Compare At Price'] = 'N/A'
            row['Shopify Status'] = 'N/A'
    
    # Write updated CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return len(rows), found_count

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Update SkuVault CSV with current Shopify prices')
    parser.add_argument('input_file', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path (default: input_file with _updated suffix)')
    
    args = parser.parse_args()
    
    # Determine output file name
    if args.output:
        output_file = args.output
    else:
        base, ext = os.path.splitext(args.input_file)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{base}_updated_{timestamp}{ext}"
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    
    # Process the CSV
    print(f"Processing: {args.input_file}")
    total_rows, found_count = update_csv_with_prices(args.input_file, output_file)
    
    print(f"\nResults:")
    print(f"- Total rows processed: {total_rows}")
    print(f"- SKUs found in Shopify: {found_count}")
    print(f"- SKUs not found: {total_rows - found_count}")
    print(f"- Output file: {output_file}")

if __name__ == "__main__":
    main()