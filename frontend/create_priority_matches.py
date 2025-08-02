#!/usr/bin/env python3
"""
Create priority product matches for ECM and Profitec products
"""

import requests
import json
import time

BASE_URL = "http://localhost:5173"

# Priority matches to create
MATCHES_TO_CREATE = [
    # ECM Synchronika Black
    {
        "idc_id": "gid://shopify/Product/7383711580194",  # ECM Synchronika Black
        "competitor_matches": [
            "17d3a3c9-b168-42e8-8158-1118c55cc4bf",  # HomeCoffeeSolutions Black
            "191e41e0-9a31-4a96-88ac-642e9a16803b",  # Kitchen Barista Anthracite
        ]
    },
    # ECM Synchronika White
    {
        "idc_id": "gid://shopify/Product/7383714627618",  # ECM Synchronika White
        "competitor_matches": [
            "fb96b6c1-06f8-40b2-8484-c6f05a56782c",  # HomeCoffeeSolutions White
        ]
    },
    # ECM Synchronika White w/ Flow Control
    {
        "idc_id": "gid://shopify/Product/7383736287266",  # ECM Synchronika White w/ FC
        "competitor_matches": [
            "51928176-84d2-4f84-ab07-7b2e179c5881",  # HomeCoffeeSolutions White w/ FC
        ]
    },
    # Profitec Pro 600 w/ PID
    {
        "idc_id": "gid://shopify/Product/1541537595426",  # Pro 600 w/ PID
        "competitor_matches": [
            "045dd571-2e9c-48e3-ae5a-7719219a30c5",  # HomeCoffeeSolutions Pro 600 w/ PID
            "94004c32-09ff-4874-b1a4-126333d81895",  # HomeCoffeeSolutions Pro 600 w/ PID (alt)
            "d20db26a-a1f4-4aa7-930e-1f4ee1cf8989",  # Kitchen Barista Open Box
        ]
    },
    # Profitec Pro 600 w/ Flow Control
    {
        "idc_id": "gid://shopify/Product/4383739215906",  # Pro 600 w/ FC
        "competitor_matches": [
            "462cca33-8e01-4f82-ad79-e1efb4822860",  # HomeCoffeeSolutions w/ FC
            "37e71b0b-6003-42e5-af25-16fc6f6e61da",  # HomeCoffeeSolutions w/ FC (alt)
        ]
    },
    # Profitec Pro 500
    {
        "idc_id": "gid://shopify/Product/5430583105",  # Pro 500 w/ PID
        "competitor_matches": [
            "5557e4d7-d500-402b-bf68-8cb35ef73552",  # Kitchen Barista Pro 500
        ]
    }
]

def create_match(idc_id, competitor_id):
    """Create a single match"""
    print(f"\n🔄 Creating match: {idc_id} <-> {competitor_id}")
    
    # Try the intelligent matching endpoint
    response = requests.post(
        f"{BASE_URL}/api/price-monitor/intelligent-matching/create-verified-match",
        json={
            "idc_product_id": idc_id,
            "competitor_product_id": competitor_id,
            "require_confidence": 70
        }
    )
    
    if response.ok:
        result = response.json()
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            # Try the regular matching endpoint
            response2 = requests.post(
                f"{BASE_URL}/api/price-monitor/product-matching",
                json={
                    "idc_product_id": idc_id,
                    "competitor_product_id": competitor_id
                }
            )
            if response2.ok:
                print("✅ Match created using alternative endpoint")
                return True
            else:
                print(f"❌ Alternative endpoint also failed: {response2.status_code}")
                return False
        else:
            print(f"✅ Match created: {result.get('message', 'Success')}")
            return True
    else:
        print(f"❌ Request failed: {response.status_code} - {response.text}")
        return False

def main():
    print("🎯 Creating Priority Product Matches")
    print("=" * 50)
    
    total_matches = 0
    successful_matches = 0
    
    for match_group in MATCHES_TO_CREATE:
        idc_id = match_group["idc_id"]
        print(f"\n📦 Processing IDC Product: {idc_id}")
        
        for competitor_id in match_group["competitor_matches"]:
            total_matches += 1
            if create_match(idc_id, competitor_id):
                successful_matches += 1
            time.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 50)
    print(f"📊 Summary:")
    print(f"  Total attempts: {total_matches}")
    print(f"  Successful: {successful_matches}")
    print(f"  Failed: {total_matches - successful_matches}")

if __name__ == "__main__":
    main()