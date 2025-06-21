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


def update_variant_price(client, variant_id, price, compare_at_price=None):
    """Update a single variant's pricing"""
    mutation = """
    mutation updateVariant($input: ProductVariantInput!) {
        productVariantUpdate(input: $input) {
            productVariant {
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
    
    input_data = {
        "id": variant_id,
        "price": price
    }
    
    if compare_at_price:
        input_data["compareAtPrice"] = compare_at_price
    
    variables = {"input": input_data}
    
    result = client.execute_graphql(mutation, variables)
    
    if result.get("data", {}).get("productVariantUpdate", {}).get("userErrors"):
        return False, result["data"]["productVariantUpdate"]["userErrors"]
    
    return True, None


def update_prices_from_csv(filename, dry_run=False):
    """Main function to update prices from CSV"""
    client = ShopifyClient()
    
    print(f"📄 Reading CSV file: {filename}")
    products = read_csv_file(filename)
    
    if not products:
        print("❌ No products found in CSV file")
        return
    
    print(f"📊 Found {len(products)} products to update")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for i, product in enumerate(products, 1):
        variant_id = product['variant_id']
        price = product['price']
        compare_at = product['compare_at_price']
        title = product['product_title']
        sku = product['sku']
        
        print(f"\n[{i}/{len(products)}] {title}" + (f" (SKU: {sku})" if sku else ""))
        print(f"   Price: {format_price(price)}" + 
              (f" (was {format_price(compare_at)})" if compare_at else ""))
        
        if dry_run:
            print("   ⏭️  Skipped (dry run)")
            success_count += 1
            continue
        
        try:
            success, error = update_variant_price(client, variant_id, price, compare_at)
            
            if success:
                print("   ✅ Updated successfully")
                success_count += 1
            else:
                error_msg = f"   ❌ Failed: {error}"
                print(error_msg)
                errors.append(f"{title}: {error}")
                error_count += 1
                
        except Exception as e:
            error_msg = f"   ❌ Error: {str(e)}"
            print(error_msg)
            errors.append(f"{title}: {str(e)}")
            error_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Update Summary:")
    print(f"   Total products: {len(products)}")
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