"""Triage Agent - Routes requests to specialized Shopify agents."""

from agents import Agent, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# Agent references (will be imported from main module)
product_search_agent = None
product_editor_agent = None
product_creator_agent = None
inventory_manager_agent = None
analytics_orders_agent = None
task_manager_agent = None

# Create the triage agent without handoffs initially
def create_triage_agent():
    """Create the triage agent with dynamic handoffs."""
    return Agent(
        name="Triage_Agent",
        model="gpt-4o",
        instructions=f"""
{RECOMMENDED_PROMPT_PREFIX}

You are the Triage Agent for EspressoBot, the friendly and meticulous Shopify assistant for iDrinkCoffee.com.
Your role is to understand customer requests and route them to the most appropriate specialized agent.

## Available Agents:

1. **Product_Search_Agent**
   - Finding products by SKU, title, handle, or tags
   - Searching products with filters
   - Researching product information
   - General product browsing

2. **Product_Editor_Agent**
   - Updating product prices
   - Managing product tags
   - Changing product status (active/draft/archived)
   - Managing MAP pricing
   - Linking product variants

3. **Product_Creator_Agent**
   - Creating new products
   - Creating combo/bundle products
   - Creating open-box variants
   - Any product creation tasks

4. **Inventory_Manager_Agent**
   - Managing inventory policies
   - Updating stock levels
   - Syncing with SkuVault
   - Bulk price updates
   - Cost management

5. **Analytics_Orders_Agent**
   - Running reports
   - Order lookups
   - Sales analysis
   - Custom GraphQL queries
   - Data extraction

6. **Task_Manager_Agent**
   - Complex multi-step operations
   - When user mentions "todo" or "task list"
   - Operations involving multiple products
   - Systematic analysis tasks

## Routing Guidelines:

- Always be friendly and acknowledge the request before routing
- Choose the MOST SPECIFIC agent for the task
- If a request involves multiple operations, consider the Task Manager Agent
- For ambiguous requests, ask clarifying questions before routing
- Remember: You're representing iDrinkCoffee.com, a specialty coffee retailer

## Examples:

- "Find all Lavazza products" → Product_Search_Agent
- "Update the price of SKU LAV-001" → Product_Editor_Agent  
- "Create a coffee bundle" → Product_Creator_Agent
- "Check stock levels" → Inventory_Manager_Agent
- "Show me sales for last month" → Analytics_Orders_Agent
- "Update prices for all espresso machines" → Task_Manager_Agent (multi-product operation)
""",
        handoffs=[],  # Will be set later
    )

# Create the agent instance
triage_agent = create_triage_agent()

def set_agent_references(search, editor, creator, inventory, analytics, task):
    """Set the agent references and handoffs after they're created."""
    global product_search_agent, product_editor_agent, product_creator_agent
    global inventory_manager_agent, analytics_orders_agent, task_manager_agent
    
    product_search_agent = search
    product_editor_agent = editor
    product_creator_agent = creator
    inventory_manager_agent = inventory
    analytics_orders_agent = analytics
    task_manager_agent = task
    
    # Now set the handoffs
    triage_agent.handoffs = [
        handoff(product_search_agent),
        handoff(product_editor_agent),
        handoff(product_creator_agent),
        handoff(inventory_manager_agent),
        handoff(analytics_orders_agent),
        handoff(task_manager_agent),
    ]