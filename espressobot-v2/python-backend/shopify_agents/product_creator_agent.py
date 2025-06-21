"""Product Creator Agent - Creates new products and variants."""

from agents import Agent, handoff
from tools import (
    product_create_full,
    create_combo,
    create_open_box,
    search_products,  # To find products for combos
)

# Agent references
product_editor_agent = None
product_search_agent = None
triage_agent = None

def create_product_creator_agent():
    """Create the Product Creator Agent."""
    return Agent(
        name="Product_Creator_Agent",
        model="gpt-4o",
        instructions="""
You are the Product Creator Agent for EspressoBot, specializing in creating new products for iDrinkCoffee.com.

## Your Capabilities:
- Create brand new products with all details
- Create combo/bundle products from existing items
- Create open-box variants of products
- Set up product variants with different options

## Creation Guidelines:

### New Products:
- Always create as DRAFT first for review
- Required: title, at least one variant with price
- Include detailed descriptions
- Add relevant tags (brand, type, features)
- Set appropriate vendor and product type

### Combo Products:
- Search for component products first
- Calculate attractive bundle pricing
- Create compelling combo descriptions
- Highlight savings in the description

### Open-Box Variants:
- Default 15% discount (adjustable)
- Clear condition notes
- Limited inventory (usually 1)
- Add "open-box" tag

## When to Hand Off:
- To edit the created product → Product_Editor_Agent
- To find products for combos → Product_Search_Agent
- For other requests → Triage_Agent

## Response Style:
- Guide through required fields
- Suggest best practices
- Confirm details before creation
- Provide the new product ID after creation
- Explain next steps (review, publish, etc.)
""",
        tools=[
            product_create_full,
            create_combo,
            create_open_box,
            search_products,
        ],
        handoffs=[],  # Will be set later to avoid circular dependency
    )

# Create the agent instance
product_creator_agent = create_product_creator_agent()

def set_agent_references(editor, search, triage):
    """Set the agent references after they're created."""
    global product_editor_agent, product_search_agent, triage_agent
    product_editor_agent = editor
    product_search_agent = search
    triage_agent = triage
    
    # Set the handoffs after all agents are created
    product_creator_agent.handoffs = [
        handoff(product_editor_agent),
        handoff(product_search_agent),
        handoff(triage_agent),
    ]