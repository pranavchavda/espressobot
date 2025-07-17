#!/usr/bin/env python3
"""
MCP Inventory Server - Specialized server for inventory and catalog management
Includes: manage_inventory_policy, manage_tags, manage_redirects
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

# Import only the inventory-related tools
from mcp_tools.inventory.manage_policy import ManageInventoryPolicyTool
from mcp_tools.products.manage_tags import ManageTagsTool
from mcp_tools.store.manage_redirects import ManageRedirectsTool


class InventoryMCPServer(EnhancedMCPServer):
    """Specialized MCP server for inventory and catalog management"""
    
    def __init__(self):
        super().__init__("espressobot-inventory", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only inventory-related tools"""
        self.add_tool(ManageInventoryPolicyTool())
        self.add_tool(ManageTagsTool())
        self.add_tool(ManageRedirectsTool())
        
    def _setup_resources(self):
        """Setup inventory-related resources"""
        # Resource for inventory policies
        policy_resource = MCPResource(
            name="inventory_policies",
            uri="inventory://policies",
            description="Inventory policy guidelines and best practices",
            mime_type="text/markdown"
        )
        
        @policy_resource.getter
        def get_policies():
            return """# Inventory Management Policies

## Inventory Policy Options

### DENY (Default)
- Prevents overselling
- Customers cannot buy when out of stock
- Use for: Physical inventory, limited stock items
- Best for: Most physical products

### ALLOW/CONTINUE
- Allows overselling
- Customers can buy even when out of stock
- Use for: Pre-orders, made-to-order items, digital products
- Requires clear messaging in product description

## When to Use Each Policy

### Use DENY for:
- Physical inventory items
- Limited edition products
- Seasonal items with fixed quantities
- Items with supply chain constraints

### Use ALLOW for:
- Pre-order campaigns
- Made-to-order products
- Digital downloads
- Services
- Items with guaranteed restocking

## Best Practices
- Always check current inventory levels before changing policy
- Update product descriptions to reflect policy changes
- Monitor oversold items when using ALLOW policy
- Set up alerts for low stock items
"""
        
        self.add_resource(policy_resource)
        
        # Resource for tagging standards
        tagging_resource = MCPResource(
            name="tagging_standards",
            uri="inventory://tagging-standards",
            description="Product tagging standards and conventions",
            mime_type="application/json"
        )
        
        @tagging_resource.getter
        def get_tagging_standards():
            return {
                "categories": [
                    "espresso-machines", "grinders", "fresh-coffee",
                    "accessories", "parts", "cleaning-supplies"
                ],
                "features": [
                    "programmable", "automatic", "manual", "commercial",
                    "home-use", "portable", "built-in", "countertop"
                ],
                "promotions": [
                    "sale", "new-arrival", "bestseller", "discontinued",
                    "clearance", "map-sale", "seasonal"
                ],
                "attributes": [
                    "burr-grinder", "blade-grinder", "single-serve",
                    "espresso-compatible", "dishwasher-safe"
                ],
                "vendors": [
                    "breville", "delonghi", "jura", "rocket", "gaggia",
                    "baratza", "eureka", "mazzer", "fellow", "hario"
                ],
                "conventions": {
                    "format": "lowercase with hyphens",
                    "examples": "espresso-machine not Espresso Machine",
                    "avoid": "spaces, underscores, special characters"
                }
            }
        
        self.add_resource(tagging_resource)
        
        # Resource for redirect patterns
        redirect_resource = MCPResource(
            name="redirect_patterns",
            uri="inventory://redirect-patterns",
            description="Common redirect patterns and URL structures",
            mime_type="text/markdown"
        )
        
        @redirect_resource.getter
        def get_redirect_patterns():
            return """# Redirect Patterns

## Common Redirect Types

### Product Redirects
- Old product URLs to new ones
- Discontinued products to similar alternatives
- Changed product handles

### Collection Redirects
- Category restructuring
- Seasonal collection changes
- Brand page moves

### Campaign Redirects
- Marketing campaign URLs
- Promotional short links
- Social media campaign links

## URL Structure Guidelines

### Product URLs
- Format: `/products/{handle}`
- Example: `/products/breville-barista-express`

### Collection URLs
- Format: `/collections/{handle}`
- Example: `/collections/espresso-machines`

### Campaign URLs
- Format: `/campaigns/{campaign-name}`
- Example: `/campaigns/black-friday-2025`

## Best Practices
- Use 301 redirects for permanent changes
- Test redirects before implementing
- Monitor redirect performance
- Clean up expired campaign redirects
- Document redirect reasons for future reference

## Common Patterns
```
Old: /products/old-product-name
New: /products/new-product-name

Old: /collections/old-category
New: /collections/new-category

Old: /promo/special-offer
New: /collections/sale
```
"""
        
        self.add_resource(redirect_resource)
        
    def _setup_prompts(self):
        """Setup inventory-related prompts"""
        # Prompt for bulk tag management
        tag_prompt = MCPPrompt(
            name="bulk_tag_management",
            description="Add or remove tags from multiple products",
            arguments=[
                {"name": "action", "description": "add or remove"},
                {"name": "tag", "description": "Tag to add or remove"},
                {"name": "products", "description": "Product identifiers (comma-separated)"}
            ]
        )
        
        @tag_prompt.handler
        def handle_bulk_tags(action: str, tag: str, products: str):
            product_list = [p.strip() for p in products.split(',')]
            return f"""{action.title()} tag "{tag}" for multiple products:

Target products: {len(product_list)} items
Products: {', '.join(product_list)}

Steps:
1. Verify tag follows naming conventions (lowercase, hyphens)
2. For each product:
   - Use search_products to find the product
   - Use manage_tags to {action} the tag
3. Report success/failure for each product

Tag validation:
- Current tag: "{tag}"
- Format check: {'✅' if tag.replace('-', '').replace('_', '').isalnum() else '❌'}
- Convention: {'✅' if tag.islower() and ' ' not in tag else '❌'}

Proceed with bulk tag {action}?"""
        
        self.add_prompt(tag_prompt)
        
        # Prompt for inventory policy review
        policy_prompt = MCPPrompt(
            name="inventory_policy_review",
            description="Review and update inventory policies for products",
            arguments=[
                {"name": "vendor", "description": "Vendor to review (optional)"},
                {"name": "product_type", "description": "Product type to review (optional)"}
            ]
        )
        
        @policy_prompt.handler
        def handle_policy_review(vendor: str = None, product_type: str = None):
            filters = []
            if vendor:
                filters.append(f"vendor: {vendor}")
            if product_type:
                filters.append(f"product_type: {product_type}")
            
            filter_text = f" ({', '.join(filters)})" if filters else ""
            
            return f"""Review inventory policies for products{filter_text}:

Review Process:
1. Search for products matching criteria
2. For each product:
   - Check current inventory policy
   - Review inventory levels
   - Assess if policy is appropriate
3. Recommend policy changes:
   - DENY: For physical inventory items
   - ALLOW: For pre-orders, made-to-order, digital items

Policy Guidelines:
- Physical products with limited stock → DENY
- Pre-orders and made-to-order items → ALLOW
- Digital products and services → ALLOW
- Seasonal items with fixed quantities → DENY

Start policy review?"""
        
        self.add_prompt(policy_prompt)
        
        # Prompt for redirect cleanup
        redirect_prompt = MCPPrompt(
            name="redirect_cleanup",
            description="Review and clean up expired or unnecessary redirects",
            arguments=[
                {"name": "pattern", "description": "URL pattern to review (optional)"}
            ]
        )
        
        @redirect_prompt.handler
        def handle_redirect_cleanup(pattern: str = None):
            pattern_text = f" matching '{pattern}'" if pattern else ""
            
            return f"""Clean up redirects{pattern_text}:

Cleanup Process:
1. List all current redirects
2. Review each redirect:
   - Check if source URL still receives traffic
   - Verify target URL is still valid
   - Identify expired campaign redirects
3. Remove unnecessary redirects:
   - Expired campaigns
   - Broken target URLs
   - Duplicate redirects

Common Cleanup Targets:
- Campaign URLs from previous seasons
- Product redirects to discontinued items
- Collection redirects to empty collections
- Temporary promotional redirects

Start redirect cleanup?"""
        
        self.add_prompt(redirect_prompt)


if __name__ == "__main__":
    server = InventoryMCPServer()
    asyncio.run(server.run())