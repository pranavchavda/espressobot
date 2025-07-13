"""
Native MCP implementation for update_status
"""

from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class UpdateStatusTool(BaseMCPTool):
    """Update product status"""
    
    name = "update_status"
    description = "Change product status between active, draft, and archived"
    context = """
    Controls product visibility and availability:
    
    Status options:
    - ACTIVE: Product is visible and available for purchase
    - DRAFT: Product is hidden from storefront (for preparation/review)
    - ARCHIVED: Product is hidden and preserved for records
    
    Important notes:
    - Changing to draft/archived will hide product from customers
    - Archived products cannot be purchased even with direct link
    - Use draft for temporary hiding, archived for permanent removal
    - Status change affects ALL variants of a product
    """
    
    input_schema = {
        "type": "object", 
        "properties": {
            "product": {
                "type": "string",
                "description": "Product ID, handle, SKU, or title"
            },
            "status": {
                "type": "string",
                "enum": ["ACTIVE", "DRAFT", "ARCHIVED"],
                "description": "New product status"
            }
        },
        "required": ["product", "status"]
    }
    
    async def execute(self, product: str, status: str) -> Dict[str, Any]:
        """Update product status natively"""
        try:
            client = ShopifyClient()
            
            # Resolve product ID
            product_id = client.resolve_product_id(product)
            if not product_id:
                return {
                    "success": False,
                    "error": f"Product not found with identifier: {product}"
                }
            
            # Get current status first
            query = '''
            query getProductStatus($id: ID!) {
                product(id: $id) {
                    id
                    title
                    status
                    handle
                }
            }
            '''
            
            result = client.execute_graphql(query, {'id': product_id})
            product_data = result.get('data', {}).get('product')
            
            if not product_data:
                return {
                    "success": False,
                    "error": "Could not retrieve product"
                }
            
            current_status = product_data['status']
            
            # Check if status is already set
            if current_status == status:
                return {
                    "success": True,
                    "message": f"Product '{product_data['title']}' is already {status}",
                    "product": product_data
                }
            
            # Update status
            mutation = '''
            mutation updateProductStatus($input: ProductInput!) {
                productUpdate(input: $input) {
                    product {
                        id
                        title
                        status
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
                'input': {
                    'id': product_id,
                    'status': status
                }
            }
            
            result = client.execute_graphql(mutation, variables)
            
            # Check for errors
            user_errors = result.get('data', {}).get('productUpdate', {}).get('userErrors', [])
            if user_errors:
                return {
                    "success": False,
                    "error": f"Update failed: {user_errors}"
                }
            
            updated_product = result.get('data', {}).get('productUpdate', {}).get('product')
            
            if updated_product:
                return {
                    "success": True,
                    "message": f"Successfully updated product status from {current_status} to {status}",
                    "product": {
                        "id": updated_product['id'],
                        "title": updated_product['title'],
                        "status": updated_product['status'],
                        "handle": updated_product['handle'],
                        "previous_status": current_status
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Update completed but product data not returned"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool"""
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