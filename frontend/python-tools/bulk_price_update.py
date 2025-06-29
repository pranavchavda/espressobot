#!/usr/bin/env python3
"""Bulk update product prices from CSV file."""

import sys
import argparse
import csv
import os
from datetime import datetime
from base import ShopifyClient, format_price


def read_csv_file(filename):
    """Read and validate CSV file"""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"CSV file not found: {filename}")
    
    required_columns = ['Variant ID', 'Price']
    products = []
    
    with open(filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Check for required columns
        if not all(col in reader.fieldnames for col in required_columns):
            missing = [col for col in required_columns if col not in reader.fieldnames]
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        
        for row in reader:
            if row['Variant ID'] and row['Price']:
                products.append({
                    'variant_id': row['Variant ID'],
                    'price': row['Price'],
                    'compare_at_price': row.get('Compare At Price', ''),
                    'product_title': row.get('Product Title', 'Unknown'),
                    'sku': row.get('SKU', '')
                })
    
    return products


def get_product_id_from_variant(client, variant_id):
    """Get the product ID for a variant"""
    query = """
    query getProductId($id: ID!) {
        productVariant(id: $id) {
            product {
                id
            }
        }
    }
    """
    
    result = client.execute_graphql(query, {"id": variant_id})
    variant = result.get("data", {}).get("productVariant")
    if variant and variant.get("product"):
        return variant["product"]["id"]
    return None


def update_variant_price(client, variant_id, price, compare_at_price=None):
    """Update a single variant's pricing"""
    # First get the product ID
    product_id = get_product_id_from_variant(client, variant_id)
    if not product_id:
        return False, [{"message": "Could not find product for variant"}]
    
    mutation = """
    mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
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
    """
    
    variant_input = {
        "id": variant_id,
        "price": price
    }
    
    if compare_at_price:
        variant_input["compareAtPrice"] = compare_at_price
    
    variables = {
        "productId": product_id,
        "variants": [variant_input]
    }
    
    result = client.execute_graphql(mutation, variables)
    
    if result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors"):
        return False, result["data"]["productVariantsBulkUpdate"]["userErrors"]
    
    return True, None


def update_prices_from_csv(filename, dry_run=False):
    """Main function to update prices from CSV"""
    client = ShopifyClient()
    
    print(f"📄 Reading CSV file: {filename}")
    products = read_csv_file(filename)
    
    if not products:
        print("❌ No products found in CSV file")
        return
    
    print(f"📊 Found {len(products)} variants to update")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    # Group variants by product ID for efficient bulk updates
    print("\n🔄 Fetching product information...")
    product_groups = {}
    variant_info_map = {}
    
    for product in products:
        variant_id = product['variant_id']
        variant_info_map[variant_id] = product
        
        if not dry_run:
            product_id = get_product_id_from_variant(client, variant_id)
            if product_id:
                if product_id not in product_groups:
                    product_groups[product_id] = []
                product_groups[product_id].append(product)
            else:
                print(f"⚠️  Could not find product for variant {variant_id}")
    
    if dry_run:
        # For dry run, just process individually
        success_count = 0
        for i, product in enumerate(products, 1):
            title = product['product_title']
            sku = product['sku']
            price = product['price']
            compare_at = product['compare_at_price']
            
            print(f"\n[{i}/{len(products)}] {title}" + (f" (SKU: {sku})" if sku else ""))
            print(f"   Price: {format_price(price)}" + 
                  (f" (was {format_price(compare_at)})" if compare_at else ""))
            print("   ⏭️  Skipped (dry run)")
            success_count += 1
        
        print(f"\n{'='*60}")
        print("📊 Update Summary:")
        print(f"   Total variants: {len(products)}")
        print(f"   Would update: {success_count}")
        return
    
    # Process updates grouped by product
    success_count = 0
    error_count = 0
    errors = []
    total_processed = 0
    
    print(f"\n🚀 Updating prices for {len(product_groups)} products...")
    
    for product_id, variants in product_groups.items():
        # Build variants input for bulk update
        variants_input = []
        for variant in variants:
            variant_input = {
                "id": variant['variant_id'],
                "price": variant['price']
            }
            if variant['compare_at_price']:
                variant_input["compareAtPrice"] = variant['compare_at_price']
            variants_input.append(variant_input)
        
        # Execute bulk update for this product
        mutation = """
        mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
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
        """
        
        variables = {
            "productId": product_id,
            "variants": variants_input
        }
        
        try:
            result = client.execute_graphql(mutation, variables)
            
            if result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors"):
                user_errors = result["data"]["productVariantsBulkUpdate"]["userErrors"]
                for variant in variants:
                    total_processed += 1
                    title = variant['product_title']
                    sku = variant['sku']
                    print(f"\n[{total_processed}/{len(products)}] {title}" + (f" (SKU: {sku})" if sku else ""))
                    print(f"   ❌ Failed: {user_errors}")
                    errors.append(f"{title}: {user_errors}")
                    error_count += 1
            else:
                for variant in variants:
                    total_processed += 1
                    title = variant['product_title']
                    sku = variant['sku']
                    price = variant['price']
                    compare_at = variant['compare_at_price']
                    
                    print(f"\n[{total_processed}/{len(products)}] {title}" + (f" (SKU: {sku})" if sku else ""))
                    print(f"   Price: {format_price(price)}" + 
                          (f" (was {format_price(compare_at)})" if compare_at else ""))
                    print("   ✅ Updated successfully")
                    success_count += 1
                    
        except Exception as e:
            for variant in variants:
                total_processed += 1
                title = variant['product_title']
                error_msg = f"   ❌ Error: {str(e)}"
                print(f"\n[{total_processed}/{len(products)}] {title}")
                print(error_msg)
                errors.append(f"{title}: {str(e)}")
                error_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Update Summary:")
    print(f"   Total variants: {len(products)}")
    print(f"   ✅ Successfully updated: {success_count}")
    print(f"   ❌ Failed: {error_count}")
    
    if errors:
        print("\n❌ Errors:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")
    
    # Create log file
    if not dry_run and success_count > 0:
        log_filename = f"price_update_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_filename, 'w') as log:
            log.write(f"Price Update Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"{'='*60}\n")
            log.write(f"Total products: {len(products)}\n")
            log.write(f"Successfully updated: {success_count}\n")
            log.write(f"Failed: {error_count}\n")
            if errors:
                log.write("\nErrors:\n")
                for error in errors:
                    log.write(f"- {error}\n")
        print(f"\n📝 Log file created: {log_filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Bulk update product prices from CSV file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
CSV Format Requirements:
- Required columns: "Variant ID", "Price"
- Optional columns: "Compare At Price", "Product Title", "SKU"
- The CSV must have headers in the first row

Examples:
  # Update prices from CSV
  python bulk_price_update.py prices.csv
  
  # Dry run to preview changes
  python bulk_price_update.py prices.csv --dry-run
  
  # Show sample CSV format
  python bulk_price_update.py --sample

Sample CSV format:
Product ID,Product Title,Variant ID,SKU,Price,Compare At Price
gid://shopify/Product/123,Product Name,gid://shopify/ProductVariant/456,SKU123,99.99,149.99
        '''
    )
    
    parser.add_argument('csv_file', nargs='?', help='CSV file with price updates')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without updating')
    parser.add_argument('--sample', action='store_true',
                       help='Create a sample CSV file')
    
    args = parser.parse_args()
    
    if args.sample:
        sample_file = 'sample_price_update.csv'
        with open(sample_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Product ID', 'Product Title', 'Variant ID', 'SKU', 'Price', 'Compare At Price'])
            writer.writerow(['gid://shopify/Product/123', 'Sample Product', 'gid://shopify/ProductVariant/456', 'SKU123', '99.99', '149.99'])
            writer.writerow(['gid://shopify/Product/789', 'Another Product', 'gid://shopify/ProductVariant/012', 'SKU456', '49.99', ''])
        print(f"✅ Sample CSV file created: {sample_file}")
        print("\nEdit this file with your product data and run:")
        print(f"python {sys.argv[0]} {sample_file}")
        return
    
    if not args.csv_file:
        parser.error("CSV file is required unless using --sample")
    
    try:
        update_prices_from_csv(args.csv_file, args.dry_run)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()