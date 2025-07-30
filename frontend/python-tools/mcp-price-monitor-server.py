#!/usr/bin/env python3
"""
MCP Price Monitor Server - Specialized server for price monitoring operations
Includes: alerts data access, sync, scraping, matching, and alert generation tools
"""

import asyncio
import sys
import os
import json
import requests
from pathlib import Path

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt
from mcp_tools.base import BaseMCPTool
from typing import Dict, Any, Optional, List


class PriceMonitorAlertsDataTool(BaseMCPTool):
    """Tool to access price monitor alerts data"""
    
    name = "price_monitor_alerts_data"
    description = "Access price monitor alerts data with filtering and sorting options"
    context = """
    Access price monitor alerts with comprehensive filtering options:
    - Filter by status (active, resolved, dismissed)
    - Filter by severity (minor, moderate, severe)
    - Filter by brand or competitor
    - Sort by recency, severity, or impact
    
    Returns alerts with product details, pricing info, and violation data.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["active", "resolved", "dismissed", "all"],
                "default": "active",
                "description": "Filter alerts by status"
            },
            "severity": {
                "type": "string",
                "enum": ["minor", "moderate", "severe"],
                "description": "Filter alerts by severity level"
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "description": "Maximum number of alerts to return"
            },
            "brand": {
                "type": "string",
                "description": "Filter alerts by brand/vendor"
            },
            "competitor": {
                "type": "string",
                "description": "Filter alerts by competitor name"
            },
            "sort_by": {
                "type": "string",
                "enum": ["recent", "severity", "impact", "oldest"],
                "default": "recent",
                "description": "Sort order for results"
            }
        }
    }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the alerts data retrieval"""
        try:
            # Build query parameters
            params = {}
            for key in ["status", "severity", "limit", "brand", "competitor", "sort_by"]:
                if key in kwargs and kwargs[key] is not None:
                    params[key] = kwargs[key]
            
            # Make request to alerts API
            response = requests.get(
                "http://localhost:5173/api/price-monitor/alerts/data",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "alerts_count": len(data.get("alerts", [])),
                    "alerts": data.get("alerts", []),
                    "summary": data.get("summary", {}),
                    "filters_applied": data.get("filters_applied", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"API request failed with status {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch alerts data: {str(e)}"
            }


class PriceMonitorMCPServer(EnhancedMCPServer):
    """Specialized MCP server for price monitoring operations"""
    
    def __init__(self):
        super().__init__("espressobot-price-monitor", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load price monitoring tools"""
        self.add_tool(PriceMonitorAlertsDataTool())
        
    def _setup_resources(self):
        """Setup price monitor resources"""
        monitoring_resource = MCPResource(
            name="price_monitoring_guide",
            uri="price-monitor://guide",
            description="Guide for using price monitoring tools effectively",
            mime_type="text/plain"
        )
        self.add_resource(monitoring_resource)
        
    def _get_resource_content(self, uri: str) -> str:
        """Get resource content by URI"""
        if uri == "price-monitor://guide":
            return """
# Price Monitoring Tools Guide

## Available Tools

### price_monitor_alerts_data
Access and filter price alerts with various criteria:
- Filter by status (active, resolved, dismissed)
- Filter by severity (minor, moderate, severe)  
- Filter by brand or competitor
- Sort by recent, severity, impact, or oldest

## Usage Examples

1. Get active severe violations:
   status: "active", severity: "severe", sort_by: "impact"

2. Get recent alerts for specific brand:
   brand: "Breville", sort_by: "recent", limit: 10

3. Get competitor-specific violations:
   competitor: "Williams Sonoma", status: "active"

## Best Practices

- Use severity filtering to prioritize critical violations
- Sort by impact to see most costly violations first
- Check status regularly to stay on top of new violations
"""
        return ""
        
    def _setup_prompts(self):
        """Setup price monitor prompts"""
        alerts_prompt = MCPPrompt(
            name="get_severe_violations",
            description="Get the most severe MAP violations"
        )
        self.add_prompt(alerts_prompt)
        
    def _get_prompt_content(self, name: str, arguments: Dict[str, Any]) -> str:
        """Get prompt content by name"""
        if name == "get_severe_violations":
            return """
# Get Most Severe MAP Violations

Retrieve the most severe MAP violations with detailed product information:
- Status: active (unresolved violations only)
- Severity: severe (biggest price gaps)
- Sort by: impact (highest revenue impact first)
- Include: SKU, brand, product type, current price, MAP price, violation percentage

Use price_monitor_alerts_data with these parameters:
- status: "active"
- severity: "severe" 
- sort_by: "impact"
- limit: 20
"""
        return ""


async def main():
    """Main entry point"""
    server = PriceMonitorMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())