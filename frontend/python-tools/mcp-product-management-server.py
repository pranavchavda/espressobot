#!/usr/bin/env python3
"""
MCP Product Management Server - Specialized server for advanced product operations
Includes: create_full_product, update_full_product, add_variants_to_product, create_combo, create_open_box
Reduces token usage by ~82% compared to loading all 28 tools
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt

# Import only the product management tools
from mcp_tools.products.create_full import CreateFullProductTool
from mcp_tools.products.update_full import UpdateFullProductTool
from mcp_tools.products.add_variants import AddVariantsTool
from mcp_tools.products.create_combo import CreateComboTool
from mcp_tools.products.create_open_box import CreateOpenBoxTool

# Scratchpad functionality
from mcp_scratchpad_tool import SCRATCHPAD_TOOLS


class ProductManagementMCPServer(EnhancedMCPServer):
    """Specialized MCP server for advanced product management"""
    
    def __init__(self):
        super().__init__("espressobot-product-management", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only product management tools"""
        # Add the product management tools
        self.add_tool(CreateFullProductTool())
        self.add_tool(UpdateFullProductTool())
        self.add_tool(AddVariantsTool())
        self.add_tool(CreateComboTool())
        self.add_tool(CreateOpenBoxTool())
        
        
        # Add scratchpad tools
        for tool_def in SCRATCHPAD_TOOLS:
            self.add_tool_from_def(tool_def)
    def _setup_resources(self):
        """Setup product management resources"""
        # Resource for product creation templates
        templates_resource = MCPResource(
            name="product_templates",
            uri="product-management://templates",
            description="Templates and examples for different product types",
            mime_type="text/markdown"
        )
        
        @templates_resource.getter
        def get_product_templates():
            return """# Product Creation Templates

## Espresso Machine Template
```json
{
  "title": "{Brand} {Model} {Type}",
  "vendor": "Brand Name",
  "product_type": "Espresso Machines",
  "price": "699.99",
  "cost": "350.00",
  "sku": "BRAND-MODEL-COLOR",
  "description": "Full HTML description...",
  "tags": ["espresso-machines", "automatic", "brand-name"],
  "tech_specs": {
    "Pressure": "15 bar",
    "Water Tank": "1.8L",
    "Power": "1350W"
  }
}
```

## Coffee Template
```json
{
  "title": "{Roaster} {Origin} {Process}",
  "vendor": "Roaster Name", 
  "product_type": "Fresh Coffee",
  "price": "19.99",
  "cost": "8.00",
  "sku": "ROASTER-ORIGIN-SIZE",
  "seasonal": true,
  "tags": ["fresh-coffee", "single-origin"]
}
```

## Grinder Template
```json
{
  "title": "{Brand} {Model} {Type} Grinder",
  "vendor": "Brand Name",
  "product_type": "Grinders", 
  "price": "299.99",
  "cost": "150.00",
  "tags": ["grinders", "burr-grinder", "electric"]
}
```
"""
        
        self.add_resource(templates_resource)
        
        # Resource for variant management
        variants_resource = MCPResource(
            name="variant_management",
            uri="product-management://variants",
            description="Guidelines for managing product variants",
            mime_type="text/markdown"
        )
        
        @variants_resource.getter
        def get_variant_guide():
            return """# Variant Management Guide

## When to Use Variants
- Different colors of same product
- Different sizes or capacities
- Different bundles or packages
- Regional model differences

## Variant Structure
- Each variant needs unique SKU
- Price can differ between variants
- Inventory tracked per variant
- Options define variant differences

## Option Values
- Color: Black, White, Stainless Steel
- Size: Small, Medium, Large
- Bundle: Machine Only, With Grinder, Starter Kit

## Best Practices
- Consistent naming conventions
- Logical option ordering
- Clear variant descriptions
- Proper inventory policies
"""
        
        self.add_resource(variants_resource)
        
        # Resource for combo and open box guidelines
        special_products_resource = MCPResource(
            name="special_products",
            uri="product-management://special",
            description="Guidelines for combo and open box products",
            mime_type="text/markdown"
        )
        
        @special_products_resource.getter
        def get_special_products_guide():
            return """# Special Product Types

## Combo Products
- Combine 2+ related products
- Offer discount vs buying separately
- Generate combined product images
- Use descriptive combo SKUs
- Format: COMBO-YYMM-SUFFIX

## Open Box Products
- Use for returned/display items
- Clear condition descriptions
- Appropriate pricing discounts
- Track with serial numbers
- Format: OB-YYMM-SERIAL-ORIGINALSKU

## Condition Descriptions
- **Excellent**: Near-new, minimal signs of use
- **Good**: Light wear, fully functional
- **Fair**: Moderate wear, cosmetic issues
- **Scratch & Dent**: Cosmetic damage only

## Pricing Guidelines
- Combo: 10-20% discount typical
- Open Box: 10-30% discount based on condition
- Consider market demand and inventory age
"""
        
        self.add_resource(special_products_resource)
        
    def _setup_prompts(self):
        """Setup product management prompts"""
        # Prompt for product creation workflow
        creation_workflow_prompt = MCPPrompt(
            name="product_creation_workflow",
            description="Step-by-step workflow for creating new products"
        )
        
        creation_workflow_prompt.arguments = [
            {"name": "product_info", "description": "Basic product information", "required": True},
            {"name": "product_type", "description": "Type of product being created", "required": True}
        ]
        
        @creation_workflow_prompt.handler
        def get_creation_workflow(product_info, product_type):
            return """# Product Creation Workflow

## Pre-Creation Checklist
1. Gather all product information
2. Verify vendor and product type
3. Research pricing and costs
4. Prepare product images
5. Draft product description

## Creation Process
1. Use create_full_product for comprehensive setup
2. Add variants if multiple options exist
3. Upload product images
4. Set up metafields (specs, FAQs, etc.)
5. Configure pricing and inventory

## Post-Creation Tasks
1. Review product for accuracy
2. Test product visibility
3. Check all images display correctly
4. Verify pricing calculations
5. Publish when ready

## Quality Assurance
- Spell check all text content
- Verify all links and images work
- Test on mobile and desktop
- Check SEO elements (title, description)
"""
        
        self.add_prompt(creation_workflow_prompt)
        
        # Prompt for bulk product updates
        bulk_update_prompt = MCPPrompt(
            name="bulk_product_updates",
            description="Guide for updating multiple products efficiently"
        )
        
        bulk_update_prompt.arguments = [
            {"name": "update_type", "description": "Type of update to perform", "required": True},
            {"name": "product_list", "description": "List of products to update", "required": True}
        ]
        
        @bulk_update_prompt.handler
        def get_bulk_update_guide(update_type, product_list):
            return """# Bulk Product Update Process

## Update Types
- **Pricing**: Update prices across product line
- **Images**: Add/replace product images
- **Content**: Update descriptions or specifications
- **Variants**: Add new color/size options
- **Metadata**: Update tags, metafields, etc.

## Execution Strategy
1. Group products by update type
2. Process in batches of 10-20 products
3. Use update_full_product for comprehensive changes
4. Monitor for errors and retry failures
5. Validate changes after completion

## Error Handling
- Log all successes and failures
- Retry failed updates with backoff
- Check for permission issues
- Verify data format correctness
- Report final summary to user
"""
        
        self.add_prompt(bulk_update_prompt)


async def main():
    server = ProductManagementMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())