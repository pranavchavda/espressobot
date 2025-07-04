"""
Native MCP implementation for add_product_images
"""

import os
import sys
import json
import mimetypes
import requests
from typing import Dict, Any, List, Optional, Union
import asyncio

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class AddProductImagesTool(BaseMCPTool):
    """Add, list, delete, or reorder product images"""
    
    name = "add_product_images"
    description = "Comprehensive image management for Shopify products - add from URLs or local files, list, delete, or reorder"
    context = """
    This tool provides complete image management for Shopify products:
    
    **Add Images:**
    - From URLs (publicly accessible images)
    - From local files (uploads to Shopify staging)
    - With optional alt text for accessibility
    
    **List Images:**
    - View all current product images
    - Get URLs, alt text, and status
    
    **Delete Images:**
    - Remove specific images by position
    - Clear all images
    
    **Reorder Images:**
    - Change the order of product images
    - First image becomes the featured image
    
    **Important Notes:**
    - Product identifier can be SKU, handle, or product ID
    - Local files are uploaded to Shopify's staging area
    - Images are processed asynchronously by Shopify
    - Changes may take a few seconds to appear in the storefront
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "Product identifier (SKU, handle, or product ID)"
            },
            "action": {
                "type": "string",
                "enum": ["add", "list", "delete", "reorder", "clear"],
                "description": "Action to perform"
            },
            "images": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Image URLs or local file paths (for add action)"
            },
            "alt_texts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Alt text for each image (optional)"
            },
            "positions": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Image positions for delete/reorder (1-based)"
            },
            "local_files": {
                "type": "boolean",
                "description": "Whether images are local files (default: auto-detect)"
            }
        },
        "required": ["product_id", "action"]
    }
    
    async def execute(self, product_id: str, action: str, images: Optional[List[str]] = None,
                     alt_texts: Optional[List[str]] = None, positions: Optional[List[int]] = None,
                     local_files: Optional[bool] = None) -> Dict[str, Any]:
        """Execute product image management"""
        try:
            client = ShopifyClient()
            
            # Resolve product ID
            resolved_id = client.resolve_product_id(product_id)
            if not resolved_id:
                return {
                    "success": False,
                    "error": f"Product not found: {product_id}"
                }
            
            if action == "list":
                return await self._list_images(client, resolved_id)
            elif action == "add":
                if not images:
                    return {"success": False, "error": "Images required for add action"}
                return await self._add_images(client, resolved_id, images, alt_texts, local_files)
            elif action == "delete":
                if not positions:
                    return {"success": False, "error": "Positions required for delete action"}
                return await self._delete_images(client, resolved_id, positions)
            elif action == "reorder":
                if not positions:
                    return {"success": False, "error": "Positions required for reorder action"}
                return await self._reorder_images(client, resolved_id, positions)
            elif action == "clear":
                return await self._clear_images(client, resolved_id)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _list_images(self, client: ShopifyClient, product_id: str) -> Dict[str, Any]:
        """List all product images"""
        query = """
        query getProductImages($id: ID!) {
            product(id: $id) {
                id
                title
                media(first: 50) {
                    edges {
                        node {
                            ... on MediaImage {
                                id
                                image {
                                    url
                                    altText
                                }
                                status
                            }
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
            return {"success": False, "error": "Product not found"}
        
        media_edges = product.get('media', {}).get('edges', [])
        images = []
        
        for edge in media_edges:
            node = edge.get('node', {})
            if node and 'image' in node:
                images.append({
                    "id": node.get('id'),
                    "url": node.get('image', {}).get('url'),
                    "alt_text": node.get('image', {}).get('altText'),
                    "status": node.get('status')
                })
        
        return {
            "success": True,
            "product_title": product.get('title'),
            "image_count": len(images),
            "images": images
        }
    
    async def _add_images(self, client: ShopifyClient, product_id: str, images: List[str],
                         alt_texts: Optional[List[str]] = None, local_files: Optional[bool] = None) -> Dict[str, Any]:
        """Add images to product"""
        
        # Auto-detect local files if not specified
        if local_files is None:
            local_files = any(self._is_local_file(img) and os.path.exists(img) for img in images)
        
        if local_files:
            # Process local files
            resource_urls = []
            processed_alt_texts = []
            
            for i, image_path in enumerate(images):
                if self._is_local_file(image_path) and os.path.exists(image_path):
                    try:
                        alt_text = alt_texts[i] if alt_texts and i < len(alt_texts) else None
                        resource_url = await self._upload_local_file(client, image_path, alt_text)
                        resource_urls.append(resource_url)
                        processed_alt_texts.append(alt_text)
                    except Exception as e:
                        return {"success": False, "error": f"Failed to upload {image_path}: {str(e)}"}
                else:
                    return {"success": False, "error": f"File not found: {image_path}"}
            
            # Use uploaded resource URLs
            result = await self._create_product_media(client, product_id, resource_urls, processed_alt_texts)
        else:
            # Use URLs directly
            result = await self._create_product_media(client, product_id, images, alt_texts)
        
        return result
    
    async def _upload_local_file(self, client: ShopifyClient, file_path: str, alt_text: Optional[str] = None) -> str:
        """Upload local file to Shopify staging"""
        # Get file info
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type or not mime_type.startswith('image/'):
            mime_type = 'image/jpeg'
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
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
        
        variables = {
            "input": [{
                "filename": filename,
                "mimeType": mime_type,
                "fileSize": str(file_size),
                "httpMethod": "POST",
                "resource": "FILE"
            }]
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors'):
            errors = result['data']['stagedUploadsCreate']['userErrors']
            raise Exception(f"Staged upload error: {errors}")
        
        targets = result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])
        if not targets:
            raise Exception("No staged upload target created")
        
        target = targets[0]
        
        # Upload to staged target
        files = []
        for param in target['parameters']:
            files.append((param['name'], (None, param['value'])))
        
        files.append(('file', (filename, file_content)))
        
        response = requests.post(target['url'], files=files)
        response.raise_for_status()
        
        return target['resourceUrl']
    
    async def _create_product_media(self, client: ShopifyClient, product_id: str, 
                                   sources: List[str], alt_texts: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create product media from URLs or resource URLs"""
        mutation = """
        mutation createProductMedia($media: [CreateMediaInput!]!, $productId: ID!) {
            productCreateMedia(media: $media, productId: $productId) {
                media {
                    ... on MediaImage {
                        id
                        image {
                            url
                            altText
                        }
                        status
                    }
                }
                mediaUserErrors {
                    field
                    message
                    code
                }
                product {
                    id
                    title
                    media(first: 50) {
                        edges {
                            node {
                                ... on MediaImage {
                                    id
                                    image {
                                        url
                                        altText
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        # Build media input
        media = []
        for i, source in enumerate(sources):
            media_item = {
                "originalSource": source,
                "mediaContentType": "IMAGE"
            }
            
            if alt_texts and i < len(alt_texts) and alt_texts[i]:
                media_item["alt"] = alt_texts[i]
            
            media.append(media_item)
        
        variables = {
            "productId": product_id,
            "media": media
        }
        
        result = client.execute_graphql(mutation, variables)
        
        # Check for errors
        if result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors'):
            errors = result['data']['productCreateMedia']['mediaUserErrors']
            return {"success": False, "error": f"Media creation error: {errors}"}
        
        media_results = result.get('data', {}).get('productCreateMedia', {}).get('media', [])
        product = result.get('data', {}).get('productCreateMedia', {}).get('product', {})
        
        return {
            "success": True,
            "added_count": len(media_results),
            "total_images": len(product.get('media', {}).get('edges', [])),
            "added_images": [
                {
                    "id": m.get('id'),
                    "url": m.get('image', {}).get('url'),
                    "alt_text": m.get('image', {}).get('altText'),
                    "status": m.get('status')
                }
                for m in media_results if m
            ]
        }
    
    async def _delete_images(self, client: ShopifyClient, product_id: str, positions: List[int]) -> Dict[str, Any]:
        """Delete images by position"""
        # Get current images
        list_result = await self._list_images(client, product_id)
        if not list_result.get('success'):
            return list_result
        
        images = list_result.get('images', [])
        if not images:
            return {"success": False, "error": "No images to delete"}
        
        # Validate positions and collect media IDs
        media_ids = []
        for pos in positions:
            if 1 <= pos <= len(images):
                media_ids.append(images[pos - 1]['id'])
            else:
                return {"success": False, "error": f"Position {pos} out of range (1-{len(images)})"}
        
        # Delete images
        mutation = """
        mutation deleteProductMedia($mediaIds: [ID!]!, $productId: ID!) {
            productDeleteMedia(mediaIds: $mediaIds, productId: $productId) {
                deletedMediaIds
                product {
                    id
                    title
                }
                mediaUserErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "productId": product_id,
            "mediaIds": media_ids
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productDeleteMedia', {}).get('mediaUserErrors'):
            errors = result['data']['productDeleteMedia']['mediaUserErrors']
            return {"success": False, "error": f"Delete error: {errors}"}
        
        deleted = result.get('data', {}).get('productDeleteMedia', {}).get('deletedMediaIds', [])
        
        return {
            "success": True,
            "deleted_count": len(deleted),
            "deleted_ids": deleted
        }
    
    async def _reorder_images(self, client: ShopifyClient, product_id: str, positions: List[int]) -> Dict[str, Any]:
        """Reorder images"""
        # Get current images
        list_result = await self._list_images(client, product_id)
        if not list_result.get('success'):
            return list_result
        
        images = list_result.get('images', [])
        if not images:
            return {"success": False, "error": "No images to reorder"}
        
        # Validate positions
        if len(positions) != len(images):
            return {"success": False, "error": f"Must specify all {len(images)} positions"}
        
        if sorted(positions) != list(range(1, len(images) + 1)):
            return {"success": False, "error": "Invalid positions. Each position must be used exactly once"}
        
        # Build reorder
        mutation = """
        mutation reorderProductMedia($id: ID!, $moves: [MoveInput!]!) {
            productReorderMedia(id: $id, moves: $moves) {
                job {
                    id
                    done
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        # Build moves array
        moves = []
        for new_pos, old_pos in enumerate(positions):
            moves.append({
                "id": images[old_pos - 1]['id'],
                "newPosition": str(new_pos)
            })
        
        variables = {
            "id": product_id,
            "moves": moves
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productReorderMedia', {}).get('userErrors'):
            errors = result['data']['productReorderMedia']['userErrors']
            return {"success": False, "error": f"Reorder error: {errors}"}
        
        return {
            "success": True,
            "message": "Images reordered successfully"
        }
    
    async def _clear_images(self, client: ShopifyClient, product_id: str) -> Dict[str, Any]:
        """Clear all images"""
        # Get current images
        list_result = await self._list_images(client, product_id)
        if not list_result.get('success'):
            return list_result
        
        images = list_result.get('images', [])
        if not images:
            return {"success": True, "message": "No images to clear"}
        
        # Delete all images
        positions = list(range(1, len(images) + 1))
        return await self._delete_images(client, product_id, positions)
    
    def _is_local_file(self, path: str) -> bool:
        """Check if path is a local file"""
        return not (path.startswith('http://') or path.startswith('https://'))
    
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