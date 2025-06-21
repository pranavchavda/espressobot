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
        result = combo_module.create_combo_product(
            title=title,
            product_ids=product_ids,
            combo_price=combo_price,
            description=description if description else None,
            create_as_draft=create_as_draft
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
        result = open_box_module.create_open_box_variant(
            product_id=product_id,
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
        result = pricing_module.update_product_pricing(
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
        result = tags_module.manage_product_tags(
            product_id=product_id,
            add_tags=tags,
            remove_tags=[]
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
        result = tags_module.manage_product_tags(
            product_id=product_id,
            add_tags=[],
            remove_tags=tags
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
        result = tags_module.manage_product_tags(
            product_id=product_id,
            add_tags=add_tags if add_tags else [],
            remove_tags=remove_tags if remove_tags else []
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
        result = status_module.update_product_status(
            product_id=product_id,
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
        result = map_module.manage_map_pricing(
            product_id=product_id,
            enable_map=enable_map,
            map_price=map_price if map_price else None,
            sale_price=sale_price if sale_price else None
        )
        return json.dumps(result, indent=2)
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
        result = variant_links_module.manage_variant_relationships(
            product_id=product_id,
            linked_product_ids=linked_product_ids if linked_product_ids else [],
            link_type=link_type,
            unlink=unlink
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
            product_id=product_id,
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
        result = skuvault_module.upload_products_to_skuvault(
            product_id=product_id if product_id else None,
            sku=sku if sku else None,
            all_products=all_products,
            sync_inventory=sync_inventory
        )
        return json.dumps(result, indent=2)
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
        
        result = bulk_price_module.bulk_update_prices(
            updates=update_data,
            price_list_id=price_list_id if price_list_id else None
        )
        return json.dumps(result, indent=2)
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
        result = gql_query_module.run_graphql_query(
            query=query,
            variables=vars if vars else None
        )
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
        result = gql_mutation_module.run_graphql_mutation(
            mutation=mutation,
            variables=vars if vars else None
        )
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