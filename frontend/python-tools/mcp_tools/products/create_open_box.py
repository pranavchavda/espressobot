"""
Native MCP implementation for creating open box products
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from ..base import BaseMCPTool, ShopifyClient

class CreateOpenBoxTool(BaseMCPTool):
    """Create open box listings from existing products"""
    
    name = "create_open_box"
    description = "Create an open box version of an existing product"
    context = """
    Creates open box listings following iDrinkCoffee.com conventions:
    
    SKU Format: OB-{YYMM}-{Serial}-{OriginalSKU}
    Title Format: {Original Title} |{Serial}| - {Condition}
    
    Features:
    - Duplicates original product with all details
    - Automatic pricing with discount options
    - Adds open-box and ob-YYMM tags
    - Optional condition notes
    - Preserves original product metadata
    
    Conditions:
    - Excellent: Near-new, minimal signs of use
    - Good: Light wear, fully functional
    - Fair: Moderate wear, may have cosmetic issues
    - Scratch & Dent: Cosmetic damage only
    
    Business Rules:
    - Default 10% discount if not specified
    - SKUs track year/month for inventory age
    - Serial numbers for individual tracking
    - Created as draft by default
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Product identifier (SKU, handle, title, or ID)"
            },
            "serial": {
                "type": "string",
                "description": "Serial number for the open box unit"
            },
            "condition": {
                "type": "string",
                "description": "Condition (Excellent, Good, Fair, Scratch & Dent)"
            },
            "price": {
                "type": "number",
                "description": "Specific price for the open box item"
            },
            "discount_pct": {
                "type": "number",
                "description": "Percentage discount from original (e.g., 15 for 15%)"
            },
            "note": {
                "type": "string",
                "description": "Additional note about condition"
            },
            "publish": {
                "type": "boolean",
                "description": "Publish immediately (default: false)"
            }
        },
        "required": ["identifier", "serial", "condition"]
    }
    
    async def execute(self, identifier: str, serial: str, condition: str, **kwargs) -> Dict[str, Any]:
        """Create open box product"""
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
            price = kwargs.get('price')
            discount_pct = kwargs.get('discount_pct')
            note = kwargs.get('note')
            publish = kwargs.get('publish', False)
            
            # Create open box product
            result = await self._create_open_box_product(
                client, original, serial, condition,
                price, discount_pct, note, publish
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
                variants(first: 10) {
                    edges {
                        node {
                            id
                            title
                            sku
                            price
                            compareAtPrice
                            inventoryItem {
                                id
                                unitCost {
                                    amount
                                }
                            }
                        }
                    }
                }
                metafields(first: 20) {
                    edges {
                        node {
                            namespace
                            key
                            value
                            type
                        }
                    }
                }
                media(first: 20) {
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
    
    async def _create_open_box_product(self, client: ShopifyClient, original: Dict[str, Any],
                                      serial: str, condition: str, price: Optional[float],
                                      discount_pct: Optional[float], note: Optional[str],
                                      publish: bool) -> Dict[str, Any]:
        """Create the open box product"""
        
        # Get current date for SKU and tag
        now = datetime.now()
        yymm = now.strftime("%y%m")
        
        # Get original variant
        original_variant = original['variants']['edges'][0]['node']
        original_sku = original_variant['sku'] or "NOSKU"
        original_price = float(original_variant['price'])
        
        # Calculate open box price
        if price:
            ob_price = price
        elif discount_pct:
            ob_price = original_price * (1 - discount_pct / 100)
        else:
            # Default 10% discount
            ob_price = original_price * 0.9
        
        # Create SKU and title
        ob_sku = f"OB-{yymm}-{serial}-{original_sku}"
        ob_title = f"{original['title']} |{serial}| - {condition}"
        
        # Step 1: Duplicate the product
        mutation = """
        mutation duplicateProduct($productId: ID!, $newTitle: String!, $newStatus: ProductStatus) {
            productDuplicate(productId: $productId, newTitle: $newTitle, newStatus: $newStatus, includeImages: true) {
                newProduct {
                    id
                    title
                    handle
                    variants(first: 10) {
                        edges {
                            node {
                                id
                                inventoryItem {
                                    id
                                }
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
            "newTitle": ob_title,
            "newStatus": "ACTIVE" if publish else "DRAFT"
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
        
        # Step 2: Update with open box details
        variant = product['variants']['edges'][0]['node']
        variant_id = variant['id']
        inventory_item_id = variant['inventoryItem']['id']
        
        # Build description with note if provided
        description_html = original.get('descriptionHtml', '')
        if note:
            description_html = f"<p><strong>Open Box Note:</strong> {note}</p>\n{description_html}"
        
        # Prepare tags
        original_tags = original.get('tags', [])
        tags = original_tags + ['open-box', f'ob-{yymm}']
        
        # Update using productSet
        mutation = """
        mutation updateProduct($product: ProductSetInput!) {
            productSet(input: $product) {
                product {
                    id
                    handle
                    title
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        update_input = {
            "id": product_id,
            "title": ob_title,
            "descriptionHtml": description_html,
            "tags": tags,
            "variants": [{
                "id": variant_id,
                "price": str(ob_price),
                "compareAtPrice": str(original_price),
                "inventoryItem": {
                    "id": inventory_item_id,
                    "sku": ob_sku
                }
            }]
        }
        
        # Add SEO if original had it
        if original.get('seo'):
            update_input['seo'] = {
                "title": f"{original['seo'].get('title', original['title'])} - Open Box {serial}",
                "description": original['seo'].get('description', '')
            }
        
        result = client.execute_graphql(mutation, {"product": update_input})
        
        if result.get('data', {}).get('productSet', {}).get('userErrors'):
            errors = result['data']['productSet']['userErrors']
            return {
                "success": False,
                "error": f"Failed to update product: {errors}"
            }
        
        updated_product = result['data']['productSet']['product']
        
        # Calculate savings
        savings = original_price - ob_price
        discount_percent = round((savings / original_price) * 100, 2)
        
        return {
            "success": True,
            "product": {
                "id": product_id,
                "handle": updated_product['handle'],
                "title": ob_title,
                "sku": ob_sku,
                "status": "active" if publish else "draft",
                "admin_url": f"https://idrinkcoffee.myshopify.com/admin/products/{product_id.split('/')[-1]}"
            },
            "pricing": {
                "original_price": original_price,
                "open_box_price": ob_price,
                "savings": savings,
                "discount_percent": discount_percent
            },
            "details": {
                "serial": serial,
                "condition": condition,
                "note": note,
                "month_tag": f"ob-{yymm}"
            }
        }
    
    async def test(self) -> Dict[str, Any]:
        """Test open box creation capability"""
        try:
            # Just verify we can access Shopify
            client = ShopifyClient()
            query = "{ shop { name } }"
            result = client.execute_graphql(query)
            
            if result and 'data' in result:
                return {
                    "status": "passed",
                    "message": "Open box creation tool ready"
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