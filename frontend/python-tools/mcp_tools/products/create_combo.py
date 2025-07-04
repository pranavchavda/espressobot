"""
Native MCP implementation for creating combo products
"""

import json
import requests
from io import BytesIO
from PIL import Image
import numpy as np
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from ..base import BaseMCPTool, ShopifyClient

class CreateComboTool(BaseMCPTool):
    """Create machine+grinder combo products"""
    
    name = "create_combo"
    description = "Create combo products by combining two products with special pricing"
    context = """
    Creates combo products for iDrinkCoffee.com by:
    - Duplicating the first product
    - Combining descriptions and tags
    - Creating a combined image
    - Setting combo pricing with discounts
    - Managing SKU generation
    
    Features:
    - Automatic combo image generation
    - Flexible pricing (fixed discount, percentage, or specific price)
    - Custom SKU generation with prefixes
    - Combines product metadata and descriptions
    - Publishes as draft or active
    
    SKU Format: {prefix}-{serial}-{suffix}
    - prefix: Default "COMBO", customizable
    - serial: Default YYMM, customizable
    - suffix: Auto-generated from product codes or custom
    
    Business Rules:
    - Combos typically offer 10-20% discount
    - Images show both products side-by-side
    - Inventory policy set to DENY (no overselling)
    - Tagged with 'combo' and monthly tag
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "product1": {
                "type": "string",
                "description": "First product (handle, SKU, or ID)"
            },
            "product2": {
                "type": "string",
                "description": "Second product (handle, SKU, or ID)"
            },
            "sku_suffix": {
                "type": "string",
                "description": "Custom suffix for combo SKU"
            },
            "discount_amount": {
                "type": "number",
                "description": "Fixed discount amount (e.g., 200 for $200 off)"
            },
            "discount_percent": {
                "type": "number",
                "description": "Percentage discount (e.g., 15 for 15% off)"
            },
            "price": {
                "type": "number",
                "description": "Set specific price for combo"
            },
            "publish": {
                "type": "boolean",
                "description": "Publish immediately (default: false)"
            },
            "prefix": {
                "type": "string",
                "description": "SKU prefix (default: COMBO)"
            },
            "serial": {
                "type": "string",
                "description": "Serial/tracking number (default: YYMM)"
            }
        },
        "required": ["product1", "product2"]
    }
    
    async def execute(self, product1: str, product2: str, **kwargs) -> Dict[str, Any]:
        """Create a combo product"""
        try:
            client = ShopifyClient()
            
            # Get product details
            product1_data = await self._get_product_details(client, product1)
            if not product1_data:
                return {
                    "success": False,
                    "error": f"Could not find product: {product1}"
                }
            
            product2_data = await self._get_product_details(client, product2)
            if not product2_data:
                return {
                    "success": False,
                    "error": f"Could not find product: {product2}"
                }
            
            # Extract options
            sku_suffix = kwargs.get('sku_suffix')
            discount_amount = kwargs.get('discount_amount')
            discount_percent = kwargs.get('discount_percent')
            price = kwargs.get('price')
            publish = kwargs.get('publish', False)
            prefix = kwargs.get('prefix', 'COMBO')
            serial = kwargs.get('serial') or datetime.now().strftime('%y%m')
            
            # Create combo
            result = await self._create_combo_listing(
                client, product1_data, product2_data,
                sku_suffix, discount_amount, discount_percent,
                price, publish, prefix, serial
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_product_details(self, client: ShopifyClient, identifier: str) -> Optional[Dict[str, Any]]:
        """Get product details including variants and images"""
        product_id = client.resolve_product_id(identifier)
        if not product_id:
            return None
        
        query = '''
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                descriptionHtml
                vendor
                productType
                tags
                images(first: 10) {
                    edges {
                        node {
                            id
                            url
                            altText
                        }
                    }
                }
                variants(first: 1) {
                    edges {
                        node {
                            id
                            price
                            compareAtPrice
                            sku
                            inventoryPolicy
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
            }
        }
        '''
        
        result = client.execute_graphql(query, {"id": product_id})
        
        if result and 'data' in result and result['data'].get('product'):
            return result['data']['product']
        
        return None
    
    async def _create_combo_listing(self, client: ShopifyClient, product1: Dict[str, Any], 
                                   product2: Dict[str, Any], sku_suffix: Optional[str],
                                   discount_amount: Optional[float], discount_percent: Optional[float],
                                   price: Optional[float], publish: bool, prefix: str, serial: str) -> Dict[str, Any]:
        """Create the combo product listing"""
        
        # Extract variant info
        variant1 = product1['variants']['edges'][0]['node'] if product1['variants']['edges'] else None
        variant2 = product2['variants']['edges'][0]['node'] if product2['variants']['edges'] else None
        
        if not variant1 or not variant2:
            return {
                "success": False,
                "error": "Products must have at least one variant"
            }
        
        # Calculate pricing
        price1 = float(variant1['price'])
        price2 = float(variant2['price'])
        total_price = price1 + price2
        
        if price:
            combo_price = float(price)
        elif discount_amount:
            combo_price = max(total_price - discount_amount, 0.01)
        elif discount_percent:
            combo_price = max(total_price * (1 - discount_percent / 100), 0.01)
        else:
            combo_price = total_price
        
        # Calculate cost
        cost1 = float(variant1['inventoryItem']['unitCost']['amount']) if variant1['inventoryItem'].get('unitCost') else 0
        cost2 = float(variant2['inventoryItem']['unitCost']['amount']) if variant2['inventoryItem'].get('unitCost') else 0
        total_cost = cost1 + cost2 if (cost1 and cost2) else None
        
        # Generate combo title and SKU
        combo_title = f"{product1['title']} + {product2['title']} Combo"
        
        # Generate SKU
        if sku_suffix:
            combo_sku = f"{prefix}-{serial}-{sku_suffix}"
        else:
            p1_code = (variant1['sku'][:3] if variant1['sku'] else product1['handle'][:3]).upper()
            p2_code = (variant2['sku'][:3] if variant2['sku'] else product2['handle'][:3]).upper()
            combo_sku = f"{prefix}-{serial}-{p1_code}-{p2_code}"
        
        # Step 1: Duplicate the first product
        mutation = '''
        mutation duplicateProduct($productId: ID!, $newTitle: String!, $includeImages: Boolean!, $newStatus: ProductStatus!) {
            productDuplicate(productId: $productId, newTitle: $newTitle, includeImages: $includeImages, newStatus: $newStatus) {
                newProduct {
                    id
                    title
                    handle
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        variables = {
            "productId": product1['id'],
            "newTitle": combo_title,
            "includeImages": False,
            "newStatus": "ACTIVE" if publish else "DRAFT"
        }
        
        result = client.execute_graphql(mutation, variables)
        if not result or 'data' not in result or not result['data'].get('productDuplicate'):
            return {
                "success": False,
                "error": "Failed to duplicate product"
            }
        
        if result['data']['productDuplicate']['userErrors']:
            return {
                "success": False,
                "error": f"Error duplicating product: {result['data']['productDuplicate']['userErrors']}"
            }
        
        new_product = result['data']['productDuplicate']['newProduct']
        
        # Step 2: Update the combo product
        tags1 = product1.get('tags', [])
        tags2 = product2.get('tags', [])
        combo_tags = list(set(tags1 + tags2 + ['combo', f'combo-{datetime.now().strftime("%y%m")}']))
        
        # Combine descriptions
        desc1 = product1.get('descriptionHtml', '')
        desc2 = product2.get('descriptionHtml', '')
        combo_description = f'''
        <div class="combo-description">
            <h3>This combo includes:</h3>
            <div class="combo-product-1">
                <h4>{product1['title']}</h4>
                {desc1}
            </div>
            <hr>
            <div class="combo-product-2">
                <h4>{product2['title']}</h4>
                {desc2}
            </div>
        </div>
        '''
        
        # Update product with productSet
        update_mutation = '''
        mutation updateProduct($product: ProductSetInput!) {
            productSet(input: $product) {
                product {
                    id
                    variants(first: 1) {
                        edges {
                            node {
                                id
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
        '''
        
        # Update variant with pricing and SKU
        variant_query = '''
        query getVariant($id: ID!) {
            product(id: $id) {
                variants(first: 1) {
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
        }
        '''
        
        variant_result = client.execute_graphql(variant_query, {"id": new_product['id']})
        if not variant_result or not variant_result.get('data'):
            return {
                "success": False,
                "error": "Failed to get variant information"
            }
        
        variant_id = variant_result['data']['product']['variants']['edges'][0]['node']['id']
        inventory_item_id = variant_result['data']['product']['variants']['edges'][0]['node']['inventoryItem']['id']
        
        # Update using productSet
        update_input = {
            "id": new_product['id'],
            "title": combo_title,
            "descriptionHtml": combo_description,
            "tags": combo_tags,
            "productType": "Combos",
            "variants": [{
                "id": variant_id,
                "price": str(combo_price),
                "compareAtPrice": str(total_price),
                "inventoryPolicy": "DENY",
                "inventoryItem": {
                    "id": inventory_item_id,
                    "sku": combo_sku
                }
            }]
        }
        
        if total_cost:
            update_input["variants"][0]["inventoryItem"]["cost"] = str(total_cost)
        
        result = client.execute_graphql(update_mutation, {"product": update_input})
        if result and result.get('data', {}).get('productSet', {}).get('userErrors'):
            errors = result['data']['productSet']['userErrors']
            if errors:
                return {
                    "success": False,
                    "error": f"Error updating product: {errors}"
                }
        
        # Step 3: Create and upload combo image if both products have images
        image_result = {"status": "skipped", "message": "No images to combine"}
        if product1['images']['edges'] and product2['images']['edges']:
            image1_url = product1['images']['edges'][0]['node']['url']
            image2_url = product2['images']['edges'][0]['node']['url']
            
            combo_image = await self._create_combo_image(image1_url, image2_url)
            if combo_image:
                upload_result = await self._upload_combo_image(client, new_product['id'], combo_image)
                if upload_result:
                    image_result = {"status": "success", "message": "Combo image uploaded"}
                else:
                    image_result = {"status": "failed", "message": "Failed to upload combo image"}
        
        # Step 4: Add combo metafields
        buybox_content = ""
        for product in [product1, product2]:
            for mf in product.get('metafields', {}).get('edges', []):
                node = mf['node']
                if node['namespace'] == 'content' and node['key'] == 'buy_box':
                    if buybox_content:
                        buybox_content += "\n<hr>\n"
                    buybox_content += node['value']
        
        metafield_result = {"status": "skipped"}
        if buybox_content:
            metafield_mutation = '''
            mutation setMetafield($metafields: [MetafieldsSetInput!]!) {
                metafieldsSet(metafields: $metafields) {
                    metafields {
                        id
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            mf_input = {
                "ownerId": new_product['id'],
                "namespace": "content",
                "key": "buy_box",
                "value": buybox_content,
                "type": "multi_line_text_field"
            }
            
            mf_result = client.execute_graphql(metafield_mutation, {"metafields": [mf_input]})
            if mf_result and not mf_result.get('data', {}).get('metafieldsSet', {}).get('userErrors'):
                metafield_result = {"status": "success", "message": "Buybox content combined"}
        
        return {
            "success": True,
            "product": {
                "id": new_product['id'],
                "handle": new_product['handle'],
                "title": combo_title,
                "sku": combo_sku,
                "price": combo_price,
                "compare_at_price": total_price,
                "status": "active" if publish else "draft"
            },
            "pricing": {
                "product1_price": price1,
                "product2_price": price2,
                "total_original": total_price,
                "combo_price": combo_price,
                "savings": total_price - combo_price,
                "discount_percent": round((total_price - combo_price) / total_price * 100, 2)
            },
            "image_upload": image_result,
            "metafield_update": metafield_result
        }
    
    async def _create_combo_image(self, image1_url: str, image2_url: str) -> Optional[bytes]:
        """Create a combined image from two product images"""
        try:
            # Download images
            response1 = requests.get(image1_url)
            response2 = requests.get(image2_url)
            
            if response1.status_code != 200 or response2.status_code != 200:
                return None
            
            # Open images
            img1 = Image.open(BytesIO(response1.content)).convert("RGBA")
            img2 = Image.open(BytesIO(response2.content)).convert("RGBA")
            
            # Trim whitespace
            img1 = self._trim_image(img1)
            img2 = self._trim_image(img2)
            
            # Calculate target dimensions
            target_height = 800
            
            # Resize maintaining aspect ratio
            ratio1 = target_height / img1.height
            new_width1 = int(img1.width * ratio1)
            img1 = img1.resize((new_width1, target_height), Image.Resampling.LANCZOS)
            
            ratio2 = target_height / img2.height
            new_width2 = int(img2.width * ratio2)
            img2 = img2.resize((new_width2, target_height), Image.Resampling.LANCZOS)
            
            # Create new image with white background
            total_width = new_width1 + new_width2 + 50  # 50px gap
            combo_img = Image.new('RGBA', (total_width, target_height), (255, 255, 255, 255))
            
            # Paste images
            combo_img.paste(img1, (0, 0), img1 if img1.mode == 'RGBA' else None)
            combo_img.paste(img2, (new_width1 + 50, 0), img2 if img2.mode == 'RGBA' else None)
            
            # Convert to RGB for JPEG
            rgb_img = Image.new('RGB', combo_img.size, (255, 255, 255))
            rgb_img.paste(combo_img, mask=combo_img.split()[3] if combo_img.mode == 'RGBA' else None)
            
            # Convert to bytes
            buffer = BytesIO()
            rgb_img.save(buffer, format='JPEG', quality=95)
            return buffer.getvalue()
            
        except Exception:
            return None
    
    def _trim_image(self, image: Image.Image) -> Image.Image:
        """Remove excess whitespace from image"""
        # Convert to numpy array
        np_image = np.array(image)
        
        # Find non-white pixels
        if image.mode == 'RGBA':
            mask = (np_image[:,:,3] > 0) & ((np_image[:,:,0] < 250) | (np_image[:,:,1] < 250) | (np_image[:,:,2] < 250))
        else:
            mask = (np_image[:,:,0] < 250) | (np_image[:,:,1] < 250) | (np_image[:,:,2] < 250)
        
        # Find bounding box
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            return image
        
        # Get bounds with padding
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        
        padding = 10
        y_min = max(0, y_min - padding)
        y_max = min(image.height, y_max + padding)
        x_min = max(0, x_min - padding)
        x_max = min(image.width, x_max + padding)
        
        return image.crop((x_min, y_min, x_max, y_max))
    
    async def _upload_combo_image(self, client: ShopifyClient, product_id: str, image_bytes: bytes) -> bool:
        """Upload combo image to product"""
        try:
            # Create staged upload
            mutation = """
            mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
                stagedUploadsCreate(input: $input) {
                    stagedTargets {
                        resourceUrl
                        url
                        parameters {
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
            
            filename = f"combo_{uuid.uuid4().hex[:8]}.jpg"
            variables = {
                "input": [{
                    "filename": filename,
                    "mimeType": "image/jpeg",
                    "fileSize": str(len(image_bytes)),
                    "httpMethod": "POST",
                    "resource": "FILE"
                }]
            }
            
            result = client.execute_graphql(mutation, variables)
            if result.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors'):
                return False
            
            targets = result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])
            if not targets:
                return False
            
            target = targets[0]
            
            # Upload to staged target
            files = []
            for param in target['parameters']:
                files.append((param['name'], (None, param['value'])))
            files.append(('file', (filename, image_bytes)))
            
            response = requests.post(target['url'], files=files)
            if response.status_code != 200 and response.status_code != 201:
                return False
            
            # Create product media
            media_mutation = '''
            mutation createProductMedia($productId: ID!, $media: [CreateMediaInput!]!) {
                productCreateMedia(productId: $productId, media: $media) {
                    media {
                        ... on MediaImage {
                            id
                        }
                    }
                    mediaUserErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            variables = {
                "productId": product_id,
                "media": [{
                    "alt": "Product Combo Image",
                    "originalSource": target['resourceUrl'],
                    "mediaContentType": "IMAGE"
                }]
            }
            
            result = client.execute_graphql(media_mutation, variables)
            if result and 'data' in result and result['data'].get('productCreateMedia'):
                return not bool(result['data']['productCreateMedia']['mediaUserErrors'])
            
            return False
            
        except Exception:
            return False
    
    async def test(self) -> Dict[str, Any]:
        """Test combo creation capability"""
        try:
            # Just verify we can import required libraries
            import PIL
            import numpy
            
            return {
                "status": "passed",
                "message": "Combo creation tool ready"
            }
        except ImportError as e:
            return {
                "status": "failed",
                "error": f"Missing required library: {str(e)}"
            }