#!/usr/bin/env python3
"""
Set buffer quantities for products in SkuVault with channel support
Testing if channel-specific buffer settings are possible
"""

import json
import os
import sys
import requests
import csv
import argparse
import time
from typing import Dict, Any, List

def update_product_buffer(sku: str, buffer_quantity: int, buffer_mode: str = "cutoff", channel: str = None) -> Dict[str, Any]:
    """Update buffer quantity for a product in SkuVault."""
    
    # Get credentials from environment
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials. Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN")
        sys.exit(1)
    
    # API endpoint
    url = "https://app.skuvault.com/api/products/updateProduct"
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Request body - using multiple field names to increase chances of success
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "Sku": sku,
        "BufferQuantity": buffer_quantity,
        "LowQuantityCutoff": buffer_quantity,  # Alternative field name
        "MinimumQuantity": buffer_quantity,    # Another alternative
        "BufferMode": buffer_mode
    }
    
    # Add channel-related fields if channel is specified
    if channel:
        payload["Channel"] = channel
        payload["ChannelName"] = channel
        payload["IntegrationName"] = channel
        # Try channel-specific buffer fields
        payload[f"{channel}BufferQuantity"] = buffer_quantity
        payload[f"{channel}BufferMode"] = buffer_mode
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return {"Status": "Error", "Errors": [str(e)]}

def main():
    parser = argparse.ArgumentParser(
        description='Set buffer quantities for SkuVault products with channel support',
        epilog='Buffer modes: cutoff (stop selling at buffer qty), reserve (always show buffer qty available)'
    )
    
    parser.add_argument('--sku', help='Single SKU to update')
    parser.add_argument('--buffer', type=int, help='Buffer quantity to set')
    parser.add_argument('--mode', choices=['cutoff', 'reserve'], default='cutoff', 
                       help='Buffer mode (default: cutoff)')
    parser.add_argument('--channel', default='Parts Site', help='Channel name (default: Parts Site)')
    parser.add_argument('--csv', help='CSV file with SKU, Buffer Quantity, and optionally Buffer Mode columns')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    
    args = parser.parse_args()
    
    if not args.sku and not args.csv:
        parser.error('Either --sku or --csv must be provided')
    
    if args.sku and not args.buffer:
        parser.error('--buffer is required when using --sku')
    
    # Process single SKU
    if args.sku:
        print(f"Setting buffer for {args.sku}:")
        print(f"  Buffer Quantity: {args.buffer}")
        print(f"  Buffer Mode: {args.mode}")
        print(f"  Channel: {args.channel}")
        
        if args.dry_run:
            print("  [DRY RUN - No changes made]")
        else:
            result = update_product_buffer(args.sku, args.buffer, args.mode, args.channel)
            
            if result.get('Status') == 'OK':
                print("  ✓ Buffer quantity set successfully")
            else:
                print(f"  ✗ Failed to set buffer quantity")
                if result.get('Errors'):
                    print(f"  Errors: {result['Errors']}")
    
    # Process CSV file
    elif args.csv:
        try:
            with open(args.csv, 'r') as f:
                reader = csv.DictReader(f)
                
                success_count = 0
                error_count = 0
                request_count = 0
                
                for row in reader:
                    # Handle different possible column names
                    sku = row.get('SKU') or row.get('Sku') or row.get('sku')
                    buffer = row.get('Buffer Quantity') or row.get('Buffer quantity') or row.get('buffer_quantity')
                    mode = row.get('Buffer Quantity Mode') or row.get('Buffer Mode') or row.get('buffer_mode') or args.mode
                    channel = row.get('Channel') or args.channel
                    
                    if not sku or not buffer:
                        print(f"Skipping invalid row: {row}")
                        error_count += 1
                        continue
                    
                    try:
                        buffer_qty = int(buffer)
                    except ValueError:
                        print(f"Invalid buffer quantity for {sku}: {buffer}")
                        error_count += 1
                        continue
                    
                    print(f"\nProcessing {sku}:")
                    print(f"  Buffer Quantity: {buffer_qty}")
                    print(f"  Buffer Mode: {mode}")
                    print(f"  Channel: {channel}")
                    
                    if args.dry_run:
                        print("  [DRY RUN - No changes made]")
                        success_count += 1
                    else:
                        # Rate limiting: wait if we've made 10 requests
                        if request_count > 0 and request_count % 10 == 0:
                            print("  ⏸ Rate limit reached. Waiting 60 seconds...")
                            time.sleep(60)
                        
                        result = update_product_buffer(sku, buffer_qty, mode, channel)
                        request_count += 1
                        
                        if result.get('Status') == 'OK':
                            print("  ✓ Success")
                            success_count += 1
                        elif "429" in str(result.get('Errors', [])):
                            # Hit rate limit unexpectedly
                            print("  ⏸ Rate limit hit. Waiting 60 seconds before retrying...")
                            time.sleep(60)
                            # Retry once
                            result = update_product_buffer(sku, buffer_qty, mode, channel)
                            if result.get('Status') == 'OK':
                                print("  ✓ Success (after retry)")
                                success_count += 1
                            else:
                                print(f"  ✗ Failed after retry")
                                if result.get('Errors'):
                                    print(f"  Errors: {result['Errors']}")
                                error_count += 1
                        else:
                            print(f"  ✗ Failed")
                            if result.get('Errors'):
                                print(f"  Errors: {result['Errors']}")
                            error_count += 1
                
                print(f"\n{'='*50}")
                print(f"Summary:")
                print(f"  Successful: {success_count}")
                print(f"  Failed: {error_count}")
                
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()