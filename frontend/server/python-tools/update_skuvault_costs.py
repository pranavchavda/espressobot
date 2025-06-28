#!/usr/bin/env python3
"""Update product costs in SkuVault from CSV file."""

import csv
import json
import os
import sys
import requests
import time
from typing import List, Dict


def update_skuvault_costs(updates: List[Dict[str, str]], dry_run: bool = False):
    """Update costs for multiple products in SkuVault."""
    
    # Get credentials from environment
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials. Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN")
        sys.exit(1)
    
    # API endpoint
    url = "https://app.skuvault.com/api/products/updateProducts"
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Process in batches of 100
    batch_size = 100
    total_updated = 0
    total_failed = 0
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        
        # Build products array for this batch
        products = []
        for update in batch:
            # Only include SKU and Cost for updates
            product = {
                "Sku": update['sku'],
                "Cost": float(update['cost'])
            }
            products.append(product)
        
        print(f"\nProcessing batch {i//batch_size + 1} ({len(products)} products)...")
        
        if dry_run:
            for p in products:
                print(f"  Would update {p['Sku']} - Cost: ${p['Cost']:.2f}")
            total_updated += len(products)
            continue
        
        # Request body - auth tokens must be in the payload
        payload = {
            "TenantToken": tenant_token,
            "UserToken": user_token,
            "Products": products
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # Check response
            if result.get('Status') == 'OK':
                print(f"  ✓ Successfully updated {len(products)} products")
                total_updated += len(products)
            else:
                print(f"  ✗ Error: {result.get('Status', 'Unknown error')}")
                if 'Errors' in result:
                    for error in result['Errors']:
                        print(f"    - {error}")
                total_failed += len(products)
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ API request failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"    Response: {e.response.text}")
            total_failed += len(products)
        
        # Rate limiting - be nice to the API
        if i + batch_size < len(updates):
            time.sleep(1)
    
    return total_updated, total_failed


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Update product costs in SkuVault from CSV',
        epilog='''
CSV Format:
  sku,cost
  COFFEE-001,12.50
  COFFEE-002,15.00
        '''
    )
    
    parser.add_argument('csv_file', help='CSV file with sku and cost columns')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without updating')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"Error: File {args.csv_file} not found")
        sys.exit(1)
    
    # Read CSV
    updates = []
    with open(args.csv_file, 'r') as f:
        reader = csv.DictReader(f)
        
        if 'sku' not in reader.fieldnames or 'cost' not in reader.fieldnames:
            print("Error: CSV must have 'sku' and 'cost' columns")
            sys.exit(1)
        
        for row in reader:
            if row['sku'] and row['cost']:
                updates.append({
                    'sku': row['sku'].strip(),
                    'cost': row['cost'].strip()
                })
    
    if not updates:
        print("No valid updates found in CSV file")
        sys.exit(1)
    
    print(f"Found {len(updates)} cost updates to process")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Process updates
    updated, failed = update_skuvault_costs(updates, args.dry_run)
    
    # Summary
    print("\n" + "="*60)
    print(f"Summary:")
    print(f"  ✓ {'Would update' if args.dry_run else 'Updated'}: {updated}")
    print(f"  ✗ Failed: {failed}")
    print(f"  Total: {updated + failed}")


if __name__ == "__main__":
    main()