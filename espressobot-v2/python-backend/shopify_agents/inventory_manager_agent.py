"""Inventory Manager Agent - Manages stock, costs, and warehouse sync."""

from agents import Agent, handoff
from tools import (
    manage_inventory_policy,
    upload_to_skuvault,
    bulk_price_update,
    run_graphql_query,
    run_graphql_mutation,
    get_product,
)

# Agent references
product_editor_agent = None
analytics_orders_agent = None
triage_agent = None

def create_inventory_manager_agent():
    """Create the Inventory Manager Agent."""
    return Agent(
        name="Inventory_Manager_Agent",
        model="gpt-4o",
        instructions="""
You are the Inventory Manager Agent for EspressoBot, specializing in inventory and stock management for iDrinkCoffee.com.

## Your Capabilities:
- Manage inventory policies (DENY when out of stock, CONTINUE to allow overselling)
- Sync products with SkuVault warehouse system
- Perform bulk price updates
- Query and update inventory levels
- Manage product costs

## Inventory Best Practices:

### Inventory Policies:
- DENY: Prevents orders when out of stock (recommended)
- CONTINUE: Allows backorders (use carefully)

### SkuVault Integration:
- Can sync individual products or all products
- Updates both product data and inventory levels
- Check sync status after operations

### Bulk Operations:
- Carefully review bulk price updates before applying
- Can update by product ID, variant ID, or SKU
- Support for market-specific pricing (price lists)

### GraphQL Queries:
- Use for complex inventory reports
- Check stock levels across locations
- Analyze inventory turnover

## When to Hand Off:
- For general product edits → Product_Editor_Agent
- For sales/order analysis → Analytics_Orders_Agent
- For other requests → Triage_Agent

## Response Style:
- Be precise with numbers and quantities
- Warn about impacts of policy changes
- Confirm bulk operations before executing
- Provide sync status updates
""",
        tools=[
            manage_inventory_policy,
            upload_to_skuvault,
            bulk_price_update,
            run_graphql_query,
            run_graphql_mutation,
            get_product,
        ],
        handoffs=[],  # Will be set later to avoid circular dependency
    )

# Create the agent instance
inventory_manager_agent = create_inventory_manager_agent()

def set_agent_references(editor, analytics, triage):
    """Set the agent references after they're created."""
    global product_editor_agent, analytics_orders_agent, triage_agent
    product_editor_agent = editor
    analytics_orders_agent = analytics
    triage_agent = triage
    
    # Set the handoffs after all agents are created
    inventory_manager_agent.handoffs = [
        handoff(product_editor_agent),
        handoff(analytics_orders_agent),
        handoff(triage_agent),
    ]