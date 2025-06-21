#!/usr/bin/env python3
"""Test script for native tool imports."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

# Test imports
try:
    from search_products import search_products
    print("✓ search_products imported successfully")
except Exception as e:
    print(f"✗ Failed to import search_products: {e}")

try:
    from get_product import get_product
    print("✓ get_product imported successfully")
except Exception as e:
    print(f"✗ Failed to import get_product: {e}")

try:
    from base import ShopifyClient
    print("✓ ShopifyClient imported successfully")
except Exception as e:
    print(f"✗ Failed to import ShopifyClient: {e}")

# Test basic functionality
print("\nTesting basic functionality...")

try:
    # Test search
    print("\nSearching for 'coffee'...")
    results = search_products("coffee", limit=3, fields=['title', 'vendor', 'price'])
    products = [edge['node'] for edge in results.get('edges', [])]
    print(f"Found {len(products)} products")
    for p in products[:3]:
        print(f"  - {p.get('title')} by {p.get('vendor')}")
except Exception as e:
    print(f"Search test failed: {e}")

print("\nAll tests completed!")