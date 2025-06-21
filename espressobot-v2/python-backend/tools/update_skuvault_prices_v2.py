#!/usr/bin/env python3
"""
Update SkuVault CSV with current prices from Shopify - Version 2
Uses productVariants query for better SKU handling
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

def fetch_all_variants_with_prices(cursor: Optional[str] = None) -> Tuple[Dict[str, Dict], Optional[str]]:
    """
    Fetch a page of product variants with prices
    Returns (prices_dict, next_cursor)
    """
    client = ShopifyClient()
    
    query = '''
    query($cursor: String) {
        productVariants(first: 250, after: $cursor) {
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
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    '''
    
    variables = {'cursor': cursor} if cursor else {}
    
    try:
        result = client.execute_graphql(query, variables)
        
        if result and 'data' in result:
            prices = {}
            variants_data = result['data'].get('productVariants', {})
            
            for edge in variants_data.get('edges', []):
                variant = edge['node']
                sku = variant.get('sku')
                if sku and isinstance(sku, str):
                    sku = sku.strip()
                    if sku:  # Only process variants with non-empty SKUs
                        prices[sku] = {
                            'price': float(variant.get('price', 0)),
                            'compare_at_price': float(variant.get('compareAtPrice', 0)) if variant.get('compareAtPrice') else None,
                            'product_title': variant.get('product', {}).get('title', ''),
                            'status': variant.get('product', {}).get('status', '')
                        }
            
            page_info = variants_data.get('pageInfo', {})
            next_cursor = page_info.get('endCursor') if page_info.get('hasNextPage') else None
            
            return prices, next_cursor
    except Exception as e:
        print(f"Error fetching variants: {e}")
        return {}, None

def get_all_shopify_prices() -> Dict[str, Dict]:
    """
    Fetch all product variants with prices from Shopify
    Returns dict mapping SKU to price info
    """
    all_prices = {}
    cursor = None
    page = 1
    
    print("Fetching all product variants from Shopify...")
    
    while True:
        print(f"  Fetching page {page}...")
        prices, next_cursor = fetch_all_variants_with_prices(cursor)
        
        if prices:
            all_prices.update(prices)
            print(f"    Found {len(prices)} variants (total: {len(all_prices)})")
        
        if not next_cursor:
            break
            
        cursor = next_cursor
        page += 1
        time.sleep(0.2)  # Small delay to avoid rate limiting
    
    print(f"Total variants found: {len(all_prices)}")
    return all_prices

def update_csv_with_prices(input_file: str, output_file: str) -> Tuple[int, int]:
    """
    Read CSV, match prices from Shopify, and write updated CSV
    Returns (total_rows, found_count)
    """
    # First, get all prices from Shopify
    shopify_prices = get_all_shopify_prices()
    
    # Read the CSV and update with prices
    rows = []
    found_count = 0
    
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames.copy()
        
        # Add new columns if they don't exist
        new_columns = ['Shopify Price', 'Shopify Compare At Price', 'Shopify Status', 'Shopify Product']
        for col in new_columns:
            if col not in fieldnames:
                fieldnames.append(col)
        
        for row in reader:
            sku = row.get('SKU', '').strip()
            
            if sku and sku in shopify_prices:
                data = shopify_prices[sku]
                row['Shopify Price'] = f"${data['price']:.2f}"
                row['Shopify Compare At Price'] = f"${data['compare_at_price']:.2f}" if data['compare_at_price'] else 'N/A'
                row['Shopify Status'] = data['status']
                row['Shopify Product'] = data['product_title']
                found_count += 1
            else:
                row['Shopify Price'] = 'N/A'
                row['Shopify Compare At Price'] = 'N/A'
                row['Shopify Status'] = 'N/A'
                row['Shopify Product'] = 'N/A'
            
            rows.append(row)
    
    # Write updated CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return len(rows), found_count

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Update SkuVault CSV with current Shopify prices (v2)')
    parser.add_argument('input_file', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path (default: input_file with _updated suffix)')
    parser.add_argument('--quick', action='store_true', help='Quick mode - only fetch first 1000 variants')
    
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
    start_time = time.time()
    
    total_rows, found_count = update_csv_with_prices(args.input_file, output_file)
    
    elapsed_time = time.time() - start_time
    print(f"\nResults:")
    print(f"- Total rows processed: {total_rows}")
    print(f"- SKUs found in Shopify: {found_count}")
    print(f"- SKUs not found: {total_rows - found_count}")
    print(f"- Output file: {output_file}")
    print(f"- Time elapsed: {elapsed_time:.1f} seconds")

if __name__ == "__main__":
    main()