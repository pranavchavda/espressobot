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
    - Complete tagging system with condition-specific tags
    - Inventory quantity set to 1, policy set to DENY
    - Optional condition notes
    - Preserves original product metadata
    
    Condition Types:
    - 14-day-return: Returns within 14 days (displays as "Return")
    - 45-day-return: Returns within 45 days 
    - used-trade-in: Trade-in items (displays as "Used")
    - store-demo: Store demonstration units
    - open-box: Standard open box items
    - shipping-damage: Items damaged in shipping
    - last-ones: Final clearance items
    - imperfection: Items with cosmetic imperfections
    
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
                "description": "Condition type: 14-day-return, 45-day-return, used-trade-in, store-demo, open-box, shipping-damage, last-ones, imperfection (or custom description)"
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
                options {
                    name
                    values
                }
                variants(first: 10) {
                    edges {
                        node {
                            id
                            title
                            sku
                            price
                            compareAtPrice
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
    
    def _get_default_location(self, client: ShopifyClient) -> str:
        """Get the default location ID for inventory."""
        query = '''
        {
            locations(first: 1) {
                edges {
                    node {
                        id
                        name
                        isActive
                    }
                }
            }
        }
        '''
        
        result = client.execute_graphql(query)
        locations = result.get('data', {}).get('locations', {}).get('edges', [])
        
        if not locations:
            raise Exception("No locations found for inventory")
        
        return locations[0]['node']['id']
    
    async def _adjust_inventory_quantity(self, client: ShopifyClient, inventory_item_id: str):
        """Set inventory quantity to 1 for open box items."""
        try:
            # Get current quantity
            variant_query = """
            query getInventoryItem($id: ID!) {
                inventoryItem(id: $id) {
                    inventoryLevels(first: 1) {
                        edges {
                            node {
                                quantities(names: ["available"]) {
                                    name
                                    quantity
                                }
                                location {
                                    id
                                }
                            }
                        }
                    }
                }
            }
            """
            
            result = client.execute_graphql(variant_query, {'id': inventory_item_id})
            inventory_levels = result.get('data', {}).get('inventoryItem', {}).get('inventoryLevels', {}).get('edges', [])
            
            if not inventory_levels:
                return
                
            # Get available quantity from the quantities array
            quantities = inventory_levels[0]['node']['quantities']
            current_quantity = 0
            for q in quantities:
                if q['name'] == 'available':
                    current_quantity = q['quantity']
                    break
            
            location_id = inventory_levels[0]['node']['location']['id']
            
            # Calculate adjustment needed (we want 1)
            adjustment = 1 - current_quantity
            
            if adjustment == 0:
                return  # Already at 1
            
            # Adjust inventory
            mutation = """
            mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
                inventoryAdjustQuantities(input: $input) {
                    inventoryAdjustmentGroup {
                        reason
                        changes {
                            name
                            delta
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
                'input': {
                    'reason': 'correction',
                    'name': 'available',
                    'changes': [{
                        'inventoryItemId': inventory_item_id,
                        'locationId': location_id,
                        'delta': adjustment
                    }]
                }
            }
            
            client.execute_graphql(mutation, variables)
            
        except Exception as e:
            # Don't fail the whole operation if inventory adjustment fails
            print(f"Warning: Failed to adjust inventory: {e}")
    
    async def _update_variant_sku_and_policy(self, client: ShopifyClient, product_id: str, variant_id: str, sku: str, price: float):
        """Update variant SKU, price, and inventory policy using productVariantsBulkUpdate."""
        try:
            
            mutation = """
            mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants {
                        id
                        sku
                        inventoryQuantity
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
                        "sku": sku
                    },
                    "price": str(price),
                    "inventoryPolicy": "DENY"
                }]
            }
            
            print(f"Updating variant with variables: {variables}")
            result = client.execute_graphql(mutation, variables)
            print(f"GraphQL response: {result}")
            
            # Check for errors and log them
            if result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = result['data']['productVariantsBulkUpdate']['userErrors']
                print(f"Error: Failed to update variant: {errors}")
                raise Exception(f"Failed to update variant: {errors}")
            
            # Log success
            updated_variants = result.get('data', {}).get('productVariantsBulkUpdate', {}).get('productVariants', [])
            if updated_variants:
                variant = updated_variants[0]
                print(f"Success: Updated variant SKU to {variant.get('sku')}, inventory to {variant.get('inventoryQuantity')}")
            else:
                print("Warning: No variants returned from productVariantsBulkUpdate")
                
        except Exception as e:
            print(f"Error: Failed to update variant: {e}")
            raise e
    
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
        
        # Create SKU and title with condition mapping
        condition_lower = condition.lower()
        condition_display_map = {
            '14-day-return': 'Return',
            '45-day-return': '45 day return',
            'used-trade-in': 'Used',
            'store-demo': 'Store Demo',
            'open-box': 'Open Box',
            'shipping-damage': 'Shipping Damage',
            'last-ones': 'Last Ones',
            'imperfection': 'Cosmetic Imperfection'
        }
        
        # Use mapped display name or original condition if no mapping exists
        display_condition = condition_display_map.get(condition_lower, condition)
        
        ob_sku = f"OB-{yymm}-{serial}-{original_sku}"
        ob_title = f"{original['title']} |{serial}| - {display_condition}"
        
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
        
        # Get original variant option values for productSet
        original_variant = original['variants']['edges'][0]['node']
        
        # Build description with note if provided
        description_html = original.get('descriptionHtml', '')
        if note:
            description_html = f"<p><strong>Open Box Note:</strong> {note}</p>\n{description_html}"
        
        # Prepare tags with complete open box tagging logic
        original_tags = original.get('tags', [])
        yymm_dd = now.strftime("%y%m%d")  # YYMMDD format for specific date tag
        
        # Base open box tags
        new_tags = ['open-box', 'openbox', f'ob-{yymm}', f'ob-{yymm_dd}']
        
        # Add condition-specific tags based on condition type
        condition_tag_map = {
            '14-day-return': 'ob-return-d',
            '45-day-return': 'ob-return-45-d',
            'used-trade-in': 'ob-used-d',
            'store-demo': 'ob-storedemo-d',
            'open-box': 'ob-openbox-d',
            'shipping-damage': 'ob-damage-d',
            'last-ones': 'ob-lastones-d',
            'imperfection': 'ob-imperfection-d',
            'return': 'ob-return-d'  # Generic return (backward compatibility)
        }
        
        # Add condition-specific tag if mapping exists
        condition_tag = condition_tag_map.get(condition_lower)
        if condition_tag:
            new_tags.append(condition_tag)
            
        tags = original_tags + new_tags
        
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
            "productOptions": [{"name": opt["name"], "values": [{"name": val} for val in opt["values"]]} for opt in original.get("options", [])],
            "variants": [{
                "id": variant_id,
                "price": str(ob_price),
                "compareAtPrice": str(original_price),
                "inventoryPolicy": "DENY",
                "optionValues": [{"optionName": option["name"], "name": option["value"]} for option in original_variant.get("selectedOptions", [])]
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
        
        # Step 3: Update SKU, price, and inventory policy using productVariantsBulkUpdate 
        await self._update_variant_sku_and_policy(client, product_id, variant_id, ob_sku, ob_price)
        
        # Step 4: Set inventory quantity to 1 using separate mutation (required for existing variants)
        await self._adjust_inventory_quantity(client, inventory_item_id)
        
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