"""
Native MCP implementation for managing URL redirects
"""

from typing import Dict, Any, List, Optional
from ..base import BaseMCPTool, ShopifyClient

class ManageRedirectsTool(BaseMCPTool):
    """Manage URL redirects in Shopify store"""
    
    name = "manage_redirects"
    description = "Create, list, or delete URL redirects in the Shopify store"
    context = """
    Manages URL redirects for SEO and user experience:
    
    Actions:
    - create: Create a new redirect
    - list: List existing redirects
    - delete: Remove a redirect
    
    Use cases:
    - Redirect old product URLs to new ones
    - Handle discontinued products
    - Fix broken links from external sites
    - Implement marketing campaign redirects
    - Maintain SEO when changing URL structure
    
    Important:
    - Paths should start with "/" (e.g., "/old-product")
    - Targets can be relative ("/new-product") or absolute
    - Redirects are permanent (301) by default
    - Cannot create circular redirects
    - Maximum 10,000 redirects per store
    
    Examples:
    - Old product: /products/old-name → /products/new-name
    - Collection move: /collections/old → /collections/new
    - Marketing: /promo → /collections/sale
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "delete"],
                "description": "Action to perform"
            },
            "from_path": {
                "type": "string",
                "description": "Source path to redirect from (for create)"
            },
            "to_path": {
                "type": "string",
                "description": "Target path to redirect to (for create)"
            },
            "redirect_id": {
                "type": "string",
                "description": "Redirect ID for deletion"
            },
            "limit": {
                "type": "integer",
                "description": "Limit for listing redirects (default: 50)",
                "default": 50
            }
        },
        "required": ["action"]
    }
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute redirect management action"""
        try:
            client = ShopifyClient()
            
            if action == "create":
                from_path = kwargs.get('from_path')
                to_path = kwargs.get('to_path')
                
                if not from_path or not to_path:
                    return {
                        "success": False,
                        "error": "Both from_path and to_path are required for create action"
                    }
                
                return await self._create_redirect(client, from_path, to_path)
                
            elif action == "list":
                limit = kwargs.get('limit', 50)
                return await self._list_redirects(client, limit)
                
            elif action == "delete":
                redirect_id = kwargs.get('redirect_id')
                
                if not redirect_id:
                    return {
                        "success": False,
                        "error": "redirect_id is required for delete action"
                    }
                
                return await self._delete_redirect(client, redirect_id)
                
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
    
    async def _create_redirect(self, client: ShopifyClient, from_path: str, to_path: str) -> Dict[str, Any]:
        """Create a URL redirect"""
        mutation = """
        mutation createUrlRedirect($redirect: UrlRedirectInput!) {
            urlRedirectCreate(urlRedirect: $redirect) {
                urlRedirect {
                    id
                    path
                    target
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "redirect": {
                "path": from_path,
                "target": to_path
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        # Check for errors
        if result.get('data', {}).get('urlRedirectCreate', {}).get('userErrors'):
            errors = result['data']['urlRedirectCreate']['userErrors']
            return {
                "success": False,
                "error": f"Failed to create redirect: {errors}"
            }
        
        redirect = result.get('data', {}).get('urlRedirectCreate', {}).get('urlRedirect')
        if redirect:
            return {
                "success": True,
                "redirect": {
                    "id": redirect['id'],
                    "path": redirect['path'],
                    "target": redirect['target']
                },
                "message": f"Successfully created redirect from {from_path} to {to_path}"
            }
        
        return {
            "success": False,
            "error": "Failed to create redirect"
        }
    
    async def _list_redirects(self, client: ShopifyClient, limit: int) -> Dict[str, Any]:
        """List URL redirects"""
        query = """
        query listRedirects($first: Int!) {
            urlRedirects(first: $first) {
                edges {
                    node {
                        id
                        path
                        target
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """
        
        variables = {"first": limit}
        
        result = client.execute_graphql(query, variables)
        
        if result and 'data' in result and result['data'].get('urlRedirects'):
            redirects = []
            for edge in result['data']['urlRedirects']['edges']:
                redirects.append(edge['node'])
            
            return {
                "success": True,
                "redirects": redirects,
                "count": len(redirects),
                "has_more": result['data']['urlRedirects']['pageInfo']['hasNextPage']
            }
        
        return {
            "success": False,
            "error": "Failed to list redirects"
        }
    
    async def _delete_redirect(self, client: ShopifyClient, redirect_id: str) -> Dict[str, Any]:
        """Delete a URL redirect"""
        # Ensure proper GID format
        if not redirect_id.startswith("gid://"):
            redirect_id = f"gid://shopify/UrlRedirect/{redirect_id}"
        
        mutation = """
        mutation deleteUrlRedirect($id: ID!) {
            urlRedirectDelete(id: $id) {
                deletedUrlRedirectId
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {"id": redirect_id}
        
        result = client.execute_graphql(mutation, variables)
        
        # Check for errors
        if result.get('data', {}).get('urlRedirectDelete', {}).get('userErrors'):
            errors = result['data']['urlRedirectDelete']['userErrors']
            return {
                "success": False,
                "error": f"Failed to delete redirect: {errors}"
            }
        
        if result.get('data', {}).get('urlRedirectDelete', {}).get('deletedUrlRedirectId'):
            return {
                "success": True,
                "message": f"Successfully deleted redirect: {redirect_id}",
                "deleted_id": redirect_id
            }
        
        return {
            "success": False,
            "error": "Failed to delete redirect"
        }
    
    async def test(self) -> Dict[str, Any]:
        """Test redirect management capability"""
        try:
            client = ShopifyClient()
            # Test with a simple query
            query = """
            {
                urlRedirects(first: 1) {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
            """
            result = client.execute_graphql(query)
            
            if result and 'data' in result:
                return {
                    "status": "passed",
                    "message": "Redirect management tool ready"
                }
            else:
                return {
                    "status": "failed",
                    "error": "Could not query redirects"
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }