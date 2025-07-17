# MCP Server Split Analysis

## Original Server (28 tools)
All 28 tools loaded together causing ~10k+ token bloat per agent invocation.

## Specialized Servers Status

### ✅ Products Server (6 tools)
- get_product
- search_products  
- create_product
- update_status
- graphql_query
- graphql_mutation

### ✅ Pricing Server (3 tools)
- update_pricing
- bulk_price_update
- update_costs

### ✅ Inventory Server (3 tools)
- manage_inventory_policy
- manage_tags
- manage_redirects

### ✅ Sales Server (2 tools)
- manage_miele_sales
- manage_map_sales

### ✅ Features Server (3 tools)
- manage_features_metaobjects
- update_metafields
- manage_variant_links

## Missing Tools (11 tools not yet moved to specialized servers)

### Media & Content (1 tool)
- add_product_images

### Marketing & Research (2 tools)
- send_review_request
- perplexity_research

### Memory System (1 tool)
- memory_operations

### SKU Vault Integration (2 tools)
- upload_to_skuvault
- manage_skuvault_kits

### Product Creation & Cloning (5 tools)
- create_full_product
- update_full_product
- add_variants_to_product
- create_combo
- create_open_box

## Recommended Additional Servers

### Media Server (1 tool)
- add_product_images

### Integrations Server (4 tools)
- send_review_request
- upload_to_skuvault
- manage_skuvault_kits
- memory_operations

### Product Management Server (3 tools)
- create_full_product
- update_full_product
- add_variants_to_product

### Product Cloning Server (2 tools)
- create_combo
- create_open_box

### Utility Server (1 tool)
- perplexity_research

## Current Progress
- **Completed**: 17/28 tools (61%) moved to specialized servers
- **Remaining**: 11/28 tools (39%) still need specialized servers
- **Token Reduction**: Each specialized server reduces token usage by ~75-90%

## Next Steps
1. Create the 5 additional specialized servers for the remaining 11 tools
2. Update MCP configuration to use specialized servers
3. Remove original mcp-server.py from active use
4. Test all specialized servers individually