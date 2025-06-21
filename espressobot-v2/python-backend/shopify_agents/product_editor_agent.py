"""Product Editor Agent - Modifies existing products."""

from agents import Agent, handoff
from tools import (
    update_pricing,
    add_tags_to_product,
    remove_tags_from_product,
    manage_tags,
    update_product_status,
    manage_map_sales,
    manage_variant_links,
    get_product,  # To verify products before editing
)

# Agent references
product_search_agent = None
product_creator_agent = None
inventory_manager_agent = None
triage_agent = None

def create_product_editor_agent():
    """Create the Product Editor Agent."""
    return Agent(
        name="Product_Editor_Agent",
        model="gpt-4o",
        instructions="""
You are the Product Editor Agent for EspressoBot, specializing in modifying existing products in the iDrinkCoffee.com store.

## Your Capabilities:
- Update product prices and compare-at prices
- Add or remove product tags
- Change product status (ACTIVE, DRAFT, ARCHIVED)
- Manage MAP (Minimum Advertised Price) settings
- Link products as variants
- Manage any product attributes

## Best Practices:
- Always verify the product exists before editing (use get_product)
- Confirm changes with the user before applying
- Explain the impact of status changes:
  - ACTIVE: Visible on storefront
  - DRAFT: Hidden from customers, editable
  - ARCHIVED: Hidden and preserved
- Be careful with pricing - double-check amounts
- When managing tags, preserve existing important tags

## When to Hand Off:
- If product needs to be found first → Product_Search_Agent
- If a new product/variant needs creation → Product_Creator_Agent
- For inventory/stock updates → Inventory_Manager_Agent
- For other requests → Triage_Agent

## Response Style:
- Be precise and clear about changes
- Confirm product details before editing
- Summarize what was changed
- Warn about any potential impacts
""",
        tools=[
            get_product,
            update_pricing,
            add_tags_to_product,
            remove_tags_from_product,
            manage_tags,
            update_product_status,
            manage_map_sales,
            manage_variant_links,
        ],
        handoffs=[],  # Will be set later to avoid circular dependency
    )

# Create the agent instance
product_editor_agent = create_product_editor_agent()

def set_agent_references(search, creator, inventory, triage):
    """Set the agent references after they're created."""
    global product_search_agent, product_creator_agent, inventory_manager_agent, triage_agent
    product_search_agent = search
    product_creator_agent = creator
    inventory_manager_agent = inventory
    triage_agent = triage
    
    # Set the handoffs after all agents are created
    product_editor_agent.handoffs = [
        handoff(product_search_agent),
        handoff(product_creator_agent),
        handoff(inventory_manager_agent),
        handoff(triage_agent),
    ]