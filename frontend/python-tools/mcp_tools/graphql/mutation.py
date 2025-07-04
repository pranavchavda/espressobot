"""
Native MCP implementation for GraphQL mutations
"""

import json
from typing import Dict, Any, Optional
from ..base import BaseMCPTool, ShopifyClient

class GraphQLMutationTool(BaseMCPTool):
    """Execute GraphQL mutations on Shopify Admin API"""
    
    name = "graphql_mutation"
    description = "Execute GraphQL mutations on Shopify Admin API"
    context = """
    Executes raw GraphQL mutations against the Shopify Admin API.
    
    This is a powerful tool for:
    - Custom mutations not covered by other tools
    - Bulk operations
    - Complex updates requiring specific mutation structure
    - Testing GraphQL mutations
    
    The tool automatically handles:
    - Authentication
    - User error checking
    - Mutation cost tracking
    
    IMPORTANT:
    - Always check userErrors in the response
    - Mutations can modify data - use with caution
    - Test mutations in development first
    
    Examples:
    - Add tags: tagsAdd mutation
    - Update product: productUpdate mutation
    - Bulk operations: Use appropriate bulk mutations
    
    Note: Prefer specialized tools (update_pricing, manage_tags) for common operations.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "mutation": {
                "type": "string",
                "description": "GraphQL mutation string"
            },
            "variables": {
                "type": "object",
                "description": "Mutation variables (optional)",
                "additionalProperties": True
            }
        },
        "required": ["mutation"]
    }
    
    async def execute(self, mutation: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL mutation"""
        try:
            client = ShopifyClient()
            
            # Execute the mutation
            result = client.execute_graphql(mutation, variables)
            
            # Check for user errors in common mutation response patterns
            user_errors = []
            data = result.get("data", {})
            
            # Check for userErrors in any mutation response
            for key, value in data.items():
                if isinstance(value, dict) and "userErrors" in value:
                    user_errors.extend(value["userErrors"])
            
            return {
                "success": True,
                "data": data,
                "userErrors": user_errors,
                "hasErrors": len(user_errors) > 0,
                "extensions": result.get("extensions", {}),
                "mutation_cost": result.get("extensions", {}).get("cost", {}).get("actualQueryCost", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "mutation": mutation,
                "variables": variables
            }
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool with a safe query (not a mutation)"""
        try:
            # Use a query for testing, not an actual mutation
            query = "{ shop { name } }"
            client = ShopifyClient()
            result = client.execute_graphql(query)
            
            return {
                "status": "passed",
                "message": "GraphQL mutation tool ready"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }