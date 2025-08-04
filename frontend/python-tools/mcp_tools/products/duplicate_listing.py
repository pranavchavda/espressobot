"""
Native MCP implementation for duplicating products
"""

import json
from typing import Dict, Any, Optional, List
from ..base import BaseMCPTool, ShopifyClient

class DuplicateListingTool(BaseMCPTool):
    """Duplicate an existing product listing"""
    
    name = "duplicate_listing"
    description = "Duplicate an existing product with optional modifications"
    context = """
    Duplicates an existing product listing with flexibility to:
    
    Features:
    - Create an exact copy or modify key attributes
    - Optional new title, SKU, and price
    - Choose whether to include images
    - Preserves all product details and metadata
    - Can publish immediately or save as draft
    
    Use cases:
    - Create product variations
    - Test new pricing strategies
    - Create seasonal versions
    - Quick product setup from templates
    
    Business Rules:
    - SKUs must be unique across all products
    - Default behavior preserves all original data
    - Images can be excluded for manual replacement
    - Status defaults to DRAFT unless specified
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Product identifier (SKU, handle, title, or ID)"
            },
            "new_title": {
                "type": "string",
                "description": "New title for the duplicated product (optional, defaults to original)"
            },
            "new_sku": {
                "type": "string",
                "description": "New SKU for the duplicated product (optional)"
            },
            "new_price": {
                "type": "number",
                "description": "New price for the duplicated product (optional)"
            },
            "include_images": {
                "type": "boolean",
                "description": "Whether to copy images from original (default: true)"
            },
            "status": {
                "type": "string",
                "enum": ["ACTIVE", "DRAFT"],
                "description": "Status of the new product (default: DRAFT)"
            },
            "tags_to_add": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional tags to add to the duplicate"
            },
            "tags_to_remove": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags to remove from the duplicate"
            }
        },
        "required": ["identifier"]
    }
    
    async def execute(self, identifier: str, **kwargs) -> Dict[str, Any]:
        """Duplicate product listing"""
        try:
            client = ShopifyClient()
            
            # Find original product
            product_id = client.resolve_product_id(identifier)
            if not product_id:
                return {
                    "success": False,
                    "error": f"Product not found: {identifier}"
                }
            
            # Get product details
            original = await self._get_product_details(client, product_id)
            if not original:
                return {
                    "success": False,
                    "error": "Failed to get product details"
                }
            
            # Extract options
            new_title = kwargs.get('new_title', original['title'])
            new_sku = kwargs.get('new_sku')
            new_price = kwargs.get('new_price')
            include_images = kwargs.get('include_images', True)
            status = kwargs.get('status', 'DRAFT')
            tags_to_add = kwargs.get('tags_to_add', [])
            tags_to_remove = kwargs.get('tags_to_remove', [])
            
            # Create duplicated product
            result = await self._duplicate_product(
                client, original, new_title, new_sku, 
                new_price, include_images, status,
                tags_to_add, tags_to_remove
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_product_details(self, client: ShopifyClient, product_id: str) -> Optional[Dict[str, Any]]:
        """Get full product details"""
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                vendor
                productType
                status
                tags
                descriptionHtml
                seo {
                    title
                    description
                }
                options {
                    name
                    values
                }
                variants(first: 100) {
                    edges {
                        node {
                            id
                            title
                            sku
                            price
                            compareAtPrice
                            barcode
                            weight
                            weightUnit
                            selectedOptions {
                                name
                                value
                            }
                            inventoryItem {
                                id
                                unitCost {
                                    amount
                                }
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
                metafields(first: 50) {
                    edges {
                        node {
                            namespace
                            key
                            value
                            type
                        }
                    }
                }
                media(first: 50) {
                    edges {
                        node {
                            ... on MediaImage {
                                id
                                alt
                                image {
                                    url
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = client.execute_graphql(query, {"id": product_id})
        if result and 'data' in result and result['data'].get('product'):
            return result['data']['product']
        return None
    
    async def _duplicate_product(self, client: ShopifyClient, original: Dict[str, Any],
                                new_title: str, new_sku: Optional[str], new_price: Optional[float],
                                include_images: bool, status: str, tags_to_add: List[str],
                                tags_to_remove: List[str]) -> Dict[str, Any]:
        """Create the duplicated product"""
        
        # Step 1: Duplicate the product
        mutation = """
        mutation duplicateProduct($productId: ID!, $newTitle: String!, $newStatus: ProductStatus, $includeImages: Boolean!) {
            productDuplicate(productId: $productId, newTitle: $newTitle, newStatus: $newStatus, includeImages: $includeImages) {
                newProduct {
                    id
                    title
                    handle
                    variants(first: 100) {
                        edges {
                            node {
                                id
                                sku
                                price
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
            "productId": original['id'],
            "newTitle": new_title,
            "newStatus": status,
            "includeImages": include_images
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productDuplicate', {}).get('userErrors'):
            errors = result['data']['productDuplicate']['userErrors']
            return {
                "success": False,
                "error": f"Failed to duplicate product: {errors}"
            }
        
        product = result['data']['productDuplicate']['newProduct']
        product_id = product['id']
        
        # Step 2: Update with modifications if needed
        if new_sku or new_price or tags_to_add or tags_to_remove:
            # Prepare tags
            original_tags = original.get('tags', [])
            new_tags = [tag for tag in original_tags if tag not in tags_to_remove]
            new_tags.extend(tags_to_add)
            
            # Get variant for updates
            variant = product['variants']['edges'][0]['node'] if product['variants']['edges'] else None
            
            if (new_sku or new_price) and variant:
                # Update variant with new SKU and/or price
                await self._update_variant(client, product_id, variant['id'], new_sku, new_price)
            
            if tags_to_add or tags_to_remove:
                # Update product tags
                await self._update_product_tags(client, product_id, new_tags)
        
        # Get final product details
        final_product = await self._get_product_details(client, product_id)
        if not final_product:
            return {
                "success": False,
                "error": "Failed to get final product details"
            }
        
        # Prepare response
        first_variant = final_product['variants']['edges'][0]['node'] if final_product['variants']['edges'] else None
        
        return {
            "success": True,
            "product": {
                "id": product_id,
                "handle": final_product['handle'],
                "title": final_product['title'],
                "status": status.lower(),
                "admin_url": f"https://idrinkcoffee.myshopify.com/admin/products/{product_id.split('/')[-1]}"
            },
            "details": {
                "sku": first_variant['sku'] if first_variant else None,
                "price": float(first_variant['price']) if first_variant else None,
                "vendor": final_product['vendor'],
                "product_type": final_product['productType'],
                "tags": final_product['tags'],
                "variants_count": len(final_product['variants']['edges']),
                "images_count": len(final_product['media']['edges']) if include_images else 0
            },
            "source": {
                "original_id": original['id'],
                "original_title": original['title'],
                "original_handle": original['handle']
            }
        }
    
    async def _update_variant(self, client: ShopifyClient, product_id: str, variant_id: str, 
                             new_sku: Optional[str], new_price: Optional[float]):
        """Update variant SKU and/or price"""
        mutation = """
        mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants {
                    id
                    sku
                    price
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variant_input = {"id": variant_id}
        
        if new_sku:
            variant_input["inventoryItem"] = {"sku": new_sku}
        
        if new_price:
            variant_input["price"] = str(new_price)
        
        variables = {
            "productId": product_id,
            "variants": [variant_input]
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
            errors = result['data']['productVariantsBulkUpdate']['userErrors']
            raise Exception(f"Failed to update variant: {errors}")
    
    async def _update_product_tags(self, client: ShopifyClient, product_id: str, tags: List[str]):
        """Update product tags"""
        mutation = """
        mutation updateProduct($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    tags
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "input": {
                "id": product_id,
                "tags": tags
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productUpdate', {}).get('userErrors'):
            errors = result['data']['productUpdate']['userErrors']
            raise Exception(f"Failed to update tags: {errors}")
    
    async def test(self) -> Dict[str, Any]:
        """Test duplicate listing capability"""
        try:
            # Just verify we can access Shopify
            client = ShopifyClient()
            query = "{ shop { name } }"
            result = client.execute_graphql(query)
            
            if result and 'data' in result:
                return {
                    "status": "passed",
                    "message": "Duplicate listing tool ready"
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