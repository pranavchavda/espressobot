"""
Native MCP implementation for GraphQL queries
"""

import json
from typing import Dict, Any, Optional
from ..base import BaseMCPTool, ShopifyClient

class GraphQLQueryTool(BaseMCPTool):
    """Execute GraphQL queries on Shopify Admin API"""
    
    name = "graphql_query"
    description = "Execute GraphQL queries on Shopify Admin API"
    context = """
    Executes raw GraphQL queries against the Shopify Admin API.
    
    This is a powerful tool for:
    - Custom queries not covered by other tools
    - Bulk data fetching with specific fields
    - Testing GraphQL queries
    - Advanced API operations
    
    The tool automatically handles:
    - Authentication
    - Error responses
    - Query cost tracking
    
    Examples:
    - Simple query: '{ shop { name } }'
    - With variables: Use the variables parameter
    - Get specific fields: Build custom queries
    
    Note: Prefer specialized tools (get_product, search_products) for common operations.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "GraphQL query string"
            },
            "variables": {
                "type": "object",
                "description": "Query variables (optional)",
                "additionalProperties": True
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        try:
            client = ShopifyClient()
            
            # Execute the query
            result = client.execute_graphql(query, variables)
            
            # Return the full result including data and extensions
            return {
                "success": True,
                "data": result.get("data", {}),
                "extensions": result.get("extensions", {}),
                "query_cost": result.get("extensions", {}).get("cost", {}).get("actualQueryCost", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "variables": variables
            }
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool with a simple query"""
        try:
            result = await self.execute("{ shop { name } }")
            if result["success"]:
                return {
                    "status": "passed",
                    "message": f"Shop name: {result['data'].get('shop', {}).get('name', 'Unknown')}"
                }
            else:
                return {
                    "status": "failed",
                    "error": result["error"]
                }
        except Exception as e:
            return {
                "status": "failed", 
                "error": str(e)
            }