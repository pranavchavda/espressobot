"""
SkuVault integration tools for the Shopify agent.
Provides functions to upload product data from Shopify to SkuVault.
"""
import os
import requests
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get SkuVault credentials from environment variables
SKUVAULT_TENANT_TOKEN = os.environ.get('SKUVAULT_TENANT_TOKEN')
SKUVAULT_USER_TOKEN = os.environ.get('SKUVAULT_USER_TOKEN')

def upload_product_to_skuvault(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upload a product to SkuVault using their API.
    
    Args:
        product_data: Dictionary containing product information from Shopify
        
    Returns:
        Dictionary with status and message about the upload result
    """
    if not SKUVAULT_TENANT_TOKEN or not SKUVAULT_USER_TOKEN:
        return {
            "success": False,
            "message": "SkuVault credentials not configured. Please set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN in .env file."
        }
    
    # Extract product data
    try:
        # Extract basic product information
        title = product_data.get('title', '')
        vendor = product_data.get('vendor', '')
        
        # Extract image if available
        images = product_data.get('images', {}).get('edges', [])
        image_url = None
        if images and len(images) > 0 and 'node' in images[0] and 'src' in images[0]['node']:
            image_url = images[0]['node']['src']
        
        # Extract variant information
        variants = product_data.get('variants', {}).get('edges', [])
        if not variants:
            return {
                "success": False,
                "message": f"No variants found for product '{title}'"
            }
            
        variant = variants[0].get('node', {}) if variants else {}
        sku = variant.get('sku', '')
        price = variant.get('price', '')
        
        # Safely extract cost with proper null checks
        inventory_item = variant.get('inventoryItem', {})
        unit_cost = inventory_item.get('unitCost', {}) if inventory_item else {}
        cost = unit_cost.get('amount', 0) if unit_cost else 0
        
        if not sku:
            return {
                "success": False,
                "message": "Product has no SKU, which is required for SkuVault"
            }
        
        # Prepare the data for SkuVault
        skuvault_product_data = {
            "Description": title,
            "ShortDescription": title,
            "LongDescription": title,
            "PartNumber": sku,
            "AllowCreateAp": False,
            "IsSerialized": False,
            "IsLotted": False,
            "Sku": sku,
            "Classification": "General",
            "Supplier": "Unknown",
            "Brand": vendor or "Unknown",
            "Cost": cost,
            "SalePrice": price,
            "TenantToken": SKUVAULT_TENANT_TOKEN,
            "UserToken": SKUVAULT_USER_TOKEN,
            "Pictures": [image_url] if image_url else []
        }
        
        # Send a POST request to SkuVault API
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            'https://app.skuvault.com/api/products/createProduct',
            headers=headers,
            json=skuvault_product_data
        )
        
        # Check the response
        if response.status_code == 200:
            return {
                "success": True,
                "message": f"Product '{sku}' added to SkuVault successfully."
            }
        else:
            return {
                "success": False,
                "message": f"Failed to add product '{sku}' to SkuVault. Status code: {response.status_code}. Response: {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing product for SkuVault: {str(e)}"
        }

async def upload_shopify_product_to_skuvault(product_sku: str) -> Dict[str, Any]:
    """
    Fetch a product from Shopify by SKU and upload it to SkuVault.
    
    Args:
        product_sku: The SKU of the Shopify product to upload
        
    Returns:
        Dictionary with status and message about the upload result
    """
    from simple_agent import execute_shopify_query
    
    # Prepare the GraphQL query to fetch product data by SKU
    query = """
    query {
      productVariants(first: 1, query: "sku:%s") {
        edges {
          node {
            id
            sku
            price
            inventoryItem {
              id
              unitCost {
                amount
              }
            }
            product {
              id
              title
              vendor
              images(first: 1) {
                edges {
                  node {
                    src
                  }
                }
              }
            }
          }
        }
      }
    }
    """ % product_sku
    
    # Execute the query
    result = await execute_shopify_query(query)
    
    # Check for errors
    if "errors" in result:
        error_message = result.get("errors", [{}])[0].get("message", "Unknown error")
        return {
            "success": False,
            "message": f"GraphQL query error for SKU '{product_sku}': {error_message}"
        }
    
    # Extract product data
    variant_edges = result.get("data", {}).get("productVariants", {}).get("edges", [])
    
    if not variant_edges:
        return {
            "success": False,
            "message": f"No product found with SKU '{product_sku}'"
        }
        
    variant_data = variant_edges[0].get("node") if variant_edges else None
    
    if not variant_data:
        return {
            "success": False,
            "message": f"No product data found for SKU '{product_sku}'"
        }
    
    # Restructure the data to match what upload_product_to_skuvault expects
    product_data = variant_data.get("product", {})
    if not product_data:
        return {
            "success": False,
            "message": f"No product information found for variant with SKU '{product_sku}'"
        }
    
    # Add variant data to product data
    product_data["variants"] = {
        "edges": [
            {
                "node": {
                    "sku": variant_data.get("sku", ""),
                    "price": variant_data.get("price", ""),
                    "inventoryItem": variant_data.get("inventoryItem", {})
                }
            }
        ]
    }
    
    # Upload the product to SkuVault
    return upload_product_to_skuvault(product_data)

async def batch_upload_to_skuvault(product_skus: str) -> Dict[str, Any]:
    """
    Upload multiple products to SkuVault in batch.
    
    Args:
        product_skus: Comma-separated list of product SKUs to upload
        
    Returns:
        Dictionary with status and results for each product
    """
    # Clean and prepare the list of product SKUs
    product_skus = product_skus.replace('|', ',')
    product_skus_list = [
        sku.strip() for sku in product_skus.split(',') if sku.strip()
    ]
    
    results = []
    success_count = 0
    failure_count = 0
    
    for product_sku in product_skus_list:
        result = await upload_shopify_product_to_skuvault(product_sku)
        results.append({
            "sku": product_sku,
            "success": result["success"],
            "message": result["message"]
        })
        
        if result["success"]:
            success_count += 1
        else:
            failure_count += 1
    
    return {
        "success": success_count > 0,
        "message": f"Processed {len(product_skus_list)} products. Success: {success_count}, Failed: {failure_count}",
        "results": results
    }
