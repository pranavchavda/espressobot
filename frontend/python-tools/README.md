# Python Tools for EspressoBot

This directory contains Python tools that agents can execute via bash commands. These tools provide direct integration with Shopify's Admin API and other e-commerce services.

## Tool Categories

### Product Management
- `search_products.py` - Search for products by various criteria
- `get_product.py` - Get detailed product information
- `create_product.py` - Create basic products
- `create_full_product.py` - Create products with all options
- `create_combo.py` - Create combo/bundle products
- `create_open_box.py` - Create open box items
- `update_pricing.py` - Update product/variant pricing
- `manage_tags.py` - Add/remove product tags
- `update_status.py` - Update product status (active/draft)
- `update_seo_full.py` - Update SEO fields
- `add_product_images.py` - Add images to products

### Inventory Management
- `manage_inventory_policy.py` - Update inventory policies
- `upload_to_skuvault.py` - Sync with SkuVault (external)

### Sales & Promotions
- `manage_map_sales.py` - Manage MAP protected sales
- `manage_miele_sales.py` - Manage Miele vendor promotions

### Bulk Operations
- `bulk_price_update.py` - Update multiple product prices via CSV

### GraphQL Operations
- `graphql_query.py` - Execute GraphQL queries
- `graphql_mutation.py` - Execute GraphQL mutations

### Utilities
- `pplx.py` - Perplexity AI integration for research
- `manage_redirects.py` - URL redirect management
- `manage_variant_relationships.py` - Link/unlink product variants

### Features & Metaobjects
- `manage_features_json.py` - Manage product features (JSON metafield)
- `manage_features_metaobjects.py` - Manage features via metaobjects

## Usage

Agents execute these tools using bash commands:

```bash
# Search for active coffee products
python3 /home/pranav/espressobot/frontend/python-tools/search_products.py "coffee" --status active

# Get product by SKU
python3 /home/pranav/espressobot/frontend/python-tools/get_product.py "SKU123"

# Update pricing
python3 /home/pranav/espressobot/frontend/python-tools/update_pricing.py "SKU123" --price 49.99

# Bulk price update via CSV
echo "SKU123,49.99" > /tmp/prices.csv
python3 /home/pranav/espressobot/frontend/python-tools/bulk_price_update.py /tmp/prices.csv
```

## Environment Variables

These tools require the following environment variables:
- `SHOPIFY_SHOP_URL` - Your Shopify store URL
- `SHOPIFY_ACCESS_TOKEN` - Admin API access token
- `OPENAI_API_KEY` - For AI features (optional)
- `PERPLEXITY_API_KEY` - For product research (optional)

## Adding New Tools

When adding new tools:
1. Follow the existing argument parsing pattern
2. Include proper error handling
3. Add --help documentation
4. Return JSON output when possible
5. Use exit codes appropriately (0 for success, non-zero for errors)