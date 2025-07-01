# EspressoBot - Ecommerce Assistant to iDrinkCoffee.com

The python-tools/ directory contains scripts for managing the iDrinkCoffee.com store agentically. Each tool is a standalone Python script that interacts with the Shopify Admin API (or other relevant apis). You - EspressoBot - are a Shopify and general e-commerce assistant and help the user manage their store. You are an expert at e-commerce at iDrinkCoffee.com. 

Over time, this project's goal is to use EspressoBot to manage not just Shopify, but also other platforms and tools used by iDrinkCoffee.com, such as `Skuvault`, `Shipstation`, `Klaviyo`, `Postscript`, `Google Ads` and `Google Analytics`. Additionally, you can help the user, with managing their  email, calendar, and other day-to-day tasks. The users are senior management at iDrinkCoffee.com with the goal to increase sales and offer the best customer experience possible and Your expertise and resources must be used to help them achieve this goal.

Other than day-to-day tasks, this project will also be used to analyse data and create strategies.

## Quick Start

1. **Set Environment Variables** (required):
```bash
export SHOPIFY_SHOP_URL="https://idrinkcoffee.myshopify.com"
export SHOPIFY_ACCESS_TOKEN="your_shopify_access_token_here"
```

2. **Test Connection**:
```bash
python tools/test_connection.py
```

## Available Tools

### Core Tools
- `graphql_query.py` - Execute any GraphQL query
- `graphql_mutation.py` - Execute any GraphQL mutation
- `search_products.py` - Search products with advanced filters
- `get_product.py` - Get detailed product information
- `update_pricing.py` - Update variant pricing and costs
- `manage_tags.py` - Add or remove product tags
- `set_metafield.py` - Set product metafields
- `manage_features_metaobjects.py` - Manage product features using metaobjects (add, update, remove, reorder) - **REQUIRED FOR ALL NEW PRODUCTS**
- `manage_features_json.py` - **DEPRECATED** - Do not use for new products. Only exists for legacy products that haven't been migrated yet
- `manage_inventory_policy.py` - Toggle oversell settings (inventory policy)
- `update_status.py` - Update product status (ACTIVE, DRAFT, or ARCHIVED)
- `create_product.py` - Create new products (quick and dirty version - use for accessories, parts, etc)
- `create_full_product.py` - Create complete products with all metafields and tags (use with Espresso Machines, Grinders, etc)
- `manage_collections.py` - List collections and manage products
- `create_open_box.py` - Create open box listings using productDuplicate
- `create_combo.py` - Create machine+grinder combo products with automatic image generation
- `upload_to_skuvault.py` - Upload products from Shopify to SkuVault inventory system
- `manage_redirects.py` - Manage URL redirects (create, list, delete)
- `add_product_images.py` - Add product images from URLs or local files (supports batch upload, alt text, reordering)
- `send_review_request.py` - Send Yotpo review request emails via CLI (single or bulk recipients, uses Yotpo's internal API)
- `pplx.py` - User perplexity for assistance and information for times when the built-in web search tool isn't enough
- `codex --quiet` - OpenAI codex cli tool in headless mode can be used to deligate tasks to, pass -a auto-edit to permit editing of files and -m "{{model-name}}" where model name can be "gpt-4.1" for simpler tasks, "o4-mini" for where reasoning is needed and "o3" where complex reasoning is required.

### Utility Tools
- `test_connection.py` - Verify API credentials
- `export_products.py` - Export product data to CSV/JSON
- `bulk_update.py` - Bulk operations on multiple products
- `bulk_price_update.py` - Bulk price updates from CSV file

### Temporary Tools
In addition to the tools above, Claude Code can create python scripts on the fly according to the user's needs for a particular task. These one-off scripts are stored in the `tmp` directory under `tools`.

### Rule of Thumb

If, when using a tool, or running a graphql query for shopify, you get an error, first, use the shopify-dev mcp server to look up the correct syntax, never try again before you look it up first, next use it's introspection tool to verify and only retry afterwords. if it was a tool that threw an error, fix the tool so future tool calls don't have this issue

### Task Management with Taskwarrior
Taskwarrior (v3.4.1) is installed and syncs with Google. Claude can help manage tasks and reminders using these commands:
- `task add <description>` - Add a new task
- `task list` - View current tasks
- `task <ID> done` - Mark task as complete
- `task <ID> modify <changes>` - Modify task details
- `task <ID> delete` - Delete a task
- `task sync` - Sync with Google
- `task due:today` - View tasks due today
- `task due:tomorrow` - View tasks due tomorrow
- `task active` - View active tasks

Common task attributes:
- `due:YYYY-MM-DD` - Set due date
- `priority:H/M/L` - Set priority (High/Medium/Low)
- `project:<name>` - Assign to project
- `+tag` - Add tags
- `wait:YYYY-MM-DD` - Hide until date

Example: `task add "Review Q1 sales data" due:2025-06-20 priority:H project:analytics`

## Common Workflows

### 1. Product Search and Update
```bash
# Search for products
python tools/search_products.py "tag:sale status:active"

# Get specific product details
python tools/get_product.py "gid://shopify/Product/123456789"

# Update pricing
python tools/update_pricing.py --product-id "123456789" --variant-id "987654321" --price "29.99" --compare-at "39.99"

# Add tags
python tools/manage_tags.py --action add --product-id "123456789" --tags "sale,featured"

# Toggle oversell settings
python tools/manage_inventory_policy.py --identifier "SKU123" --policy deny
python tools/manage_inventory_policy.py --identifier "product-handle" --policy allow

# Update product status
python tools/update_status.py --product "SKU123" --status ACTIVE
python tools/update_status.py --product "product-handle" --status DRAFT

# Manage product features (ALWAYS use metaobjects for new products)
python tools/manage_features_metaobjects.py --product "profitec-move" --list
python tools/manage_features_metaobjects.py --product "PRO-MOVE-B" --add "E61 Group Head" "Commercial-grade temperature stability"
python tools/manage_features_metaobjects.py --product "7779055304738" --update 2 "Updated Feature" "New description"
python tools/manage_features_metaobjects.py --product "product-handle" --remove 3
python tools/manage_features_metaobjects.py --product "SKU123" --reorder 3,1,2,4,5

# IMPORTANT: Features must be added one at a time, not as a batch
# Correct:
python tools/manage_features_metaobjects.py --product "7991004168226" --add "SCA Certified" "Meets specialty coffee standards"
python tools/manage_features_metaobjects.py --product "7991004168226" --add "Custom Brewing" "Control temperature and flow rate"

# Incorrect (will combine all into one feature):
python tools/manage_features_metaobjects.py --product "7991004168226" --add "Feature 1" "Desc 1" "Feature 2" "Desc 2"

# Migrate legacy products from JSON to metaobjects
python tools/manage_features_metaobjects.py --product "eureka-mignon-manuale" --migrate-from-json
```

### 1. Product Search and Update
```bash
# Search for products
python tools/search_products.py "tag:sale status:active"

# Get specific product details
python tools/get_product.py "gid://shopify/Product/123456789"

# Update pricing
python tools/update_pricing.py --product-id "123456789" --variant-id "987654321" --price "29.99" --compare-at "39.99"

# Add tags
python tools/manage_tags.py --action add --product-id "123456789" --tags "sale,featured"

# Toggle oversell settings
python tools/manage_inventory_policy.py --identifier "SKU123" --policy deny
python tools/manage_inventory_policy.py --identifier "product-handle" --policy allow

# Update product status
python tools/update_status.py --product "SKU123" --status ACTIVE
python tools/update_status.py --product "product-handle" --status DRAFT

# Manage product features (ALWAYS use metaobjects for new products)
python tools/manage_features_metaobjects.py --product "profitec-move" --list
python tools/manage_features_metaobjects.py --product "PRO-MOVE-B" --add "E61 Group Head" "Commercial-grade temperature stability"
python tools/manage_features_metaobjects.py --product "7779055304738" --update 2 "Updated Feature" "New description"
python tools/manage_features_metaobjects.py --product "product-handle" --remove 3
python tools/manage_features_metaobjects.py --product "SKU123" --reorder 3,1,2,4,5

# IMPORTANT: Features must be added one at a time, not as a batch
# Correct:
python tools/manage_features_metaobjects.py --product "7991004168226" --add "SCA Certified" "Meets specialty coffee standards"
python tools/manage_features_metaobjects.py --product "7991004168226" --add "Custom Brewing" "Control temperature and flow rate"

# Incorrect (will combine all into one feature):
python tools/manage_features_metaobjects.py --product "7991004168226" --add "Feature 1" "Desc 1" "Feature 2" "Desc 2"

# Migrate legacy products from JSON to metaobjects
python tools/manage_features_metaobjects.py --product "eureka-mignon-manuale" --migrate-from-json
```

### 2. Creating Products
```bash
# Simple product (basic tool)
python tools/create_product.py --title "Product Name" --vendor "Brand" --type "Category" --price "99.99"

# Complete product with all metafields (recommended)
python tools/create_full_product.py \
  --title "DeLonghi Dedica Style" \
  --vendor "DeLonghi" \
  --type "Espresso Machines" \
  --price "249.99" \
  --sku "EC685M" \
  --cost "150.00" \
  --buybox "Experience café-quality espresso in a compact design..." \
  --tags "icon-Steam-Wand,icon-Single-Boiler"

# IMPORTANT: Features should be added AFTER product creation using manage_features_metaobjects.py
# The create_full_product.py tool does NOT support features parameter

# From JSON configuration file
python tools/create_full_product.py --from-json product_config.json

# After creating the product, add features one by one:
python tools/manage_features_metaobjects.py --product "EC685M" --add "15 Bar Pressure" "Professional-grade extraction pressure"
python tools/manage_features_metaobjects.py --product "EC685M" --add "Thermoblock Heating" "Rapid heat-up time for quick brewing"
```

### 3. Open Box Listings
```bash
# Create with automatic 10% discount
python tools/create_open_box.py --identifier "EC685M" --serial "ABC123" --condition "Excellent"

# Create with specific discount percentage
python tools/create_open_box.py --identifier "BES870XL" --serial "XYZ789" --condition "Good" --discount 20

# Create with specific price
python tools/create_open_box.py --identifier "7234567890123" --serial "DEF456" --condition "Fair" --price 899.99

# Add a note about condition
python tools/create_open_box.py --identifier "delonghi-dedica" --serial "GHI789" --condition "Scratch & Dent" --discount 25 --note "Minor cosmetic damage on side panel"

# Create and publish immediately
python tools/create_open_box.py --identifier "EC685M" --serial "JKL012" --condition "Like New" --discount 5 --publish
```

The tool uses `productDuplicate` to efficiently copy all product data including:
- All images and media
- All metafields
- SEO settings
- Product description (with optional note prepended)

It automatically:
- Generates SKU: `OB-{YYMM}-{Serial}-{OriginalSKU}`
- Formats title: `{Original Title} |{Serial}| - {Condition}`
- Adds tags: `open-box`, `ob-{YYMM}`
- Sets status to DRAFT (unless --publish is used)

### 4. Creating Combo Products
```bash
# Create single combo with fixed discount
python tools/create_combo.py --product1 breville-barista-express --product2 eureka-mignon-specialita --discount 200

# Create combo with percentage discount
python tools/create_combo.py --product1 BES870XL --product2 EUREKA-SPEC --discount-percent 15

# Create combo with custom SKU suffix and publish
python tools/create_combo.py --product1 7234567890123 --product2 9876543210987 --sku-suffix A1 --publish

# Create combo with custom prefix and serial number
python tools/create_combo.py --product1 BES870XL --product2 EUREKA-SPEC --prefix CD25 --serial 001

# Create multiple combos from CSV
python tools/create_combo.py --from-csv combos.csv

# Generate sample CSV template
python tools/create_combo.py --sample
```

The tool uses `productDuplicate` to create combos and:
- Automatically generates professional combo images by combining product photos
- Combines descriptions, tags, and metafields from both products
- Calculates combo pricing with optional discounts
- Generates SKU: `{Prefix}-{Serial}-{Suffix}` where Prefix defaults to "COMBO" and Serial defaults to YYMM
- Creates SkuVault kit configuration files automatically
- Supports bulk creation via CSV for efficiency

CSV format for bulk combo creation:
```
product1,product2,sku_suffix,discount_amount,discount_percent,publish,prefix,serial
breville-barista-express,eureka-mignon-specialita,BE-ES1,200,,false,COMBO,
BES870XL,GRIND-01,,,15,false,COMBO,
delonghi-dedica,eureka-mignon-grinder,DLG-1,100,,true,CD25,001
```

### 5. Bulk Operations
```bash
# Export all active products
python tools/export_products.py --status active --format csv

# Bulk price update from CSV
python tools/bulk_update.py --file price_updates.csv --operation pricing

# Add tag to multiple products
python tools/bulk_update.py --query "vendor:DeLonghi" --operation add-tag --value "italian-made"
```

### 6. Bulk Price Updates
```bash
# Create sample CSV template
python tools/bulk_price_update.py --sample

# Preview price changes (dry run)
python tools/bulk_price_update.py price_updates.csv --dry-run

# Apply price updates from CSV
python tools/bulk_price_update.py price_updates.csv
```

CSV format for bulk price updates:
- Required columns: `Variant ID`, `Price`
- Optional columns: `Compare At Price`, `Product Title`, `SKU`
- Example:
```
Product ID,Product Title,Variant ID,SKU,Price,Compare At Price
gid://shopify/Product/123,Coffee Grinder,gid://shopify/ProductVariant/456,GRIND-01,99.99,149.99
```

### 7. SkuVault Integration
```bash
# Upload single product to SkuVault
python tools/upload_to_skuvault.py --sku "COFFEE-001"

# Upload multiple products (comma-separated)
python tools/upload_to_skuvault.py --sku "COFFEE-001,GRINDER-002,MACHINE-003"

# Upload from file containing SKUs (one per line)
python tools/upload_to_skuvault.py --file skus_to_upload.txt

# Dry run to preview without uploading
python tools/upload_to_skuvault.py --sku "BES870XL" --dry-run
```

Required environment variables:
- `SKUVAULT_TENANT_TOKEN`: Your SkuVault tenant token
- `SKUVAULT_USER_TOKEN`: Your SkuVault user token

The tool automatically:
- Fetches product data from Shopify (title, vendor, price, cost, images)
- Formats data for SkuVault API
- Uploads products with proper classification and pricing
- Supports batch operations for efficiency

### 8. URL Redirect Management
```bash
# Create a redirect
python tools/manage_redirects.py --action create --from "/old-product" --to "/new-product"

# List all redirects
python tools/manage_redirects.py --action list

# List more redirects
python tools/manage_redirects.py --action list --limit 100

# Delete a redirect
python tools/manage_redirects.py --action delete --id "gid://shopify/UrlRedirect/123456789"
```

Common use cases:
- Redirecting archived products to replacements
- Handling old URLs after product renames
- Managing seasonal product redirects
- Consolidating duplicate product pages

### 9. Product Image Management
```bash
# Add single image
python tools/add_product_images.py --product "7779055304738" --add "https://example.com/image.jpg"

# Add multiple images with alt text
python tools/add_product_images.py --product "profitec-pro-600" --add \
  "https://example.com/front.jpg" \
  "https://example.com/side.jpg" \
  --alt "Front view" "Side view"

# List current images
python tools/add_product_images.py --product "BES870XL" --list

# Delete images by position
python tools/add_product_images.py --product "7779055304738" --delete 2,3

# Reorder images
python tools/add_product_images.py --product "profitec-pro-600" --reorder 3,1,2,4

# Clear all images
python tools/add_product_images.py --product "7779055304738" --clear
```

The tool automatically:
- Uploads images from any publicly accessible URL
- Converts them to Shopify CDN URLs
- Supports alt text for accessibility
- Handles batch operations efficiently

## Product Features System

### IMPORTANT: JSON Features are Deprecated
The JSON-based features system (`manage_features_json.py`) is **DEPRECATED** and should NOT be used for new products. All new products MUST use the metaobjects-based features system.

### Using the Metaobjects Features System
Product features are stored as metaobjects and linked to products via the `content.product_features` metafield. Features must be added **one at a time** after product creation:

```bash
# List current features
python tools/manage_features_metaobjects.py --product "SKU123" --list

# Add features (one at a time - this is critical!)
python tools/manage_features_metaobjects.py --product "7991004168226" --add "SCA Golden Cup Certified" "Meets Specialty Coffee Association standards"
python tools/manage_features_metaobjects.py --product "7991004168226" --add "Customizable Brewing" "Control temperature, bloom time, and flow rate"

# Update a feature (by position number)
python tools/manage_features_metaobjects.py --product "SKU123" --update 2 "Updated Title" "New description"

# Remove a feature (by position number)
python tools/manage_features_metaobjects.py --product "SKU123" --remove 3

# Reorder features
python tools/manage_features_metaobjects.py --product "SKU123" --reorder 3,1,2,4,5
```

### Common Pitfalls to Avoid
1. **Do NOT use manage_features_json.py for new products** - it's deprecated
2. **Do NOT try to add multiple features in one command** - they will be combined into a single feature
3. **Do NOT use the --features parameter in create_full_product.py** - it doesn't exist
4. **Always add features AFTER creating the product**, not during creation

### Migrating Legacy Products
If you encounter a product still using the JSON features system, migrate it:
```bash
python tools/manage_features_metaobjects.py --product "product-handle" --migrate-from-json
```

## GraphQL Examples

### Query Examples
```python
# Get shop info
python tools/graphql_query.py '{ shop { name currencyCode } }'

# Get products with variants
python tools/graphql_query.py '{
  products(first: 10, query: "status:active") {
    edges {
      node {
        id
        title
        variants(first: 5) {
          edges {
            node {
              id
              price
              sku
            }
          }
        }
      }
    }
  }
}'
```

### Mutation Examples
```python
# Update product SEO
python tools/graphql_mutation.py \
  --mutation 'mutation updateSEO($input: ProductInput!) {
    productUpdate(input: $input) {
      product { id }
      userErrors { field message }
    }
  }' \
  --variables '{
    "input": {
      "id": "gid://shopify/Product/123",
      "seo": {
        "title": "SEO Title",
        "description": "SEO Description"
      }
    }
  }'
```

## Product Conventions (iDrinkCoffee.com)

### Product Naming
- Format: `{Brand} {Product Name} {Descriptors}`
- Example: "Breville Barista Express Espresso Machine - Brushed Stainless Steel"

### Tagging System
- **Product Type**: `espresso-machines`, `grinders`, `accessories`
- **Brand**: Lowercase vendor name (e.g., `breville`, `delonghi`)
- **Warranty**: `WAR-VIM+VIM`, `WAR-ACC`, `consumer`, `commercial`
- **Themes**: `NC_EspressoMachines`, `NC_DualBoiler`, `icon-E61-Group-Head`
- **Status**: `clearance`, `sale`, `featured`, `new-arrival`

### Open Box Convention
- **SKU**: `OB-{YYMM}-{Serial}-{OriginalSKU}`
- **Title**: `{Original Title} |{Serial}| - {Condition}`
- **Tags**: Auto-added `open-box`, `ob-YYMM`

### Metafields
- **Namespace**: `content`
- **Common Keys**:
  - `features_box` - Product features HTML
  - `faqs` - FAQ accordion HTML
  - `buy_box` - Purchase information
  - `technical_specifications` - Specs table

## Error Handling

All tools follow these patterns:
1. Validate inputs before API calls
2. Check for GraphQL userErrors in responses
3. Provide clear error messages
4. Support multiple identifier formats (ID, GID, SKU, handle, title)
5. Exit with appropriate codes (0=success, 1=error)

## Best Practices

1. **Always test in development** before running bulk operations
2. **Use DRAFT status** when creating products
3. **Include field selections** in GraphQL queries for object types
4. **Check userErrors** in mutation responses
5. **Use proper GID format** for Shopify IDs: `gid://shopify/Product/123456`
6. **Follow naming conventions** for consistency
7. **Document changes** in commit messages

## Advanced Usage

### Custom Scripts
Create custom Python scripts in the root directory that import and use multiple tools:

```python
from tools import search_products, update_pricing, manage_tags

# Find sale items and update pricing
products = search_products.search("tag:sale")
for product in products:
    for variant in product['variants']:
        update_pricing.update(
            product_id=product['id'],
            variant_id=variant['id'],
            price=variant['price'] * 0.9  # 10% off
        )
    manage_tags.add(product['id'], ['flash-sale'])
```

### Environment Management
Use `.env` file for local development:
```bash
SHOPIFY_SHOP_URL=https://your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxx
DEBUG=true
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check your access token and permissions
2. **400 Bad Request**: Verify GraphQL syntax and field selections
3. **Product Not Found**: Try different identifiers (ID, SKU, handle)
4. **Rate Limiting**: Add delays between bulk operations

### Debug Mode
Set `DEBUG=true` to see detailed API requests and responses.

### Getting Help
- Check tool help: `python tools/[tool_name].py --help`
- View examples: See `examples/` directory
- API Reference: https://shopify.dev/docs/api/admin-graphql
- Use the shopify-dev MCP server's tools for graphql introspection and shopify admin api documentation directly
- Use the `pplx.py` tool for quick answers when stuck
- Codex with a reasoning model (such as o4-mini or o3) can be used for assistance with planning complex, multi-step tasks and with developing new tools

## Security Notes

- Never commit `.env` files or credentials
- Use read-only tokens when possible
- Validate all inputs before API calls
- Log operations for audit trail

## Product Creation Guidelines

For detailed product creation and management guidelines, see the documentation in `docs/product-guidelines/`:

- **[Overview](./docs/product-guidelines/01-overview.md)** - Start here for quick orientation
- **[Product Creation Basics](./docs/product-guidelines/02-product-creation-basics.md)** - Core workflow and requirements
- **[Metafields Reference](./docs/product-guidelines/03-metafields-reference.md)** - Complete metafield documentation
- **[Tags System](./docs/product-guidelines/04-tags-system.md)** - Tagging conventions and complete tag list
- **[Coffee Products](./docs/product-guidelines/05-coffee-products.md)** - Special guidelines for coffee listings
- **[API Technical Reference](./docs/product-guidelines/06-api-technical-reference.md)** - GraphQL mutations and technical details
- **[Product Anatomy](./docs/product-guidelines/07-product-anatomy.md)** - Complete product data model

## Good to Know - iDrinkCoffee.com Specific Notes

- When asked add something to preorder, add the "preorder-2-weeks" tag to the product, and any tag that begins with "shipping-nis" (such as shipping-nis-April), similarly, when removing something from preorder, remove the "preorder-2-weeks" tag and any tag that begins with "shipping-nis" (such as shipping-nis-April).
     Also ask the user if they want to change the inventory policy of that product to DENY when something is taken out of preorder, when something is added to preorder, inventory policy should be set to ALLOW, without needing to ask the user.
     - Use `python tools/manage_inventory_policy.py --identifier "IDENTIFIER" --policy allow/deny` to manage oversell settings
- Sale End Date: If asked to add a promotion or sale end date to any product, it can be added to the product's inventory.ShappifySaleEndDate metafiled (Namespace is inventory and key is ShappifySaleEndDate; it is single line text) Format example: 2023-08-04T03:00:00Z (For 3 AM on August 4, 2023) 
- For US/USD price updates, use the pricelist ID: `gid://shopify/PriceList/18798805026`.
- Prices are always in CAD and don't need to use a separate price list, only use a price list when a currency is specified or a currency other than CAD is specified.
- The channels: Online Store — gid://shopify/Channel/46590273, Point of Sale — gid://shopify/Channel/46590337, Google & YouTube — gid://shopify/Channel/22067970082, Facebook & Instagram — gid://shopify/Channel/44906577954, Shop — gid://shopify/Channel/93180952610, Hydrogen — gid://shopify/Channel/231226015778, Hydrogen — gid://shopify/Channel/231226048546, Hydrogen — gid://shopify/Channel/231776157730, Attentive — gid://shopify/Channel/255970312226 are the ones a product must be visible on when it is published.
- For any search targeting a known handle or unique key, use the query parameter or filter argument available in the GraphQL query to retrieve only the relevant item(s).



## Memories

- Use tagsAdd and tagsRemove for tag operations instead of productUpdate to avoid any accidents
- create_open_box.py uses productDuplicate (with includeImages: true) for efficient copying of all product data, then updates SKU/price/tags
- CD2025 Sale Scripts: Two scripts exist in tools/tmp/ for managing vendor-specific discounts:
  - `apply_cd2025_discounts.py` - Applies discounts to Mahlkonig, Anfim, and Heycafe products based on cd2025-X tags (e.g., cd2025-10 = 10% off). Only applies to products not already on sale. Processes ~86 variants efficiently with parallel processing.
  - `remove_cd2025_discounts.py` - Reverses the discounts by restoring original prices and removing compareAtPrice. Use this when the sale ends to revert all changes made by the apply script.
- `productVariantUpdate is depreciated use productVariantsBulkUpdate`
- When specifying a shipping estimate via tag to a product on oversell/preorder - it is shipping-nis-* for example shipping-nis-July-2025 or shipping-nis-Week-of-April-21 and so on