#!/usr/bin/env python3
"""Test Shopify API connection and credentials."""

import sys
import argparse
from base import ShopifyClient, print_json


def test_connection():
    """Test the Shopify API connection."""
    try:
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
            return True
            
        else:
            print("\n❌ Connection failed!")
            print("Please check your credentials and try again.")
            print(f"Response: {result}")
            return False
            
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Tests the connection to the Shopify API using credentials from environment variables."
    )
    parser.parse_args()

    print("Running connection test...")
    success = test_connection()
    
    if success:
        print("\nTest finished successfully.")
    else:
        print("\nTest finished with errors.")
        
    sys.exit(0 if success else 1)