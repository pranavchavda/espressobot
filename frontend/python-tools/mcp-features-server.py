#!/usr/bin/env python3
"""
MCP Features Server - Specialized server for product features and content management
Includes: manage_features_metaobjects, update_metafields, manage_variant_links
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

# Import only the features-related tools
from mcp_tools.features.manage_metaobjects import ManageFeaturesMetaobjectsTool
from mcp_tools.products.update_metafields import UpdateMetafieldsTool
from mcp_tools.products.manage_variant_links import ManageVariantLinksTool


class FeaturesMCPServer(EnhancedMCPServer):
    """Specialized MCP server for product features and content management"""
    
    def __init__(self):
        super().__init__("espressobot-features", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only features-related tools"""
        self.add_tool(ManageFeaturesMetaobjectsTool())
        self.add_tool(UpdateMetafieldsTool())
        self.add_tool(ManageVariantLinksTool())
        
    def _setup_resources(self):
        """Setup features-related resources"""
        # Resource for metafield structure
        metafield_resource = MCPResource(
            name="metafield_structure",
            uri="features://metafield-structure",
            description="Shopify metafield structure and best practices",
            mime_type="application/json"
        )
        
        @metafield_resource.getter
        def get_metafield_structure():
            return {
                "common_namespaces": {
                    "content": "Rich content like buy box, descriptions",
                    "specs": "Technical specifications",
                    "faq": "Frequently asked questions",
                    "new": "New fields and variant links"
                },
                "metafield_types": {
                    "single_line_text_field": "Short text values",
                    "multi_line_text_field": "Longer text with line breaks",
                    "json": "Structured data objects",
                    "rich_text": "HTML formatted content",
                    "metaobject_reference": "Reference to metaobjects",
                    "list.metaobject_reference": "List of metaobject references"
                },
                "common_metafields": {
                    "content.buy_box": {
                        "type": "multi_line_text_field",
                        "description": "Marketing copy for product pages"
                    },
                    "specs.technical": {
                        "type": "json",
                        "description": "Technical specifications object"
                    },
                    "faq.questions": {
                        "type": "json",
                        "description": "FAQ questions and answers"
                    },
                    "new.varLinks": {
                        "type": "list.product_reference",
                        "description": "Links to product variants"
                    },
                    "content.features_box": {
                        "type": "list.metaobject_reference",
                        "description": "Product features as metaobjects"
                    }
                },
                "best_practices": [
                    "Use consistent namespace naming",
                    "Choose appropriate metafield types",
                    "Validate JSON structure before saving",
                    "Test metafield display on storefront",
                    "Document custom metafields for team"
                ]
            }
        
        self.add_resource(metafield_resource)
        
        # Resource for feature writing guidelines
        features_resource = MCPResource(
            name="feature_writing_guidelines",
            uri="features://writing-guidelines",
            description="Guidelines for writing product features and descriptions",
            mime_type="text/markdown"
        )
        
        @features_resource.getter
        def get_feature_guidelines():
            return """# Product Feature Writing Guidelines

## Feature Box Guidelines

### Structure
- **Title**: Bold, concise benefit statement
- **Description**: 1-2 sentences explaining the feature
- **Image**: Optional visual to support the feature

### Writing Style
- Focus on benefits, not just features
- Use active voice
- Keep titles under 6 words
- Make descriptions scannable

### Examples

#### Good Features
- **Title**: **Precision Grinding**
- **Description**: Burr grinder ensures consistent particle size for perfect extraction every time.

- **Title**: **One-Touch Operation**
- **Description**: Single button activates the entire brewing process from grinding to steaming.

#### Poor Features
- **Title**: Has a grinder (too basic)
- **Description**: This machine includes a built-in grinder that grinds coffee beans (redundant)

## Content Categories

### Technical Features
- Specifications and capabilities
- Performance metrics
- Build quality details

### User Benefits
- Convenience improvements
- Quality enhancements
- Time-saving features

### Unique Selling Points
- Differentiators from competitors
- Exclusive features
- Award-winning elements

## Formatting Rules
- Use **bold** for feature titles
- Keep descriptions under 100 characters
- Use bullet points for multiple benefits
- Include relevant keywords for SEO

## Common Mistakes to Avoid
- Too technical without explaining benefits
- Redundant features (saying the same thing twice)
- Missing context (what does this mean for the user?)
- Poor grammar or spelling
- Features that aren't actually features
"""
        
        self.add_resource(features_resource)
        
        # Resource for variant linking strategy
        linking_resource = MCPResource(
            name="variant_linking_strategy",
            uri="features://variant-linking",
            description="Strategy for linking product variants",
            mime_type="text/markdown"
        )
        
        @linking_resource.getter
        def get_linking_strategy():
            return """# Variant Linking Strategy

## When to Link Products

### Same Model, Different Options
- Color variations (Black, White, Stainless)
- Size options (Small, Medium, Large)
- Configuration differences (Basic, Premium)

### Same Brand Family
- Different models in same series
- Upgraded versions
- Complementary products

## Linking Structure

### Bidirectional Links
- All linked products reference the same group
- Products include themselves in the link list
- Minimum 2 products for linking

### Metafield Structure
- **Namespace**: "new"
- **Key**: "varLinks"
- **Type**: list.product_reference
- **Value**: Array of product IDs

## Implementation Examples

### Breville Barista Express (3 colors)
- Black: Links to [Black, Stainless, Cranberry]
- Stainless: Links to [Black, Stainless, Cranberry]
- Cranberry: Links to [Black, Stainless, Cranberry]

### Miele Coffee Machine Series
- CM5310: Links to [CM5310, CM6160, CM6360]
- CM6160: Links to [CM5310, CM6160, CM6360]
- CM6360: Links to [CM5310, CM6160, CM6360]

## Best Practices

### Link Maintenance
- Update all products when adding/removing variants
- Verify links work in both directions
- Remove links when products are discontinued

### User Experience
- Group similar products for easy comparison
- Enable switching between variants
- Show clear differentiation between options

### Performance
- Use manage_variant_links for bulk operations
- Sync entire groups to maintain consistency
- Audit links regularly for broken references

## Common Use Cases
- Color/finish variations
- Size options
- Feature upgrades
- Regional differences
- Bundle variations
"""
        
        self.add_resource(linking_resource)
        
    def _setup_prompts(self):
        """Setup features-related prompts"""
        # Prompt for creating product features
        features_prompt = MCPPrompt(
            name="create_product_features",
            description="Create compelling product features for a product",
            arguments=[
                {"name": "product_id", "description": "Product identifier (SKU, handle, or ID)"},
                {"name": "feature_count", "description": "Number of features to create (default: 3)"}
            ]
        )
        
        @features_prompt.handler
        def handle_features(product_id: str, feature_count: str = "3"):
            return f"""Create {feature_count} compelling features for {product_id}:

Research Phase:
1. Get product details using product tools
2. Identify key specifications and benefits
3. Research similar products for differentiation
4. Review existing features (if any)

Feature Creation Process:
1. For each feature:
   - Write a bold, benefit-focused title (under 6 words)
   - Create a compelling description (1-2 sentences)
   - Focus on user benefits, not just specifications
   - Use active voice and clear language

Example Feature Structure:
- **Title**: **Precision Temperature Control**
- **Description**: Advanced PID system maintains optimal brewing temperature within 1°F for consistent extraction.

Quality Checklist:
□ Features focus on benefits, not just specs
□ Titles are concise and impactful
□ Descriptions are scannable and clear
□ No redundant or overlapping features
□ Proper grammar and spelling

Ready to create {feature_count} features for {product_id}?"""
        
        self.add_prompt(features_prompt)
        
        # Prompt for variant linking setup
        linking_prompt = MCPPrompt(
            name="setup_variant_linking",
            description="Set up variant links between related products",
            arguments=[
                {"name": "product_group", "description": "Product identifiers to link (comma-separated)"},
                {"name": "link_type", "description": "Type of link (color, size, model, etc.)"}
            ]
        )
        
        @linking_prompt.handler
        def handle_linking(product_group: str, link_type: str):
            products = [p.strip() for p in product_group.split(',')]
            return f"""Set up {link_type} variant linking for {len(products)} products:

Products to link:
{chr(10).join(f'- {p}' for p in products)}

Linking Strategy:
1. Verify all products exist and are active
2. Check current variant links (if any)
3. Create bidirectional links:
   - Each product references all products in group
   - Products include themselves in the link list
   - Use manage_variant_links for bulk operations

Implementation Steps:
1. Use manage_variant_links with action="link"
2. Pass all product IDs in product_ids array
3. Verify links are created correctly
4. Test links on storefront

Link Type: {link_type}
- Color variations: Show as color swatches
- Size options: Display as size selector
- Model upgrades: Present as comparison table
- Feature differences: Highlight key distinctions

Quality Assurance:
□ All products are active and available
□ Links work in both directions
□ Clear differentiation between variants
□ Consistent product information
□ Proper SEO optimization

Proceed with {link_type} linking setup?"""
        
        self.add_prompt(linking_prompt)
        
        # Prompt for metafield audit
        audit_prompt = MCPPrompt(
            name="metafield_audit",
            description="Audit product metafields for consistency and completeness",
            arguments=[
                {"name": "product_filter", "description": "Product filter (vendor, type, or 'all')"}
            ]
        )
        
        @audit_prompt.handler
        def handle_audit(product_filter: str):
            return f"""Audit metafields for products: {product_filter}

Audit Checklist:
1. **Metafield Structure**:
   □ Consistent namespace usage
   □ Appropriate metafield types
   □ Valid JSON structure
   □ No empty or null values

2. **Content Quality**:
   □ Features are benefit-focused
   □ Descriptions are well-written
   □ Technical specs are accurate
   □ FAQ answers are helpful

3. **Variant Links**:
   □ Bidirectional linking
   □ No broken references
   □ Consistent grouping
   □ Proper link types

4. **Common Issues**:
   □ Missing required metafields
   □ Inconsistent formatting
   □ Outdated information
   □ Duplicate content

Audit Process:
1. Search for products matching filter
2. For each product:
   - Check metafield presence
   - Validate content quality
   - Verify variant links
   - Document issues
3. Generate improvement recommendations
4. Prioritize fixes by impact

Report Format:
- Products audited: X
- Issues found: Y
- Critical issues: Z
- Recommendations: Listed by priority

Start metafield audit for {product_filter}?"""
        
        self.add_prompt(audit_prompt)


if __name__ == "__main__":
    server = FeaturesMCPServer()
    asyncio.run(server.run())