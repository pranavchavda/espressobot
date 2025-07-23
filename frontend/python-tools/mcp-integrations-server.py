#!/usr/bin/env python3
"""
MCP Integrations Server - Specialized server for external integrations
Includes: upload_to_skuvault, manage_skuvault_kits, send_review_request, perplexity_research
Reduces token usage by ~85% compared to loading all 28 tools
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt

# Import only the integration-related tools
from mcp_tools.skuvault.upload_products import UploadToSkuVaultTool
from mcp_tools.skuvault.manage_kits import ManageSkuVaultKitsTool
from mcp_tools.marketing.send_review_request import SendReviewRequestTool
from mcp_tools.research.perplexity import PerplexityResearchTool

# Scratchpad functionality
from mcp_scratchpad_tool import SCRATCHPAD_TOOLS


class IntegrationsMCPServer(EnhancedMCPServer):
    """Specialized MCP server for external integrations"""
    
    def __init__(self):
        super().__init__("espressobot-integrations", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only integration-related tools"""
        # Add the integration tools
        self.add_tool(UploadToSkuVaultTool())
        self.add_tool(ManageSkuVaultKitsTool())
        self.add_tool(SendReviewRequestTool())
        self.add_tool(PerplexityResearchTool())
        
        
        # Add scratchpad tools
        for tool_def in SCRATCHPAD_TOOLS:
            self.add_tool_from_def(tool_def)
    def _setup_resources(self):
        """Setup integration-related resources"""
        # Resource for SkuVault integration guidelines
        skuvault_resource = MCPResource(
            name="skuvault_integration",
            uri="integrations://skuvault",
            description="SkuVault integration guidelines and best practices",
            mime_type="text/markdown"
        )
        
        @skuvault_resource.getter
        def get_skuvault_guide():
            return """# SkuVault Integration Guide

## Authentication
- SKUVAULT_TENANT_TOKEN: Your tenant authentication token
- SKUVAULT_USER_TOKEN: Your user authentication token
- Both required in environment variables

## Product Upload Process
1. Fetch product data from Shopify by SKU
2. Convert to SkuVault format
3. Upload via SkuVault API
4. Verify successful creation

## Kit Management
- Kits are bundles of products sold as single SKU
- Component format: "SKU1:QTY1,SKU2:QTY2"
- Example: "BES870XL:1,EUREKA-SPEC:1"

## Best Practices
- Use dry run mode for testing
- Upload in batches of 10-50 products
- Verify all components exist before creating kits
- Monitor API rate limits
"""
        
        self.add_resource(skuvault_resource)
        
        # Resource for review request guidelines
        review_resource = MCPResource(
            name="review_requests",
            uri="integrations://reviews",
            description="Best practices for review request campaigns",
            mime_type="text/markdown"
        )
        
        @review_resource.getter
        def get_review_guide():
            return """# Review Request Best Practices

## Timing
- Send 7-14 days after delivery
- Avoid holidays and weekends
- Consider customer purchase patterns

## Targeting
- High-value customers first
- Satisfied customers (previous positive feedback)
- Active email subscribers

## Content Guidelines
- Personalized to product purchased
- Clear call-to-action
- Easy review submission process
- Mobile-friendly format

## Spam Prevention
- Respect unsubscribe requests
- Limit frequency (max 5 emails per 30 days)
- Use spam filter option when available
"""
        
        self.add_resource(review_resource)
        
        # Resource for research guidelines
        research_resource = MCPResource(
            name="research_guidelines", 
            uri="integrations://research",
            description="Guidelines for effective product and market research",
            mime_type="text/markdown"
        )
        
        @research_resource.getter
        def get_research_guide():
            return """# Research Best Practices

## Product Research
- Competitor pricing analysis
- Feature comparison studies
- Technical specification verification
- Market positioning research

## Query Optimization
- Use specific, targeted questions
- Include relevant context and constraints
- Specify desired output format
- Ask for sources and citations

## Data Validation
- Cross-reference multiple sources
- Verify recent publication dates
- Check for bias in sources
- Validate technical claims

## Use Cases
- Pre-purchase decision support
- Competitive analysis
- Market trend identification
- Technical troubleshooting
"""
        
        self.add_resource(research_resource)
        
    def _setup_prompts(self):
        """Setup integration-related prompts"""
        # Prompt for SkuVault bulk upload
        bulk_upload_prompt = MCPPrompt(
            name="skuvault_bulk_upload",
            description="Guide for bulk uploading products to SkuVault"
        )
        
        bulk_upload_prompt.arguments = [
            {"name": "sku_list", "description": "List of SKUs to upload", "required": True},
            {"name": "batch_size", "description": "Number of products per batch", "required": False}
        ]
        
        bulk_upload_prompt.content = """# SkuVault Bulk Upload Process

## Pre-Upload Checklist
1. Verify all SKUs exist in Shopify
2. Check SkuVault credentials are configured
3. Test with single product first
4. Prepare for potential failures

## Upload Strategy
- Start with dry run to validate data
- Upload in batches of 10-20 products
- Monitor for API rate limits
- Log successes and failures separately

## Error Handling
- Retry failed uploads with exponential backoff
- Check for duplicate SKUs in SkuVault
- Validate required fields before upload
- Report final success/failure summary
"""
        
        self.add_prompt(bulk_upload_prompt)
        
        # Prompt for review campaign setup
        review_campaign_prompt = MCPPrompt(
            name="review_campaign_setup",
            description="Setup and execute review request campaigns"
        )
        
        review_campaign_prompt.arguments = [
            {"name": "product_id", "description": "Yotpo product ID", "required": True},
            {"name": "customer_list", "description": "List of customers to target", "required": True}
        ]
        
        review_campaign_prompt.content = """# Review Campaign Setup

## Campaign Planning
1. Identify target product and customers
2. Verify Yotpo product ID mapping
3. Prepare customer list with email/name
4. Set spam filter preferences

## Execution Steps
1. Validate all customer email addresses
2. Check spam filter settings
3. Send review requests via API
4. Monitor delivery and open rates

## Success Metrics
- Delivery rate (emails sent successfully)
- Open rate (customers viewing emails)
- Click-through rate (customers clicking review link)
- Conversion rate (actual reviews submitted)
"""
        
        self.add_prompt(review_campaign_prompt)


async def main():
    server = IntegrationsMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())