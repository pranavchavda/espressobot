#!/usr/bin/env python3
"""
MCP Server for Shopify Orders and Analytics
Handles high-volume order analytics and reporting
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logger = logging.getLogger('orders-server')

# Import base server and tools
from mcp_base_server import EnhancedMCPServer as MCPServerBase

# Scratchpad functionality
from mcp_scratchpad_tool import SCRATCHPAD_TOOLS

from mcp_tools.analytics import (
    OrderAnalyticsTool,
    DailySalesTool,
    RevenueReportsTool,
    OrderDetailsTool
)

class OrdersServer(MCPServerBase):
    """MCP server for Shopify order analytics"""
    
    def __init__(self):
        super().__init__(
            name="espressobot-orders",
            version="1.0.0"
        )
        
        # Register analytics tools
        self.add_tool(OrderAnalyticsTool())
        self.add_tool(DailySalesTool())
        self.add_tool(RevenueReportsTool())
        self.add_tool(OrderDetailsTool())
        
        # Add scratchpad tools
        for tool_def in SCRATCHPAD_TOOLS:
            self.add_tool_from_def(tool_def)
        
        logger.info(f"Orders MCP Server initialized with {len(self.tools)} tools")
    
    async def handle_initialize(self, params):
        """Handle initialization request"""
        result = await super().handle_initialize(params)
        
        # Add server-specific capabilities
        result["capabilities"]["experimental"] = {
            "highVolumeSupport": True,
            "paginationOptimized": True,
            "realtimeAnalytics": True
        }
        
        return result
    
    async def test_all_tools(self):
        """Test all registered tools"""
        logger.info("Testing all analytics tools...")
        results = {}
        
        for tool_name, tool in self.tools.items():
            try:
                logger.info(f"Testing {tool_name}...")
                result = await tool.test()
                results[tool_name] = result
                
                if result.get("status") == "passed":
                    logger.info(f"✓ {tool_name}: {result.get('message', 'Passed')}")
                else:
                    logger.error(f"✗ {tool_name}: {result.get('error', 'Failed')}")
                    
            except Exception as e:
                logger.error(f"✗ {tool_name}: Test failed with {str(e)}")
                results[tool_name] = {"status": "failed", "error": str(e)}
        
        # Summary
        passed = sum(1 for r in results.values() if r.get("status") == "passed")
        total = len(results)
        
        logger.info(f"\nTest Summary: {passed}/{total} tools passed")
        
        return results

def main():
    """Main entry point"""
    server = OrdersServer()
    
    # If run with --test flag, run tests
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        async def run_tests():
            await server.test_all_tools()
        
        asyncio.run(run_tests())
    else:
        # Run as MCP server
        asyncio.run(server.run())

if __name__ == "__main__":
    main()