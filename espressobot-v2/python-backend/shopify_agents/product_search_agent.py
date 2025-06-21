"""Product Search & Discovery Agent - Finds and researches products."""

from agents import Agent, handoff
from tools import search_products, get_product, perplexity_search

# Agent references (will be set by main module)
product_editor_agent = None
product_creator_agent = None
triage_agent = None

def create_product_search_agent():
    """Create the Product Search & Discovery Agent."""
    return Agent(
        name="Product_Search_Agent",
        model="gpt-4o",
        instructions="""
You are the Product Search & Discovery Agent for EspressoBot, specializing in finding products in the iDrinkCoffee.com Shopify store.

## Your Capabilities:
- Search products by any criteria (title, SKU, vendor, tags, etc.)
- Get detailed information about specific products
- Research product information using Perplexity AI
- Help customers browse and discover products

## Search Tips:
- Use Shopify query syntax for precise searches:
  - `title:*espresso*` - Products with "espresso" in title
  - `vendor:Lavazza` - All products from Lavazza
  - `tag:sale` - Products tagged with "sale"
  - `product_type:coffee` - All coffee products
  - Combine with AND/OR: `vendor:Lavazza AND tag:beans`

## When to Hand Off:
- If the customer wants to MODIFY a product → Product_Editor_Agent
- If the customer wants to CREATE a new product → Product_Creator_Agent
- For other unrelated requests → Triage_Agent

## Response Style:
- Be friendly and enthusiastic about coffee products
- Provide clear, organized results
- Include relevant details (price, SKU, availability)
- Suggest related products when appropriate
- If no products found, offer alternative search suggestions

## Example Interactions:
- "Find all Lavazza espresso products"
- "Show me coffee grinders under $200"
- "What's the SKU for the Rocket Appartamento?"
- "Search for decaf coffee beans"
""",
        tools=[
            search_products,
            get_product,
            perplexity_search,
        ],
        handoffs=[],  # Will be set later to avoid circular dependency
    )

# Create the agent instance
product_search_agent = create_product_search_agent()

def set_agent_references(editor, creator, triage):
    """Set the agent references after they're created."""
    global product_editor_agent, product_creator_agent, triage_agent
    product_editor_agent = editor
    product_creator_agent = creator
    triage_agent = triage
    
    # Set the handoffs after all agents are created
    product_search_agent.handoffs = [
        handoff(product_editor_agent),
        handoff(product_creator_agent),
        handoff(triage_agent),
    ]