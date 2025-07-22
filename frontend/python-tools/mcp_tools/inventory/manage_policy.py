"""
MCP wrapper for manage_inventory_policy tool
"""

from typing import Dict, Any, Optional, List
import json
from ..base import BaseMCPTool
from base import ShopifyClient

class ManageInventoryPolicyTool(BaseMCPTool):
    """Manage product inventory policy (oversell settings)"""
    
    name = "manage_inventory_policy"
    description = "Set inventory policy to control whether products can be oversold"
    context = """
    Controls whether customers can purchase when inventory reaches zero:
    
    - DENY (default): Prevents overselling - customers cannot buy when out of stock
      Use for: Physical inventory, limited stock items
      
    - ALLOW/CONTINUE: Allows overselling - customers can buy even when out of stock  
      Use for: Pre-orders, made-to-order items, digital products
      
    IMPORTANT: 
    - This applies to ALL variants of a product
    - Check current inventory levels before changing policy
    - For pre-orders, use ALLOW with clear messaging in product description
    
    Accepts identifiers:
    - Variant ID (e.g., "31480448974882" or "gid://shopify/ProductVariant/31480448974882")
    - SKU (e.g., "ESP-1001")
    - Product handle (e.g., "mexican-altura")
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Variant ID, SKU, or product handle"
            },
            "policy": {
                "type": "string",
                "enum": ["deny", "allow", "continue"],
                "description": "Inventory policy (deny=no oversell, allow/continue=oversell allowed)"
            }
        },
        "required": ["identifier", "policy"]
    }
    
    async def execute(self, identifier: str, policy: str) -> Dict[str, Any]:
        """Execute inventory policy update via Shopify API"""
        self.validate_env()
        
        # Normalize policy value
        policy = policy.lower()
        if policy == "continue":
            policy = "allow"  # Handle both naming conventions
        
        # Convert to GraphQL enum value
        if policy == "deny":
            inventory_policy = "DENY"
        elif policy == "allow":
            inventory_policy = "CONTINUE"
        else:
            raise ValueError(f"Invalid policy '{policy}'. Must be 'deny' or 'allow'")
        
        try:
            # Initialize Shopify client
            client = ShopifyClient()
            
            # First, find the product/variants based on identifier
            variants = await self._find_variants(client, identifier)
            
            if not variants:
                return {
                    "success": False,
                    "error": f"No variants found for identifier: {identifier}"
                }
            
            # Update inventory policy for all variants
            updated_variants = []
            errors = []
            
            # Get product ID from first variant
            product_id = variants[0].get('product', {}).get('id') if variants else None
            
            for variant in variants:
                try:
                    # Validate variant data
                    variant_id = variant.get('id')
                    if not variant_id:
                        errors.append(f"Variant missing ID: {variant}")
                        continue
                    
                    # Use product ID from variant if available, otherwise from first variant
                    variant_product_id = variant.get('product', {}).get('id') or product_id
                    if not variant_product_id:
                        errors.append(f"Variant {variant_id}: No product ID found")
                        continue
                    
                    result = await self._update_variant_inventory_policy(
                        client, variant_id, inventory_policy, variant_product_id
                    )
                    if result['success']:
                        updated_variants.append({
                            "id": variant['id'],
                            "sku": variant.get('sku'),
                            "title": variant.get('title')
                        })
                    else:
                        errors.append(f"Variant {variant['id']}: {result['error']}")
                        
                except Exception as e:
                    errors.append(f"Variant {variant['id']}: {str(e)}")
            
            return {
                "success": len(updated_variants) > 0,
                "updated_variants": updated_variants,
                "total_updated": len(updated_variants),
                "policy_set": inventory_policy,
                "errors": errors if errors else None
            }
                
        except Exception as e:
            raise Exception(f"manage_inventory_policy failed: {str(e)}")
    
    async def _find_variants(self, client: ShopifyClient, identifier: str) -> List[Dict[str, Any]]:
        """Find variants based on identifier (variant ID, SKU, or product handle)"""
        
        if not identifier:
            return []
        
        # Clean identifier - remove GID prefix if present
        if identifier.startswith("gid://shopify/"):
            if "/ProductVariant/" in identifier:
                # Extract variant ID from GID
                identifier = identifier.split("/ProductVariant/")[-1]
            elif "/Product/" in identifier:
                # Extract product ID from GID
                identifier = identifier.split("/Product/")[-1]
        
        # Try as variant ID first (if numeric)
        if identifier.isdigit():
            query = """
            query getVariant($id: ID!) {
                productVariant(id: $id) {
                    id
                    sku
                    title
                    inventoryPolicy
                    product {
                        id
                        title
                        handle
                    }
                }
            }
            """
            
            result = client.execute_graphql(query, {
                "id": f"gid://shopify/ProductVariant/{identifier}"
            })
            
            if result.get('data', {}).get('productVariant'):
                return [result['data']['productVariant']]
        
        # Try as SKU
        sku_query = """
        query findVariantBySku($query: String!) {
            productVariants(first: 10, query: $query) {
                edges {
                    node {
                        id
                        sku
                        title
                        inventoryPolicy
                        product {
                            id
                            title
                            handle
                        }
                    }
                }
            }
        }
        """
        
        result = client.execute_graphql(sku_query, {
            "query": f"sku:{identifier}"
        })
        
        variants = [edge['node'] for edge in result.get('data', {}).get('productVariants', {}).get('edges', [])]
        if variants:
            return variants
        
        # Try as product handle - get all variants for the product
        handle_query = """
        query findProductByHandle($handle: String!) {
            product(handle: $handle) {
                id
                title
                variants(first: 100) {
                    edges {
                        node {
                            id
                            sku
                            title
                            inventoryPolicy
                            product {
                                id
                                title
                                handle
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = client.execute_graphql(handle_query, {
            "handle": identifier
        })
        
        if result.get('data', {}).get('product'):
            product = result['data']['product']
            # Add product info to each variant
            variants_with_product = []
            for edge in product['variants']['edges']:
                variant = edge['node']
                variant['product'] = {
                    'id': product['id'],
                    'title': product['title'], 
                    'handle': product.get('handle')
                }
                variants_with_product.append(variant)
            return variants_with_product
        
        return []
    
    async def _update_variant_inventory_policy(self, client: ShopifyClient, variant_id: str, policy: str, product_id: str) -> Dict[str, Any]:
        """Update inventory policy for a specific variant using bulk update"""
        
        mutation = """
        mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants {
                    id
                    sku
                    inventoryPolicy
                    title
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        # Validate and ensure IDs are in GID format
        if not variant_id:
            return {
                "success": False,
                "error": "Variant ID is None or empty"
            }
        
        if not product_id:
            return {
                "success": False,
                "error": "Product ID is None or empty"
            }
        
        if not variant_id.startswith("gid://"):
            variant_id = f"gid://shopify/ProductVariant/{variant_id}"
        if not product_id.startswith("gid://"):
            product_id = f"gid://shopify/Product/{product_id}"
        
        result = client.execute_graphql(mutation, {
            "productId": product_id,
            "variants": [{
                "id": variant_id,
                "inventoryPolicy": policy
            }]
        })
        
        data = result.get('data', {}).get('productVariantsBulkUpdate', {})
        user_errors = data.get('userErrors', [])
        
        if user_errors:
            return {
                "success": False,
                "error": "; ".join([error['message'] for error in user_errors])
            }
        
        updated_variants = data.get('productVariants', [])
        if updated_variants:
            return {
                "success": True,
                "variant": updated_variants[0]
            }
        
        return {
            "success": False,
            "error": "No variants returned from update"
        }
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool (read-only test)"""
        try:
            # Test environment and API connectivity
            self.validate_env()
            
            # Test by performing a read-only query
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