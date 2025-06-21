"""
Shopify tools for OpenAI agents.
These are Python wrappers that call the existing EspressoBot custom tools.
"""

import subprocess
import json
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from agents import RunContextWrapper, function_tool
from context import ShopifyAgentContext

# Path to the Python tools directory
TOOLS_PATH = "/home/pranav/idc/tools"
TOOLS_DIR = TOOLS_PATH  # Alias for compatibility

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

def execute_python_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Python tool from the tools directory."""
    tool_path = os.path.join(TOOLS_PATH, f"{tool_name}.py")
    
    if not os.path.exists(tool_path):
        return {"error": f"Tool {tool_name} not found at {tool_path}"}
    
    try:
        # Convert args to command line arguments
        cmd = ["python", tool_path]
        for key, value in args.items():
            if value is not None and value != "":
                if isinstance(value, bool):
                    if value:
                        cmd.append(f"--{key}")
                elif isinstance(value, list):
                    cmd.extend([f"--{key}", json.dumps(value)])
                else:
                    cmd.extend([f"--{key}", str(value)])
        
        # Execute the tool
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return {"error": f"Tool execution failed: {result.stderr}"}
        
        # Parse the output as JSON
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"output": result.stdout, "error": "Invalid JSON response"}
    
    except subprocess.TimeoutExpired:
        return {"error": "Tool execution timed out"}
    except Exception as e:
        return {"error": f"Tool execution error: {str(e)}"}

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
    # Special handling for search_products which expects query as positional arg
    cmd = ["python", f"{TOOLS_DIR}/search_products.py", query]
    if limit != 10:
        cmd.extend(["--limit", str(limit)])
    if fields != "all":
        cmd.extend(["--fields", fields])
    cmd.extend(["--output", "json"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return json.dumps({"error": f"Tool execution failed: {result.stderr}"})
        return result.stdout
    except Exception as e:
        return json.dumps({"error": f"Tool execution error: {str(e)}"}, indent=2)

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
    
    result = execute_python_tool("get_product", {
        "id": id,
        "handle": handle,
        "sku": sku
    })
    
    # Update context with product info if found
    if "product" in result:
        product = result["product"]
        context.context.product_id = product.get("id")
        context.context.product_title = product.get("title")
    
    return json.dumps(result, indent=2)

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
    result = execute_python_tool("product_create_full", {
        "title": title,
        "description": description,
        "product_type": product_type,
        "vendor": vendor,
        "tags": tags,
        "variants": [v.model_dump() for v in variants] if variants else []
    })
    
    # Update context with new product info
    if "product" in result:
        product = result["product"]
        context.context.product_id = product.get("id")
        context.context.product_title = product.get("title")
    
    return json.dumps(result, indent=2)

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
    result = execute_python_tool("create_combo", {
        "title": title,
        "product_ids": product_ids,
        "combo_price": combo_price,
        "description": description,
        "create_as_draft": create_as_draft
    })
    return json.dumps(result, indent=2)

@function_tool
async def create_open_box(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    discount_percentage: int = 15,
    condition_notes: str = "Open box - inspected and certified",
    inventory_quantity: int = 1
) -> str:
    """Create an open box variant of an existing product."""
    result = execute_python_tool("create_open_box", {
        "product_id": product_id,
        "discount_percentage": discount_percentage,
        "condition_notes": condition_notes,
        "inventory_quantity": inventory_quantity
    })
    return json.dumps(result, indent=2)

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
    result = execute_python_tool("update_pricing", {
        "product_id": product_id,
        "variant_id": variant_id,
        "price": price,
        "compare_at_price": compare_at_price
    })
    return json.dumps(result, indent=2)

@function_tool
async def add_tags_to_product(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    tags: List[str]
) -> str:
    """Add tags to a product."""
    result = execute_python_tool("add_tags_to_product", {
        "product_id": product_id,
        "tags": tags
    })
    return json.dumps(result, indent=2)

@function_tool
async def remove_tags_from_product(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    tags: List[str]
) -> str:
    """Remove tags from a product."""
    result = execute_python_tool("remove_tags_from_product", {
        "product_id": product_id,
        "tags": tags
    })
    return json.dumps(result, indent=2)

@function_tool
async def manage_tags(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    add_tags: List[str] = [],
    remove_tags: List[str] = []
) -> str:
    """Add or remove multiple tags from a product in one operation."""
    result = execute_python_tool("manage_tags", {
        "product_id": product_id,
        "add_tags": add_tags,
        "remove_tags": remove_tags
    })
    return json.dumps(result, indent=2)

@function_tool
async def update_product_status(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    status: str
) -> str:
    """Update product status (ACTIVE, DRAFT, ARCHIVED)."""
    result = execute_python_tool("update_product_status", {
        "product_id": product_id,
        "status": status
    })
    return json.dumps(result, indent=2)

@function_tool
async def manage_map_sales(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    enable_map: bool,
    map_price: str = "",
    sale_price: str = ""
) -> str:
    """Manage MAP (Minimum Advertised Price) sales for products."""
    result = execute_python_tool("manage_map_sales", {
        "product_id": product_id,
        "enable_map": enable_map,
        "map_price": map_price,
        "sale_price": sale_price
    })
    return json.dumps(result, indent=2)

@function_tool
async def manage_variant_links(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    linked_product_ids: List[str] = [],
    link_type: str = "variant",
    unlink: bool = False
) -> str:
    """Manage variant links between products."""
    result = execute_python_tool("manage_variant_links", {
        "product_id": product_id,
        "linked_product_ids": linked_product_ids,
        "link_type": link_type,
        "unlink": unlink
    })
    return json.dumps(result, indent=2)

# Inventory Tools

@function_tool
async def manage_inventory_policy(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str,
    policy: str,
    apply_to_all_variants: bool = True
) -> str:
    """Update inventory policy for products."""
    result = execute_python_tool("manage_inventory_policy", {
        "product_id": product_id,
        "policy": policy,
        "apply_to_all_variants": apply_to_all_variants
    })
    return json.dumps(result, indent=2)

@function_tool
async def upload_to_skuvault(
    context: RunContextWrapper[ShopifyAgentContext],
    product_id: str = "",
    sku: str = "",
    all_products: bool = False,
    sync_inventory: bool = True
) -> str:
    """Upload product data to SkuVault inventory management system."""
    result = execute_python_tool("upload_to_skuvault", {
        "product_id": product_id,
        "sku": sku,
        "all_products": all_products,
        "sync_inventory": sync_inventory
    })
    return json.dumps(result, indent=2)

@function_tool
async def bulk_price_update(
    context: RunContextWrapper[ShopifyAgentContext],
    updates: List[PriceUpdate],
    price_list_id: str = ""
) -> str:
    """Update prices for multiple products or variants in bulk."""
    result = execute_python_tool("bulk_price_update", {
        "updates": [u.model_dump() for u in updates] if updates else [],
        "price_list_id": price_list_id
    })
    return json.dumps(result, indent=2)

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
    
    result = execute_python_tool("run_full_shopify_graphql_query", {
        "query": query,
        "variables": vars
    })
    return json.dumps(result, indent=2)

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
    
    result = execute_python_tool("run_full_shopify_graphql_mutation", {
        "mutation": mutation,
        "variables": vars
    })
    return json.dumps(result, indent=2)

# Research Tools

@function_tool
async def perplexity_search(
    context: RunContextWrapper[ShopifyAgentContext],
    query: str,
    focus: str = "web",
    include_sources: bool = True
) -> str:
    """Query Perplexity AI for research, product information, or general questions."""
    result = execute_python_tool("pplx", {
        "query": query,
        "focus": focus,
        "include_sources": include_sources
    })
    return json.dumps(result, indent=2)

# Task Management Tools

@function_tool
async def generate_todos(
    context: RunContextWrapper[ShopifyAgentContext],
    conversation_id: str,
    task_context: str
) -> str:
    """Generate a todo list for complex operations."""
    result = execute_python_tool("generate_todos", {
        "conversation_id": conversation_id,
        "context": task_context
    })
    return json.dumps(result, indent=2)

@function_tool
async def get_todos(
    context: RunContextWrapper[ShopifyAgentContext],
    conversation_id: str
) -> str:
    """Get the current todo list for a conversation."""
    result = execute_python_tool("get_todos", {
        "conversation_id": conversation_id
    })
    return json.dumps(result, indent=2)

@function_tool
async def update_task_status(
    context: RunContextWrapper[ShopifyAgentContext],
    task_id: str,
    status: str
) -> str:
    """Update the status of a task."""
    result = execute_python_tool("update_task_status", {
        "task_id": task_id,
        "status": status
    })
    return json.dumps(result, indent=2)