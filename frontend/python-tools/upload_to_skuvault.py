#!/usr/bin/env python
"""
Upload products from Shopify to SkuVault

This tool fetches product data from Shopify and uploads it to SkuVault's inventory management system.
Supports both single product uploads and batch uploads.

Usage:
    # Upload single product by SKU
    python upload_to_skuvault.py --sku "COFFEE-001"
    
    # Upload multiple products (comma-separated)
    python upload_to_skuvault.py --sku "COFFEE-001,GRINDER-002,MACHINE-003"
    
    # Upload from file containing SKUs (one per line)
    python upload_to_skuvault.py --file skus.txt
    
    # Dry run to preview without uploading
    python upload_to_skuvault.py --sku "COFFEE-001" --dry-run

Required environment variables:
    SKUVAULT_TENANT_TOKEN: Your SkuVault tenant token
    SKUVAULT_USER_TOKEN: Your SkuVault user token
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import ShopifyClient


class SkuVaultUploader(ShopifyClient):
    """Tool for uploading products from Shopify to SkuVault"""
    
    def __init__(self):
        super().__init__()
        
        # Load SkuVault credentials
        self.skuvault_tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
        self.skuvault_user_token = os.environ.get('SKUVAULT_USER_TOKEN')
        
        if not self.skuvault_tenant_token or not self.skuvault_user_token:
            print("⚠️  Warning: SkuVault credentials not found in environment variables.")
            print("   Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN")
    
    def fetch_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Fetch product data from Shopify by SKU"""
        query = """
        query getProductBySku($sku: String!) {
            productVariants(first: 1, query: $sku) {
                edges {
                    node {
                        id
                        sku
                        price
                        inventoryItem {
                            id
                            unitCost {
                                amount
                            }
                        }
                        product {
                            id
                            title
                            vendor
                            productType
                            description
                            images(first: 5) {
                                edges {
                                    node {
                                        src
                                        altText
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {"sku": f"sku:{sku}"}
        result = self.execute_graphql(query, variables)
        
        if 'errors' in result:
            print(f"❌ Error fetching SKU {sku}: {result['errors']}")
            return None
        
        edges = result.get('data', {}).get('productVariants', {}).get('edges', [])
        if not edges:
            print(f"❌ No product found with SKU: {sku}")
            return None
        
        return edges[0]['node']
    
    def prepare_skuvault_data(self, shopify_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Shopify product data to SkuVault format"""
        variant = shopify_data
        product = variant.get('product', {})
        
        # Extract basic info
        title = product.get('title', '')
        vendor = product.get('vendor', 'Unknown')
        sku = variant.get('sku', '')
        price = float(variant.get('price', 0))
        
        # Extract cost
        inventory_item = variant.get('inventoryItem', {})
        unit_cost = inventory_item.get('unitCost', {})
        cost = float(unit_cost.get('amount', 0)) if unit_cost else 0
        
        # Extract images
        images = []
        for edge in product.get('images', {}).get('edges', []):
            if 'node' in edge and 'src' in edge['node']:
                images.append(edge['node']['src'])
        
        # Build SkuVault product data
        return {
            "Sku": sku,
            "PartNumber": sku,
            "Description": title,
            "ShortDescription": title[:100] if len(title) > 100 else title,
            "LongDescription": product.get('description', title),
            "Classification": "General",  # Default classification for SkuVault
            "Supplier": "Unknown",  # Default supplier to avoid validation errors
            "Brand": vendor,
            "Cost": cost,
            "SalePrice": price,
            "RetailPrice": price,
            "AllowCreateAp": False,
            "IsSerialized": False,
            "IsLotted": False,
            "Pictures": images[:5],  # SkuVault typically limits to 5 images
            "TenantToken": self.skuvault_tenant_token,
            "UserToken": self.skuvault_user_token
        }
    
    def upload_to_skuvault(self, product_data: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Upload product data to SkuVault"""
        if dry_run:
            print(f"\n🔍 Dry run - would upload:")
            print(json.dumps({k: v for k, v in product_data.items() 
                            if k not in ['TenantToken', 'UserToken']}, indent=2))
            return {"success": True, "message": "Dry run completed"}
        
        if not self.skuvault_tenant_token or not self.skuvault_user_token:
            return {
                "success": False,
                "message": "SkuVault credentials not configured"
            }
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                'https://app.skuvault.com/api/products/createProduct',
                headers=headers,
                json=product_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Product '{product_data['Sku']}' uploaded successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed with status {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Request error: {str(e)}"
            }
    
    def process_sku(self, sku: str, dry_run: bool = False) -> Dict[str, Any]:
        """Process a single SKU: fetch from Shopify and upload to SkuVault"""
        print(f"\n📦 Processing SKU: {sku}")
        
        # Fetch from Shopify
        shopify_data = self.fetch_product_by_sku(sku)
        if not shopify_data:
            return {
                "sku": sku,
                "success": False,
                "message": "Failed to fetch from Shopify"
            }
        
        # Prepare for SkuVault
        skuvault_data = self.prepare_skuvault_data(shopify_data)
        
        # Upload to SkuVault
        result = self.upload_to_skuvault(skuvault_data, dry_run)
        result["sku"] = sku
        
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
        
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Upload products from Shopify to SkuVault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--sku',
        help='Single SKU or comma-separated list of SKUs to upload'
    )
    
    parser.add_argument(
        '--file',
        help='File containing SKUs (one per line)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be uploaded without actually uploading'
    )
    
    args = parser.parse_args()
    
    if not args.sku and not args.file:
        parser.error("Either --sku or --file must be provided")
    
    # Initialize uploader
    uploader = SkuVaultUploader()
    
    # Collect SKUs to process
    skus = []
    
    if args.sku:
        # Handle comma-separated SKUs
        skus.extend([s.strip() for s in args.sku.split(',') if s.strip()])
    
    if args.file:
        # Read SKUs from file
        try:
            with open(args.file, 'r') as f:
                skus.extend([line.strip() for line in f if line.strip()])
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            sys.exit(1)
    
    if not skus:
        print("❌ No SKUs to process")
        sys.exit(1)
    
    # Process SKUs
    print(f"\n🚀 Processing {len(skus)} SKU(s)...")
    if args.dry_run:
        print("   (DRY RUN - no actual uploads will occur)")
    
    results = []
    success_count = 0
    
    for sku in skus:
        result = uploader.process_sku(sku, args.dry_run)
        results.append(result)
        if result["success"]:
            success_count += 1
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total processed: {len(results)}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {len(results) - success_count}")
    
    # Show failures
    failures = [r for r in results if not r["success"]]
    if failures:
        print(f"\n❌ Failed SKUs:")
        for failure in failures:
            print(f"   - {failure['sku']}: {failure['message']}")
    
    # Exit with appropriate code
    sys.exit(0 if success_count == len(results) else 1)


if __name__ == "__main__":
    main()