#!/usr/bin/env python3
"""
Create perfect manual product matches for price monitoring.
This tool helps create exact matches between IDC products and competitor products.
"""

import requests
import json
import sys
from typing import List, Dict, Optional
import argparse

BASE_URL = "http://localhost:5173"

def search_idc_products(search_term: str, limit: int = 10) -> List[Dict]:
    """Search for IDC products by title or SKU"""
    response = requests.get(
        f"{BASE_URL}/api/price-monitor/shopify-sync/idc-products",
        params={"search": search_term, "limit": limit}
    )
    if response.ok:
        data = response.json()
        return data.get("products", [])
    return []

def search_competitor_products(search_term: str, competitor: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """Search for competitor products by title"""
    params = {"search": search_term, "limit": limit}
    if competitor:
        params["competitor"] = competitor
    
    response = requests.get(
        f"{BASE_URL}/api/price-monitor/competitors/products",
        params=params
    )
    if response.ok:
        data = response.json()
        return data.get("products", [])
    return []

def create_perfect_match(idc_product_id: str, competitor_product_id: str) -> Dict:
    """Create a perfect manual match between two products"""
    response = requests.post(
        f"{BASE_URL}/api/price-monitor/product-matching/perfect-match",
        json={
            "idc_product_id": idc_product_id,
            "competitor_product_id": competitor_product_id
        }
    )
    if response.ok:
        return response.json()
    else:
        return {"error": f"Failed to create match: {response.text}"}

def list_competitors() -> List[Dict]:
    """List all available competitors"""
    response = requests.get(f"{BASE_URL}/api/price-monitor/competitors")
    if response.ok:
        data = response.json()
        return data.get("competitors", [])
    return []

def interactive_match():
    """Interactive mode for creating matches"""
    print("\n🎯 Perfect Product Match Creator\n")
    
    # Step 1: Search for IDC product
    idc_search = input("Search for IDC product (by title or SKU): ").strip()
    if not idc_search:
        print("❌ Search term required")
        return
    
    print("\n🔍 Searching IDC products...")
    idc_products = search_idc_products(idc_search, limit=20)
    
    if not idc_products:
        print("❌ No IDC products found")
        return
    
    print(f"\n📦 Found {len(idc_products)} IDC products:")
    for i, product in enumerate(idc_products, 1):
        print(f"{i}. {product['title']}")
        print(f"   Vendor: {product['vendor']} | SKU: {product['sku']} | Price: ${product['price']}")
        print()
    
    try:
        selection = int(input("Select IDC product number (or 0 to cancel): "))
        if selection == 0:
            return
        if selection < 1 or selection > len(idc_products):
            print("❌ Invalid selection")
            return
    except ValueError:
        print("❌ Invalid input")
        return
    
    selected_idc = idc_products[selection - 1]
    print(f"\n✅ Selected: {selected_idc['title']}")
    
    # Step 2: List competitors
    print("\n🏪 Available competitors:")
    competitors = list_competitors()
    for i, comp in enumerate(competitors, 1):
        print(f"{i}. {comp['name']} ({comp['domain']})")
    
    comp_selection = input("\nFilter by competitor number (or press Enter for all): ").strip()
    selected_competitor = None
    if comp_selection:
        try:
            comp_idx = int(comp_selection) - 1
            if 0 <= comp_idx < len(competitors):
                selected_competitor = competitors[comp_idx]['name']
        except ValueError:
            pass
    
    # Step 3: Search for competitor product
    comp_search = input("\nSearch for competitor product: ").strip()
    if not comp_search:
        # Use IDC product title as search term
        comp_search = selected_idc['title']
        print(f"Using IDC product title for search: {comp_search}")
    
    print("\n🔍 Searching competitor products...")
    comp_products = search_competitor_products(comp_search, selected_competitor, limit=20)
    
    if not comp_products:
        print("❌ No competitor products found")
        return
    
    print(f"\n📦 Found {len(comp_products)} competitor products:")
    for i, product in enumerate(comp_products, 1):
        competitor_name = product.get('competitors', {}).get('name', 'Unknown')
        print(f"{i}. {product['title']}")
        print(f"   Vendor: {product['vendor']} | Price: ${product['price']} | Competitor: {competitor_name}")
        print()
    
    try:
        selection = int(input("Select competitor product number (or 0 to cancel): "))
        if selection == 0:
            return
        if selection < 1 or selection > len(comp_products):
            print("❌ Invalid selection")
            return
    except ValueError:
        print("❌ Invalid input")
        return
    
    selected_comp = comp_products[selection - 1]
    
    # Step 4: Confirm and create match
    print("\n📋 Match Preview:")
    print(f"IDC Product: {selected_idc['title']}")
    print(f"  - Vendor: {selected_idc['vendor']}")
    print(f"  - SKU: {selected_idc['sku']}")
    print(f"  - Price: ${selected_idc['price']}")
    print()
    print(f"Competitor Product: {selected_comp['title']}")
    print(f"  - Vendor: {selected_comp['vendor']}")
    print(f"  - Price: ${selected_comp['price']}")
    print(f"  - Competitor: {selected_comp.get('competitors', {}).get('name', 'Unknown')}")
    
    confirm = input("\nCreate this perfect match? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Match creation cancelled")
        return
    
    print("\n🔄 Creating perfect match...")
    result = create_perfect_match(selected_idc['id'], selected_comp['id'])
    
    if 'error' in result:
        print(f"❌ {result['error']}")
    else:
        print(f"✅ {result['message']}")
        print(f"Match ID: {result['match']['id']}")

def batch_match(csv_file: str):
    """Create matches from a CSV file"""
    import csv
    
    print(f"\n📄 Loading matches from {csv_file}...")
    
    matches_created = 0
    errors = 0
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                idc_id = row.get('idc_product_id', '').strip()
                comp_id = row.get('competitor_product_id', '').strip()
                
                if not idc_id or not comp_id:
                    print(f"❌ Skipping row with missing IDs: {row}")
                    errors += 1
                    continue
                
                print(f"\n🔄 Creating match: {idc_id} <-> {comp_id}")
                result = create_perfect_match(idc_id, comp_id)
                
                if 'error' in result:
                    print(f"❌ {result['error']}")
                    errors += 1
                else:
                    print(f"✅ Match created")
                    matches_created += 1
    
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file}")
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    print(f"\n📊 Summary:")
    print(f"  - Matches created: {matches_created}")
    print(f"  - Errors: {errors}")

def main():
    parser = argparse.ArgumentParser(description="Create perfect manual product matches")
    parser.add_argument("--batch", help="CSV file with match pairs (idc_product_id,competitor_product_id)")
    parser.add_argument("--search-idc", help="Search for IDC products")
    parser.add_argument("--search-comp", help="Search for competitor products")
    parser.add_argument("--list-competitors", action="store_true", help="List all competitors")
    
    args = parser.parse_args()
    
    if args.batch:
        batch_match(args.batch)
    elif args.search_idc:
        products = search_idc_products(args.search_idc)
        print(json.dumps(products, indent=2))
    elif args.search_comp:
        products = search_competitor_products(args.search_comp)
        print(json.dumps(products, indent=2))
    elif args.list_competitors:
        competitors = list_competitors()
        for comp in competitors:
            print(f"{comp['name']} - {comp['domain']}")
    else:
        # Interactive mode
        try:
            while True:
                interactive_match()
                another = input("\n\nCreate another match? (y/n): ").strip().lower()
                if another != 'y':
                    break
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")

if __name__ == "__main__":
    main()