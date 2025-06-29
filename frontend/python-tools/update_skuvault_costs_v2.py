#!/usr/bin/env python3
"""Update product costs in SkuVault from CSV file - Version 2 using single product updates."""

import csv
import json
import os
import sys
import requests
import time
from typing import List, Dict


def update_single_product_cost(sku: str, cost: float, tenant_token: str, user_token: str):
    """Update cost for a single product in SkuVault."""
    
    # API endpoint for single product update
    url = "https://app.skuvault.com/api/products/updateProduct"
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Request body
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "Sku": sku,
        "Cost": cost
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # Check response
        if result.get('Status') == 'OK':
            return True, "Success"
        else:
            return False, result.get('Status', 'Unknown error')
            
    except requests.exceptions.RequestException as e:
        return False, f"API request failed: {e}"


def update_skuvault_costs(updates: List[Dict[str, str]], dry_run: bool = False):
    """Update costs for multiple products in SkuVault using individual API calls."""
    
    # Get credentials from environment
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials. Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN")
        sys.exit(1)
    
    total_updated = 0
    total_failed = 0
    
    print(f"Processing {len(updates)} products individually...")
    
    for i, update in enumerate(updates, 1):
        sku = update['sku']
        cost = float(update['cost'])
        
        print(f"\n[{i}/{len(updates)}] {sku} - Cost: ${cost:.2f}")
        
        if dry_run:
            print(f"  🔍 Would update")
            total_updated += 1
            continue
        
        # Update the product
        success, message = update_single_product_cost(sku, cost, tenant_token, user_token)
        
        if success:
            print(f"  ✓ Updated successfully")
            total_updated += 1
        else:
            print(f"  ✗ Failed: {message}")
            total_failed += 1
        
        # Rate limiting - API allows only 10 calls per minute
        # So we need to wait 6 seconds between calls (60 sec / 10 calls = 6 sec)
        if i < len(updates):
            if i % 10 == 0:
                print("  ⏳ Waiting 60 seconds to avoid rate limit...")
                time.sleep(60)
            else:
                time.sleep(6)
    
    return total_updated, total_failed


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Update product costs in SkuVault from CSV (v2 - single product updates)',
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
    parser.add_argument('--limit', type=int, 
                       help='Limit number of products to update (for testing)')
    
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
                
                if args.limit and len(updates) >= args.limit:
                    break
    
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