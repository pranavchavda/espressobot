#!/usr/bin/env python3
"""
Manage MAP (Minimum Advertised Price) sales based on calendar data.

This tool reads the enhanced sales calendar and can:
1. Check what sales should be active today
2. Apply sale prices for a specific date range
3. Revert prices back to regular after sales end
4. Preview changes before applying them
"""

import argparse
import re
from datetime import datetime, date
from pathlib import Path
import sys
import os
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from base import ShopifyClient

class MAPSalesManager:
    def __init__(self, calendar_file, dry_run=False):
        self.calendar_file = Path(calendar_file)
        self.dry_run = dry_run
        self.sales_data = {}
        self.client = ShopifyClient()
        self.load_calendar()
    
    def load_calendar(self):
        """Load and parse the enhanced markdown calendar."""
        if not self.calendar_file.exists():
            raise FileNotFoundError(f"Calendar file not found: {self.calendar_file}")
        
        with open(self.calendar_file, 'r') as f:
            content = f.read()
        
        # Parse markdown sections by date ranges
        date_pattern = r'^## (.+ - .+)$'
        current_date_range = None
        
        for line in content.split('\n'):
            # Check for date range header
            date_match = re.match(date_pattern, line)
            if date_match:
                current_date_range = date_match.group(1)
                self.sales_data[current_date_range] = []
                continue
            
            # Parse table rows (skip headers and separators)
            if current_date_range and line.startswith('|') and not line.startswith('| Product') and not line.startswith('|---'):
                parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first/last elements
                if len(parts) >= 8:
                    product_data = {
                        'product_title': parts[0],
                        'color': parts[1],
                        'sku': parts[2],
                        'regular_price': float(parts[3].replace('$', '').replace(',', '')),
                        'sale_price': float(parts[4].replace('$', '').replace(',', '')),
                        'discount': parts[5],
                        'product_id': parts[6],
                        'variant_id': parts[7] if len(parts) > 7 else None  # Variant ID is now in the calendar
                    }
                    self.sales_data[current_date_range].append(product_data)
    
    def get_variant_id(self, product_id, sku):
        """Get variant ID for a product - fetches the first (default) variant."""
        if product_id == 'NOT_FOUND':
            return 'NOT_FOUND'
        
        # Query to get the first variant of the product
        query = '''
        query getProductVariant($id: ID!) {
            product(id: $id) {
                id
                title
                variants(first: 1) {
                    edges {
                        node {
                            id
                            sku
                            price
                            compareAtPrice
                        }
                    }
                }
            }
        }
        '''
        
        variables = {"id": product_id}
        
        try:
            response = self.client.execute_graphql(query, variables)
            if response and 'data' in response and response['data'].get('product'):
                variants = response['data']['product'].get('variants', {}).get('edges', [])
                if variants:
                    return variants[0]['node']['id']
        except Exception as e:
            print(f"Error fetching variant for product {product_id}: {e}")
        
        return None
    
    def parse_date_range(self, date_range):
        """Parse date range string into start and end dates."""
        # Format: "30 May - 05 Jun" or "26 Dec - 01 Jan"
        parts = date_range.split(' - ')
        
        # Parse start date
        start_parts = parts[0].split(' ')
        start_day = int(start_parts[0])
        start_month = start_parts[1]
        
        # Parse end date
        end_parts = parts[1].split(' ')
        end_day = int(end_parts[0])
        end_month = end_parts[1]
        
        # Convert month names to numbers
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
        
        start_month_num = months[start_month]
        end_month_num = months[end_month]
        
        # Determine year (handle year boundary)
        current_year = datetime.now().year
        start_year = current_year
        end_year = current_year
        
        # If end month is January and start month is December, end year is next year
        if start_month_num == 12 and end_month_num == 1:
            end_year = current_year + 1
        
        start_date = date(start_year, start_month_num, start_day)
        end_date = date(end_year, end_month_num, end_day)
        
        return start_date, end_date
    
    def get_active_sales(self, check_date=None):
        """Get all sales that should be active on the given date."""
        if check_date is None:
            check_date = date.today()
        
        active_sales = []
        
        for date_range, products in self.sales_data.items():
            start_date, end_date = self.parse_date_range(date_range)
            
            # Check if date is within range
            if start_date <= check_date <= end_date:
                active_sales.extend(products)
        
        return active_sales
    
    def update_variant_price(self, variant_id, price, compare_at_price=None):
        """Update a single variant's price."""
        # First get the product ID for this variant
        query = '''
        query getProductId($id: ID!) {
            productVariant(id: $id) {
                product {
                    id
                }
            }
        }
        '''
        
        if not self.dry_run:
            product_response = self.client.execute_graphql(query, {"id": variant_id})
            product_id = product_response.get('data', {}).get('productVariant', {}).get('product', {}).get('id')
            
            if not product_id:
                print(f"Error: Could not find product for variant {variant_id}")
                return False
        else:
            product_id = "dry-run-product-id"
        
        # Now use bulk update mutation
        mutation = '''
        mutation updateVariantPrice($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
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
        '''
        
        variant_input = {
            "id": variant_id,
            "price": str(price)
        }
        
        if compare_at_price:
            variant_input["compareAtPrice"] = str(compare_at_price)
        
        variables = {
            "productId": product_id,
            "variants": [variant_input]
        }
        
        if self.dry_run:
            print(f"[DRY RUN] Would update variant {variant_id}: price=${price}, compare_at=${compare_at_price}")
            return True
        
        response = self.client.execute_graphql(mutation, variables)
        
        if response.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
            errors = response['data']['productVariantsBulkUpdate']['userErrors']
            print(f"Error updating variant {variant_id}: {errors}")
            return False
        
        return True
    
    def apply_sales(self, target_date=None):
        """Apply sale prices for all products that should be on sale on the target date."""
        if target_date is None:
            target_date = date.today()
        
        active_sales = self.get_active_sales(target_date)
        
        if not active_sales:
            print(f"No sales found for {target_date}")
            return
        
        print(f"\nApplying sale prices for {len(active_sales)} products on {target_date}")
        print("=" * 80)
        
        # Group products by product ID for bulk updates
        product_groups = {}
        skip_count = 0
        
        for product in active_sales:
            if product['product_id'] == 'NOT_FOUND':
                print(f"⚠️  Skipping {product['product_title']} ({product['color']}) - not in Shopify")
                skip_count += 1
                continue
            
            # Get variant ID if not already present
            variant_id = product.get('variant_id')
            if not variant_id:
                variant_id = self.get_variant_id(product['product_id'], product['sku'])
                product['variant_id'] = variant_id
            
            if not variant_id:
                print(f"⚠️  Could not find variant for {product['product_title']} ({product['sku']})")
                skip_count += 1
                continue
            
            # Group by product ID
            if product['product_id'] not in product_groups:
                product_groups[product['product_id']] = []
            product_groups[product['product_id']].append(product)
        
        # Apply updates in bulk by product
        success_count = 0
        error_count = 0
        
        for product_id, variants in product_groups.items():
            print(f"\nUpdating {len(variants)} variant(s) for product {product_id}")
            
            # Build variants input
            variants_input = []
            for variant in variants:
                print(f"  {variant['product_title']} - {variant['color']}")
                print(f"    SKU: {variant['sku']}")
                print(f"    Regular: ${variant['regular_price']:.2f} → Sale: ${variant['sale_price']:.2f} ({variant['discount']})")
                
                variants_input.append({
                    "id": variant['variant_id'],
                    "price": str(variant['sale_price']),
                    "compareAtPrice": str(variant['regular_price'])
                })
            
            if self.dry_run:
                print("  [DRY RUN] Would update prices")
                success_count += len(variants)
                continue
            
            # Bulk update mutation
            mutation = '''
            mutation updateVariantPrices($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
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
            '''
            
            variables = {
                "productId": product_id,
                "variants": variants_input
            }
            
            response = self.client.execute_graphql(mutation, variables)
            
            if response.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = response['data']['productVariantsBulkUpdate']['userErrors']
                print(f"  ❌ Error: {errors}")
                error_count += len(variants)
            else:
                print(f"  ✅ Successfully updated {len(variants)} variant(s)")
                success_count += len(variants)
        
        print("\n" + "=" * 80)
        print(f"Summary: {success_count} products updated, {error_count} errors, {skip_count} skipped")
    
    def revert_prices(self, date_range):
        """Revert prices back to regular for a specific date range."""
        if date_range not in self.sales_data:
            print(f"Date range '{date_range}' not found in calendar")
            return
        
        products = self.sales_data[date_range]
        print(f"\nReverting {len(products)} products to regular prices for {date_range}")
        print("=" * 80)
        
        # Group products by product ID for bulk updates
        product_groups = {}
        skip_count = 0
        
        for product in products:
            if product['product_id'] == 'NOT_FOUND':
                skip_count += 1
                continue
            
            # Get variant ID if not already present
            variant_id = product.get('variant_id')
            if not variant_id:
                variant_id = self.get_variant_id(product['product_id'], product['sku'])
                product['variant_id'] = variant_id
            
            if not variant_id:
                print(f"⚠️  Could not find variant for {product['product_title']} ({product['sku']})")
                skip_count += 1
                continue
            
            # Group by product ID
            if product['product_id'] not in product_groups:
                product_groups[product['product_id']] = []
            product_groups[product['product_id']].append(product)
        
        # Apply updates in bulk by product
        success_count = 0
        error_count = 0
        
        for product_id, variants in product_groups.items():
            print(f"\nReverting {len(variants)} variant(s) for product {product_id}")
            
            # Build variants input
            variants_input = []
            for variant in variants:
                print(f"  {variant['product_title']} - {variant['color']}")
                print(f"    Reverting to regular price: ${variant['regular_price']:.2f}")
                
                variants_input.append({
                    "id": variant['variant_id'],
                    "price": str(variant['regular_price']),
                    "compareAtPrice": None  # Clear compare-at price when reverting
                })
            
            if self.dry_run:
                print("  [DRY RUN] Would revert prices")
                success_count += len(variants)
                continue
            
            # Bulk update mutation
            mutation = '''
            mutation updateVariantPrices($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
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
            '''
            
            variables = {
                "productId": product_id,
                "variants": variants_input
            }
            
            response = self.client.execute_graphql(mutation, variables)
            
            if response.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = response['data']['productVariantsBulkUpdate']['userErrors']
                print(f"  ❌ Error: {errors}")
                error_count += len(variants)
            else:
                print(f"  ✅ Successfully reverted {len(variants)} variant(s)")
                success_count += len(variants)
        
        print("\n" + "=" * 80)
        print(f"Summary: {success_count} products reverted, {error_count} errors, {skip_count} skipped")
    
    def show_calendar_summary(self):
        """Display a summary of all sale periods."""
        print("\nBreville MAP Sales Calendar Summary")
        print("=" * 80)
        
        for date_range in sorted(self.sales_data.keys(), 
                                 key=lambda x: self.parse_date_range(x)[0]):
            products = self.sales_data[date_range]
            start_date, end_date = self.parse_date_range(date_range)
            
            # Check if currently active
            today = date.today()
            is_active = start_date <= today <= end_date
            status = "🟢 ACTIVE" if is_active else "⏰ Scheduled"
            
            print(f"\n{status} {date_range} ({len(products)} products)")
            
            # Group by product name
            product_groups = {}
            for p in products:
                name = p['product_title'].split(' - ')[0]  # Remove color from title
                if name not in product_groups:
                    product_groups[name] = []
                product_groups[name].append(p)
            
            for name, variants in product_groups.items():
                print(f"  • {name} ({len(variants)} colors) - {variants[0]['discount']} off")


def main():
    parser = argparse.ArgumentParser(description='Manage MAP sales based on calendar data')
    parser.add_argument('--calendar', default='resources/breville_espresso_sales_2025_enhanced.md',
                        help='Path to enhanced calendar file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying them')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check what sales should be active')
    check_parser.add_argument('--date', help='Check for specific date (YYYY-MM-DD)')
    
    # Apply command
    apply_parser = subparsers.add_parser('apply', help='Apply sale prices')
    apply_parser.add_argument('--date', help='Apply sales for specific date (YYYY-MM-DD)')
    
    # Revert command
    revert_parser = subparsers.add_parser('revert', help='Revert prices to regular')
    revert_parser.add_argument('date_range', help='Date range to revert (e.g., "30 May - 05 Jun")')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show calendar summary')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = MAPSalesManager(args.calendar, args.dry_run)
    
    if args.command == 'check':
        check_date = date.today()
        if args.date:
            check_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        
        active_sales = manager.get_active_sales(check_date)
        if active_sales:
            print(f"\nActive sales for {check_date}:")
            print("=" * 80)
            for product in active_sales:
                print(f"{product['product_title']} - {product['color']}: "
                      f"${product['regular_price']:.2f} → ${product['sale_price']:.2f} ({product['discount']})")
        else:
            print(f"No active sales for {check_date}")
    
    elif args.command == 'apply':
        target_date = date.today()
        if args.date:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        manager.apply_sales(target_date)
    
    elif args.command == 'revert':
        manager.revert_prices(args.date_range)
    
    elif args.command == 'summary':
        manager.show_calendar_summary()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()