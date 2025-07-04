"""
Native MCP implementation for uploading products to SkuVault
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from ..base import BaseMCPTool, ShopifyClient

class UploadToSkuVaultTool(BaseMCPTool):
    """Upload products from Shopify to SkuVault inventory system"""
    
    name = "upload_to_skuvault"
    description = "Upload products from Shopify to SkuVault inventory management"
    context = """
    Uploads product data from Shopify to SkuVault for inventory synchronization.
    
    Features:
    - Fetch product data from Shopify by SKU
    - Convert to SkuVault format
    - Upload to SkuVault API
    - Support batch uploads
    - Dry run preview mode
    
    Process:
    1. Fetch product from Shopify by SKU
    2. Extract title, vendor, price, cost, images
    3. Format for SkuVault requirements
    4. Upload via SkuVault API
    
    Requirements:
    - SKUVAULT_TENANT_TOKEN environment variable
    - SKUVAULT_USER_TOKEN environment variable
    
    SkuVault fields mapped:
    - Sku: Product SKU
    - Description: Product title
    - Brand: Vendor
    - Cost: Unit cost from inventory
    - SalePrice/RetailPrice: Variant price
    - Pictures: Up to 5 product images
    
    Use cases:
    - Initial product setup in SkuVault
    - Sync new products after creation
    - Update product details
    - Bulk uploads from SKU lists
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "skus": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of SKUs to upload"
            },
            "sku": {
                "type": "string",
                "description": "Single SKU (alternative to skus array)"
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview without uploading",
                "default": False
            }
        }
    }
    
    def __init__(self):
        super().__init__()
        self.skuvault_tenant_token = os.environ.get('SKUVAULT_TENANT_TOKEN')
        self.skuvault_user_token = os.environ.get('SKUVAULT_USER_TOKEN')
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Upload products to SkuVault"""
        if not self.skuvault_tenant_token or not self.skuvault_user_token:
            return {
                "success": False,
                "error": "SkuVault credentials not configured. Set SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN"
            }
        
        # Get SKUs to process
        skus = []
        if 'skus' in kwargs:
            skus = kwargs['skus']
        elif 'sku' in kwargs:
            skus = [kwargs['sku']]
        else:
            return {
                "success": False,
                "error": "Either 'skus' array or 'sku' string required"
            }
        
        dry_run = kwargs.get('dry_run', False)
        
        # Process each SKU
        results = []
        client = ShopifyClient()
        
        for sku in skus:
            result = await self._process_sku(client, sku, dry_run)
            results.append(result)
        
        # Summary
        success_count = sum(1 for r in results if r.get('success'))
        failed_count = len(results) - success_count
        
        return {
            "success": True,
            "summary": {
                "total": len(results),
                "successful": success_count,
                "failed": failed_count
            },
            "results": results,
            "dry_run": dry_run
        }
    
    async def _process_sku(self, client: ShopifyClient, sku: str, dry_run: bool) -> Dict[str, Any]:
        """Process a single SKU"""
        try:
            # Fetch from Shopify
            shopify_data = await self._fetch_product_by_sku(client, sku)
            if not shopify_data:
                return {
                    "sku": sku,
                    "success": False,
                    "error": "Product not found in Shopify"
                }
            
            # Prepare SkuVault data
            skuvault_data = self._prepare_skuvault_data(shopify_data)
            
            if dry_run:
                # Remove tokens from preview
                preview_data = {k: v for k, v in skuvault_data.items() 
                               if k not in ['TenantToken', 'UserToken']}
                return {
                    "sku": sku,
                    "success": True,
                    "action": "would_upload",
                    "data": preview_data
                }
            
            # Upload to SkuVault
            upload_result = await self._upload_to_skuvault(skuvault_data)
            
            return {
                "sku": sku,
                "success": upload_result['success'],
                "message": upload_result.get('message', ''),
                "product_title": shopify_data['product']['title']
            }
            
        except Exception as e:
            return {
                "sku": sku,
                "success": False,
                "error": str(e)
            }
    
    async def _fetch_product_by_sku(self, client: ShopifyClient, sku: str) -> Optional[Dict[str, Any]]:
        """Fetch product data from Shopify by SKU"""
        query = """
        query getProductBySku($sku: String!) {
            productVariants(first: 1, query: $sku) {
                edges {
                    node {
                        id
                        sku
                        price
                        inventoryItem {
                            id
                            unitCost {
                                amount
                            }
                        }
                        product {
                            id
                            title
                            vendor
                            productType
                            descriptionHtml
                            images(first: 5) {
                                edges {
                                    node {
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
        
        variables = {"sku": f"sku:{sku}"}
        result = client.execute_graphql(query, variables)
        
        if 'errors' in result:
            return None
        
        edges = result.get('data', {}).get('productVariants', {}).get('edges', [])
        if not edges:
            return None
        
        return edges[0]['node']
    
    def _prepare_skuvault_data(self, shopify_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Shopify product data to SkuVault format"""
        variant = shopify_data
        product = variant.get('product', {})
        
        # Extract basic info
        title = product.get('title', '')
        vendor = product.get('vendor', 'Unknown')
        sku = variant.get('sku', '')
        price = float(variant.get('price', 0))
        
        # Extract cost
        inventory_item = variant.get('inventoryItem', {})
        unit_cost = inventory_item.get('unitCost', {})
        cost = float(unit_cost.get('amount', 0)) if unit_cost else 0
        
        # Extract images
        images = []
        for edge in product.get('images', {}).get('edges', []):
            if 'node' in edge and 'url' in edge['node']:
                images.append(edge['node']['url'])
        
        # Extract description (strip HTML)
        description_html = product.get('descriptionHtml', '')
        # Simple HTML stripping
        import re
        description = re.sub('<[^<]+?>', '', description_html)
        
        # Build SkuVault product data
        return {
            "Sku": sku,
            "PartNumber": sku,
            "Description": title,
            "ShortDescription": title[:100] if len(title) > 100 else title,
            "LongDescription": description or title,
            "Classification": product.get('productType', 'General'),
            "Supplier": vendor,  # Use vendor as supplier
            "Brand": vendor,
            "Cost": cost,
            "SalePrice": price,
            "RetailPrice": price,
            "AllowCreateAp": False,
            "IsSerialized": False,
            "IsLotted": False,
            "Pictures": images[:5],  # SkuVault limits to 5 images
            "TenantToken": self.skuvault_tenant_token,
            "UserToken": self.skuvault_user_token
        }
    
    async def _upload_to_skuvault(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload product data to SkuVault API"""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                'https://app.skuvault.com/api/products/createProduct',
                headers=headers,
                json=product_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Product '{product_data['Sku']}' uploaded successfully"
                }
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get('ErrorMessages', [response.text])
                    return {
                        "success": False,
                        "message": f"SkuVault API error: {error_msg}"
                    }
                except:
                    return {
                        "success": False,
                        "message": f"Failed with status {response.status_code}: {response.text}"
                    }
                    
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Request error: {str(e)}"
            }
    
    async def test(self) -> Dict[str, Any]:
        """Test SkuVault upload capability"""
        if not self.skuvault_tenant_token or not self.skuvault_user_token:
            return {
                "status": "failed",
                "error": "SkuVault credentials not configured"
            }
        
        return {
            "status": "passed",
            "message": "SkuVault upload tool ready"
        }