#!/usr/bin/env python3
"""Update product costs by SKU - single or bulk from CSV."""

import sys
import argparse
import csv
import time
from base import ShopifyClient, print_json, format_price


def get_variant_by_sku(client: ShopifyClient, sku: str):
    """Get variant and inventory item info by SKU."""
    query = '''
    query getVariantBySku($query: String!) {
        productVariants(first: 1, query: $query) {
            edges {
                node {
                    id
                    sku
                    product {
                        id
                        title
                    }
                    inventoryItem {
                        id
                        unitCost {
                            amount
                            currencyCode
                        }
                    }
                }
            }
        }
    }
    '''
    
    variables = {"query": f"sku:{sku}"}
    result = client.execute_graphql(query, variables)
    
    edges = result.get('data', {}).get('productVariants', {}).get('edges', [])
    if edges:
        return edges[0]['node']
    return None


def update_cost_by_sku(client: ShopifyClient, sku: str, cost: float):
    """Update cost for a variant by SKU."""
    # Get variant info
    variant = get_variant_by_sku(client, sku)
    if not variant:
        return False, f"SKU not found: {sku}"
    
    # Update cost
    mutation = '''
    mutation updateCost($id: ID!, $input: InventoryItemInput!) {
        inventoryItemUpdate(id: $id, input: $input) {
            inventoryItem {
                id
                unitCost {
                    amount
                    currencyCode
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    '''
    
    variables = {
        'id': variant['inventoryItem']['id'],
        'input': {
            'cost': str(cost)
        }
    }
    
    result = client.execute_graphql(mutation, variables)
    
    # Check for errors
    errors = result.get('data', {}).get('inventoryItemUpdate', {}).get('userErrors', [])
    if errors:
        return False, f"Update failed: {errors}"
    
    return True, {
        'product': variant['product']['title'],
        'old_cost': float(variant['inventoryItem']['unitCost']['amount']) if variant['inventoryItem']['unitCost'] else 0,
        'new_cost': cost
    }


def process_csv_file(client: ShopifyClient, csv_file: str, dry_run: bool = False):
    """Process bulk cost updates from CSV file."""
    updates = []
    
    # Read CSV
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'sku' in row and 'cost' in row:
                updates.append({
                    'sku': row['sku'].strip(),
                    'cost': float(row['cost'])
                })
    
    if not updates:
        print("No valid updates found in CSV file")
        return 0, 0
    
    print(f"Processing {len(updates)} cost updates...")
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    successful = 0
    failed = 0
    
    for update in updates:
        sku = update['sku']
        cost = update['cost']
        
        if dry_run:
            # Just check if SKU exists
            variant = get_variant_by_sku(client, sku)
            if variant:
                current_cost = float(variant['inventoryItem']['unitCost']['amount']) if variant['inventoryItem']['unitCost'] else 0
                print(f"✓ {sku} - {variant['product']['title']}")
                print(f"  Current: ${current_cost:.2f} → New: ${cost:.2f}")
                successful += 1
            else:
                print(f"✗ {sku} - NOT FOUND")
                failed += 1
        else:
            # Perform actual update
            success, result = update_cost_by_sku(client, sku, cost)
            
            if success:
                print(f"✓ {sku} - {result['product']}")
                print(f"  Updated: ${result['old_cost']:.2f} → ${result['new_cost']:.2f}")
                successful += 1
            else:
                print(f"✗ {sku} - {result}")
                failed += 1
            
            # Rate limiting
            time.sleep(0.25)
    
    return successful, failed


def main():
    parser = argparse.ArgumentParser(
        description='Update product costs by SKU',
        epilog='''
Examples:
  # Update single SKU
  python update_costs_by_sku.py --sku "COFFEE-001" --cost 12.50
  
  # Bulk update from CSV
  python update_costs_by_sku.py --csv costs.csv
  
  # Dry run to preview changes
  python update_costs_by_sku.py --csv costs.csv --dry-run
  
CSV Format:
  sku,cost
  COFFEE-001,12.50
  COFFEE-002,15.00
        '''
    )
    
    # Single update options
    parser.add_argument('--sku', help='Single SKU to update')
    parser.add_argument('--cost', type=float, help='New cost for single SKU')
    
    # Bulk update options
    parser.add_argument('--csv', help='CSV file with sku and cost columns')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without updating')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.sku and args.csv:
        print("Error: Cannot use both --sku and --csv options")
        sys.exit(1)
    
    if args.sku and not args.cost:
        print("Error: Must provide --cost when using --sku")
        sys.exit(1)
    
    if not args.sku and not args.csv:
        print("Error: Must provide either --sku or --csv")
        parser.print_help()
        sys.exit(1)
    
    # Initialize client
    client = ShopifyClient()
    
    # Process updates
    if args.sku:
        # Single SKU update
        print(f"Updating cost for {args.sku} to ${args.cost:.2f}")
        
        if args.dry_run:
            variant = get_variant_by_sku(client, args.sku)
            if variant:
                current_cost = float(variant['inventoryItem']['unitCost']['amount']) if variant['inventoryItem']['unitCost'] else 0
                print(f"✓ Found: {variant['product']['title']}")
                print(f"  Current cost: ${current_cost:.2f}")
                print(f"  New cost: ${args.cost:.2f}")
            else:
                print(f"✗ SKU not found: {args.sku}")
        else:
            success, result = update_cost_by_sku(client, args.sku, args.cost)
            if success:
                print(f"✅ Successfully updated {args.sku}")
                print(f"  Product: {result['product']}")
                print(f"  Cost: ${result['old_cost']:.2f} → ${result['new_cost']:.2f}")
            else:
                print(f"❌ Failed to update: {result}")
                sys.exit(1)
    
    else:
        # Bulk CSV update
        successful, failed = process_csv_file(client, args.csv, args.dry_run)
        
        print("\n" + "="*60)
        print(f"Summary:")
        print(f"  ✓ {'Would update' if args.dry_run else 'Updated'}: {successful}")
        print(f"  ✗ Failed: {failed}")
        print(f"  Total: {successful + failed}")


if __name__ == "__main__":
    main()