#!/usr/bin/env python3
"""
MCP Products Server - Specialized server for product operations and GraphQL
Includes: get_product, search_products, create_product, update_status, graphql_query, graphql_mutation
Reduces token usage by ~75% compared to loading all 28 tools
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt

# Import only the product-related tools
from mcp_tools.products.get import GetProductTool
from mcp_tools.products.search import SearchProductsTool
from mcp_tools.products.create import CreateProductTool
from mcp_tools.products.update_status import UpdateStatusTool
from mcp_tools.products.update_variant_weight import UpdateVariantWeightTool

# Import GraphQL tools for collections and advanced operations
from mcp_tools.graphql.query import GraphQLQueryTool
from mcp_tools.graphql.mutation import GraphQLMutationTool


class ProductsMCPServer(EnhancedMCPServer):
    """Specialized MCP server for product operations"""
    
    def __init__(self):
        super().__init__("espressobot-products", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only product-related tools"""
        # Add the 5 product tools
        self.add_tool(GetProductTool())
        self.add_tool(SearchProductsTool())
        self.add_tool(CreateProductTool())
        self.add_tool(UpdateStatusTool())
        self.add_tool(UpdateVariantWeightTool())
        
        # Add GraphQL tools for collections and advanced operations
        self.add_tool(GraphQLQueryTool())
        self.add_tool(GraphQLMutationTool())
        
    def _setup_resources(self):
        """Setup product-related resources"""
        # Resource for product creation guidelines
        resource = MCPResource(
            name="product_guidelines",
            uri="products://guidelines",
            description="Guidelines for creating and managing products",
            mime_type="text/markdown"
        )
        
        @resource.getter
        def get_guidelines():
            return """# Product Management Guidelines

## Product Creation
- Always include vendor, product type, and SKU
- Products start as DRAFT by default
- Use consistent naming conventions
- Include detailed descriptions

## Product Types
- Espresso Machines
- Grinders  
- Fresh Coffee
- Accessories
- Parts & Cleaning

## Status Options
- ACTIVE: Visible and purchasable
- DRAFT: Hidden for preparation
- ARCHIVED: Preserved but hidden

## Best Practices
- Verify SKU uniqueness before creation
- Set proper product type for filtering
- Add relevant tags for searchability
"""
        
        self.add_resource(resource)
        
        # Resource for vendor list
        vendor_resource = MCPResource(
            name="approved_vendors",
            uri="products://vendors",
            description="List of approved product vendors",
            mime_type="application/json"
        )
        
        @vendor_resource.getter
        def get_vendors():
            return {
                "vendors": [
                    "Breville", "DeLonghi", "Gaggia", "Jura", "Rocket",
                    "ECM", "Profitec", "Lelit", "Rancilio", "La Pavoni",
                    "Baratza", "Eureka", "Mazzer", "Ceado", "Niche",
                    "iDrinkCoffee", "Hario", "Fellow", "Acaia"
                ]
            }
        
        self.add_resource(vendor_resource)
        
    def _setup_prompts(self):
        """Setup product-related prompts"""
        # Prompt for bulk product status update
        prompt = MCPPrompt(
            name="bulk_status_update",
            description="Update status for multiple products",
            arguments=[
                {"name": "product_list", "description": "Comma-separated list of SKUs or handles"},
                {"name": "new_status", "description": "New status (ACTIVE, DRAFT, or ARCHIVED)"}
            ]
        )
        
        @prompt.handler
        def handle_bulk_status(product_list: str, new_status: str):
            products = [p.strip() for p in product_list.split(',')]
            return f"""Update the status of these products to {new_status}:

Products to update:
{chr(10).join(f'- {p}' for p in products)}

Steps:
1. Use search_products to verify each product exists
2. For each product, use update_status to set status to {new_status}
3. Confirm all updates completed successfully

Important: {new_status} products are {'visible to customers' if new_status == 'ACTIVE' else 'hidden from customers'}."""
        
        self.add_prompt(prompt)
        
        # Prompt for product research
        research_prompt = MCPPrompt(
            name="product_research",
            description="Research a product before adding to catalog",
            arguments=[
                {"name": "product_name", "description": "Name or model of the product"}
            ]
        )
        
        @research_prompt.handler
        def handle_research(product_name: str):
            return f"""Research {product_name} before adding to catalog:

1. First, use search_products to check if it already exists
2. If it doesn't exist, gather information about:
   - Full product name and model number
   - Vendor/manufacturer
   - Product type category
   - Key features and specifications
   
3. Prepare for product creation with:
   - Unique SKU
   - Proper vendor name from approved list
   - Accurate product type
   - Detailed description

Would you like me to search for existing {product_name} products first?"""
        
        self.add_prompt(research_prompt)


if __name__ == "__main__":
    server = ProductsMCPServer()
    asyncio.run(server.run())