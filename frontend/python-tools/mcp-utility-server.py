#!/usr/bin/env python3
"""
MCP Utility Server - Specialized server for utility operations
Includes: memory_operations
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

# Import only the utility tools
from mcp_tools.memory.operations import MemoryOperationsTool

# Scratchpad functionality
from mcp_scratchpad_tool import SCRATCHPAD_TOOLS


class UtilityMCPServer(EnhancedMCPServer):
    """Specialized MCP server for utility operations"""
    
    def __init__(self):
        super().__init__("espressobot-utility", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only utility tools"""
        # Add the utility tool
        self.add_tool(MemoryOperationsTool())
        
        
        # Add scratchpad tools
        for tool_def in SCRATCHPAD_TOOLS:
            self.add_tool_from_def(tool_def)
    def _setup_resources(self):
        """Setup utility-related resources"""
        # Resource for memory management guidelines
        memory_resource = MCPResource(
            name="memory_guidelines",
            uri="utility://memory",
            description="Guidelines for effective memory management",
            mime_type="text/markdown"
        )
        
        @memory_resource.getter
        def get_memory_guidelines():
            return """# Memory Management Guidelines

## Memory Operations
- **search**: Find relevant memories with semantic similarity
- **add**: Store new memories with automatic deduplication
- **list**: Show recent memories for context
- **delete**: Remove specific memories by ID

## Best Practices

### What to Remember
- Important business decisions and rationale
- Customer preferences and requirements
- Product information and specifications
- Process improvements and learnings
- Error resolutions and troubleshooting

### What NOT to Remember
- Temporary data or one-time operations
- Sensitive customer information
- API keys or authentication details
- Redundant or duplicate information

## Memory Content Guidelines
- Be specific and actionable
- Include relevant context
- Use clear, searchable language
- Avoid overly technical jargon
- Include dates when relevant

## Search Tips
- Use descriptive keywords
- Include relevant context
- Try different search terms
- Review similarity scores
- Use results to refine queries
"""
        
        self.add_resource(memory_resource)
        
        # Resource for data privacy guidelines
        privacy_resource = MCPResource(
            name="privacy_guidelines",
            uri="utility://privacy",
            description="Data privacy and security guidelines",
            mime_type="text/markdown"
        )
        
        @privacy_resource.getter
        def get_privacy_guidelines():
            return """# Data Privacy Guidelines

## Personal Information
- Never store customer PII in memory
- Avoid storing sensitive financial data
- Anonymize data when possible
- Use general patterns instead of specifics

## Business Information
- Store general processes and guidelines
- Remember product categories and rules
- Keep business logic and decisions
- Avoid storing specific pricing data

## Security Considerations
- No API keys or tokens in memory
- No authentication credentials
- No internal system details
- No customer communication content

## Compliance
- Follow GDPR data minimization
- Respect customer privacy rights
- Maintain data accuracy
- Enable data deletion when requested
"""
        
        self.add_resource(privacy_resource)
        
    def _setup_prompts(self):
        """Setup utility-related prompts"""
        # Prompt for memory management strategy
        memory_strategy_prompt = MCPPrompt(
            name="memory_management_strategy",
            description="Develop effective memory management strategies"
        )
        
        memory_strategy_prompt.arguments = [
            {"name": "context", "description": "Current context or situation", "required": True},
            {"name": "goal", "description": "What you want to achieve", "required": True}
        ]
        
        @memory_strategy_prompt.handler
        def get_memory_strategy(context, goal):
            return """# Memory Management Strategy

## Assessment Questions
1. What information is most valuable for future decisions?
2. What patterns or insights should be preserved?
3. How can this knowledge help future interactions?
4. What specific details are worth remembering?

## Storage Strategy
- **Search First**: Check existing memories before adding new ones
- **Consolidate**: Combine related information when possible
- **Prioritize**: Focus on high-value, reusable information
- **Organize**: Use consistent terminology and categories

## Maintenance Tasks
- Regular cleanup of outdated information
- Merge duplicate or similar memories
- Update memories with new insights
- Archive historical data appropriately

## Quality Checks
- Information is accurate and up-to-date
- Content is searchable and well-structured
- No sensitive data is stored
- Memories serve a clear future purpose
"""
        
        self.add_prompt(memory_strategy_prompt)
        
        # Prompt for knowledge extraction
        knowledge_extraction_prompt = MCPPrompt(
            name="knowledge_extraction",
            description="Extract valuable knowledge from conversations or events"
        )
        
        knowledge_extraction_prompt.arguments = [
            {"name": "source_content", "description": "Content to extract knowledge from", "required": True},
            {"name": "focus_area", "description": "Specific area to focus on", "required": False}
        ]
        
        @knowledge_extraction_prompt.handler
        def get_knowledge_extraction_guide(source_content, focus_area=None):
            return """# Knowledge Extraction Process

## Extraction Criteria
- **Actionable Insights**: Information that can guide future decisions
- **Process Improvements**: Better ways to handle similar situations
- **Business Rules**: Important policies or guidelines discovered
- **Problem Solutions**: Effective resolutions to common issues

## Analysis Framework
1. **What Worked**: Successful strategies and approaches
2. **What Failed**: Mistakes to avoid in the future
3. **Key Learnings**: Important insights or discoveries
4. **Process Changes**: Improvements to current workflows

## Memory Creation
- Summarize key points concisely
- Include relevant context and conditions
- Add searchable keywords and tags
- Specify when/how to apply the knowledge

## Validation Steps
- Check for existing similar memories
- Verify accuracy of extracted information
- Ensure content is genuinely valuable
- Confirm appropriate level of detail
"""
        
        self.add_prompt(knowledge_extraction_prompt)


async def main():
    server = UtilityMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())