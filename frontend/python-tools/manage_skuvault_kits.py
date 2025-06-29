#!/usr/bin/env python3
"""
Manage SkuVault kits (bundles/combos)

This tool allows creating, updating, and removing kits in SkuVault.
A kit is a group of products sold together as a single SKU.

Usage:
    # Create a kit from components
    python manage_skuvault_kits.py --action create --kit-sku "COMBO-2506-BE-ES" \
        --components "BES870XL:1,EUREKA-SPEC:1" \
        --title "Breville Barista Express + Eureka Specialita Combo"
    
    # Update kit components
    python manage_skuvault_kits.py --action update --kit-sku "COMBO-2506-BE-ES" \
        --components "BES870XL:1,EUREKA-SPEC:1,COFFEE-BAG:2"
    
    # Remove a kit
    python manage_skuvault_kits.py --action remove --kit-sku "COMBO-2506-BE-ES"
    
    # List all kits
    python manage_skuvault_kits.py --action list
    
    # Get kit details
    python manage_skuvault_kits.py --action get --kit-sku "COMBO-2506-BE-ES"
    
    # Create from CSV file
    python manage_skuvault_kits.py --action create-bulk --file kits.csv

Required environment variables:
    SKUVAULT_TENANT_TOKEN: Your SkuVault tenant token
    SKUVAULT_USER_TOKEN: Your SkuVault user token
"""

import os
import sys
import json
import argparse
import requests
import csv
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import ShopifyClient


class SkuVaultKitManager:
    """Manage kits in SkuVault"""
    
    def __init__(self):
        # Load SkuVault credentials
        self.tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
        self.user_token = os.environ.get('SKUVAULT_USER_TOKEN')
        
        if not self.tenant_token or not self.user_token:
            print("Error: Missing SkuVault credentials", file=sys.stderr)
            print("Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN", file=sys.stderr)
            sys.exit(1)
        
        self.base_url = "https://app.skuvault.com/api"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to SkuVault API"""
        url = f"{self.base_url}/{endpoint}"
        
        # Add credentials to the request body
        request_body = {
            "TenantToken": self.tenant_token,
            "UserToken": self.user_token,
            **data
        }
        
        try:
            response = requests.post(url, json=request_body, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}", file=sys.stderr)
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)
    
    def parse_components(self, components_str: str) -> List[Tuple[str, int]]:
        """Parse component string into list of (sku, quantity) tuples
        Format: "SKU1:QTY1,SKU2:QTY2"
        """
        components = []
        for component in components_str.split(','):
            component = component.strip()
            if ':' in component:
                sku, qty = component.split(':', 1)
                try:
                    quantity = int(qty)
                    if quantity <= 0:
                        print(f"Warning: Invalid quantity {quantity} for {sku}, using 1", file=sys.stderr)
                        quantity = 1
                    components.append((sku.strip(), quantity))
                except ValueError:
                    print(f"Warning: Invalid quantity '{qty}' for {sku}, using 1", file=sys.stderr)
                    components.append((sku.strip(), 1))
            else:
                # Default quantity is 1
                components.append((component.strip(), 1))
        
        return components
    
    def create_kit(self, kit_sku: str, components: List[Tuple[str, int]], 
                   title: Optional[str] = None, dry_run: bool = False) -> bool:
        """Create a new kit in SkuVault"""
        
        if not components:
            print("Error: At least one component is required", file=sys.stderr)
            return False
        
        # Build kit data according to SkuVault API spec
        # Based on working curl, KitLines should be an array, not an object
        kit_lines = []
        
        # Create a line for each component
        for sku, quantity in components:
            kit_line = {
                "LineName": sku,  # Will use SKU as line name for now
                "Combine": 3,     # Use 3 as it works in the curl example
                "Quantity": quantity,
                "Items": [sku]
            }
            kit_lines.append(kit_line)
        
        kit_data = {
            "Sku": kit_sku,
            "Title": title or f"Kit {kit_sku}",  # Back to "Title" as per correction
            "KitLines": kit_lines
            # No Code or AllowCreateAp needed based on working example
        }
        
        print(f"\nCreating kit: {kit_sku}")
        print(f"Title: {kit_data['Title']}")
        print(f"Components:")
        for sku, qty in components:
            print(f"  - {sku}: {qty}")
        
        if dry_run:
            print("\n[DRY RUN] Kit would be created with above details")
            return True
        
        # Make API call
        if os.environ.get('DEBUG'):
            print(f"\nDEBUG - Sending request: {json.dumps(kit_data, indent=2)}")
        response = self._make_request("products/createKit", kit_data)
        
        # Check response
        if os.environ.get('DEBUG'):
            print(f"\nDEBUG - Response: {json.dumps(response, indent=2)}")
            
        if response.get("Status") in ["OK", "Success"]:
            print(f"\n✅ Kit created successfully: {kit_sku}")
            return True
        else:
            errors = response.get("Errors", [])
            # If no errors and no explicit failure status, might still be success
            if not errors and response.get("Status") != "Error":
                print(f"\n✅ Kit likely created successfully: {kit_sku}")
                print(f"   Response: {response}")
                return True
            print(f"\n❌ Failed to create kit: {errors}", file=sys.stderr)
            return False
    
    def update_kit(self, kit_sku: str, components: List[Tuple[str, int]], 
                   dry_run: bool = False) -> bool:
        """Update an existing kit's components"""
        
        # First remove the old kit
        print(f"\nUpdating kit: {kit_sku}")
        
        if not dry_run:
            # Remove existing kit
            remove_response = self._make_request("products/removeKit", {"Sku": kit_sku})
            if remove_response.get("Status") != "OK":
                print(f"Warning: Could not remove existing kit: {remove_response.get('Errors', [])}")
        
        # Create new kit with updated components
        return self.create_kit(kit_sku, components, dry_run=dry_run)
    
    def remove_kit(self, kit_sku: str, dry_run: bool = False) -> bool:
        """Remove a kit from SkuVault"""
        
        print(f"\nRemoving kit: {kit_sku}")
        
        if dry_run:
            print(f"[DRY RUN] Kit {kit_sku} would be removed")
            return True
        
        response = self._make_request("products/removeKit", {"Sku": kit_sku})
        
        if response.get("Status") == "OK":
            print(f"✅ Kit removed successfully: {kit_sku}")
            return True
        else:
            errors = response.get("Errors", [])
            print(f"❌ Failed to remove kit: {errors}", file=sys.stderr)
            return False
    
    def get_kit(self, kit_sku: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific kit"""
        
        # Get product details which includes kit info
        response = self._make_request("products/getProducts", {
            "ProductSKUs": [kit_sku],
            "IncludeKitLines": True
        })
        
        if response.get("Status") == "OK" and response.get("Products"):
            product = response["Products"][0]
            if product.get("KitLines"):
                print(f"\nKit: {kit_sku}")
                print(f"Description: {product.get('Description', 'N/A')}")
                print(f"Components:")
                for line in product["KitLines"]:
                    print(f"  - {line['SKU']}: {line['Quantity']}")
                return product
            else:
                print(f"Product {kit_sku} exists but is not a kit", file=sys.stderr)
                return None
        else:
            print(f"Kit not found: {kit_sku}", file=sys.stderr)
            return None
    
    def list_kits(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all kits (products with kit lines)"""
        
        # This is a simplified version - in production you'd want pagination
        print("\nFetching kits...")
        print("Note: This shows a sample of products. Full kit listing requires pagination.")
        
        # Get sample of products
        response = self._make_request("products/getProducts", {
            "PageNumber": 1,
            "PageSize": limit,
            "IncludeKitLines": True
        })
        
        if response.get("Status") == "OK":
            kits = []
            for product in response.get("Products", []):
                if product.get("KitLines"):
                    kits.append(product)
                    print(f"\nKit: {product['Sku']}")
                    print(f"Description: {product.get('Description', 'N/A')}")
                    print(f"Components:")
                    for line in product["KitLines"]:
                        print(f"  - {line['SKU']}: {line['Quantity']}")
            
            if not kits:
                print("No kits found in the first page of products")
            
            return kits
        else:
            print(f"Failed to list kits: {response.get('Errors', [])}", file=sys.stderr)
            return []
    
    def create_bulk_from_csv(self, csv_file: str, dry_run: bool = False) -> None:
        """Create multiple kits from CSV file
        
        CSV format:
        kit_sku,title,components
        COMBO-001,"Coffee Combo","COFFEE-001:1,GRINDER-001:1"
        """
        
        if not os.path.exists(csv_file):
            print(f"Error: CSV file not found: {csv_file}", file=sys.stderr)
            sys.exit(1)
        
        success_count = 0
        error_count = 0
        
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                kit_sku = row.get('kit_sku', '').strip()
                title = row.get('title', '').strip()
                components_str = row.get('components', '').strip()
                
                if not kit_sku or not components_str:
                    print(f"Skipping invalid row: {row}")
                    error_count += 1
                    continue
                
                components = self.parse_components(components_str)
                
                if self.create_kit(kit_sku, components, title, dry_run):
                    success_count += 1
                else:
                    error_count += 1
        
        print(f"\n{'='*60}")
        print(f"Bulk creation complete:")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")


def create_sample_csv():
    """Create a sample CSV template"""
    sample_file = "skuvault_kits_template.csv"
    
    with open(sample_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['kit_sku', 'title', 'components'])
        writer.writerow(['COMBO-2506-BE-ES', 'Breville Barista Express + Eureka Specialita', 'BES870XL:1,EUREKA-SPEC:1'])
        writer.writerow(['BUNDLE-STARTER', 'Starter Bundle', 'COFFEE-001:2,FILTERS-100:1,CLEANER-01:1'])
        writer.writerow(['COMBO-2506-PRO-MAZ', 'Profitec Move + Mazzer Philos', 'PRO-MOVE:1,MAZ-PHILOS:1'])
    
    print(f"Sample CSV created: {sample_file}")
    print("\nColumns:")
    print("  kit_sku: The SKU for the kit/combo")
    print("  title: Description of the kit")
    print("  components: Component SKUs and quantities (format: SKU1:QTY1,SKU2:QTY2)")


def main():
    parser = argparse.ArgumentParser(description='Manage SkuVault kits')
    parser.add_argument('--action', choices=['create', 'update', 'remove', 'get', 'list', 'create-bulk'],
                        required=True, help='Action to perform')
    parser.add_argument('--kit-sku', help='Kit SKU')
    parser.add_argument('--components', help='Components (format: SKU1:QTY1,SKU2:QTY2)')
    parser.add_argument('--title', help='Kit title/description')
    parser.add_argument('--file', help='CSV file for bulk operations')
    parser.add_argument('--limit', type=int, default=100, help='Limit for list operation')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--sample', action='store_true', help='Create sample CSV template')
    
    args = parser.parse_args()
    
    # Handle sample creation
    if args.sample:
        create_sample_csv()
        return
    
    # Initialize manager
    manager = SkuVaultKitManager()
    
    # Execute action
    if args.action == 'create':
        if not args.kit_sku or not args.components:
            print("Error: --kit-sku and --components are required for create action", file=sys.stderr)
            sys.exit(1)
        
        components = manager.parse_components(args.components)
        manager.create_kit(args.kit_sku, components, args.title, args.dry_run)
    
    elif args.action == 'update':
        if not args.kit_sku or not args.components:
            print("Error: --kit-sku and --components are required for update action", file=sys.stderr)
            sys.exit(1)
        
        components = manager.parse_components(args.components)
        manager.update_kit(args.kit_sku, components, args.dry_run)
    
    elif args.action == 'remove':
        if not args.kit_sku:
            print("Error: --kit-sku is required for remove action", file=sys.stderr)
            sys.exit(1)
        
        manager.remove_kit(args.kit_sku, args.dry_run)
    
    elif args.action == 'get':
        if not args.kit_sku:
            print("Error: --kit-sku is required for get action", file=sys.stderr)
            sys.exit(1)
        
        manager.get_kit(args.kit_sku)
    
    elif args.action == 'list':
        manager.list_kits(args.limit)
    
    elif args.action == 'create-bulk':
        if not args.file:
            print("Error: --file is required for create-bulk action", file=sys.stderr)
            sys.exit(1)
        
        manager.create_bulk_from_csv(args.file, args.dry_run)


if __name__ == '__main__':
    main()