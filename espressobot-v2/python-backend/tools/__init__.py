# Shopify Assistant Tools
from .base import ShopifyClient

# Import from shopify_tools which wraps all the native tools
from .shopify_tools import (
    # Search and Discovery
    search_products,
    get_product,
    perplexity_search,
    
    # Product Creation
    product_create_full,
    create_combo,
    create_open_box,
    
    # Product Editing
    update_pricing,
    add_tags_to_product,
    remove_tags_from_product,
    manage_tags,
    update_product_status,
    manage_map_sales,
    manage_variant_links,
    
    # Inventory Management
    manage_inventory_policy,
    upload_to_skuvault,
    bulk_price_update,
    
    # GraphQL Tools
    run_graphql_query,
    run_graphql_mutation,
    
    # Task Management
    generate_todos,
    get_todos,
    update_task_status,
)

# Export all tools
__all__ = [
    'ShopifyClient',
    'search_products',
    'get_product',
    'perplexity_search',
    'product_create_full',
    'create_combo',
    'create_open_box',
    'update_pricing',
    'add_tags_to_product',
    'remove_tags_from_product',
    'manage_tags',
    'update_product_status',
    'manage_map_sales',
    'manage_variant_links',
    'manage_inventory_policy',
    'upload_to_skuvault',
    'bulk_price_update',
    'run_graphql_query',
    'run_graphql_mutation',
    'generate_todos',
    'get_todos',
    'update_task_status',
]