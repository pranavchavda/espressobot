"""
Native MCP implementation for managing variant links between products
"""

import json
from typing import Dict, Any, List, Optional
from ..base import BaseMCPTool, ShopifyClient

class ManageVariantLinksTool(BaseMCPTool):
    """Manage variant links between related products"""
    
    name = "manage_variant_links"
    description = "Link related product variants (e.g., different colors of same model)"
    context = """
    Manages variant links between related products using the varLinks metafield.
    
    Features:
    - Link products together (different colors/styles)
    - Unlink products
    - Check current links
    - Sync entire variant groups
    - Audit link consistency
    
    Actions:
    - link: Connect products together
    - unlink: Remove variant links
    - check: Show current links for a product
    - sync: Sync all products in a group
    - audit: Check for consistency issues
    
    Metafield structure:
    - Namespace: "new"
    - Key: "varLinks"
    - Type: list.product_reference
    - Value: Array of linked product IDs
    
    Use cases:
    - Machine color variants (black/white/stainless)
    - Different sizes of same product
    - Style variations
    - Regional model differences
    
    Business Rules:
    - All linked products reference the same list
    - Products reference themselves in the list
    - Links are bidirectional
    - Minimum 2 products for linking
    
    Example: Breville machines in Black, White, Stainless
    Each product's varLinks contains all 3 product IDs
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["link", "unlink", "check", "sync", "audit"],
                "description": "Action to perform"
            },
            "product_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of product IDs (for link/unlink)"
            },
            "product_id": {
                "type": "string",
                "description": "Single product ID (for check/sync)"
            },
            "search_query": {
                "type": "string",
                "description": "Search query for audit action"
            }
        },
        "required": ["action"]
    }
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute variant links management action"""
        try:
            client = ShopifyClient()
            
            if action == "link":
                return await self._link_products(client, kwargs)
            elif action == "unlink":
                return await self._unlink_products(client, kwargs)
            elif action == "check":
                return await self._check_links(client, kwargs)
            elif action == "sync":
                return await self._sync_group(client, kwargs)
            elif action == "audit":
                return await self._audit_links(client, kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    async def _link_products(self, client: ShopifyClient, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Link a group of products together"""
        product_ids = kwargs.get('product_ids', [])
        
        if not product_ids:
            return {
                "success": False,
                "error": "product_ids list is required for link action"
            }
        
        if len(product_ids) < 2:
            return {
                "success": False,
                "error": "Need at least 2 products to link"
            }
        
        # Validate and get product info
        valid_products = []
        product_info = {}
        
        for pid in product_ids:
            product = await self._get_product_info(client, pid)
            if product:
                gid = product['id']
                valid_products.append(gid)
                product_info[gid] = product
            else:
                return {
                    "success": False,
                    "error": f"Product not found: {pid}"
                }
        
        # Update all products with the complete list
        success_count = 0
        failed_products = []
        
        for product_id in valid_products:
            if await self._update_variant_links(client, product_id, valid_products):
                success_count += 1
            else:
                failed_products.append(product_info[product_id]['title'])
        
        if success_count == len(valid_products):
            return {
                "success": True,
                "message": f"Successfully linked {len(valid_products)} products",
                "linked_products": [
                    {
                        "id": pid,
                        "title": product_info[pid]['title']
                    } for pid in valid_products
                ]
            }
        else:
            return {
                "success": False,
                "error": f"Only {success_count}/{len(valid_products)} products updated successfully",
                "failed_products": failed_products
            }
    
    async def _unlink_products(self, client: ShopifyClient, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove products from variant linking"""
        product_ids = kwargs.get('product_ids', [])
        
        if not product_ids:
            return {
                "success": False,
                "error": "product_ids list is required for unlink action"
            }
        
        success_count = 0
        failed_products = []
        unlinked_products = []
        
        for pid in product_ids:
            product = await self._get_product_info(client, pid)
            if not product:
                failed_products.append(f"Not found: {pid}")
                continue
            
            # Remove varLinks by setting empty array
            if await self._update_variant_links(client, product['id'], []):
                success_count += 1
                unlinked_products.append({
                    "id": product['id'],
                    "title": product['title']
                })
            else:
                failed_products.append(product['title'])
        
        return {
            "success": success_count > 0,
            "message": f"Successfully unlinked {success_count}/{len(product_ids)} products",
            "unlinked_products": unlinked_products,
            "failed_products": failed_products
        }
    
    async def _check_links(self, client: ShopifyClient, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Check variant links for a product"""
        product_id = kwargs.get('product_id')
        
        if not product_id:
            return {
                "success": False,
                "error": "product_id is required for check action"
            }
        
        product = await self._get_product_info(client, product_id)
        if not product:
            return {
                "success": False,
                "error": f"Product not found: {product_id}"
            }
        
        # Get current varLinks
        varlinks_metafield = product.get('metafield')
        if not varlinks_metafield or not varlinks_metafield.get('value'):
            return {
                "success": True,
                "product": {
                    "id": product['id'],
                    "title": product['title'],
                    "handle": product['handle'],
                    "status": product['status']
                },
                "linked_products": [],
                "message": "No variant links found"
            }
        
        linked_ids = json.loads(varlinks_metafield['value'])
        linked_products = []
        
        # Fetch details for each linked product
        for linked_id in linked_ids:
            linked_product = await self._get_product_info(client, linked_id)
            if linked_product:
                linked_products.append({
                    "id": linked_product['id'],
                    "title": linked_product['title'],
                    "handle": linked_product['handle'],
                    "status": linked_product['status'],
                    "is_self": linked_product['id'] == product['id']
                })
            else:
                linked_products.append({
                    "id": linked_id,
                    "title": "NOT FOUND",
                    "status": "unknown",
                    "is_self": False,
                    "error": "Product not found"
                })
        
        return {
            "success": True,
            "product": {
                "id": product['id'],
                "title": product['title'],
                "handle": product['handle'],
                "status": product['status']
            },
            "linked_products": linked_products,
            "link_count": len(linked_ids)
        }
    
    async def _sync_group(self, client: ShopifyClient, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Sync all products in a variant group based on one product's links"""
        product_id = kwargs.get('product_id')
        
        if not product_id:
            return {
                "success": False,
                "error": "product_id is required for sync action"
            }
        
        # Get the sample product's links
        product = await self._get_product_info(client, product_id)
        if not product:
            return {
                "success": False,
                "error": f"Product not found: {product_id}"
            }
        
        varlinks_metafield = product.get('metafield')
        if not varlinks_metafield or not varlinks_metafield.get('value'):
            return {
                "success": False,
                "error": "No variant links found on sample product"
            }
        
        linked_ids = json.loads(varlinks_metafield['value'])
        
        # Use link_products to sync the group
        return await self._link_products(client, {"product_ids": linked_ids})
    
    async def _audit_links(self, client: ShopifyClient, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Audit variant links for consistency issues"""
        search_query = kwargs.get('search_query', '')
        
        # Search for products with varLinks
        query = """
        query searchProducts($query: String!) {
            products(first: 100, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        metafields(first: 1, namespace: "new", key: "varLinks") {
                            edges {
                                node {
                                    value
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = client.execute_graphql(query, {"query": search_query})
        
        if 'errors' in result:
            return {
                "success": False,
                "error": f"GraphQL error: {result['errors']}"
            }
        
        products = result.get('data', {}).get('products', {}).get('edges', [])
        
        # Group products by their varLinks
        link_groups = {}
        unlinked = []
        
        for edge in products:
            product = edge['node']
            varlinks_data = product.get('metafields', {}).get('edges', [])
            
            if not varlinks_data:
                unlinked.append(product)
            else:
                links = tuple(sorted(json.loads(varlinks_data[0]['node']['value'])))
                if links not in link_groups:
                    link_groups[links] = []
                link_groups[links].append(product)
        
        # Format groups for response
        groups = []
        for i, (links, group_products) in enumerate(link_groups.items(), 1):
            groups.append({
                "group_id": i,
                "product_count": len(group_products),
                "total_links": len(links),
                "products": [
                    {
                        "id": p['id'],
                        "title": p['title'],
                        "handle": p['handle']
                    } for p in group_products
                ]
            })
        
        unlinked_list = [
            {
                "id": p['id'],
                "title": p['title'],
                "handle": p['handle']
            } for p in unlinked
        ]
        
        return {
            "success": True,
            "summary": {
                "total_products": len(products),
                "variant_groups": len(link_groups),
                "unlinked_products": len(unlinked)
            },
            "groups": groups,
            "unlinked": unlinked_list
        }
    
    async def _get_product_info(self, client: ShopifyClient, product_id: str) -> Optional[Dict]:
        """Get product title and current varLinks"""
        # Convert to GID if needed
        if not product_id.startswith('gid://'):
            if product_id.isdigit():
                product_id = f"gid://shopify/Product/{product_id}"
            else:
                # Try to resolve by other identifiers
                resolved_id = client.resolve_product_id(product_id)
                if not resolved_id:
                    return None
                product_id = resolved_id
        
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                status
                metafield(namespace: "new", key: "varLinks") {
                    id
                    value
                }
            }
        }
        """
        
        result = client.execute_graphql(query, {"id": product_id})
        
        if 'errors' in result:
            return None
        
        return result.get('data', {}).get('product')
    
    async def _update_variant_links(self, client: ShopifyClient, product_id: str, 
                                   linked_products: List[str]) -> bool:
        """Update the varLinks metafield for a product"""
        mutation = """
        mutation setMetafield($input: MetafieldsSetInput!) {
            metafieldsSet(metafields: [$input]) {
                metafields {
                    id
                    namespace
                    key
                    value
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        # Ensure all IDs are in GID format
        formatted_ids = []
        for pid in linked_products:
            if not pid.startswith('gid://'):
                formatted_ids.append(f"gid://shopify/Product/{pid}")
            else:
                formatted_ids.append(pid)
        
        variables = {
            "input": {
                "ownerId": product_id,
                "namespace": "new",
                "key": "varLinks",
                "value": json.dumps(formatted_ids),
                "type": "list.product_reference"
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if 'errors' in result:
            return False
        
        user_errors = result.get('data', {}).get('metafieldsSet', {}).get('userErrors', [])
        return len(user_errors) == 0
    
    async def test(self) -> Dict[str, Any]:
        """Test variant links management"""
        try:
            client = ShopifyClient()
            
            # Test basic GraphQL connectivity
            query = "{ shop { name } }"
            result = client.execute_graphql(query)
            
            if result and 'data' in result:
                return {
                    "status": "passed",
                    "message": "Variant links management tool ready"
                }
            else:
                return {
                    "status": "failed",
                    "error": "Could not connect to Shopify"
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }