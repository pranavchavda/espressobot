"""
Native MCP implementation for update_variant_weight
"""

from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class UpdateVariantWeightTool(BaseMCPTool):
    """Update product variant weight by SKU"""
    
    name = "update_variant_weight"
    description = "Update the weight of a specific product variant using its SKU"
    context = """
    Updates the weight of a product variant using the Shopify GraphQL API.
    
    Features:
    - Find variant by SKU automatically
    - Update weight using productVariantsBulkUpdate mutation
    - Supports all Shopify weight units (GRAMS, KILOGRAMS, OUNCES, POUNDS)
    - Shows previous and new weight values
    - Validates input parameters
    
    Weight Units:
    - GRAMS: For small items (accessories, filters)
    - KILOGRAMS: For medium items (grinders, small machines)
    - OUNCES: Imperial system alternative
    - POUNDS: For heavy items (large espresso machines)
    
    Use cases:
    - Correct weight information after receiving products
    - Update shipping weight for accurate calculations
    - Fix data entry errors
    - Bulk weight corrections for similar products
    """
    
    input_schema = {
        "type": "object", 
        "properties": {
            "sku": {
                "type": "string",
                "description": "The SKU of the variant to update"
            },
            "weight": {
                "type": "number",
                "description": "The weight value (must be positive)"
            },
            "weight_unit": {
                "type": "string",
                "enum": ["GRAMS", "KILOGRAMS", "OUNCES", "POUNDS"],
                "description": "Weight unit",
                "default": "KILOGRAMS"
            }
        },
        "required": ["sku", "weight"]
    }
    
    async def execute(self, sku: str, weight: float, weight_unit: str = "KILOGRAMS") -> Dict[str, Any]:
        """Update variant weight natively"""
        try:
            # Validate inputs
            if not sku or not sku.strip():
                return {"success": False, "error": "SKU is required"}
                
            if weight <= 0:
                return {"success": False, "error": "Weight must be a positive number"}
                
            valid_units = ["GRAMS", "KILOGRAMS", "OUNCES", "POUNDS"]
            if weight_unit.upper() not in valid_units:
                return {"success": False, "error": f"Weight unit must be one of: {', '.join(valid_units)}"}
            
            weight_unit = weight_unit.upper()
            
            client = ShopifyClient()
            
            # First, find the variant by SKU
            search_query = """
            query findVariantBySku($sku: String!) {
                productVariants(first: 1, query: $sku) {
                    edges {
                        node {
                            id
                            sku
                            product {
                                id
                                title
                            }
                            inventoryItem {
                                id
                                measurement {
                                    weight {
                                        value
                                        unit
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """
            
            search_result = client.execute_graphql(search_query, {"sku": f"sku:{sku}"})
            
            if "errors" in search_result:
                return {"success": False, "error": f"GraphQL error: {search_result['errors']}"}
                
            variants = search_result.get("data", {}).get("productVariants", {}).get("edges", [])
            
            if not variants:
                return {"success": False, "error": f"No variant found with SKU: {sku}"}
                
            variant = variants[0]["node"]
            variant_id = variant["id"]
            product_id = variant["product"]["id"]
            product_title = variant["product"]["title"]
            
            # Get current weight for comparison
            current_weight = None
            current_unit = None
            if variant.get("inventoryItem", {}).get("measurement", {}).get("weight"):
                current_weight = variant["inventoryItem"]["measurement"]["weight"]["value"]
                current_unit = variant["inventoryItem"]["measurement"]["weight"]["unit"]
            
            # Update the variant weight using productVariantsBulkUpdate
            update_mutation = """
            mutation updateVariantWeight($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants {
                        id
                        sku
                        inventoryItem {
                            measurement {
                                weight {
                                    value
                                    unit
                                }
                            }
                        }
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            
            variables = {
                "productId": product_id,
                "variants": [{
                    "id": variant_id,
                    "inventoryItem": {
                        "measurement": {
                            "weight": {
                                "value": weight,
                                "unit": weight_unit
                            }
                        }
                    }
                }]
            }
            
            result = client.execute_graphql(update_mutation, variables)
            
            if "errors" in result:
                return {"success": False, "error": f"GraphQL error: {result['errors']}"}
                
            data = result.get("data", {}).get("productVariantsBulkUpdate", {})
            user_errors = data.get("userErrors", [])
            
            if user_errors:
                return {"success": False, "error": f"Update failed: {user_errors}"}
                
            updated_variants = data.get("productVariants", [])
            if not updated_variants:
                return {"success": False, "error": "No variants were updated"}
                
            updated_variant = updated_variants[0]
            new_weight_data = updated_variant.get("inventoryItem", {}).get("measurement", {}).get("weight", {})
            
            return {
                "success": True,
                "message": f"Successfully updated weight for SKU {sku}",
                "variant": {
                    "id": updated_variant["id"],
                    "sku": updated_variant["sku"],
                    "product_title": product_title,
                    "weight": {
                        "previous": {
                            "value": current_weight,
                            "unit": current_unit
                        } if current_weight else None,
                        "current": {
                            "value": new_weight_data.get("value"),
                            "unit": new_weight_data.get("unit")
                        }
                    }
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to update variant weight: {str(e)}"}
    
    async def test(self) -> Dict[str, Any]:
        """Test the tool"""
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