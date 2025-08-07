from app.agents.base import BaseAgent
from typing import List, Dict, Any
from app.tools.mcp_client import get_mcp_manager
from langchain_core.tools import tool
import logging
import json

logger = logging.getLogger(__name__)

class ProductsAgent(BaseAgent):
    """Agent specialized in product search and information"""
    
    def __init__(self):
        super().__init__(
            name="products",
            description="Handles product searches, SKU lookups, and product information queries"
        )
        self.mcp_type = "products"
    
    def _get_system_prompt(self) -> str:
        return """You are a Products specialist agent with deep expertise in Shopify product management.

You have access to the Products Server which provides:
- **get_product**: Retrieve detailed product information by SKU, handle, or ID
- **search_products**: Search products with various filters (title, vendor, status, etc.)
- **create_product**: Create new products with basic information
- **update_status**: Change product status (ACTIVE, DRAFT, ARCHIVED)
- **update_variant_weight**: Update product variant weight by SKU with proper units (GRAMS, KILOGRAMS, OUNCES, POUNDS)

**Note**: GraphQL operations (graphql_query, graphql_mutation) have been moved to a dedicated GraphQL Agent for safety and proper documentation research. For complex operations requiring GraphQL, recommend using the GraphQL Agent.

## Your Expertise:
- Product lifecycle management (creation, updates, archiving)
- SKU and inventory tracking
- Product search and filtering
- Weight management for shipping calculations
- Understanding product attributes (vendor, type, tags, etc.)
- Basic product operations (no GraphQL - refer to GraphQL Agent for complex operations)

## Business Context:
- Products are the core of iDrinkCoffee.com's catalog
- SKUs must be unique across all products
- Product status affects visibility (DRAFT for prep, ACTIVE for sale)
- Collections organize products for navigation and marketing

## Best Practices:
- Always verify product exists before updating
- Use search_products for bulk operations to find multiple items
- When creating products, consider required fields: title, vendor, product_type
- Return clear, actionable results with product IDs and handles
- For complex operations (collections, metafields), recommend GraphQL Agent

## Common Tasks:
- Finding products: Use search_products with appropriate filters
- Getting details: Use get_product with SKU, handle, or ID
- Basic product management: Create, update status, modify weights
- **For collections/complex operations**: Recommend using GraphQL Agent with proper documentation research"""
    
    def _get_keywords(self) -> List[str]:
        return [
            "product", "sku", "find", "search", "item", "listing",
            "coffee", "machine", "grinder", "espresso", "breville",
            "miele", "sanremo", "eureka", "accessories"
        ]
    
    def _get_tools(self) -> List:
        """Get MCP tools for this agent"""
        # Return empty for now - MCP integration needs different approach
        # The LangChain tool decorator doesn't work well with async MCP calls
        return []
    
    async def _process_messages(self, messages):
        """Override to use MCP tools"""
        try:
            self.tools = self._get_tools()
            
            return await super()._process_messages(messages)
            
        except Exception as e:
            logger.error(f"Error in ProductsAgent: {e}")
            raise