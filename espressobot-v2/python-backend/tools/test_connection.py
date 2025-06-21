#!/usr/bin/env python3
"""Test Shopify API connection and credentials."""

import sys
from base import ShopifyClient, print_json


def test_connection():
    """Test the Shopify API connection."""
    print("Testing Shopify API connection...")
    
    client = ShopifyClient()
    
    # Test basic shop query
    query = '''
    {
        shop {
            name
            email
            currencyCode
            weightUnit
            primaryDomain {
                url
            }
            plan {
                displayName
            }
        }
    }
    '''
    
    result = client.execute_graphql(query)
    
    if 'data' in result and 'shop' in result['data']:
        shop = result['data']['shop']
        print("\n✅ Connection successful!\n")
        print(f"Shop Name: {shop['name']}")
        print(f"Email: {shop['email']}")
        print(f"Currency: {shop['currencyCode']}")
        print(f"Weight Unit: {shop['weightUnit']}")
        print(f"Domain: {shop['primaryDomain']['url']}")
        print(f"Plan: {shop['plan']['displayName']}")
        
        # Test product count
        count_query = '{ products { count } }'
        count_result = client.execute_graphql(count_query)
        product_count = count_result.get('data', {}).get('products', {}).get('count', 0)
        print(f"\nTotal Products: {product_count}")
        
        return True
    else:
        print("\n❌ Connection failed!")
        print("Please check your credentials and try again.")
        return False


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)