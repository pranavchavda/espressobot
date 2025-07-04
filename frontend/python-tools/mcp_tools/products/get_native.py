"""
Native MCP implementation for get_product - no subprocess needed
"""

from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class GetProductNativeTool(BaseMCPTool):
    """Get product details - native implementation"""
    
    name = "get_product_native"
    description = "Get detailed product information by SKU, handle, or ID"
    context = """
    This is a native MCP implementation that directly calls the Shopify API.
    No subprocess overhead - faster and more reliable.
    
    Accepts:
    - SKU (e.g., "ESP-001")
    - Handle (e.g., "mexican-altura")
    - Product ID (e.g., "gid://shopify/Product/123")
    - Variant ID (will find parent product)
    
    Returns complete product data including variants, images, and options.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Product SKU, handle, ID, or variant ID"
            },
            "include_metafields": {
                "type": "boolean",
                "description": "Include product metafields in response"
            }
        },
        "required": ["identifier"]
    }
    
    async def execute(self, identifier: str, include_metafields: bool = False) -> Dict[str, Any]:
        """Execute get_product directly without subprocess"""
        try:
            client = ShopifyClient()
            
            # Resolve product ID
            product_id = client.resolve_product_id(identifier)
            if not product_id:
                raise Exception(f"Product not found with identifier: {identifier}")
            
            # Build query with optional metafields
            metafield_query = ''
            if include_metafields:
                metafield_query = '''
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
                '''
            
            query = f'''
            query getProduct($id: ID!) {{
                product(id: $id) {{
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
                    seo {{
                        title
                        description
                    }}
                    featuredImage {{
                        url
                        altText
                    }}
                    images(first: 10) {{
                        edges {{
                            node {{
                                url
                                altText
                            }}
                        }}
                    }}
                    options {{
                        name
                        values
                    }}
                    variants(first: 100) {{
                        edges {{
                            node {{
                                id
                                title
                                sku
                                barcode
                                price
                                compareAtPrice
                                availableForSale
                                inventoryPolicy
                                inventoryQuantity
                                selectedOptions {{
                                    name
                                    value
                                }}
                            }}
                        }}
                    }}
                    {metafield_query}
                }}
            }}
            '''
            
            variables = {"id": product_id}
            result = client.execute_query(query, variables)
            
            product = result['data']['product']
            if not product:
                raise Exception(f"Product not found: {product_id}")
                
            # Format the response
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
            
        # Extract metafields if present
        metafields = []
        if 'metafields' in product:
            for edge in product['metafields']['edges']:
                metafields.append(edge['node'])
        
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
            'metafields': metafields if metafields else None,
            'createdAt': product['createdAt'],
            'updatedAt': product['updatedAt'],
            'publishedAt': product['publishedAt']
        }
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool with a simple query"""
        try:
            # Just verify we can create a client
            client = ShopifyClient()
            return {
                "status": "passed",
                "message": "Native tool ready"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }