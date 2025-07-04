"""
MCP wrapper for create_product tool
"""

from typing import Dict, Any, Optional, List
import sys
import os

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class CreateProductTool(BaseMCPTool):
    """Create new products in Shopify"""
    
    name = "create_product"
    description = "Create a new product in Shopify with basic information"
    context = """
    Creates a new product with essential information:
    - Title and description
    - Product type and vendor
    - Initial price and SKU
    - Status (active/draft)
    
    For more complex product creation with variants, images, and metafields,
    use create_full_product instead.
    
    Business rules:
    - Products start as draft unless explicitly set to active
    - SKU must be unique across all products
    - Vendor should match existing vendors for consistency
    - Product type helps with organization and filtering
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Product title"
            },
            "description": {
                "type": "string", 
                "description": "Product description (HTML allowed)"
            },
            "sku": {
                "type": "string",
                "description": "Unique SKU identifier"
            },
            "price": {
                "type": "number",
                "description": "Product price"
            },
            "vendor": {
                "type": "string",
                "description": "Product vendor/manufacturer"
            },
            "product_type": {
                "type": "string",
                "description": "Product type for categorization"
            },
            "status": {
                "type": "string",
                "enum": ["ACTIVE", "DRAFT"],
                "description": "Product status (default: DRAFT)"
            },
            "tags": {
                "type": "string",
                "description": "Comma-separated list of tags"
            },
            "barcode": {
                "type": "string",
                "description": "Product barcode"
            },
            "weight": {
                "type": "number",
                "description": "Product weight"
            },
            "weight_unit": {
                "type": "string",
                "enum": ["GRAMS", "KILOGRAMS", "OUNCES", "POUNDS"],
                "description": "Weight unit (default: KILOGRAMS)"
            },
            "inventory": {
                "type": "integer",
                "description": "Initial inventory quantity (default: 0)"
            },
            "no_track_inventory": {
                "type": "boolean",
                "description": "Disable inventory tracking"
            }
        },
        "required": ["title", "vendor", "product_type"]
    }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute product creation natively"""
        try:
            client = ShopifyClient()
            
            # Extract required fields
            title = kwargs.get('title')
            vendor = kwargs.get('vendor')
            product_type = kwargs.get('product_type')
            
            if not all([title, vendor, product_type]):
                return {
                    "success": False,
                    "error": "title, vendor, and product_type are required"
                }
            
            # Build product input
            product_input = {
                "title": title,
                "vendor": vendor,
                "productType": product_type,
                "status": kwargs.get('status', 'DRAFT')
            }
            
            if kwargs.get('description'):
                product_input['descriptionHtml'] = kwargs['description']
            
            if kwargs.get('tags'):
                # Handle both string and list formats
                tags = kwargs['tags']
                if isinstance(tags, str):
                    product_input['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
                else:
                    product_input['tags'] = tags
            
            # Create product
            mutation = '''
            mutation createProduct($input: ProductInput!) {
                productCreate(input: $input) {
                    product {
                        id
                        title
                        handle
                        status
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
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            variables = {"input": product_input}
            result = client.execute_graphql(mutation, variables)
            
            if 'errors' in result:
                return {"success": False, "error": f"GraphQL errors: {result['errors']}"}
            
            product_create = result['data']['productCreate']
            if product_create['userErrors']:
                return {"success": False, "error": f"User errors: {product_create['userErrors']}"}
            
            product = product_create['product']
            product_id = product['id']
            variant_id = product['variants']['edges'][0]['node']['id']
            inventory_item_id = product['variants']['edges'][0]['node']['inventoryItem']['id']
            
            # Update variant with additional details if provided
            if any([kwargs.get('price'), kwargs.get('sku'), kwargs.get('barcode'), kwargs.get('weight')]):
                await self._update_variant_details(
                    client, product_id, variant_id, inventory_item_id, kwargs
                )
            
            # Get shop URL for admin link
            shop_url = os.getenv('SHOPIFY_SHOP_URL', '').replace('https://', '')
            product_admin_id = product_id.split('/')[-1]
            
            return {
                "success": True,
                "product_id": product_id,
                "variant_id": variant_id,
                "title": product['title'],
                "handle": product['handle'],
                "status": product['status'],
                "admin_url": f"https://{shop_url}/admin/products/{product_admin_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_variant_details(self, client: ShopifyClient, product_id: str, variant_id: str,
                                      inventory_item_id: str, kwargs: Dict[str, Any]) -> None:
        """Update variant with price, SKU, and other details"""
        mutation = '''
        mutation updateVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        variant_input = {
            "id": variant_id,
            "inventoryPolicy": "DENY",
            "inventoryItem": {
                "tracked": not kwargs.get('no_track_inventory', False)
            }
        }
        
        if kwargs.get('price'):
            variant_input['price'] = str(kwargs['price'])
        
        if kwargs.get('sku'):
            variant_input['inventoryItem']['sku'] = kwargs['sku']
        
        if kwargs.get('barcode'):
            variant_input['barcode'] = kwargs['barcode']
        
        if kwargs.get('weight'):
            variant_input['inventoryItem']['measurement'] = {
                "weight": {
                    "value": kwargs['weight'],
                    "unit": kwargs.get('weight_unit', 'KILOGRAMS')
                }
            }
        
        variables = {
            "productId": product_id,
            "variants": [variant_input]
        }
        
        client.execute_graphql(mutation, variables)
        
        # Set initial inventory if provided
        if kwargs.get('inventory') is not None:
            await self._set_inventory(client, inventory_item_id, kwargs['inventory'])
    
    async def _set_inventory(self, client: ShopifyClient, inventory_item_id: str, quantity: int) -> None:
        """Set initial inventory quantity"""
        # First get the location
        location_query = '''
        query {
            locations(first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
        '''
        
        result = client.execute_graphql(location_query)
        locations = result.get('data', {}).get('locations', {}).get('edges', [])
        
        if not locations:
            return
        
        location_id = locations[0]['node']['id']
        
        # Set inventory
        inventory_mutation = '''
        mutation inventorySetOnHand($input: InventorySetOnHandInput!) {
            inventorySetOnHand(input: $input) {
                inventoryLevel {
                    available
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        variables = {
            "input": {
                "locationId": location_id,
                "inventoryItemId": inventory_item_id,
                "quantity": quantity
            }
        }
        
        client.execute_graphql(inventory_mutation, variables)
            
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