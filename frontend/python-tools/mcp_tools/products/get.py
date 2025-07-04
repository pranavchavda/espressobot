"""
MCP wrapper for get_product tool
"""

from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class GetProductTool(BaseMCPTool):
    """Get product details by SKU, handle, or product ID"""
    
    name = "get_product"
    description = "Retrieve detailed product information from Shopify by SKU, handle, or product ID"
    context = """
    This tool retrieves comprehensive product data including:
    - Basic info (title, description, status)
    - All variants with pricing and inventory
    - Images and metafields
    - SEO settings
    
    Accepts multiple identifier types:
    - SKU (e.g., "ESP-1001")
    - Handle (e.g., "sanremo-cube-white")
    - Product ID (e.g., "gid://shopify/Product/123")
    - Numeric ID (e.g., "123456789")
    
    Returns JSON with full product details.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Product SKU, handle, or ID"
            }
        },
        "required": ["identifier"]
    }
    
    async def execute(self, identifier: str) -> Dict[str, Any]:
        """Execute get_product natively"""
        try:
            client = ShopifyClient()
            
            # Resolve product ID
            product_id = client.resolve_product_id(identifier)
            if not product_id:
                return {
                    "success": False,
                    "error": f"Product not found with identifier: {identifier}"
                }
            
            # Get product data
            query = '''
            query getProduct($id: ID!) {
                product(id: $id) {
                    id
                    title
                    handle
                    description
                    descriptionHtml
                    vendor
                    productType
                    status
                    tags
                    createdAt
                    updatedAt
                    publishedAt
                    seo {
                        title
                        description
                    }
                    featuredImage {
                        url
                        altText
                    }
                    images(first: 10) {
                        edges {
                            node {
                                url
                                altText
                            }
                        }
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
                                barcode
                                price
                                compareAtPrice
                                availableForSale
                                inventoryPolicy
                                inventoryQuantity
                                selectedOptions {
                                    name
                                    value
                                }
                            }
                        }
                    }
                }
            }
            '''
            
            variables = {"id": product_id}
            result = client.execute_graphql(query, variables)
            
            product = result['data']['product']
            if not product:
                return {
                    "success": False,
                    "error": f"Product not found: {product_id}"
                }
                
            # Format the response to match original tool output
            return {
                "success": True,
                "product": self._format_product(product)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Format product data for consistent output"""
        # Extract variants
        variants = []
        for edge in product.get('variants', {}).get('edges', []):
            variant = edge['node']
            variants.append({
                'id': variant['id'],
                'title': variant['title'],
                'sku': variant['sku'],
                'barcode': variant['barcode'],
                'price': variant['price'],
                'compareAtPrice': variant['compareAtPrice'],
                'availableForSale': variant['availableForSale'],
                'inventoryPolicy': variant['inventoryPolicy'],
                'inventoryQuantity': variant['inventoryQuantity'],
                'options': variant['selectedOptions']
            })
        
        # Extract images
        images = []
        for edge in product.get('images', {}).get('edges', []):
            images.append(edge['node'])
        
        return {
            'id': product['id'],
            'title': product['title'],
            'handle': product['handle'],
            'description': product['description'],
            'vendor': product['vendor'],
            'productType': product['productType'],
            'status': product['status'],
            'tags': product['tags'],
            'options': product['options'],
            'variants': variants,
            'images': images,
            'featuredImage': product['featuredImage'],
            'seo': product['seo'],
            'createdAt': product['createdAt'],
            'updatedAt': product['updatedAt'],
            'publishedAt': product['publishedAt']
        }
            
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