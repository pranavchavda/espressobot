#!/usr/bin/env python3
"""
MCP Sales Server - Specialized server for sales and promotion management
Includes: manage_miele_sales, manage_map_sales
Reduces token usage by ~92% compared to loading all 28 tools
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_base_server import EnhancedMCPServer, MCPResource, MCPPrompt

# Import only the sales-related tools
from mcp_tools.sales.manage_miele_sales import ManageMieleSalesTool
from mcp_tools.sales.manage_map_sales import ManageMapSalesTool


class SalesMCPServer(EnhancedMCPServer):
    """Specialized MCP server for sales and promotion management"""
    
    def __init__(self):
        super().__init__("espressobot-sales", "1.0.0")
        self._load_tools()
        self._setup_resources()
        self._setup_prompts()
        
    def _load_tools(self):
        """Load only sales-related tools"""
        self.add_tool(ManageMieleSalesTool())
        self.add_tool(ManageMapSalesTool())
        
    def _setup_resources(self):
        """Setup sales-related resources"""
        # Resource for MAP pricing rules
        map_resource = MCPResource(
            name="map_pricing_rules",
            uri="sales://map-rules",
            description="MAP pricing rules and compliance guidelines",
            mime_type="text/markdown"
        )
        
        @map_resource.getter
        def get_map_rules():
            return """# MAP Pricing Rules & Compliance

## What is MAP?
Minimum Advertised Price (MAP) is the lowest price a retailer can advertise a product for sale.

## Key Rules
- Cannot advertise below MAP price
- Can sell below MAP but not advertise it
- MAP applies to all advertising channels
- Violations can result in supplier penalties

## Compliance Guidelines

### Breville MAP
- Strict enforcement of MAP pricing
- Sale periods must be approved by Breville
- Discount percentages are pre-approved
- Sale dates are predetermined

### Miele MAP
- Premium brand with high MAP compliance
- Limited sale windows throughout the year
- Specific models may have different MAP rules
- Professional vs consumer product distinctions

### Other Vendors
- ECM, Rocket, Profitec: Generally honor MAP
- Baratza: Flexible MAP policy
- Eureka: Seasonal MAP adjustments

## Sale Implementation
1. Verify sale is approved by vendor
2. Set compare_at_price to MSRP
3. Set price to MAP-approved sale price
4. Add appropriate sale tags
5. Monitor sale period compliance

## Penalties for Violations
- Warning letters from vendors
- Suspension of product allocation
- Termination of dealer agreements
- Legal action in severe cases

## Best Practices
- Always check MAP before pricing
- Document all sale approvals
- Monitor competitor pricing
- Review MAP agreements regularly
"""
        
        self.add_resource(map_resource)
        
        # Resource for current sale schedules
        schedule_resource = MCPResource(
            name="sale_schedules",
            uri="sales://schedules",
            description="Current and upcoming sale schedules",
            mime_type="application/json"
        )
        
        @schedule_resource.getter
        def get_sale_schedules():
            # This would typically load from a database
            current_date = datetime.now()
            
            return {
                "current_sales": [
                    {
                        "vendor": "Miele",
                        "type": "MAP Sale",
                        "start_date": "2025-01-15",
                        "end_date": "2025-01-31",
                        "products": ["CM5310", "CM6160"],
                        "status": "active"
                    }
                ],
                "upcoming_sales": [
                    {
                        "vendor": "Breville",
                        "type": "Valentine's Day Sale",
                        "start_date": "2025-02-14",
                        "end_date": "2025-02-18",
                        "products": ["BES870XL", "BES878BSS"],
                        "discount": "15%",
                        "status": "scheduled"
                    },
                    {
                        "vendor": "Miele",
                        "type": "Spring Sale",
                        "start_date": "2025-03-15",
                        "end_date": "2025-03-31",
                        "products": ["CM5310", "CM6160", "CM6360"],
                        "discount": "Various",
                        "status": "planned"
                    }
                ],
                "past_sales": [
                    {
                        "vendor": "Breville",
                        "type": "Black Friday",
                        "start_date": "2024-11-29",
                        "end_date": "2024-12-02",
                        "products": ["BES870XL", "BES878BSS", "BES980XL"],
                        "performance": "Exceeded targets",
                        "status": "completed"
                    }
                ]
            }
        
        self.add_resource(schedule_resource)
        
        # Resource for sale performance metrics
        metrics_resource = MCPResource(
            name="sale_metrics",
            uri="sales://metrics",
            description="Sale performance metrics and KPIs",
            mime_type="application/json"
        )
        
        @metrics_resource.getter
        def get_sale_metrics():
            return {
                "kpis": {
                    "conversion_rate": "Target: 3.5%+",
                    "average_order_value": "Target: $450+",
                    "units_sold": "Target: 50+ units per sale",
                    "profit_margin": "Target: 15%+ on sale items"
                },
                "best_performing_sales": [
                    {
                        "sale": "Breville Black Friday 2024",
                        "units_sold": 127,
                        "revenue": "$58,450",
                        "conversion_rate": "4.2%"
                    },
                    {
                        "sale": "Miele Spring Sale 2024",
                        "units_sold": 89,
                        "revenue": "$112,340",
                        "conversion_rate": "3.8%"
                    }
                ],
                "optimization_tips": [
                    "Email campaigns 48 hours before sale start",
                    "Social media teasers 1 week prior",
                    "Bundle offers increase AOV by 25%",
                    "Limited-time messaging improves urgency"
                ]
            }
        
        self.add_resource(metrics_resource)
        
    def _setup_prompts(self):
        """Setup sales-related prompts"""
        # Prompt for planning a new sale
        plan_prompt = MCPPrompt(
            name="plan_new_sale",
            description="Plan and prepare a new promotional sale",
            arguments=[
                {"name": "vendor", "description": "Vendor for the sale (Breville, Miele, etc.)"},
                {"name": "sale_type", "description": "Type of sale (MAP, seasonal, clearance, etc.)"},
                {"name": "duration", "description": "Sale duration in days"}
            ]
        )
        
        @plan_prompt.handler
        def handle_plan_sale(vendor: str, sale_type: str, duration: str):
            return f"""Plan {vendor} {sale_type} sale ({duration} days):

Pre-Sale Checklist:
□ Verify MAP compliance with {vendor}
□ Get written approval for sale prices
□ Review inventory levels for target products
□ Plan marketing campaign timeline
□ Set up sale tags and messaging
□ Schedule price updates
□ Prepare email campaigns
□ Update website banners

Sale Setup Steps:
1. Use manage_{vendor.lower()}_sales to check available windows
2. Select appropriate products based on inventory
3. Calculate MAP-compliant sale prices
4. Set compare_at_price to MSRP
5. Add sale tags: {vendor.lower()}-sale, sale-YYYY-MM

Marketing Timeline:
- Week 1: Internal preparation
- 48 hours before: Email announcement
- Day of: Social media activation
- During sale: Daily performance monitoring
- After sale: Performance analysis

Ready to proceed with {vendor} {sale_type} planning?"""
        
        self.add_prompt(plan_prompt)
        
        # Prompt for sale performance review
        review_prompt = MCPPrompt(
            name="sale_performance_review",
            description="Review performance of completed sales",
            arguments=[
                {"name": "sale_period", "description": "Sale period to review (YYYY-MM format)"}
            ]
        )
        
        @review_prompt.handler
        def handle_review(sale_period: str):
            return f"""Review sale performance for {sale_period}:

Performance Analysis:
1. Identify all sales that occurred in {sale_period}
2. For each sale, analyze:
   - Units sold vs. target
   - Revenue generated
   - Conversion rate
   - Average order value
   - Profit margins
3. Compare against KPIs:
   - Conversion rate target: 3.5%+
   - AOV target: $450+
   - Units sold target: 50+ per sale
   - Profit margin target: 15%+

Review Process:
1. Use manage_map_sales to check {sale_period} sales
2. Gather sales data from analytics
3. Calculate key metrics
4. Identify top performers
5. Document lessons learned
6. Recommend optimizations

Start performance review for {sale_period}?"""
        
        self.add_prompt(review_prompt)
        
        # Prompt for emergency sale setup
        emergency_prompt = MCPPrompt(
            name="emergency_sale_setup",
            description="Quickly set up an emergency or flash sale",
            arguments=[
                {"name": "reason", "description": "Reason for emergency sale"},
                {"name": "products", "description": "Product SKUs or categories"},
                {"name": "discount", "description": "Discount percentage or amount"}
            ]
        )
        
        @emergency_prompt.handler
        def handle_emergency_sale(reason: str, products: str, discount: str):
            return f"""Emergency sale setup: {reason}

Quick Setup Process:
1. Verify MAP compliance for {discount} discount
2. Products to include: {products}
3. Emergency approval workflow:
   - Get verbal approval from vendor (if MAP protected)
   - Document approval in notes
   - Set temporary sale pricing
   - Add emergency-sale tag

Immediate Actions:
□ Check inventory levels for {products}
□ Calculate sale prices with {discount}
□ Set compare_at_price to preserve original
□ Add tags: emergency-sale, flash-sale, sale-YYYY-MM-DD
□ Update product messaging
□ Notify marketing team
□ Set sale end date (recommend 24-48 hours max)

MAP Compliance Check:
- Reason: {reason}
- Products: {products}
- Discount: {discount}
- Approval status: ⚠️ PENDING

CRITICAL: Verify MAP compliance before proceeding!
Proceed with emergency sale setup?"""
        
        self.add_prompt(emergency_prompt)


if __name__ == "__main__":
    server = SalesMCPServer()
    asyncio.run(server.run())