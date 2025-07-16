"""
MCP wrapper for update_pricing tool
"""

from typing import Dict, Any, Optional
import json
from ..base import BaseMCPTool
from base import ShopifyClient

class UpdatePricingTool(BaseMCPTool):
    """Update product variant pricing"""
    
    name = "update_pricing"
    description = "Update product variant pricing including price, compare-at price, and cost"
    context = """
    Updates pricing for products with intelligent handling of discounts:
    
    Price Types:
    - price: The selling price customers pay
    - compare_at_price: Original/MSRP price (shows as strikethrough)
    
    Discount Logic:
    - If compare_at_price > price: Shows as "On Sale" 
    - If compare_at_price = null: No discount shown
    - To remove discount: Set price = compare_at_price, then clear compare_at_price
    
    IMPORTANT Business Rules:
    - Always preserve original price in compare_at_price before discounting
    - For MAP pricing: Use compare_at_price for MSRP, price for selling price
    - Price changes apply to ALL variants of a product
    - Prices should be in store's currency (USD for iDrinkCoffee)
    
    Examples:
    - Regular price update: --price 49.99
    - Add discount: --price 39.99 --compare-at-price 49.99
    - Remove discount: --price 49.99 --compare-at-price null
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "Product ID (numeric or GID format)"
            },
            "variant_id": {
                "type": "string",
                "description": "Variant ID to update"
            },
            "price": {
                "type": "number",
                "description": "New selling price"
            },
            "compare_at_price": {
                "type": ["number", "null"],
                "description": "Original/MSRP price (null to remove)"
            },
            "cost": {
                "type": ["number", "null"],
                "description": "Unit cost for inventory tracking"
            }
        },
        "required": ["product_id", "variant_id", "price"]
    }
    
    async def execute(self, product_id: str, variant_id: str, price: float, compare_at_price: Optional[float] = None, cost: Optional[float] = None) -> Dict[str, Any]:
        """Execute pricing update via Shopify API"""
        self.validate_env()
        
        try:
            client = ShopifyClient()
            
            # Normalize IDs
            if not product_id.startswith('gid://'):
                product_id = f"gid://shopify/Product/{product_id}"
            if not variant_id.startswith('gid://'):
                variant_id = f"gid://shopify/ProductVariant/{variant_id}"
            
            # Build variant input for pricing update
            variant_input = {'id': variant_id}
            
            # Format price (ensure 2 decimal places)
            if price is not None:
                variant_input['price'] = f"{float(price):.2f}"
            
            # Handle compare_at_price
            if compare_at_price is not None:
                variant_input['compareAtPrice'] = f"{float(compare_at_price):.2f}" if compare_at_price > 0 else None
            
            # Update pricing via productVariantsBulkUpdate
            mutation = '''
            mutation updateVariantPricing($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    product {
                        id
                        title
                    }
                    productVariants {
                        id
                        title
                        price
                        compareAtPrice
                        sku
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            variables = {
                'productId': product_id,
                'variants': [variant_input]
            }
            
            result = client.execute_graphql(mutation, variables)
            
            # Check for errors
            data = result.get('data', {}).get('productVariantsBulkUpdate', {})
            user_errors = data.get('userErrors', [])
            
            if user_errors:
                return {
                    "success": False,
                    "errors": [f"{error['field']}: {error['message']}" for error in user_errors]
                }
            
            updated_variants = data.get('productVariants', [])
            
            # Handle cost update separately if provided
            cost_result = None
            if cost is not None and updated_variants:
                cost_result = await self._update_variant_cost(client, variant_id, cost)
            
            return {
                "success": True,
                "product": data.get('product'),
                "updated_variants": updated_variants,
                "cost_update": cost_result
            }
                
        except Exception as e:
            raise Exception(f"update_pricing failed: {str(e)}")
    
    async def _update_variant_cost(self, client: ShopifyClient, variant_id: str, cost: float) -> Dict[str, Any]:
        """Update inventory item cost (separate mutation)"""
        try:
            # First get the inventory item ID
            query = '''
            query getInventoryItem($id: ID!) {
                productVariant(id: $id) {
                    inventoryItem {
                        id
                    }
                }
            }
            '''
            
            inv_result = client.execute_graphql(query, {'id': variant_id})
            inventory_item = inv_result.get('data', {}).get('productVariant', {}).get('inventoryItem')
            
            if not inventory_item:
                return {"success": False, "error": "Could not find inventory item for cost update"}
            
            # Update cost
            mutation = '''
            mutation updateCost($id: ID!, $input: InventoryItemInput!) {
                inventoryItemUpdate(id: $id, input: $input) {
                    inventoryItem {
                        id
                        unitCost {
                            amount
                            currencyCode
                        }
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            variables = {
                'id': inventory_item['id'],
                'input': {
                    'cost': f"{float(cost):.2f}"
                }
            }
            
            cost_result = client.execute_graphql(mutation, variables)
            
            # Check for errors
            cost_data = cost_result.get('data', {}).get('inventoryItemUpdate', {})
            cost_errors = cost_data.get('userErrors', [])
            
            if cost_errors:
                return {
                    "success": False,
                    "errors": [f"{error['field']}: {error['message']}" for error in cost_errors]
                }
            
            return {
                "success": True,
                "inventory_item": cost_data.get('inventoryItem')
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool (read-only test)"""
        try:
            # Test environment and API connectivity
            self.validate_env()
            
            client = ShopifyClient()
            
            # Simple query to test API connectivity
            query = """
            query testConnection {
                shop {
                    name
                    myshopifyDomain
                }
            }
            """
            
            result = client.execute_graphql(query)
            
            if result.get('data', {}).get('shop'):
                return {
                    "status": "passed",
                    "message": f"API connectivity verified for shop: {result['data']['shop']['name']}"
                }
            else:
                return {
                    "status": "failed",
                    "message": "Failed to connect to Shopify API"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }