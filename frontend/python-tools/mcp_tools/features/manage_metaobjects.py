"""
Native MCP implementation for managing product features via metaobjects
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from ..base import BaseMCPTool, ShopifyClient

class ManageFeaturesMetaobjectsTool(BaseMCPTool):
    """Manage product features using Shopify metaobjects"""
    
    name = "manage_features_metaobjects"
    description = "Manage product features using Shopify metaobjects"
    context = """
    Manages product features box using Shopify metaobjects for rich content.
    
    Features:
    - List current features
    - Add new features with text and optional images
    - Update existing features
    - Remove features
    - Reorder features
    - Clear all features
    
    Feature format:
    - Title: **Bold title**
    - Description: Supporting text
    - Image: Optional product feature image
    
    Actions:
    - list: Show current features
    - add: Add new feature
    - update: Update existing feature by position
    - remove: Remove feature by position
    - reorder: Change feature order
    - clear: Remove all features
    
    Metaobject structure:
    - Type: product_features_block
    - Fields: text (rich text), image (optional)
    - Storage: content.features_box metafield
    
    Use cases:
    - Product spec highlights
    - Key selling points
    - Technical features
    - Benefits and advantages
    
    Note: Features are stored as metaobject references for rich editing.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "add", "update", "remove", "reorder", "clear"],
                "description": "Action to perform"
            },
            "product": {
                "type": "string",
                "description": "Product identifier (ID, handle, SKU, title)"
            },
            "title": {
                "type": "string",
                "description": "Feature title (for add/update)"
            },
            "description": {
                "type": "string",
                "description": "Feature description (for add/update)"
            },
            "position": {
                "type": "integer",
                "description": "Feature position (1-based, for update/remove)"
            },
            "image_id": {
                "type": "string",
                "description": "Image ID (gid://shopify/MediaImage/123)"
            },
            "order": {
                "type": "string",
                "description": "New order (comma-separated positions, e.g., '3,1,2,4')"
            }
        },
        "required": ["action", "product"]
    }
    
    async def execute(self, action: str, product: str, **kwargs) -> Dict[str, Any]:
        """Execute features management action"""
        try:
            client = ShopifyClient()
            
            # Find product
            product_id = client.resolve_product_id(product)
            if not product_id:
                return {
                    "success": False,
                    "error": f"Product not found: {product}"
                }
            
            # Get current features
            current_features, metafield_id = await self._get_current_features(client, product_id)
            
            if action == "list":
                return await self._list_features(current_features)
            elif action == "add":
                return await self._add_feature(client, product_id, current_features, metafield_id, kwargs)
            elif action == "update":
                return await self._update_feature(client, current_features, kwargs)
            elif action == "remove":
                return await self._remove_feature(client, product_id, current_features, metafield_id, kwargs)
            elif action == "reorder":
                return await self._reorder_features(client, product_id, current_features, metafield_id, kwargs)
            elif action == "clear":
                return await self._clear_features(client, product_id, current_features)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    async def _get_current_features(self, client: ShopifyClient, product_id: str) -> Tuple[List[Dict], Optional[str]]:
        """Get current features from metafield"""
        query = f'''{{
            product(id: "{product_id}") {{
                featuresMetafield: metafield(namespace: "content", key: "features_box") {{
                    id
                    value
                    references(first: 50) {{
                        edges {{
                            node {{
                                __typename
                                ... on Metaobject {{
                                    id
                                    type
                                    fields {{
                                        key
                                        value
                                        type
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}'''
        
        result = client.execute_graphql(query)
        
        if 'errors' in result:
            return [], None
        
        metafield = result.get('data', {}).get('product', {}).get('featuresMetafield')
        if not metafield:
            return [], None
        
        features = []
        for edge in metafield.get('references', {}).get('edges', []):
            node = edge['node']
            if node['__typename'] == 'Metaobject':
                feature = {'id': node['id'], 'fields': {}}
                for field in node['fields']:
                    feature['fields'][field['key']] = {
                        'value': field['value'],
                        'type': field['type']
                    }
                features.append(feature)
        
        return features, metafield.get('id')
    
    async def _list_features(self, features: List[Dict]) -> Dict[str, Any]:
        """List current features"""
        if not features:
            return {
                "success": True,
                "features": [],
                "count": 0,
                "message": "No features found"
            }
        
        formatted_features = []
        for i, feature in enumerate(features, 1):
            text = feature['fields'].get('text', {}).get('value', '')
            image_id = feature['fields'].get('image', {}).get('value')
            
            # Parse title and description
            lines = text.split('\n', 1)
            title = lines[0].replace('**', '').strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            
            formatted_features.append({
                "position": i,
                "id": feature['id'],
                "title": title,
                "description": description,
                "image_id": image_id,
                "raw_text": text
            })
        
        return {
            "success": True,
            "features": formatted_features,
            "count": len(features)
        }
    
    async def _add_feature(self, client: ShopifyClient, product_id: str, 
                          current_features: List[Dict], metafield_id: Optional[str], 
                          kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new feature"""
        title = kwargs.get('title')
        description = kwargs.get('description', '')
        image_id = kwargs.get('image_id')
        
        if not title:
            return {
                "success": False,
                "error": "title is required for add action"
            }
        
        # Format text
        text = self._format_feature_text(title, description)
        
        # Create metaobject
        metaobject_id = await self._create_feature_metaobject(client, text, image_id)
        if not metaobject_id:
            return {
                "success": False,
                "error": "Failed to create feature metaobject"
            }
        
        # Update metafield
        metaobject_ids = [f['id'] for f in current_features] + [metaobject_id]
        
        if await self._update_features_metafield(client, product_id, metaobject_ids):
            return {
                "success": True,
                "message": f"Added feature: {title}",
                "feature_id": metaobject_id,
                "position": len(current_features) + 1
            }
        else:
            return {
                "success": False,
                "error": "Failed to update features metafield"
            }
    
    async def _update_feature(self, client: ShopifyClient, current_features: List[Dict], 
                             kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing feature"""
        position = kwargs.get('position')
        title = kwargs.get('title')
        description = kwargs.get('description', '')
        image_id = kwargs.get('image_id')
        
        if not position or not title:
            return {
                "success": False,
                "error": "position and title are required for update action"
            }
        
        # Convert to 0-indexed
        pos_index = position - 1
        if pos_index < 0 or pos_index >= len(current_features):
            return {
                "success": False,
                "error": f"Invalid position {position}. Must be between 1 and {len(current_features)}"
            }
        
        # Format text
        text = self._format_feature_text(title, description)
        
        # Update metaobject
        metaobject_id = current_features[pos_index]['id']
        if await self._update_feature_metaobject(client, metaobject_id, text, image_id):
            return {
                "success": True,
                "message": f"Updated feature at position {position}",
                "feature_id": metaobject_id
            }
        else:
            return {
                "success": False,
                "error": "Failed to update feature metaobject"
            }
    
    async def _remove_feature(self, client: ShopifyClient, product_id: str,
                             current_features: List[Dict], metafield_id: Optional[str],
                             kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a feature"""
        position = kwargs.get('position')
        
        if not position:
            return {
                "success": False,
                "error": "position is required for remove action"
            }
        
        # Convert to 0-indexed
        pos_index = position - 1
        if pos_index < 0 or pos_index >= len(current_features):
            return {
                "success": False,
                "error": f"Invalid position {position}. Must be between 1 and {len(current_features)}"
            }
        
        # Remove from list
        removed_feature = current_features.pop(pos_index)
        
        # Update metafield
        metaobject_ids = [f['id'] for f in current_features]
        
        if await self._update_features_metafield(client, product_id, metaobject_ids):
            # Delete the metaobject
            await self._delete_feature_metaobject(client, removed_feature['id'])
            
            return {
                "success": True,
                "message": f"Removed feature at position {position}",
                "removed_feature_id": removed_feature['id']
            }
        else:
            return {
                "success": False,
                "error": "Failed to update features metafield"
            }
    
    async def _reorder_features(self, client: ShopifyClient, product_id: str,
                               current_features: List[Dict], metafield_id: Optional[str],
                               kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Reorder features"""
        order = kwargs.get('order')
        
        if not order:
            return {
                "success": False,
                "error": "order is required for reorder action"
            }
        
        try:
            # Parse order string
            positions = [int(p.strip()) - 1 for p in order.split(',')]  # Convert to 0-indexed
            
            if len(positions) != len(current_features):
                return {
                    "success": False,
                    "error": f"Order must specify all {len(current_features)} positions"
                }
            
            # Validate positions
            if sorted(positions) != list(range(len(current_features))):
                return {
                    "success": False,
                    "error": "Order must contain each position exactly once"
                }
            
            # Reorder
            reordered_features = [current_features[i] for i in positions]
            metaobject_ids = [f['id'] for f in reordered_features]
            
            if await self._update_features_metafield(client, product_id, metaobject_ids):
                return {
                    "success": True,
                    "message": "Features reordered successfully",
                    "new_order": order
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update features metafield"
                }
                
        except ValueError:
            return {
                "success": False,
                "error": "Invalid order format. Use comma-separated numbers (e.g., '3,1,2,4')"
            }
    
    async def _clear_features(self, client: ShopifyClient, product_id: str,
                             current_features: List[Dict]) -> Dict[str, Any]:
        """Clear all features"""
        # Delete all metaobjects
        for feature in current_features:
            await self._delete_feature_metaobject(client, feature['id'])
        
        # Update metafield with empty list
        if await self._update_features_metafield(client, product_id, []):
            return {
                "success": True,
                "message": f"Cleared {len(current_features)} features",
                "cleared_count": len(current_features)
            }
        else:
            return {
                "success": False,
                "error": "Failed to clear features metafield"
            }
    
    def _format_feature_text(self, title: str, description: str = "") -> str:
        """Format feature text"""
        if description:
            return f"**{title}**  \n{description}"
        else:
            return f"**{title}**"
    
    async def _get_metaobject_definition_id(self, client: ShopifyClient) -> Optional[str]:
        """Get metaobject definition ID for product_features_block"""
        query = '''
        {
            metaobjectDefinitions(first: 100) {
                edges {
                    node {
                        id
                        type
                    }
                }
            }
        }
        '''
        
        result = client.execute_graphql(query)
        
        if 'errors' in result:
            return None
        
        edges = result.get('data', {}).get('metaobjectDefinitions', {}).get('edges', [])
        for edge in edges:
            if edge['node']['type'] == 'product_features_block':
                return edge['node']['id']
        
        return None
    
    async def _create_feature_metaobject(self, client: ShopifyClient, text: str, 
                                        image_id: Optional[str] = None) -> Optional[str]:
        """Create a new feature metaobject"""
        fields = [{"key": "text", "value": text}]
        
        if image_id:
            fields.append({"key": "image", "value": image_id})
        
        mutation = """
        mutation createMetaobject($metaobject: MetaobjectCreateInput!) {
            metaobjectCreate(metaobject: $metaobject) {
                metaobject {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "metaobject": {
                "type": "product_features_block",
                "fields": fields
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if 'errors' in result:
            return None
        
        user_errors = result.get('data', {}).get('metaobjectCreate', {}).get('userErrors', [])
        if user_errors:
            return None
        
        metaobject = result.get('data', {}).get('metaobjectCreate', {}).get('metaobject')
        return metaobject['id'] if metaobject else None
    
    async def _update_feature_metaobject(self, client: ShopifyClient, metaobject_id: str, 
                                        text: str, image_id: Optional[str] = None) -> bool:
        """Update an existing feature metaobject"""
        fields = [{"key": "text", "value": text}]
        
        if image_id:
            fields.append({"key": "image", "value": image_id})
        
        mutation = """
        mutation updateMetaobject($id: ID!, $metaobject: MetaobjectUpdateInput!) {
            metaobjectUpdate(id: $id, metaobject: $metaobject) {
                metaobject {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "id": metaobject_id,
            "metaobject": {
                "fields": fields
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if 'errors' in result:
            return False
        
        user_errors = result.get('data', {}).get('metaobjectUpdate', {}).get('userErrors', [])
        return len(user_errors) == 0
    
    async def _delete_feature_metaobject(self, client: ShopifyClient, metaobject_id: str) -> bool:
        """Delete a feature metaobject"""
        mutation = """
        mutation deleteMetaobject($id: ID!) {
            metaobjectDelete(id: $id) {
                deletedId
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {"id": metaobject_id}
        
        result = client.execute_graphql(mutation, variables)
        
        if 'errors' in result:
            return False
        
        user_errors = result.get('data', {}).get('metaobjectDelete', {}).get('userErrors', [])
        return len(user_errors) == 0
    
    async def _update_features_metafield(self, client: ShopifyClient, product_id: str, 
                                        metaobject_ids: List[str]) -> bool:
        """Update features metafield with metaobject references"""
        mutation = """
        mutation setMetafield($input: [MetafieldsSetInput!]!) {
            metafieldsSet(metafields: $input) {
                metafields {
                    id
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
                "ownerId": product_id,
                "namespace": "content",
                "key": "features_box",
                "type": "list.mixed_reference",
                "value": json.dumps(metaobject_ids)
            }]
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if 'errors' in result:
            return False
        
        user_errors = result.get('data', {}).get('metafieldsSet', {}).get('userErrors', [])
        return len(user_errors) == 0
    
    async def test(self) -> Dict[str, Any]:
        """Test features metaobjects management"""
        try:
            client = ShopifyClient()
            
            # Test getting metaobject definition
            definition_id = await self._get_metaobject_definition_id(client)
            
            if definition_id:
                return {
                    "status": "passed",
                    "message": "Features metaobjects tool ready"
                }
            else:
                return {
                    "status": "failed",
                    "error": "product_features_block metaobject definition not found"
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }