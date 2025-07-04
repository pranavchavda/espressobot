"""
MCP wrapper for manage_tags tool
"""

from typing import Dict, Any, Optional, List
import sys
import os

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class ManageTagsTool(BaseMCPTool):
    """Manage product tags"""
    
    name = "manage_tags"
    description = "Add, remove, or replace tags on products"
    context = """
    Tags are used for organization, filtering, and automation:
    
    Common tag uses at iDrinkCoffee:
    - Product categories: "espresso-machines", "grinders", "accessories"
    - Features: "programmable", "automatic", "manual"
    - Promotions: "sale", "new-arrival", "bestseller"
    - Attributes: "commercial", "home-use", "portable"
    
    Operations:
    - add: Add tags (preserves existing)
    - remove: Remove specific tags
    
    Important:
    - Tags are case-sensitive
    - Use consistent naming conventions
    - Some tags trigger automations (e.g., "sale" may show sale badge)
    - Tags affect search and filtering
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "product": {
                "type": "string",
                "description": "Product ID, handle, SKU, or title"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags to add/remove/replace"
            },
            "action": {
                "type": "string",
                "enum": ["add", "remove"],
                "description": "Tag action to perform (add or remove)"
            }
        },
        "required": ["product", "tags", "action"]
    }
    
    async def execute(self, product: str, tags: List[str], action: str) -> Dict[str, Any]:
        """Execute tag management natively"""
        try:
            client = ShopifyClient()
            
            # Resolve product ID
            product_id = client.resolve_product_id(product)
            if not product_id:
                return {
                    "success": False,
                    "error": f"Product not found: {product}"
                }
            
            if action == "add":
                return await self._add_tags(client, product_id, tags)
            elif action == "remove":
                return await self._remove_tags(client, product_id, tags)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}. Use 'add' or 'remove'"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _add_tags(self, client: ShopifyClient, product_id: str, tags: List[str]) -> Dict[str, Any]:
        """Add tags to product"""
        mutation = '''
        mutation addTags($id: ID!, $tags: [String!]!) {
            tagsAdd(id: $id, tags: $tags) {
                node {
                    id
                    ... on Product {
                        tags
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        variables = {
            "id": product_id,
            "tags": tags
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('tagsAdd', {}).get('userErrors'):
            errors = result['data']['tagsAdd']['userErrors']
            return {"success": False, "error": f"Tag add errors: {errors}"}
        
        node = result.get('data', {}).get('tagsAdd', {}).get('node', {})
        current_tags = node.get('tags', [])
        
        return {
            "success": True,
            "action": "add",
            "tags_added": tags,
            "current_tags": current_tags,
            "message": f"Added {len(tags)} tag(s) to product"
        }
    
    async def _remove_tags(self, client: ShopifyClient, product_id: str, tags: List[str]) -> Dict[str, Any]:
        """Remove tags from product"""
        mutation = '''
        mutation removeTags($id: ID!, $tags: [String!]!) {
            tagsRemove(id: $id, tags: $tags) {
                node {
                    id
                    ... on Product {
                        tags
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        variables = {
            "id": product_id,
            "tags": tags
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('tagsRemove', {}).get('userErrors'):
            errors = result['data']['tagsRemove']['userErrors']
            return {"success": False, "error": f"Tag remove errors: {errors}"}
        
        node = result.get('data', {}).get('tagsRemove', {}).get('node', {})
        current_tags = node.get('tags', [])
        
        return {
            "success": True,
            "action": "remove",
            "tags_removed": tags,
            "current_tags": current_tags,
            "message": f"Removed {len(tags)} tag(s) from product"
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