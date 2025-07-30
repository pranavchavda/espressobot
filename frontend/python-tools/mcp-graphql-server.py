#!/usr/bin/env python3
"""
MCP GraphQL Server - Specialized server for Shopify GraphQL operations
Includes: graphql_query, graphql_mutation
Requires extensive documentation research before any execution
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt

# Import GraphQL tools
from mcp_tools.graphql.query import GraphQLQueryTool
from mcp_tools.graphql.mutation import GraphQLMutationTool

# Scratchpad functionality
from mcp_scratchpad_tool import SCRATCHPAD_TOOLS


class GraphQLMCPServer(EnhancedMCPServer):
    """Specialized MCP server for GraphQL operations"""
    
    def __init__(self):
        super().__init__("espressobot-graphql", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load GraphQL tools only"""
        # Add the 2 GraphQL tools
        self.add_tool(GraphQLQueryTool())
        self.add_tool(GraphQLMutationTool())
        
        # Add scratchpad tools
        for tool_def in SCRATCHPAD_TOOLS:
            self.add_tool_from_def(tool_def)
            
    def _setup_resources(self):
        """Setup GraphQL-related resources"""
        # Resource for GraphQL best practices
        graphql_resource = MCPResource(
            name="graphql_best_practices",
            uri="graphql://best_practices",
            description="GraphQL best practices and safety guidelines for Shopify Admin API",
            mime_type="text/markdown"
        )
        
        @graphql_resource.getter
        def get_graphql_guide():
            return """# GraphQL Best Practices for Shopify Admin API

## CRITICAL SAFETY PROTOCOLS

### NEVER Execute Without Documentation Research
1. **ALWAYS** research the schema first using documentation agent
2. **VERIFY** field names, types, and requirements
3. **UNDERSTAND** rate limits and cost implications
4. **VALIDATE** query structure before execution

## Query Guidelines

### Query Best Practices
- Use fragments for reusable field sets
- Request only needed fields to minimize cost
- Include proper error handling
- Respect GraphQL cost limits (1000 points default)

### Common Query Patterns
```graphql
# Product query with essential fields
query getProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    vendor
    productType
    status
    variants(first: 10) {
      edges {
        node {
          id
          sku
          price
          inventoryQuantity
        }
      }
    }
  }
}
```

## Mutation Guidelines

### Mutation Safety Rules
1. **TEST** with single items before bulk operations
2. **VERIFY** input structure matches schema
3. **CHECK** userErrors in response
4. **VALIDATE** results after execution

### Common Mutation Patterns
```graphql
# Product update mutation
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      status
    }
    userErrors {
      field
      message
    }
  }
}
```

## Error Handling
- Always check userErrors array
- Handle network timeouts gracefully
- Retry on rate limit errors with backoff
- Log all mutations for audit trail

## Cost Management
- Monitor query costs in response headers
- Use cost analysis before execution
- Implement cost limits per operation
- Cache expensive query results

## Schema Research Process
1. Use introspect_admin_schema to find types
2. Verify field availability and requirements
3. Check deprecation warnings
4. Understand relationship structures
5. Validate input types for mutations
"""

        self.add_resource(graphql_resource)
        
        # Resource for common GraphQL patterns
        patterns_resource = MCPResource(
            name="graphql_patterns",
            uri="graphql://patterns",
            description="Common GraphQL query and mutation patterns for Shopify",
            mime_type="text/markdown"
        )
        
        @patterns_resource.getter
        def get_patterns():
            return """# Common GraphQL Patterns

## Product Operations
- Product CRUD operations
- Variant management
- Inventory updates
- Price modifications

## Collection Operations
- Collection creation and updates
- Product assignment to collections
- Collection rule management

## Order Operations
- Order queries with filters
- Order status updates
- Fulfillment operations

## Customer Operations
- Customer data retrieval
- Customer group management
- Customer metafields

## Metafield Operations
- Setting product metafields
- Querying metafield values
- Metaobject management

## Bulk Operations
- Bulk query operations
- Staged upload mutations
- Background job monitoring
"""

        self.add_resource(patterns_resource)
        
    def _setup_prompts(self):
        """Setup GraphQL-specific prompts"""
        safety_prompt = MCPPrompt(
            name="graphql_safety_check",
            description="Safety checklist before executing GraphQL operations",
            arguments=[
                {
                    "name": "operation_type",
                    "description": "Type of GraphQL operation (query or mutation)",
                    "required": True
                },
                {
                    "name": "target_objects",
                    "description": "Objects being queried or modified",
                    "required": True
                }
            ]
        )
        
        @safety_prompt.handler
        def format_safety_check(operation_type, target_objects):
            return f"""
# GraphQL Safety Checklist

## Operation: {operation_type}
## Target: {target_objects}

### Pre-Execution Checklist:
- [ ] Schema research completed via documentation agent
- [ ] Field names and types verified
- [ ] Required vs optional fields identified
- [ ] Cost implications understood
- [ ] Error handling strategy defined
- [ ] Rate limits considered

### For Mutations Only:
- [ ] Input structure validated against schema
- [ ] Test data prepared for single-item test
- [ ] Rollback strategy defined
- [ ] User permissions verified

### Documentation Research Required:
1. Use introspect_admin_schema to find type definitions
2. Search for field requirements and constraints
3. Check for deprecation warnings
4. Understand relationship structures
5. Verify authentication requirements

**CRITICAL**: Never execute without completing this checklist!
"""
        
        self.add_prompt(safety_prompt)


async def main():
    """Main entry point"""
    server = GraphQLMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())