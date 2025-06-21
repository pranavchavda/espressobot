from __future__ import annotations as _annotations

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ShopifyAgentContext(BaseModel):
    """Context for Shopify e-commerce agents."""
    # Store information
    store_name: str | None = "iDrinkCoffee.com"
    store_domain: str | None = "idrinkcoffee.myshopify.com"
    
    # Product context
    product_id: str | None = None
    product_handle: str | None = None
    product_title: str | None = None
    variant_id: str | None = None
    sku: str | None = None
    
    # Search and filter context
    search_query: str | None = None
    selected_products: List[str] = []
    filter_criteria: Dict[str, Any] = {}
    
    # Order context
    order_id: str | None = None
    customer_email: str | None = None
    
    # Task management context
    conversation_id: str | None = None
    current_task_id: str | None = None
    task_context: Dict[str, Any] = {}
    
    # Operation context
    last_operation: str | None = None
    operation_results: List[Dict[str, Any]] = []

def create_initial_context(conversation_id: str | None = None) -> ShopifyAgentContext:
    """
    Factory for a new ShopifyAgentContext.
    """
    ctx = ShopifyAgentContext()
    if conversation_id:
        ctx.conversation_id = conversation_id
    return ctx