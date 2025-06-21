"""Main module for EspressoBot v0.2 - Shopify Agent System."""

from __future__ import annotations as _annotations

from agents import (
    Agent,
    GuardrailFunctionOutput,
    input_guardrail,
    RunContextWrapper,
)

# Import context
from context import create_initial_context, ShopifyAgentContext

# Import all agents
from shopify_agents import (
    triage_agent,
    product_search_agent,
    product_editor_agent,
    product_creator_agent,
    inventory_manager_agent,
    analytics_orders_agent,
    task_manager_agent,
)

# =========================
# GUARDRAILS
# =========================

@input_guardrail(name="Relevance Guardrail")
async def relevance_guardrail(
    context: RunContextWrapper[ShopifyAgentContext], 
    agent: Agent, 
    input: str | list
) -> GuardrailFunctionOutput | None:
    """
    Check if the user's message is relevant to Shopify/e-commerce operations.
    """
    # Extract the actual message text
    if isinstance(input, list):
        # Get the last user message
        user_messages = [item for item in input if isinstance(item, dict) and item.get('role') == 'user']
        if not user_messages:
            return None
        input_message = user_messages[-1].get('content', '')
    else:
        input_message = str(input)
    
    message_lower = input_message.lower()
    
    # Keywords that indicate relevant queries
    relevant_keywords = [
        # Product operations
        "product", "item", "sku", "variant", "inventory", "stock",
        "price", "cost", "tag", "category", "vendor", "brand",
        "create", "update", "edit", "modify", "search", "find",
        
        # E-commerce operations
        "order", "sale", "revenue", "customer", "shipping",
        "fulfillment", "discount", "promotion", "bundle", "combo",
        
        # Specific brands/products (common at iDrinkCoffee)
        "coffee", "espresso", "grinder", "machine", "lavazza",
        "rocket", "baratza", "breville", "delonghi",
        
        # Task management
        "task", "todo", "list", "bulk", "multiple", "all",
        
        # Analytics
        "report", "analyze", "data", "trend", "metric",
        
        # System operations
        "sync", "skuvault", "warehouse", "map", "graphql"
    ]
    
    # Check if message contains any relevant keywords
    if not any(keyword in message_lower for keyword in relevant_keywords):
        # Check for general help/greeting which is allowed
        if any(word in message_lower for word in ["hello", "hi", "help", "what can you do"]):
            # Allow general greetings
            return None
            
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info=GuardrailOutputInfo(
                explanation="I'm EspressoBot, specialized in Shopify operations for iDrinkCoffee.com. "
                          "I can help you search products, update prices, manage inventory, create bundles, "
                          "analyze sales data, and more. What Shopify task can I help you with today?"
            )
        )
    
    # Message is relevant, allow it through
    return None

@input_guardrail(name="Jailbreak Guardrail")
async def jailbreak_guardrail(
    context: RunContextWrapper[ShopifyAgentContext], 
    agent: Agent, 
    input: str | list
) -> GuardrailFunctionOutput | None:
    """
    Detect attempts to extract system prompts or bypass agent instructions.
    """
    # Extract the actual message text
    if isinstance(input, list):
        # Get the last user message
        user_messages = [item for item in input if isinstance(item, dict) and item.get('role') == 'user']
        if not user_messages:
            return None
        input_message = user_messages[-1].get('content', '')
    else:
        input_message = str(input)
    
    message_lower = input_message.lower()
    
    jailbreak_patterns = [
        "ignore previous", "ignore all previous", "disregard instructions",
        "system prompt", "show prompt", "reveal prompt", "display prompt",
        "what are your instructions", "show me your instructions",
        "forget everything", "new instructions", "you are now",
        "pretend to be", "act as if", "roleplay as",
        "bypass", "override", "hack"
    ]
    
    if any(pattern in message_lower for pattern in jailbreak_patterns):
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info=GuardrailOutputInfo(
                explanation="I'm designed to help with Shopify operations only. "
                          "Let me know how I can assist with product management, "
                          "inventory, orders, or analytics for your store."
            )
        )
    
    # Message is safe, allow it through
    return None

# Set up guardrails for all agents
def setup_guardrails():
    """Add guardrails to all agents."""
    all_agents = [
        triage_agent,
        product_search_agent,
        product_editor_agent,
        product_creator_agent,
        inventory_manager_agent,
        analytics_orders_agent,
        task_manager_agent,
    ]
    
    for agent in all_agents:
        agent.input_guardrails = [relevance_guardrail, jailbreak_guardrail]

# Set up guardrails on import
# Temporarily disabled due to openai-agents library compatibility issue
# The library expects .tripwire_triggered attribute on None objects
# setup_guardrails()

# Export everything needed by the API
__all__ = [
    "triage_agent",
    "product_search_agent", 
    "product_editor_agent",
    "product_creator_agent",
    "inventory_manager_agent",
    "analytics_orders_agent",
    "task_manager_agent",
    "create_initial_context",
]