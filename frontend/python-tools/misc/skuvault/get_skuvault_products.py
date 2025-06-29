#!/usr/bin/env python3
"""
Fetch product information from SkuVault API based on SKUs
Retrieves product codes, descriptions, quantities, and other details
"""

import json
import os
import sys
import requests
import csv
import argparse
from typing import List, Dict, Any

def get_skuvault_products(skus: List[str]) -> Dict[str, Any]:
    """Fetch product details from SkuVault API."""
    
    # Get credentials from environment
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials. Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN")
        sys.exit(1)
    
    # API endpoint
    url = "https://app.skuvault.com/api/products/getProducts"
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Request body - include auth tokens and use ProductSKUs
    payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token,
        "ProductSKUs": skus,
        "IncludeKitLines": True
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        sys.exit(1)

def extract_channel_info(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract channel information from a product if available."""
    channels = []
    
    # Check for ChannelQuantities or similar fields
    if 'ChannelQuantities' in product:
        for channel in product['ChannelQuantities']:
            channels.append({
                'ChannelName': channel.get('ChannelName', 'Unknown'),
                'AvailableQuantity': channel.get('AvailableQuantity', 0),
                'ReservedQuantity': channel.get('ReservedQuantity', 0),
                'TotalQuantity': channel.get('TotalQuantity', 0)
            })
    
    return channels

def main():
    parser = argparse.ArgumentParser(description='Fetch product information from SkuVault')
    parser.add_argument('--skus', nargs='+', help='List of SKUs to fetch')
    parser.add_argument('--csv', help='CSV file containing SKUs')
    parser.add_argument('--sku-column', default='SKU', help='Column name for SKUs in CSV (default: SKU)')
    parser.add_argument('--output-json', help='Output JSON file path')
    parser.add_argument('--output-csv', help='Output CSV file path')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    if not args.skus and not args.csv:
        parser.error('Either --skus or --csv must be provided')
    
    # Collect SKUs
    skus = []
    
    if args.skus:
        skus.extend(args.skus)
    
    if args.csv:
        try:
            with open(args.csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get(args.sku_column):
                        skus.append(row[args.sku_column])
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            sys.exit(1)
    
    if not skus:
        print("No SKUs found to process")
        sys.exit(1)
    
    print(f"Fetching data for {len(skus)} SKUs from SkuVault...")
    
    # Fetch products from SkuVault
    result = get_skuvault_products(skus)
    
    # Check response status
    if result.get('Status') != 'OK' and 'Products' not in result:
        print(f"Error: API returned status: {result.get('Status')}")
        if 'Errors' in result and result['Errors']:
            print(f"Errors: {result['Errors']}")
        sys.exit(1)
    
    # Process results
    if 'Products' in result:
        products = result['Products']
        print(f"\nFound {len(products)} products in SkuVault")
        
        # Create output data
        output_data = []
        
        for product in products:
            sku = product.get('Sku', 'Unknown')
            code = product.get('Code', 'Unknown')
            description = product.get('Description', 'N/A')
            quantity_available = product.get('QuantityAvailable', 0)
            quantity_on_hand = product.get('QuantityOnHand', 0)
            cost = product.get('Cost', 0)
            sale_price = product.get('SalePrice', 0)
            
            # Get channel information
            channels = extract_channel_info(product)
            
            if args.verbose:
                print(f"\nSKU: {sku}")
                print(f"Code: {code}")
                print(f"Description: {description}")
                print(f"Quantity Available: {quantity_available}")
                print(f"Quantity On Hand: {quantity_on_hand}")
                print(f"Cost: ${cost}")
                print(f"Sale Price: ${sale_price}")
                
                if channels:
                    print("Channels:")
                    for channel in channels:
                        print(f"  - {channel['ChannelName']}: Available={channel['AvailableQuantity']}")
            
            # Add to output data
            output_data.append({
                'SKU': sku,
                'Code': code,
                'Description': description,
                'QuantityAvailable': quantity_available,
                'QuantityOnHand': quantity_on_hand,
                'Cost': cost,
                'SalePrice': sale_price,
                'Channels': channels
            })
        
        # Save JSON output if requested
        if args.output_json:
            with open(args.output_json, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nJSON results saved to: {args.output_json}")
        
        # Save CSV output if requested
        if args.output_csv:
            with open(args.output_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['SKU', 'Code', 'Description', 'Quantity Available', 'Quantity On Hand', 'Cost', 'Sale Price'])
                
                for item in output_data:
                    writer.writerow([
                        item['SKU'],
                        item['Code'],
                        item['Description'],
                        item['QuantityAvailable'],
                        item['QuantityOnHand'],
                        item['Cost'],
                        item['SalePrice']
                    ])
            
            print(f"CSV results saved to: {args.output_csv}")
        
        # If no output files specified, print summary
        if not args.output_json and not args.output_csv and not args.verbose:
            print("\nSummary:")
            for item in output_data:
                print(f"{item['SKU']} -> Code: {item['Code']}")
        
    else:
        print("No products found in response")

if __name__ == "__main__":
    main()