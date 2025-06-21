"""
Shopify tools for OpenAI agents - Native Python imports version.
These tools are imported directly as Python modules instead of subprocess calls.
"""

import json
import os
import sys
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from agents import RunContextWrapper, function_tool
from context import ShopifyAgentContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the tools directory to Python path so we can import the tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the individual tool modules
import base
import search_products as search_module
import get_product as get_module
import create_full_product as create_full_module
import create_combo as combo_module
import create_open_box as open_box_module
import update_pricing as pricing_module
import manage_tags as tags_module
import update_status as status_module
import manage_map_sales as map_module
import manage_variant_links as variant_links_module
import manage_inventory_policy as inventory_policy_module
import upload_to_skuvault as skuvault_module
import bulk_price_update as bulk_price_module
import graphql_query as gql_query_module
import graphql_mutation as gql_mutation_module
import pplx as pplx_module

# Pydantic models for complex types
class ProductVariant(BaseModel):
    """Product variant data."""
    title: str = "Default Title"
    price: str = "0.00"
    sku: str = ""
    inventory_quantity: int = 0

class PriceUpdate(BaseModel):
    """Price update data."""
    product_id: str = ""
    variant_id: str = ""
    sku: str = ""
    price: str
    compare_at_price: str = ""

# Search and Discovery Tools

@function_tool
async def search_products(
    context: RunContextWrapper[ShopifyAgentContext],
    query: str,
    limit: int = 10,
    fields: str = "all"
) -> str:
    """Search for products in the Shopify store.
    
    Args:
        query: Search query using Shopify syntax (e.g., "coffee machine", "price:<500")
        limit: Number of products to return (default: 10)
        fields: Fields to include in results (default: "all")
    """
    context.context.search_query = query
    
    try:
        # Convert fields string to list
        field_list = ['all'] if fields == 'all' else fields.split(',')
        
        # Call the native function
        results = search_module.search_products(query, limit=limit, fields=field_list)
        
        # Extract products from edges
        products = [edge['node'] for edge in results.get('edges', [])]
        
        return json.dumps({
            "products": products,
            "count": len(products),
            "has_next_page": results.get('pageInfo', {}).get('hasNextPage', False)
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"}, indent=2)

@function_tool
async def get_product(
    context: RunContextWrapper[ShopifyAgentContext],
    id: str = "",
    handle: str = "",
    sku: str = ""
) -> str:
    """Get detailed information about a specific product."""
    if id:
        context.context.product_id = id
    elif handle:
        context.context.product_handle = handle
    elif sku:
        context.context.sku = sku
    
    try:
        # The get_product module expects these as function parameters
        result = get_module.get_product_info(
            product_id=id if id else None,
            handle=handle if handle else None,
            sku=sku if sku else None
        )
        
        # Update context with product info if found
        if result and not result.get('error'):
            product = result
            context.context.product_id = product.get("id")
            context.context.product_title = product.get("title")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Get product failed: {str(e)}"}, indent=2)

# Product Creation Tools

@function_tool
async def product_create_full(
    context: RunContextWrapper[ShopifyAgentContext],
    title: str,
    description: str = "",
    product_type: str = "",
    vendor: str = "",
    tags: List[str] = [],
    variants: List[ProductVariant] = []
) -> str:
    """Create a new product with all details."""
    try:
        # Convert variants to the format expected by the native function
        variant_data = []
        for v in variants:
            variant_data.append({
                "title": v.title,
                "price": v.price,
                "sku": v.sku,
                "inventory_quantity": v.inventory_quantity
            })
        
        result = create_full_module.create_full_product(
            title=title,
            description=description if description else None,
            product_type=product_type if product_type else None,
            vendor=vendor if vendor else None,
            tags=tags if tags else None,
            variants=variant_data if variant_data else None
        )
        
        # Update context with new product info
        if result and not result.get('error'):
            product = result.get("product", {})
            context.context.product_id = product.get("id")
            context.context.product_title = product.get("title")
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Product creation failed: {str(e)}"}, indent=2)

@function_tool
async def create_combo(
    context: RunContextWrapper[ShopifyAgentContext],
    title: str,
    product_ids: List[str],
    combo_price: str,
    description: str = "",
    create_as_draft: bool = True
) -> str:
    """Create a combo/bundle product from multiple existing products."""
    try:
        # create_combo_listing expects two product IDs
        if len(product_ids) < 2:
            return json.dumps({"error": "At least 2 product IDs required for combo"}, indent=2)
        
        # Create a ShopifyClient instance
        client = base.ShopifyClient()
        
        # Call with the correct function name and parameters
        result = combo_module.create_combo_listing(
            client=client,
            product1_id=product_ids[0],
            product2_id=product_ids[1],
            sku_suffix=None,  # Let it auto-generate
            discount_amount=None,  # Use specific price instead
            discount_percent=None,
            price=float(combo_price),
            publish=not create_as_draft  # publish=False means draft
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Combo creation failed: {str(e)}"}, indent=2)

@function_tool
async def create_open_box(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    discount_percentage: int = 15,
    condition_notes: str = "Open box - inspected and certified",
    inventory_quantity: int = 1
) -> str:
    """Create an open box variant of an existing product."""
    try:
        # Create a ShopifyClient instance
        client = base.ShopifyClient()
        
        # First find the product
        original_product = open_box_module.find_product(client, product_id)
        if not original_product:
            return json.dumps({"error": f"Product not found: {product_id}"}, indent=2)
        
        # Create the open box product
        result = open_box_module.create_open_box_product(
            client=client,
            original=original_product,
            discount_percentage=discount_percentage,
            condition_notes=condition_notes,
            inventory_quantity=inventory_quantity
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Open box creation failed: {str(e)}"}, indent=2)

# Product Editing Tools

@function_tool
async def update_pricing(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str = "",
    variant_id: str = "",
    price: str = "",
    compare_at_price: str = ""
) -> str:
    """Update product or variant pricing."""
    try:
        result = pricing_module.update_variant_pricing(
            product_id=product_id if product_id else None,
            variant_id=variant_id if variant_id else None,
            price=price if price else None,
            compare_at_price=compare_at_price if compare_at_price else None
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Price update failed: {str(e)}"}, indent=2)

@function_tool
async def add_tags_to_product(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    tags: List[str]
) -> str:
    """Add tags to a product."""
    try:
        result = tags_module.manage_tags(
            action="add",
            identifier=product_id,
            tags=tags
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Add tags failed: {str(e)}"}, indent=2)

@function_tool
async def remove_tags_from_product(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    tags: List[str]
) -> str:
    """Remove tags from a product."""
    try:
        result = tags_module.manage_tags(
            action="remove",
            identifier=product_id,
            tags=tags
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Remove tags failed: {str(e)}"}, indent=2)

@function_tool
async def manage_tags(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    add_tags: List[str] = [],
    remove_tags: List[str] = []
) -> str:
    """Add or remove multiple tags from a product in one operation."""
    try:
        # Handle adding tags first
        if add_tags:
            result = tags_module.manage_tags(
                action="add",
                identifier=product_id,
                tags=add_tags
            )
            if result.get('error'):
                return json.dumps(result, indent=2)
        
        # Then handle removing tags
        if remove_tags:
            result = tags_module.manage_tags(
                action="remove",
                identifier=product_id,
                tags=remove_tags
            )
            
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Manage tags failed: {str(e)}"}, indent=2)

@function_tool
async def update_product_status(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    status: str
) -> str:
    """Update product status (ACTIVE, DRAFT, ARCHIVED)."""
    try:
        result = status_module.update_status(
            identifier=product_id,
            status=status
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Status update failed: {str(e)}"}, indent=2)

@function_tool
async def manage_map_sales(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    enable_map: bool,
    map_price: str = "",
    sale_price: str = ""
) -> str:
    """Manage MAP (Minimum Advertised Price) sales for products."""
    try:
        # manage_map_sales.py is a CLI tool, need to call it differently
        # For now, return not implemented
        return json.dumps({"error": "MAP sales management not yet implemented in native mode"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"MAP management failed: {str(e)}"}, indent=2)

@function_tool
async def manage_variant_links(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    linked_product_ids: List[str] = [],
    link_type: str = "variant",
    unlink: bool = False
) -> str:
    """Manage variant links between products."""
    try:
        if unlink:
            result = variant_links_module.unlink_products(
                product_id=product_id,
                linked_product_ids=linked_product_ids if linked_product_ids else []
            )
        else:
            result = variant_links_module.link_products(
                product_id=product_id,
                linked_product_ids=linked_product_ids if linked_product_ids else [],
                link_type=link_type
            )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Variant link management failed: {str(e)}"}, indent=2)

# Inventory Tools

@function_tool
async def manage_inventory_policy(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    policy: str,
    apply_to_all_variants: bool = True
) -> str:
    """Update inventory policy for products."""
    try:
        result = inventory_policy_module.update_inventory_policy(
            identifier=product_id,
            policy=policy,
            apply_to_all_variants=apply_to_all_variants
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Inventory policy update failed: {str(e)}"}, indent=2)

@function_tool
async def upload_to_skuvault(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str = "",
    sku: str = "",
    all_products: bool = False,
    sync_inventory: bool = True
) -> str:
    """Upload product data to SkuVault inventory management system."""
    try:
        # upload_to_skuvault.py is a CLI tool, need to handle differently
        # For now, return not implemented
        return json.dumps({"error": "SkuVault upload not yet implemented in native mode"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"SkuVault upload failed: {str(e)}"}, indent=2)

@function_tool
async def bulk_price_update(
    context: RunContextWrapper[ShopifyAgentContext],
    updates: List[PriceUpdate],
    price_list_id: str = ""
) -> str:
    """Update prices for multiple products or variants in bulk."""
    try:
        # Convert PriceUpdate objects to dicts
        update_data = []
        for u in updates:
            update_data.append({
                "product_id": u.product_id,
                "variant_id": u.variant_id,
                "sku": u.sku,
                "price": u.price,
                "compare_at_price": u.compare_at_price
            })
        
        # bulk_price_update uses CSV, so we need to handle it differently
        # For now, update each price individually
        results = []
        for update in update_data:
            try:
                result = pricing_module.update_variant_pricing(
                    product_id=update.get('product_id'),
                    variant_id=update.get('variant_id'),
                    price=update.get('price'),
                    compare_at_price=update.get('compare_at_price')
                )
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "update": update})
        
        return json.dumps({"results": results, "total": len(update_data)}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Bulk price update failed: {str(e)}"}, indent=2)

# GraphQL Tools

@function_tool
async def run_graphql_query(
    context: RunContextWrapper[ShopifyAgentContext],
    query: str,
    variables: Optional[str] = None
) -> str:
    """Execute a custom GraphQL query against Shopify Admin API.
    
    Args:
        query: The GraphQL query string
        variables: JSON string of variables (e.g. '{"id": "gid://shopify/Product/123"}')
    """
    vars = {}
    if variables:
        try:
            vars = json.loads(variables)
        except json.JSONDecodeError:
            pass
    
    try:
        # Since graphql_query.py is a CLI tool, we execute it directly
        client = base.ShopifyClient()
        result = client.execute_graphql(query, vars if vars else None)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"GraphQL query failed: {str(e)}"}, indent=2)

@function_tool
async def run_graphql_mutation(
    context: RunContextWrapper[ShopifyAgentContext],
    mutation: str,
    variables: Optional[str] = None
) -> str:
    """Execute a custom GraphQL mutation against Shopify Admin API.
    
    Args:
        mutation: The GraphQL mutation string
        variables: JSON string of variables (e.g. '{"input": {"id": "gid://shopify/Product/123"}}')
    """
    vars = {}
    if variables:
        try:
            vars = json.loads(variables)
        except json.JSONDecodeError:
            pass
    
    try:
        # Since graphql_mutation.py is a CLI tool, we execute it directly
        client = base.ShopifyClient()
        result = client.execute_graphql(mutation, vars if vars else None)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"GraphQL mutation failed: {str(e)}"}, indent=2)

# Research Tools

@function_tool
async def perplexity_search(
    context: RunContextWrapper[ShopifyAgentContext],
    query: str,
    focus: str = "web",
    include_sources: bool = True
) -> str:
    """Query Perplexity AI for research, product information, or general questions."""
    try:
        result = pplx_module.search_perplexity(
            query=query,
            focus=focus,
            include_sources=include_sources
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Perplexity search failed: {str(e)}"}, indent=2)

# Task Management Tools
# Note: These tools don't have native implementations yet, so we'll keep them as subprocess calls
# or implement them separately

@function_tool
async def generate_todos(
    context: RunContextWrapper[ShopifyAgentContext],
    conversation_id: str,
    task_context: str
) -> str:
    """Generate a todo list for complex operations."""
    # This would need to be implemented natively or kept as subprocess
    return json.dumps({"error": "Task management tools not yet implemented natively"}, indent=2)

@function_tool
async def get_todos(
    context: RunContextWrapper[ShopifyAgentContext],
    conversation_id: str
) -> str:
    """Get the current todo list for a conversation."""
    # This would need to be implemented natively or kept as subprocess
    return json.dumps({"error": "Task management tools not yet implemented natively"}, indent=2)

@function_tool
async def update_task_status(
    context: RunContextWrapper[ShopifyAgentContext],
    task_id: str,
    status: str
) -> str:
    """Update the status of a task."""
    # This would need to be implemented natively or kept as subprocess
    return json.dumps({"error": "Task management tools not yet implemented natively"}, indent=2)