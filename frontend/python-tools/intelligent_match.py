#!/usr/bin/env python3
"""
Intelligent Product Matching Tool using AI
Leverages advanced AI to accurately match coffee equipment products
"""

import requests
import json
import sys
from typing import List, Dict, Optional
import argparse
from tabulate import tabulate
import time

BASE_URL = "http://localhost:5173"

class IntelligentMatcher:
    def __init__(self):
        self.base_url = BASE_URL
    
    def analyze_match(self, idc_product_id: str, competitor_product_id: str) -> Dict:
        """Analyze if two products match using AI"""
        response = requests.post(
            f"{self.base_url}/api/price-monitor/intelligent-matching/analyze-match",
            json={
                "idc_product_id": idc_product_id,
                "competitor_product_id": competitor_product_id
            }
        )
        return response.json() if response.ok else {"error": response.text}
    
    def find_matches(self, idc_product_id: str, competitor_id: Optional[str] = None, 
                     limit: int = 10, min_confidence: int = 70) -> Dict:
        """Find best matches for an IDC product"""
        response = requests.post(
            f"{self.base_url}/api/price-monitor/intelligent-matching/find-matches",
            json={
                "idc_product_id": idc_product_id,
                "competitor_id": competitor_id,
                "limit": limit,
                "min_confidence": min_confidence
            }
        )
        return response.json() if response.ok else {"error": response.text}
    
    def create_verified_match(self, idc_product_id: str, competitor_product_id: str, 
                            require_confidence: int = 80) -> Dict:
        """Create a match after AI verification"""
        response = requests.post(
            f"{self.base_url}/api/price-monitor/intelligent-matching/create-verified-match",
            json={
                "idc_product_id": idc_product_id,
                "competitor_product_id": competitor_product_id,
                "require_confidence": require_confidence
            }
        )
        return response.json() if response.ok else {"error": response.text}
    
    def get_unmatched_suggestions(self, brand: Optional[str] = None, limit: int = 20) -> Dict:
        """Get unmatched products that need matching"""
        params = {"limit": limit}
        if brand:
            params["brand"] = brand
        
        response = requests.get(
            f"{self.base_url}/api/price-monitor/intelligent-matching/suggestions",
            params=params
        )
        return response.json() if response.ok else {"error": response.text}
    
    def search_products(self, search_term: str, product_type: str = "idc") -> List[Dict]:
        """Search for products"""
        if product_type == "idc":
            url = f"{self.base_url}/api/price-monitor/shopify-sync/idc-products"
        else:
            url = f"{self.base_url}/api/price-monitor/competitors/products"
        
        response = requests.get(url, params={"search": search_term, "limit": 20})
        if response.ok:
            data = response.json()
            return data.get("products", [])
        return []

def interactive_intelligent_match(matcher: IntelligentMatcher):
    """Interactive mode for intelligent matching"""
    print("\n🤖 AI-Powered Product Matching\n")
    
    # Step 1: Get unmatched products
    brand = input("Filter by brand (or press Enter for all): ").strip()
    suggestions = matcher.get_unmatched_suggestions(brand=brand if brand else None)
    
    if "error" in suggestions:
        print(f"❌ Error: {suggestions['error']}")
        return
    
    if not suggestions["products"]:
        print("✅ No unmatched products found!")
        return
    
    print(f"\n📦 Found {suggestions['unmatched_count']} unmatched products:")
    table_data = []
    for i, product in enumerate(suggestions["products"][:10], 1):
        table_data.append([
            i,
            product["title"][:50] + "..." if len(product["title"]) > 50 else product["title"],
            product["vendor"],
            f"${product['price']}"
        ])
    
    print(tabulate(table_data, headers=["#", "Title", "Brand", "Price"], tablefmt="simple"))
    
    # Step 2: Select product to match
    try:
        selection = int(input("\nSelect product to find matches for (or 0 to cancel): "))
        if selection == 0:
            return
        if selection < 1 or selection > len(suggestions["products"]):
            print("❌ Invalid selection")
            return
    except ValueError:
        print("❌ Invalid input")
        return
    
    selected_product = suggestions["products"][selection - 1]
    print(f"\n✅ Selected: {selected_product['title']}")
    print(f"   Brand: {selected_product['vendor']} | Price: ${selected_product['price']}")
    
    # Step 3: Find AI matches
    print("\n🔍 Using AI to find matches...")
    matches = matcher.find_matches(selected_product["id"], min_confidence=70)
    
    if "error" in matches:
        print(f"❌ Error: {matches['error']}")
        return
    
    if not matches.get("matches"):
        print("❌ No confident matches found")
        return
    
    print(f"\n🎯 Found {len(matches['matches'])} potential matches:")
    for i, match in enumerate(matches["matches"], 1):
        analysis = match["analysis"]
        comp_product = match["competitor_product"]
        
        print(f"\n{i}. {comp_product['title']}")
        print(f"   Competitor: {comp_product['competitors']['name']}")
        print(f"   Price: ${comp_product['price']}")
        print(f"   Confidence: {analysis['confidence']}%")
        print(f"   Match: {'✅ YES' if analysis['is_match'] else '❌ NO'}")
        print(f"   Reasoning: {analysis['reasoning'][:200]}...")
        
        if analysis.get("warnings"):
            print(f"   ⚠️  Warnings: {', '.join(analysis['warnings'])}")
    
    # Step 4: Create match
    if matches["matches"]:
        try:
            match_num = int(input("\nSelect match to create (or 0 to skip): "))
            if match_num > 0 and match_num <= len(matches["matches"]):
                selected_match = matches["matches"][match_num - 1]
                
                # Confirm creation
                print(f"\n📋 Confirm Match Creation:")
                print(f"IDC: {selected_product['title']}")
                print(f"Competitor: {selected_match['competitor_product']['title']}")
                print(f"Confidence: {selected_match['analysis']['confidence']}%")
                
                confirm = input("\nCreate this match? (y/n): ").strip().lower()
                if confirm == 'y':
                    result = matcher.create_verified_match(
                        selected_product["id"],
                        selected_match["competitor_product"]["id"],
                        require_confidence=70
                    )
                    
                    if "error" in result:
                        print(f"❌ {result['error']}")
                        if "analysis" in result:
                            print(f"   Confidence: {result['analysis']['confidence']}%")
                            print(f"   Reasoning: {result['analysis']['reasoning']}")
                    else:
                        print(f"✅ {result['message']}")
                        print(f"   Match ID: {result['match']['id']}")
        except ValueError:
            pass

def analyze_specific_match(matcher: IntelligentMatcher):
    """Analyze a specific pair of products"""
    print("\n🔍 Analyze Specific Product Match\n")
    
    # Search for IDC product
    idc_search = input("Search for IDC product: ").strip()
    idc_products = matcher.search_products(idc_search, "idc")
    
    if not idc_products:
        print("❌ No IDC products found")
        return
    
    print("\nIDC Products:")
    for i, p in enumerate(idc_products[:5], 1):
        print(f"{i}. {p['title']} - ${p['price']}")
    
    idc_selection = int(input("Select IDC product: "))
    idc_product = idc_products[idc_selection - 1]
    
    # Search for competitor product
    comp_search = input("\nSearch for competitor product: ").strip()
    comp_products = matcher.search_products(comp_search, "competitor")
    
    if not comp_products:
        print("❌ No competitor products found")
        return
    
    print("\nCompetitor Products:")
    for i, p in enumerate(comp_products[:5], 1):
        print(f"{i}. {p['title']} - ${p['price']} ({p.get('competitors', {}).get('name', 'Unknown')})")
    
    comp_selection = int(input("Select competitor product: "))
    comp_product = comp_products[comp_selection - 1]
    
    # Analyze match
    print("\n🤖 Analyzing match with AI...")
    result = matcher.analyze_match(idc_product["id"], comp_product["id"])
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    analysis = result["analysis"]
    print(f"\n📊 Analysis Results:")
    print(f"Match: {'✅ YES' if analysis['is_match'] else '❌ NO'}")
    print(f"Confidence: {analysis['confidence']}%")
    print(f"\nModel Extraction:")
    print(f"  IDC: {analysis.get('model_extracted', {}).get('idc', 'Unknown')}")
    print(f"  Competitor: {analysis.get('model_extracted', {}).get('competitor', 'Unknown')}")
    print(f"\nReasoning: {analysis['reasoning']}")
    
    if analysis.get("warnings"):
        print(f"\n⚠️  Warnings:")
        for warning in analysis["warnings"]:
            print(f"  - {warning}")

def main():
    parser = argparse.ArgumentParser(description="AI-powered product matching tool")
    parser.add_argument("--analyze", nargs=2, metavar=("IDC_ID", "COMP_ID"), 
                       help="Analyze specific product match")
    parser.add_argument("--find", metavar="IDC_ID", help="Find matches for IDC product")
    parser.add_argument("--unmatched", action="store_true", help="Show unmatched products")
    parser.add_argument("--brand", help="Filter by brand")
    parser.add_argument("--confidence", type=int, default=70, help="Minimum confidence (default: 70)")
    
    args = parser.parse_args()
    matcher = IntelligentMatcher()
    
    if args.analyze:
        result = matcher.analyze_match(args.analyze[0], args.analyze[1])
        print(json.dumps(result, indent=2))
    elif args.find:
        result = matcher.find_matches(args.find, min_confidence=args.confidence)
        print(json.dumps(result, indent=2))
    elif args.unmatched:
        result = matcher.get_unmatched_suggestions(brand=args.brand)
        if "products" in result:
            for p in result["products"]:
                print(f"{p['id']}: {p['title']} ({p['vendor']}) - ${p['price']}")
    else:
        # Interactive mode
        print("🤖 AI-Powered Product Matching Tool")
        print("\n1. Find matches for unmatched products")
        print("2. Analyze specific product pair")
        print("3. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            interactive_intelligent_match(matcher)
        elif choice == "2":
            analyze_specific_match(matcher)

if __name__ == "__main__":
    main()