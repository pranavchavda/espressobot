#!/usr/bin/env python3
"""
MCP Pricing Server - Specialized server for pricing operations
Only includes: update_pricing, bulk_price_update, update_costs
Reduces token usage by ~90% compared to loading all 28 tools
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt

# Import only the pricing-related tools
from mcp_tools.pricing.update import UpdatePricingTool
from mcp_tools.pricing.bulk_update import BulkPriceUpdateTool
from mcp_tools.pricing.update_costs import UpdateCostsTool

# Scratchpad functionality
from mcp_scratchpad_tool import SCRATCHPAD_TOOLS


class PricingMCPServer(EnhancedMCPServer):
    """Specialized MCP server for pricing operations"""
    
    def __init__(self):
        super().__init__("espressobot-pricing", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only pricing-related tools"""
        self.add_tool(UpdatePricingTool())
        self.add_tool(BulkPriceUpdateTool())
        self.add_tool(UpdateCostsTool())
        
        
        # Add scratchpad tools
        for tool_def in SCRATCHPAD_TOOLS:
            self.add_tool_from_def(tool_def)
    def _setup_resources(self):
        """Setup pricing-related resources"""
        # Resource for pricing rules
        rules_resource = MCPResource(
            name="pricing_rules",
            uri="pricing://rules",
            description="Business rules for pricing updates",
            mime_type="text/markdown"
        )
        
        @rules_resource.getter
        def get_rules():
            return """# Pricing Business Rules

## Discount Handling
- Always preserve original price in compare_at_price before discounting
- To show discount: compare_at_price > price
- To remove discount: Set price = compare_at_price, then clear compare_at_price

## MAP Pricing
- Use compare_at_price for MSRP
- Price must respect MAP agreements
- Never go below MAP without authorization

## Cost Updates
- Cost affects margin calculations
- Update costs when supplier prices change
- Cost is for internal tracking only

## Bulk Operations
- Group variants by product for efficiency
- Validate all prices before applying
- Report success/failure per product

## Price Formatting
- Always use string format (e.g., "19.99")
- Include two decimal places
- Currency is USD for iDrinkCoffee
"""
        
        self.add_resource(rules_resource)
        
        # Resource for current MAP schedules
        map_resource = MCPResource(
            name="map_schedules",
            uri="pricing://map-schedules",
            description="Current MAP pricing schedules",
            mime_type="application/json"
        )
        
        @map_resource.getter
        def get_map_schedules():
            # This would normally load from a database or file
            return {
                "breville": {
                    "active_sale": None,
                    "upcoming": [
                        {
                            "start": "2025-02-14",
                            "end": "2025-02-28",
                            "products": ["BES870XL", "BES878BSS"],
                            "discount": "15%"
                        }
                    ]
                },
                "miele": {
                    "active_sale": {
                        "start": "2025-01-15",
                        "end": "2025-01-31",
                        "products": ["CM5310", "CM6160"],
                        "map_prices": {
                            "CM5310": "849.00",
                            "CM6160": "1299.00"
                        }
                    }
                }
            }
        
        self.add_resource(map_resource)
        
    def _setup_prompts(self):
        """Setup pricing-related prompts"""
        # Prompt for sale pricing
        sale_prompt = MCPPrompt(
            name="apply_sale_discount",
            description="Apply a percentage discount to products",
            arguments=[
                {"name": "products", "description": "Comma-separated SKUs or 'all' for a search query"},
                {"name": "discount_percent", "description": "Discount percentage (e.g., 15 for 15% off)"},
                {"name": "preserve_original", "description": "Whether to preserve original price (true/false)", "default": "true"}
            ]
        )
        
        @sale_prompt.handler
        def handle_sale(products: str, discount_percent: str, preserve_original: str = "true"):
            return f"""Apply {discount_percent}% discount to products:

Target products: {products}

Steps:
1. First, get current prices for all products
2. Calculate new prices: original * (1 - {discount_percent}/100)
3. If preserve_original is true:
   - Set compare_at_price to current price (if not already set)
   - Set price to discounted amount
4. Use bulk_price_update for efficiency

Example calculation:
- Original: $100.00
- Discount: {discount_percent}%
- New price: ${100 * (1 - int(discount_percent)/100):.2f}
- Compare at: $100.00 (shows as strikethrough)

Proceed with applying the discount?"""
        
        self.add_prompt(sale_prompt)
        
        # Prompt for margin analysis
        margin_prompt = MCPPrompt(
            name="analyze_margins",
            description="Analyze profit margins for products",
            arguments=[
                {"name": "min_margin", "description": "Minimum acceptable margin percentage"}
            ]
        )
        
        @margin_prompt.handler
        def handle_margins(min_margin: str):
            return f"""Analyze products with margins below {min_margin}%:

Analysis steps:
1. Search for all active products
2. For each product:
   - Get current price and cost
   - Calculate margin: (price - cost) / price * 100
   - Flag if margin < {min_margin}%
3. Suggest price adjustments to meet minimum margin

Margin formula: (Price - Cost) / Price × 100

Would you like to search for low-margin products?"""
        
        self.add_prompt(margin_prompt)
        
        # Prompt for cost updates from supplier
        cost_prompt = MCPPrompt(
            name="supplier_cost_update",
            description="Update costs based on supplier price list",
            arguments=[
                {"name": "supplier", "description": "Supplier name"},
                {"name": "change_type", "description": "increase or decrease"},
                {"name": "change_percent", "description": "Percentage change (optional)"}
            ]
        )
        
        @cost_prompt.handler
        def handle_cost_update(supplier: str, change_type: str, change_percent: str = None):
            if change_percent:
                return f"""Update costs for {supplier} products ({change_percent}% {change_type}):

Steps:
1. Search for all products from vendor: {supplier}
2. For each product:
   - Get current cost
   - Calculate new cost: current * {1 + int(change_percent)/100 if change_type == 'increase' else 1 - int(change_percent)/100}
   - Update using update_costs tool
3. Track updated products and any failures

This will affect margin calculations but NOT selling prices.
Proceed with cost updates?"""
            else:
                return f"""Prepare for {supplier} cost {change_type}:

Please provide:
1. Specific SKUs and their new costs, or
2. A percentage change to apply to all {supplier} products

Current action: Ready to search for {supplier} products to update costs."""
        
        self.add_prompt(cost_prompt)


if __name__ == "__main__":
    server = PricingMCPServer()
    asyncio.run(server.run())