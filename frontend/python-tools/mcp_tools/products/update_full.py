"""
Native MCP implementation for update_full_product
"""

import os
import sys
import json
import mimetypes
import requests
from typing import Dict, Any, List, Optional, Union

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class UpdateFullProductTool(BaseMCPTool):
    """Update an existing product with comprehensive content including variants, media, and metafields"""
    
    name = "update_full_product"
    description = "Comprehensively update an existing Shopify product with title, description, variants, media, metafields, and more"
    context = """
    This tool provides complete product updating capabilities for Shopify products:
    
    **Product Updates:**
    - Basic info (title, description, vendor, type)
    - Product status and visibility settings
    - SEO settings and URL handle
    - Tags and categorization
    
    **Variant Management:**
    - Update existing variants by ID
    - Add new variants with option values
    - Modify pricing, SKUs, and inventory
    - Set variant-specific settings
    
    **Media Management:**
    - Add new images from URLs
    - Upload local files to Shopify staging
    - Set alt text for accessibility
    - Replace or add to existing media
    
    **Metafields:**
    - Add or update custom metafields
    - Support for all Shopify metafield types
    - Proper namespace and key structure
    
    **Advanced Features:**
    - Synchronous updates for immediate consistency
    - Local file upload with staged uploads
    - Comprehensive error handling
    - Preserves existing data not specified in update
    
    **Input Structure:**
    The tool accepts a comprehensive payload with any combination of:
    - Product fields (title, description, etc.)
    - Variants array (existing updates + new variants)
    - Media array (URLs and local files)
    - Metafields array (custom data)
    
    **Important Notes:**
    - Uses productSet mutation for atomic updates
    - Local files are uploaded to Shopify staging first
    - Existing data is preserved unless explicitly updated
    - Variants can be updated by ID or created new
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "Product identifier (SKU, handle, or product ID)"
            },
            "title": {
                "type": "string",
                "description": "Product title"
            },
            "description_html": {
                "type": "string",
                "description": "Product description (HTML supported)"
            },
            "product_type": {
                "type": "string",
                "description": "Product type"
            },
            "vendor": {
                "type": "string",
                "description": "Product vendor/brand"
            },
            "status": {
                "type": "string",
                "enum": ["ACTIVE", "ARCHIVED", "DRAFT"],
                "description": "Product status"
            },
            "handle": {
                "type": "string",
                "description": "URL handle"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Product tags"
            },
            "seo": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"}
                },
                "description": "SEO settings"
            },
            "metafields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "key": {"type": "string"},
                        "type": {"type": "string"},
                        "value": {"type": "string"}
                    },
                    "required": ["namespace", "key", "type", "value"]
                },
                "description": "Product metafields"
            },
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Variant ID (for updating existing variant)"
                        },
                        "price": {"type": "string"},
                        "compare_at_price": {"type": "string"},
                        "sku": {"type": "string"},
                        "barcode": {"type": "string"},
                        "weight": {"type": "number"},
                        "weight_unit": {"type": "string", "enum": ["GRAMS", "KILOGRAMS", "POUNDS", "OUNCES"]},
                        "inventory_policy": {"type": "string", "enum": ["DENY", "CONTINUE"]},
                        "inventory_quantity": {"type": "integer"},
                        "taxable": {"type": "boolean"},
                        "option_values": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "option_name": {"type": "string"},
                                    "value": {"type": "string"}
                                }
                            },
                            "description": "Option values for new variants"
                        }
                    }
                },
                "description": "Product variants (update existing by ID or create new)"
            },
            "media": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "original_source": {
                            "type": "string",
                            "description": "Image URL"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Local file path to upload"
                        },
                        "alt": {
                            "type": "string",
                            "description": "Alt text for accessibility"
                        },
                        "media_content_type": {
                            "type": "string",
                            "enum": ["IMAGE", "VIDEO", "MODEL_3D"],
                            "description": "Media type (default: IMAGE)"
                        }
                    },
                    "description": "Media files (URLs or local files)"
                }
            }
        },
        "required": ["product_id"]
    }
    
    async def execute(self, product_id: str, title: Optional[str] = None,
                     description_html: Optional[str] = None, product_type: Optional[str] = None,
                     vendor: Optional[str] = None, status: Optional[str] = None,
                     handle: Optional[str] = None, tags: Optional[List[str]] = None,
                     seo: Optional[Dict[str, str]] = None, metafields: Optional[List[Dict[str, str]]] = None,
                     variants: Optional[List[Dict[str, Any]]] = None,
                     media: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Execute product update"""
        try:
            client = ShopifyClient()
            
            # Resolve product ID
            resolved_id = client.resolve_product_id(product_id)
            if not resolved_id:
                return {
                    "success": False,
                    "error": f"Product not found: {product_id}"
                }
            
            # Build product input
            product_input = await self._build_product_input(
                resolved_id, title, description_html, product_type, vendor,
                status, handle, tags, seo, metafields, variants
            )
            
            # Update product using productSet
            print(f"Updating product: {product_id}...")
            update_result = await self._update_product(client, product_input)
            
            if not update_result["success"]:
                return update_result
            
            # Handle media uploads/additions
            media_result = {"success": True, "media_added": 0}
            if media:
                print(f"Processing {len(media)} media items...")
                media_result = await self._process_media(client, resolved_id, media)
                if not media_result["success"]:
                    print(f"Warning: Media processing failed: {media_result['error']}")
            
            return {
                "success": True,
                "product_id": resolved_id,
                "updated_fields": self._get_updated_fields(locals()),
                "media_added": media_result.get("media_added", 0),
                "admin_url": self._get_admin_url(resolved_id)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _build_product_input(self, product_id: str, title: Optional[str] = None,
                                  description_html: Optional[str] = None, product_type: Optional[str] = None,
                                  vendor: Optional[str] = None, status: Optional[str] = None,
                                  handle: Optional[str] = None, tags: Optional[List[str]] = None,
                                  seo: Optional[Dict[str, str]] = None, metafields: Optional[List[Dict[str, str]]] = None,
                                  variants: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Build product input for productSet mutation"""
        product_input = {"id": product_id}
        
        # Add provided fields
        if title is not None:
            product_input["title"] = title
        
        if description_html is not None:
            product_input["descriptionHtml"] = description_html
        
        if product_type is not None:
            product_input["productType"] = product_type
        
        if vendor is not None:
            product_input["vendor"] = vendor
        
        if status is not None:
            product_input["status"] = status
        
        if handle is not None:
            product_input["handle"] = handle
        
        if tags is not None:
            product_input["tags"] = tags
        
        if seo is not None:
            product_input["seo"] = seo
        
        if metafields is not None:
            product_input["metafields"] = metafields
        
        if variants is not None:
            # Format variants for GraphQL
            formatted_variants = []
            for variant in variants:
                formatted_variant = {}
                
                if variant.get("id"):
                    formatted_variant["id"] = variant["id"]
                
                if variant.get("price"):
                    formatted_variant["price"] = variant["price"]
                
                if variant.get("compare_at_price"):
                    formatted_variant["compareAtPrice"] = variant["compare_at_price"]
                
                if variant.get("sku"):
                    formatted_variant["sku"] = variant["sku"]
                
                if variant.get("barcode"):
                    formatted_variant["barcode"] = variant["barcode"]
                
                if variant.get("weight") is not None:
                    formatted_variant["weight"] = variant["weight"]
                
                if variant.get("weight_unit"):
                    formatted_variant["weightUnit"] = variant["weight_unit"]
                
                if variant.get("inventory_policy"):
                    formatted_variant["inventoryPolicy"] = variant["inventory_policy"]
                
                if variant.get("inventory_quantity") is not None:
                    formatted_variant["inventoryQuantity"] = variant["inventory_quantity"]
                
                if variant.get("taxable") is not None:
                    formatted_variant["taxable"] = variant["taxable"]
                
                if variant.get("option_values"):
                    formatted_variant["optionValues"] = [
                        {"optionName": ov["option_name"], "value": ov["value"]}
                        for ov in variant["option_values"]
                    ]
                
                formatted_variants.append(formatted_variant)
            
            product_input["variants"] = formatted_variants
        
        return product_input
    
    async def _update_product(self, client: ShopifyClient, product_input: Dict[str, Any]) -> Dict[str, Any]:
        """Update product using productSet mutation"""
        mutation = """
        mutation productSet($input: ProductSetInput!, $sync: Boolean!) {
            productSet(input: $input, synchronous: $sync) {
                product {
                    id
                    title
                    handle
                    status
                }
                userErrors {
                    field
                    message
                    code
                }
            }
        }
        """
        
        variables = {"input": product_input, "sync": True}
        result = client.execute_graphql(mutation, variables)
        
        if 'errors' in result:
            return {"success": False, "error": f"GraphQL errors: {result['errors']}"}
        
        product_set = result.get('data', {}).get('productSet', {})
        if product_set.get('userErrors'):
            return {"success": False, "error": f"User errors: {product_set['userErrors']}"}
        
        return {
            "success": True,
            "product": product_set.get('product', {})
        }
    
    async def _process_media(self, client: ShopifyClient, product_id: str, media_items: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process media uploads and additions"""
        create_inputs = []
        
        for media in media_items:
            original_source = media.get("original_source")
            
            # Handle local file upload
            if not original_source and media.get("file_path"):
                try:
                    original_source = await self._upload_local_file(client, media["file_path"])
                except Exception as e:
                    return {"success": False, "error": f"File upload failed: {str(e)}"}
            
            if not original_source:
                continue
            
            create_inputs.append({
                "originalSource": original_source,
                "mediaContentType": media.get("media_content_type", "IMAGE"),
                "alt": media.get("alt")
            })
        
        if not create_inputs:
            return {"success": True, "media_added": 0}
        
        # Create media using productCreateMedia
        mutation = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
            productCreateMedia(productId: $productId, media: $media) {
                media {
                    id
                    alt
                    ... on MediaImage {
                        image {
                            url
                        }
                    }
                }
                mediaUserErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {"productId": product_id, "media": create_inputs}
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors'):
            errors = result['data']['productCreateMedia']['mediaUserErrors']
            return {"success": False, "error": f"Media creation errors: {errors}"}
        
        created_media = result.get('data', {}).get('productCreateMedia', {}).get('media', [])
        
        return {
            "success": True,
            "media_added": len(created_media),
            "media": created_media
        }
    
    async def _upload_local_file(self, client: ShopifyClient, file_path: str) -> str:
        """Upload local file to Shopify staging"""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "image/jpeg"
        file_size = os.path.getsize(file_path)
        
        # Create staged upload
        staged_mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
            stagedUploadsCreate(input: $input) {
                stagedTargets {
                    url
                    resourceUrl
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
                "resource": "IMAGE",
                "filename": filename,
                "mimeType": mime_type,
                "httpMethod": "POST",
                "fileSize": file_size
            }]
        }
        
        result = client.execute_graphql(staged_mutation, variables)
        
        if result.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors'):
            errors = result['data']['stagedUploadsCreate']['userErrors']
            raise Exception(f"Staged upload errors: {errors}")
        
        targets = result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])
        if not targets:
            raise Exception("No staged upload target created")
        
        target = targets[0]
        
        # Upload file
        upload_url = target["url"]
        params = {p["name"]: p["value"] for p in target["parameters"]}
        
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            response = requests.post(upload_url, data=params, files=files)
            response.raise_for_status()
        
        return target["resourceUrl"]
    
    def _get_updated_fields(self, local_vars: Dict[str, Any]) -> List[str]:
        """Get list of fields that were updated"""
        updated = []
        field_mapping = {
            "title": "title",
            "description_html": "description",
            "product_type": "productType",
            "vendor": "vendor",
            "status": "status",
            "handle": "handle",
            "tags": "tags",
            "seo": "seo",
            "metafields": "metafields",
            "variants": "variants"
        }
        
        for param, field in field_mapping.items():
            if local_vars.get(param) is not None:
                updated.append(field)
        
        return updated
    
    def _get_admin_url(self, product_id: str) -> str:
        """Get admin URL for the product"""
        shop_url = os.getenv('SHOPIFY_SHOP_URL', '').replace('https://', '')
        product_admin_id = product_id.split('/')[-1]
        return f"https://{shop_url}/admin/products/{product_admin_id}"
    
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