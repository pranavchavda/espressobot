"""
Native MCP implementation for add_variants_to_product
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional, Union

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class AddVariantsTool(BaseMCPTool):
    """Add new variants to an existing product using bulk operation"""
    
    name = "add_variants_to_product"
    description = "Add multiple variants to an existing product with different options, prices, and SKUs"
    context = """
    This tool allows you to add multiple variants to an existing product in a single operation.
    
    **Key Features:**
    - Bulk add variants with different option values
    - Set individual prices and SKUs for each variant
    - Specify option combinations (Size, Color, etc.)
    - Validate variants before creation
    
    **Input Format:**
    Each variant should specify:
    - price: String price (e.g., "19.99")
    - sku: Unique SKU for the variant
    - optionValues: Array of option name/value pairs
    
    **Example Variants:**
    ```
    [
      {
        "price": "19.99",
        "sku": "ABC-SMALL",
        "optionValues": [
          {"optionName": "Size", "value": "Small"}
        ]
      },
      {
        "price": "29.99", 
        "sku": "ABC-LARGE",
        "optionValues": [
          {"optionName": "Size", "value": "Large"}
        ]
      }
    ]
    ```
    
    **Important Notes:**
    - Option names must match existing product options
    - SKUs must be unique across all products
    - Prices should be strings with decimal format
    - The product must already exist
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "Product identifier (SKU, handle, or product ID)"
            },
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "price": {
                            "type": "string",
                            "description": "Variant price (e.g., '19.99')"
                        },
                        "sku": {
                            "type": "string",
                            "description": "Unique SKU for the variant"
                        },
                        "optionValues": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "optionName": {
                                        "type": "string",
                                        "description": "Name of the option (e.g., 'Size')"
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Value for the option (e.g., 'Large')"
                                    }
                                },
                                "required": ["optionName", "value"]
                            }
                        },
                        "compareAtPrice": {
                            "type": "string",
                            "description": "Compare at price (optional)"
                        },
                        "inventoryPolicy": {
                            "type": "string",
                            "enum": ["DENY", "CONTINUE"],
                            "description": "Inventory policy when out of stock"
                        },
                        "inventoryQuantity": {
                            "type": "integer",
                            "description": "Initial inventory quantity"
                        },
                        "barcode": {
                            "type": "string",
                            "description": "Barcode for the variant"
                        },
                        "taxable": {
                            "type": "boolean",
                            "description": "Whether the variant is taxable"
                        }
                    },
                    "required": ["price", "sku", "optionValues"]
                }
            }
        },
        "required": ["product_id", "variants"]
    }
    
    async def execute(self, product_id: str, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute variant addition"""
        try:
            client = ShopifyClient()
            
            # Resolve product ID
            resolved_id = client.resolve_product_id(product_id)
            if not resolved_id:
                return {
                    "success": False,
                    "error": f"Product not found: {product_id}"
                }
            
            # Validate variants
            validation_result = await self._validate_variants(client, resolved_id, variants)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
            
            # Create variants
            result = await self._create_variants(client, resolved_id, variants)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _validate_variants(self, client: ShopifyClient, product_id: str, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate variants before creation"""
        
        # Get product info to check existing options
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                options {
                    name
                    values
                }
                variants(first: 100) {
                    edges {
                        node {
                            sku
                        }
                    }
                }
            }
        }
        """
        
        variables = {"id": product_id}
        result = client.execute_graphql(query, variables)
        
        product = result.get('data', {}).get('product')
        if not product:
            return {"valid": False, "error": "Product not found"}
        
        # Get existing options
        existing_options = {opt['name']: opt['values'] for opt in product.get('options', [])}
        
        # Get existing SKUs
        existing_skus = set()
        for edge in product.get('variants', {}).get('edges', []):
            sku = edge.get('node', {}).get('sku')
            if sku:
                existing_skus.add(sku.upper())
        
        # Validate each variant
        for i, variant in enumerate(variants):
            # Check required fields
            if not variant.get('price'):
                return {"valid": False, "error": f"Variant {i+1}: Price is required"}
            
            if not variant.get('sku'):
                return {"valid": False, "error": f"Variant {i+1}: SKU is required"}
            
            # Check SKU uniqueness
            if variant['sku'].upper() in existing_skus:
                return {"valid": False, "error": f"Variant {i+1}: SKU '{variant['sku']}' already exists"}
            
            # Check option values
            option_values = variant.get('optionValues', [])
            if not option_values:
                return {"valid": False, "error": f"Variant {i+1}: Option values are required"}
            
            for option_value in option_values:
                option_name = option_value.get('optionName')
                option_val = option_value.get('value')
                
                if not option_name or not option_val:
                    return {"valid": False, "error": f"Variant {i+1}: Option name and value are required"}
                
                if option_name not in existing_options:
                    return {"valid": False, "error": f"Variant {i+1}: Option '{option_name}' does not exist on product"}
            
            # Add to existing SKUs for next iteration
            existing_skus.add(variant['sku'].upper())
        
        return {"valid": True}
    
    async def _create_variants(self, client: ShopifyClient, product_id: str, variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create the variants using GraphQL mutation"""
        
        mutation = """
        mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkCreate(productId: $productId, variants: $variants) {
                productVariants {
                    id
                    title
                    sku
                    price
                    compareAtPrice
                    availableForSale
                    inventoryPolicy
                    inventoryQuantity
                    barcode
                    taxable
                    selectedOptions {
                        name
                        value
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        # Format variants for GraphQL
        formatted_variants = []
        for variant in variants:
            formatted_variant = {
                "price": variant["price"],
                "sku": variant["sku"],
                "optionValues": variant["optionValues"]
            }
            
            # Add optional fields
            if variant.get("compareAtPrice"):
                formatted_variant["compareAtPrice"] = variant["compareAtPrice"]
            
            if variant.get("inventoryPolicy"):
                formatted_variant["inventoryPolicy"] = variant["inventoryPolicy"]
            
            if variant.get("inventoryQuantity") is not None:
                formatted_variant["inventoryQuantity"] = variant["inventoryQuantity"]
            
            if variant.get("barcode"):
                formatted_variant["barcode"] = variant["barcode"]
            
            if variant.get("taxable") is not None:
                formatted_variant["taxable"] = variant["taxable"]
            
            formatted_variants.append(formatted_variant)
        
        variables = {
            "productId": product_id,
            "variants": formatted_variants
        }
        
        result = client.execute_graphql(mutation, variables)
        
        # Check for errors
        errors = result.get("data", {}).get("productVariantsBulkCreate", {}).get("userErrors")
        if errors:
            return {
                "success": False,
                "error": f"Variant creation errors: {errors}"
            }
        
        created_variants = result.get("data", {}).get("productVariantsBulkCreate", {}).get("productVariants", [])
        
        return {
            "success": True,
            "created_count": len(created_variants),
            "variants": [
                {
                    "id": v.get("id"),
                    "title": v.get("title"),
                    "sku": v.get("sku"),
                    "price": v.get("price"),
                    "compareAtPrice": v.get("compareAtPrice"),
                    "options": v.get("selectedOptions", [])
                }
                for v in created_variants
            ]
        }
    
    async def test(self) -> Dict[str, Any]:
        """Test the tool with validation"""
        try:
            self.validate_env()
            client = ShopifyClient()
            
            # Test with a simple query to verify connection
            result = client.execute_graphql('{ shop { name } }')
            
            return {
                "status": "passed",
                "message": f"Connected to shop: {result.get('data', {}).get('shop', {}).get('name', 'Unknown')}"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }