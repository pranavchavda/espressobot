#!/usr/bin/env python3
"""
MCP Media Server - Specialized server for media and image operations
Includes: add_product_images
Reduces token usage by ~96% compared to loading all 28 tools
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt

# Import only the media-related tools
from mcp_tools.media.add_images import AddProductImagesTool


class MediaMCPServer(EnhancedMCPServer):
    """Specialized MCP server for media operations"""
    
    def __init__(self):
        super().__init__("espressobot-media", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only media-related tools"""
        # Add the media tool
        self.add_tool(AddProductImagesTool())
        
    def _setup_resources(self):
        """Setup media-related resources"""
        # Resource for image guidelines
        resource = MCPResource(
            name="image_guidelines",
            uri="media://guidelines",
            description="Guidelines for product image management",
            mime_type="text/markdown"
        )
        
        @resource.getter
        def get_image_guidelines():
            return """# Product Image Guidelines

## Image Requirements
- Format: JPG, PNG, WebP preferred
- Resolution: Minimum 1024x1024px
- Aspect Ratio: Square (1:1) or product-appropriate
- File Size: Under 2MB per image

## Image Order
1. Main product photo (white background)
2. Product in use/lifestyle shot
3. Product details/close-ups
4. Packaging/accessories
5. Additional angles

## Quality Standards
- High resolution and clarity
- Proper lighting and color accuracy
- Clean, professional appearance
- Consistent styling across product line

## Alt Text Best Practices
- Descriptive and specific
- Include brand and product name
- Mention key features or colors
- Keep under 125 characters
"""
        
        self.add_resource(resource)
        
        # Resource for image optimization tips
        optimization_resource = MCPResource(
            name="image_optimization",
            uri="media://optimization",
            description="Image optimization best practices",
            mime_type="text/markdown"
        )
        
        @optimization_resource.getter
        def get_optimization_guide():
            return """# Image Optimization

## File Size Optimization
- Use appropriate compression levels
- Consider WebP format for better compression
- Optimize for web delivery speeds

## SEO Considerations
- Descriptive file names
- Proper alt text for accessibility
- Structured data for rich snippets

## Performance Impact
- Lazy loading for large catalogs
- Progressive JPEG for faster perceived load
- CDN delivery optimization
"""
        
        self.add_resource(optimization_resource)
        
    def _setup_prompts(self):
        """Setup media-related prompts"""
        # Prompt for bulk image uploads
        bulk_upload_prompt = MCPPrompt(
            name="bulk_image_upload",
            description="Guide for uploading images to multiple products"
        )
        
        bulk_upload_prompt.arguments = [
            {"name": "product_list", "description": "List of products needing images", "required": True},
            {"name": "image_sources", "description": "Sources for product images", "required": True}
        ]
        
        @bulk_upload_prompt.handler
        def get_bulk_upload_guide(product_list, image_sources):
            return """# Bulk Image Upload Process

## Pre-Upload Checklist
1. Verify all image URLs are accessible
2. Check image quality and format requirements
3. Prepare alt text for each image
4. Organize images by product

## Upload Strategy
- Process products in batches of 10-20
- Use add_product_images tool for each product
- Monitor for failed uploads and retry
- Verify images appear correctly in storefront

## Error Handling
- Log failed uploads for manual review
- Check network connectivity for timeouts
- Validate image formats before upload
- Ensure proper authentication tokens
"""
        
        self.add_prompt(bulk_upload_prompt)
        
        # Prompt for image troubleshooting
        troubleshooting_prompt = MCPPrompt(
            name="image_troubleshooting",
            description="Troubleshoot common image upload issues"
        )
        
        @troubleshooting_prompt.handler
        def get_troubleshooting_guide():
            return """# Image Upload Troubleshooting

## Common Issues
1. **Upload Timeout**: Large files or slow connection
   - Solution: Compress images, check network
   
2. **Invalid Format**: Unsupported file type
   - Solution: Convert to JPG/PNG/WebP
   
3. **Access Denied**: Authentication issues
   - Solution: Check API tokens and permissions
   
4. **Image Not Displaying**: Processing delays
   - Solution: Wait for Shopify processing, check URLs

## Debugging Steps
1. Test with single image first
2. Verify product exists and is accessible
3. Check image URL accessibility
4. Monitor API response for errors
"""
        
        self.add_prompt(troubleshooting_prompt)


async def main():
    server = MediaMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())