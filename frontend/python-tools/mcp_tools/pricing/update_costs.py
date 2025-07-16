"""
MCP wrapper for update_costs tool - update costs by SKU
"""

from typing import Dict, Any, Optional, List
import json
from ..base import BaseMCPTool
from base import ShopifyClient

class UpdateCostsTool(BaseMCPTool):
    """Update product costs by SKU - faster than update_pricing for cost-only changes"""
    
    name = "update_costs"
    description = "Update product costs by SKU - optimized for bulk cost updates only"
    context = """
    Efficiently update product costs by SKU without touching pricing:
    
    Key Benefits:
    - Faster than update_pricing when only cost needs updating
    - Direct SKU lookup (no need for product/variant IDs)  
    - Bulk-friendly with detailed success/failure reporting
    - Preserves all other variant fields
    
    Use Cases:
    - Inventory cost adjustments after supplier price changes
    - Bulk cost corrections from spreadsheets
    - Cost sync from external systems
    - Margin analysis preparations
    
    Important Notes:
    - Only updates cost (unit cost for inventory tracking)
    - Does not change selling price or compare-at price
    - SKU must exist and be unique in the store
    - Cost affects profit margin calculations
    
    For pricing changes, use update_pricing tool instead.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "sku": {
                "type": "string",
                "description": "Product variant SKU to update"
            },
            "cost": {
                "type": "number",
                "description": "New unit cost for inventory tracking"
            },
            "currency": {
                "type": "string",
                "description": "Currency code (default: USD)",
                "default": "USD"
            }
        },
        "required": ["sku", "cost"]
    }
    
    async def execute(self, sku: str, cost: float, currency: str = "USD") -> Dict[str, Any]:
        """Update cost for a variant by SKU"""
        self.validate_env()
        
        # Validate cost parameter
        if cost is None:
            return {
                "success": False,
                "error": "Cost parameter cannot be None. Please provide a valid numeric cost value."
            }
        
        if not isinstance(cost, (int, float)):
            try:
                cost = float(cost)
            except (ValueError, TypeError):
                return {
                    "success": False,
                    "error": f"Invalid cost value: {cost}. Must be a number."
                }
        
        if cost < 0:
            return {
                "success": False,
                "error": "Cost cannot be negative"
            }
        
        try:
            client = ShopifyClient()
            
            # Get variant info by SKU
            variant = await self._get_variant_by_sku(client, sku)
            if not variant:
                return {
                    "success": False,
                    "error": f"SKU not found: {sku}"
                }
            
            # Get current cost for comparison
            current_cost = 0.0
            if variant.get('inventoryItem', {}).get('unitCost'):
                current_cost = float(variant['inventoryItem']['unitCost']['amount'])
            
            # Update cost via inventory item
            success, result = await self._update_inventory_cost(
                client, 
                variant['inventoryItem']['id'], 
                cost
            )
            
            if success:
                return {
                    "success": True,
                    "sku": sku,
                    "product_title": variant['product']['title'],
                    "variant_title": variant.get('title', 'Default'),
                    "cost_update": {
                        "old_cost": current_cost,
                        "new_cost": cost,
                        "currency": currency,
                        "change": cost - current_cost
                    },
                    "inventory_item_id": variant['inventoryItem']['id']
                }
            else:
                return {
                    "success": False,
                    "sku": sku,
                    "error": result
                }
                
        except Exception as e:
            raise Exception(f"update_costs failed: {str(e)}")
    
    async def _get_variant_by_sku(self, client: ShopifyClient, sku: str) -> Optional[Dict[str, Any]]:
        """Get variant and inventory item info by SKU"""
        query = '''
        query getVariantBySku($query: String!) {
            productVariants(first: 1, query: $query) {
                edges {
                    node {
                        id
                        sku
                        title
                        product {
                            id
                            title
                            handle
                        }
                        inventoryItem {
                            id
                            unitCost {
                                amount
                                currencyCode
                            }
                        }
                    }
                }
            }
        }
        '''
        
        variables = {"query": f"sku:{sku}"}
        result = client.execute_graphql(query, variables)
        
        edges = result.get('data', {}).get('productVariants', {}).get('edges', [])
        if edges:
            return edges[0]['node']
        return None
    
    async def _update_inventory_cost(self, client: ShopifyClient, inventory_item_id: str, cost: float) -> tuple[bool, Any]:
        """Update cost for inventory item"""
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
            'id': inventory_item_id,
            'input': {
                'cost': f"{float(cost):.2f}"
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        # Check for errors
        update_data = result.get('data', {}).get('inventoryItemUpdate', {})
        user_errors = update_data.get('userErrors', [])
        
        if user_errors:
            error_messages = [f"{error['field']}: {error['message']}" for error in user_errors]
            return False, "; ".join(error_messages)
        
        return True, update_data.get('inventoryItem')
            
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