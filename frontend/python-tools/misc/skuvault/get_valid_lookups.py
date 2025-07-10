#!/usr/bin/env python3
"""
Get valid Classification and Supplier values from SkuVault API
"""

import os
import json
import requests
from typing import Dict, Any, List

def get_skuvault_lookups():
    """Fetch valid Classifications and Suppliers from SkuVault"""
    
    tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
    user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    if not tenant_token or not user_token:
        print("Error: Missing SkuVault credentials")
        return
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Get Classifications
    print("VALID CLASSIFICATIONS:")
    print("=" * 50)
    
    classifications_url = "https://app.skuvault.com/api/products/getClassifications"
    classifications_payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token
    }
    
    try:
        response = requests.post(classifications_url, json=classifications_payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            classifications = data.get('Classifications', [])
            for clf in classifications:
                status = "✓" if clf.get('IsEnabled', False) else "✗"
                print(f"{status} {clf.get('Name', 'Unknown')}")
                if 'Attributes' in clf and clf['Attributes']:
                    for attr in clf['Attributes']:
                        print(f"   - Attribute: {attr}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n")
    
    # Get Suppliers
    print("VALID SUPPLIERS:")
    print("=" * 50)
    
    suppliers_url = "https://app.skuvault.com/api/products/getSuppliers"
    suppliers_payload = {
        "TenantToken": tenant_token,
        "UserToken": user_token
    }
    
    try:
        response = requests.post(suppliers_url, json=suppliers_payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            suppliers = data.get('Suppliers', [])
            
            # Sort suppliers alphabetically
            suppliers.sort(key=lambda x: x.get('Name', ''))
            
            for supplier in suppliers:
                status = "✓" if supplier.get('IsEnabled', False) else "✗"
                print(f"{status} {supplier.get('Name', 'Unknown')}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("\nNOTE: Use only enabled (✓) values when creating products in SkuVault")
    print("The default values 'General' and 'Unknown' should work, but may not be ideal.")
    print("\nFor iDrinkCoffee.com, consider using supplier names like:")
    print("- For coffee products: Use the actual roaster/brand name if it exists in the list")
    print("- For equipment: Use the manufacturer name (e.g., 'Profitec', 'Rocket', etc.)")

if __name__ == "__main__":
    get_skuvault_lookups()