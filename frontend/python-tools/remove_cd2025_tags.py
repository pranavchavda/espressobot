#!/usr/bin/env python3
"""
Remove cd2025-* tags from products of specific brands
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SHOPIFY_SHOP_URL = os.getenv('SHOPIFY_SHOP_URL')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')

if not SHOPIFY_SHOP_URL or not SHOPIFY_ACCESS_TOKEN:
    print("Error: Missing SHOPIFY_SHOP_URL or SHOPIFY_ACCESS_TOKEN environment variables")
    sys.exit(1)

headers = {
    'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

# Brands to process
BRANDS = ['Behmor', 'Profitec', 'ECM', 'Eureka', 'Eureka Oro']

def get_all_products_for_brand(brand):
    """Get all ACTIVE products for a specific brand using GraphQL"""
    products = []
    cursor = None
    
    while True:
        after_clause = f', after: "{cursor}"' if cursor else ''
        
        query = f'''
        {{
          products(first: 250, query: "vendor:{brand} AND status:ACTIVE"{after_clause}) {{
            edges {{
              node {{
                id
                title
                vendor
                status
                tags
              }}
              cursor
            }}
            pageInfo {{
              hasNextPage
            }}
          }}
        }}
        '''
        
        response = requests.post(
            f'{SHOPIFY_SHOP_URL}/admin/api/2023-10/graphql.json',
            headers=headers,
            json={'query': query}
        )
        
        if response.status_code != 200:
            print(f"Error fetching products for {brand}: {response.status_code}")
            print(response.text)
            break
            
        data = response.json()
        
        if 'errors' in data:
            print(f"GraphQL errors for {brand}: {data['errors']}")
            break
            
        edges = data.get('data', {}).get('products', {}).get('edges', [])
        products.extend([edge['node'] for edge in edges])
        
        if not data.get('data', {}).get('products', {}).get('pageInfo', {}).get('hasNextPage'):
            break
            
        cursor = edges[-1]['cursor'] if edges else None
        
    return products

def remove_cd2025_tags(product_id, current_tags):
    """Remove cd2025-* tags from a product"""
    # Filter out tags that start with cd2025-
    new_tags = [tag for tag in current_tags if not tag.startswith('cd2025-')]
    
    if len(new_tags) == len(current_tags):
        return False  # No changes needed
    
    # Update product tags using GraphQL
    mutation = '''
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          title
          tags
        }
        userErrors {
          field
          message
        }
      }
    }
    '''
    
    variables = {
        'input': {
            'id': product_id,
            'tags': new_tags
        }
    }
    
    response = requests.post(
        f'{SHOPIFY_SHOP_URL}/admin/api/2023-10/graphql.json',
        headers=headers,
        json={'query': mutation, 'variables': variables}
    )
    
    if response.status_code != 200:
        print(f"Error updating product {product_id}: {response.status_code}")
        print(response.text)
        return False
        
    data = response.json()
    
    if 'errors' in data:
        print(f"GraphQL errors updating product: {data['errors']}")
        return False
        
    user_errors = data.get('data', {}).get('productUpdate', {}).get('userErrors', [])
    if user_errors:
        print(f"User errors updating product: {user_errors}")
        return False
        
    return True

def main():
    # Check for command line arguments
    import sys
    test_mode = '--test' in sys.argv or len(sys.argv) == 1
    
    if test_mode:
        print("=== TEST MODE - Processing one product only ===")
        print("Run with --full to process all products")
        
        # Find first product with cd2025-* tags
        for brand in BRANDS:
            print(f"\nChecking brand: {brand}")
            products = get_all_products_for_brand(brand)
            
            for product in products:
                cd2025_tags = [tag for tag in product['tags'] if tag.startswith('cd2025-')]
                
                if cd2025_tags:
                    print(f"\nFound test product: {product['title']}")
                    print(f"Vendor: {product['vendor']}")
                    print(f"Product ID: {product['id']}")
                    print(f"Status: {product.get('status', 'Unknown')}")
                    print(f"Current tags: {product['tags']}")
                    print(f"CD2025 tags to remove: {cd2025_tags}")
                    
                    print("\nRemoving tags...")
                    if remove_cd2025_tags(product['id'], product['tags']):
                        print("✓ Successfully updated product!")
                        
                        # Verify the update
                        print("\nVerifying update...")
                        updated_products = get_all_products_for_brand(brand)
                        for p in updated_products:
                            if p['id'] == product['id']:
                                print(f"New tags: {p['tags']}")
                                remaining_cd2025 = [tag for tag in p['tags'] if tag.startswith('cd2025-')]
                                if remaining_cd2025:
                                    print(f"⚠️  Warning: Still has cd2025 tags: {remaining_cd2025}")
                                else:
                                    print("✓ All cd2025-* tags successfully removed!")
                                break
                    else:
                        print("✗ Failed to update product")
                    
                    print("\nTest complete. Run with --full to process all products.")
                    return
        
        print("No products found with cd2025-* tags")
        return
    
    # Full processing mode
    print("\n=== BULK PROCESSING MODE ===")
    total_processed = 0
    total_updated = 0
    
    for brand in BRANDS:
        print(f"\nProcessing brand: {brand}")
        products = get_all_products_for_brand(brand)
        print(f"Found {len(products)} ACTIVE products for {brand}")
        
        brand_updated = 0
        for product in products:
            # Check if product has any cd2025-* tags
            cd2025_tags = [tag for tag in product['tags'] if tag.startswith('cd2025-')]
            
            if cd2025_tags:
                print(f"  Removing tags {cd2025_tags} from: {product['title']}")
                if remove_cd2025_tags(product['id'], product['tags']):
                    brand_updated += 1
                    total_updated += 1
                else:
                    print(f"    Failed to update product")
            
            total_processed += 1
        
        print(f"Updated {brand_updated} products for {brand}")
    
    print(f"\n=== Summary ===")
    print(f"Total products processed: {total_processed}")
    print(f"Total products updated: {total_updated}")

if __name__ == '__main__':
    main()