"""EspressoBot Agents for Shopify operations."""

from .triage_agent import triage_agent, set_agent_references as set_triage_refs
from .product_search_agent import product_search_agent, set_agent_references as set_search_refs
from .product_editor_agent import product_editor_agent, set_agent_references as set_editor_refs
from .product_creator_agent import product_creator_agent, set_agent_references as set_creator_refs
from .inventory_manager_agent import inventory_manager_agent, set_agent_references as set_inventory_refs
from .analytics_orders_agent import analytics_orders_agent, set_agent_references as set_analytics_refs
from .task_manager_agent import task_manager_agent, set_agent_references as set_task_refs

# Initialize all agent references
def initialize_agent_references():
    """Set up all agent cross-references after import."""
    # Triage agent needs references to all other agents
    set_triage_refs(
        product_search_agent,
        product_editor_agent,
        product_creator_agent,
        inventory_manager_agent,
        analytics_orders_agent,
        task_manager_agent
    )
    
    # Product search agent references
    set_search_refs(
        product_editor_agent,
        product_creator_agent,
        triage_agent
    )
    
    # Product editor agent references
    set_editor_refs(
        product_search_agent,
        product_creator_agent,
        inventory_manager_agent,
        triage_agent
    )
    
    # Product creator agent references
    set_creator_refs(
        product_editor_agent,
        product_search_agent,
        triage_agent
    )
    
    # Inventory manager agent references
    set_inventory_refs(
        product_editor_agent,
        analytics_orders_agent,
        triage_agent
    )
    
    # Analytics & orders agent references
    set_analytics_refs(
        product_search_agent,
        inventory_manager_agent,
        triage_agent
    )
    
    # Task manager agent references
    set_task_refs(triage_agent)

# Initialize references on import
initialize_agent_references()

__all__ = [
    "triage_agent",
    "product_search_agent",
    "product_editor_agent",
    "product_creator_agent",
    "inventory_manager_agent",
    "analytics_orders_agent",
    "task_manager_agent",
]