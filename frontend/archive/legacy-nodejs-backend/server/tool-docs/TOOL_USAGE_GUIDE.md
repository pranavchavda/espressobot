# EspressoBot Tool Usage GuideLearn

## Overview
This guide provides comprehensive documentation for all Python tools available in the `/home/pranav/espressobot/frontend/python-tools/` directory. These tools interact with Shopify Admin API and other e-commerce systems to manage iDrinkCoffee.com.

## Quick Start
1. **Set Environment Variables** (required):
```bash
export SHOPIFY_SHOP_URL="https://idrinkcoffee.myshopify.com"
export SHOPIFY_ACCESS_TOKEN="your_shopify_access_token_here"
```

2. **Test Connection**:
```bash
python3 /home/pranav/espressobot/frontend/python-tools/test_connection.py
```

## Core Tools Reference

### 🔍 Search & Information Tools

#### search_products.py
Search products with advanced filters.
```bash
# Basic search
python3 search_products.py "coffee"

# Advanced search with filters
python3 search_products.py "tag:sale status:active vendor:Breville"

# Search by SKU
python3 search_products.py "SKU:BES870XL"

# Complex queries
python3 search_products.py "type:'Espresso Machines' price:>500"
```

#### get_product.py
Get detailed product information.
```bash
# By Product ID
python3 get_product.py "123456789"

# By GID
python3 get_product.py "gid://shopify/Product/123456789"

# By SKU
python3 get_product.py "BES870XL"

# By Handle
python3 get_product.py "breville-barista-express"
```

#### pplx.py
Use Perplexity AI for research and information.
```bash
python3 pplx.py "What are the latest espresso machine trends for 2025?"
```

### 💰 Pricing & Inventory Tools

#### update_pricing.py
Update variant pricing and costs.
```bash
# Basic price update
python3 update_pricing.py --product-id "123456789" --variant-id "987654321" --price "29.99"

# With compare-at price
python3 update_pricing.py --product-id "123456789" --variant-id "987654321" --price "29.99" --compare-at "39.99"

# Update cost
python3 update_pricing.py --product-id "123456789" --variant-id "987654321" --cost "15.00"

# Update using SKU
python3 update_pricing.py --sku "BES870XL" --price "899.99" --compare-at "999.99"
```

#### bulk_price_update.py
Bulk price updates from CSV file.
```bash
# Generate sample CSV
python3 bulk_price_update.py --sample

# Preview changes (dry run)
python3 bulk_price_update.py price_updates.csv --dry-run

# Apply updates
python3 bulk_price_update.py price_updates.csv
```

CSV Format:
```csv
Product ID,Product Title,Variant ID,SKU,Price,Compare At Price
gid://shopify/Product/123,Coffee Grinder,gid://shopify/ProductVariant/456,GRIND-01,99.99,149.99
```

#### manage_inventory_policy.py
Toggle oversell settings (inventory policy).
```bash
# Allow overselling (for preorders)
python3 manage_inventory_policy.py --identifier "SKU123" --policy allow

# Deny overselling (normal products)
python3 manage_inventory_policy.py --identifier "product-handle" --policy deny
```

### 🏷️ Tags & Metadata Tools

#### manage_tags.py
Add or remove product tags.
```bash
# Add tags
python3 manage_tags.py --action add --product-id "123456789" --tags "sale,featured,summer2025"

# Remove tags
python3 manage_tags.py --action remove --product-id "123456789" --tags "clearance,old-season"

# Using SKU
python3 manage_tags.py --action add --identifier "BES870XL" --tags "bestseller"
```

#### set_metafield.py
Set product metafields.
```bash
# Set buy box content
python3 set_metafield.py --product "123456789" --namespace "content" --key "buy_box" --value "<p>Premium espresso at home</p>" --type "single_line_text_field"

# Set sale end date
python3 set_metafield.py --product "BES870XL" --namespace "inventory" --key "ShappifySaleEndDate" --value "2025-08-04T03:00:00Z" --type "single_line_text_field"
```

#### manage_features_metaobjects.py
Manage product features using metaobjects (REQUIRED for all new products).
```bash
# List current features
python3 manage_features_metaobjects.py --product "profitec-move" --list

# Add features (ONE AT A TIME!)
python3 manage_features_metaobjects.py --product "7991004168226" --add "E61 Group Head" "Commercial-grade temperature stability"
python3 manage_features_metaobjects.py --product "7991004168226" --add "PID Controller" "Precise temperature control"

# Update feature
python3 manage_features_metaobjects.py --product "SKU123" --update 2 "Updated Title" "New description"

# Remove feature
python3 manage_features_metaobjects.py --product "SKU123" --remove 3

# Reorder features
python3 manage_features_metaobjects.py --product "SKU123" --reorder 3,1,2,4,5

# Migrate from legacy JSON
python3 manage_features_metaobjects.py --product "eureka-mignon-manuale" --migrate-from-json
```

### 📦 Product Creation Tools

#### create_full_product.py
Create complete products with all metafields and tags.
```bash
# Create espresso machine
python3 create_full_product.py \
  --title "DeLonghi Dedica Style" \
  --vendor "DeLonghi" \
  --type "Espresso Machines" \
  --price "249.99" \
  --sku "EC685M" \
  --cost "150.00" \
  --buybox "Experience café-quality espresso in a compact design..." \
  --tags "icon-Steam-Wand,icon-Single-Boiler,WAR-VIM+VIM"

# From JSON config
python3 create_full_product.py --from-json product_config.json
```

#### create_product.py
Create simple products (for accessories, parts).
```bash
python3 create_product.py --title "Espresso Tamper" --vendor "Generic" --type "Accessories" --price "29.99" --sku "TAMP-01"
```

#### create_open_box.py
Create open box listings using productDuplicate.
```bash
# Auto 10% discount
python3 create_open_box.py --identifier "EC685M" --serial "ABC123" --condition "Excellent"

# Custom discount percentage
python3 create_open_box.py --identifier "BES870XL" --serial "XYZ789" --condition "Good" --discount 20

# With note and publish
python3 create_open_box.py --identifier "delonghi-dedica" --serial "GHI789" --condition "Scratch & Dent" --discount 25 --note "Minor cosmetic damage" --publish
```

#### create_combo.py
Create machine+grinder combo products.
```bash
# Single combo with fixed discount
python3 create_combo.py --product1 breville-barista-express --product2 eureka-mignon-specialita --discount 200

# With percentage discount
python3 create_combo.py --product1 BES870XL --product2 EUREKA-SPEC --discount-percent 15

# Bulk from CSV
python3 create_combo.py --from-csv combos.csv

# Generate sample CSV
python3 create_combo.py --sample
```

### 🔧 Management Tools

#### update_status.py
Update product status (ACTIVE, DRAFT, ARCHIVED).
```bash
# Activate product
python3 update_status.py --product "SKU123" --status ACTIVE

# Set to draft
python3 update_status.py --product "product-handle" --status DRAFT

# Archive product
python3 update_status.py --product "7234567890123" --status ARCHIVED
```

#### manage_collections.py
List collections and manage products.
```bash
# List all collections
python3 manage_collections.py --list

# Add product to collection
python3 manage_collections.py --action add --collection "Summer Sale" --product "BES870XL"

# Remove from collection
python3 manage_collections.py --action remove --collection "123456789" --product "EC685M"
```

#### manage_redirects.py
Manage URL redirects.
```bash
# Create redirect
python3 manage_redirects.py --action create --from "/old-product" --to "/new-product"

# List redirects
python3 manage_redirects.py --action list --limit 50

# Delete redirect
python3 manage_redirects.py --action delete --id "gid://shopify/UrlRedirect/123456789"
```

#### add_product_images.py
Add product images from URLs or local files.
```bash
# Add single image
python3 add_product_images.py --product "7779055304738" --add "https://example.com/image.jpg"

# Multiple images with alt text
python3 add_product_images.py --product "profitec-pro-600" --add "https://example.com/front.jpg" "https://example.com/side.jpg" --alt "Front view" "Side view"

# List images
python3 add_product_images.py --product "BES870XL" --list

# Delete images
python3 add_product_images.py --product "7779055304738" --delete 2,3

# Reorder images
python3 add_product_images.py --product "profitec-pro-600" --reorder 3,1,2,4
```

### 🔌 Integration Tools

#### upload_to_skuvault.py
Upload products to SkuVault inventory system.
```bash
# Single product
python3 upload_to_skuvault.py --sku "COFFEE-001"

# Multiple products
python3 upload_to_skuvault.py --sku "COFFEE-001,GRINDER-002,MACHINE-003"

# From file
python3 upload_to_skuvault.py --file skus_to_upload.txt

# Dry run
python3 upload_to_skuvault.py --sku "BES870XL" --dry-run
```

#### send_review_request.py
Send Yotpo review request emails.
```bash
# Single recipient
python3 send_review_request.py --email "customer@example.com" --name "John Doe" --order "1234"

# Multiple recipients
python3 send_review_request.py --file recipients.csv
```

### 🛠️ GraphQL Tools

#### graphql_query.py
Execute any GraphQL query.
```bash
# Shop info
python3 graphql_query.py '{ shop { name currencyCode } }'

# Complex query
python3 graphql_query.py '{
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

#### graphql_mutation.py
Execute any GraphQL mutation.
```bash
python3 graphql_mutation.py \
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

### 📊 Utility Tools

#### test_connection.py
Verify API credentials.
```bash
python3 test_connection.py
```

#### export_products.py
Export product data.
```bash
# Export active products to CSV
python3 export_products.py --status active --format csv

# Export with specific fields
python3 export_products.py --fields "id,title,sku,price" --format json
```

#### bulk_update.py
Bulk operations on multiple products.
```bash
# Add tag to vendor products
python3 bulk_update.py --query "vendor:DeLonghi" --operation add-tag --value "italian-made"

# Update status in bulk
python3 bulk_update.py --query "tag:clearance" --operation status --value "ARCHIVED"
```

## Common Workflows

### Preorder Product Setup
```bash
# 1. Add preorder tags
python3 manage_tags.py --action add --identifier "SKU123" --tags "preorder-2-weeks,shipping-nis-July-2025"

# 2. Set inventory policy to allow overselling
python3 manage_inventory_policy.py --identifier "SKU123" --policy allow

# 3. Add sale end date if applicable
python3 set_metafield.py --product "SKU123" --namespace "inventory" --key "ShappifySaleEndDate" --value "2025-07-31T03:00:00Z" --type "single_line_text_field"
```

### Complete Product Creation
```bash
# 1. Create the product
python3 create_full_product.py \
  --title "Profitec Pro 500" \
  --vendor "Profitec" \
  --type "Espresso Machines" \
  --price "2699.00" \
  --sku "PRO-500" \
  --cost "1800.00" \
  --buybox "Professional-grade espresso machine..."

# 2. Add features one by one
python3 manage_features_metaobjects.py --product "PRO-500" --add "E61 Group Head" "Commercial temperature stability"
python3 manage_features_metaobjects.py --product "PRO-500" --add "PID Temperature Control" "±1°C accuracy"
python3 manage_features_metaobjects.py --product "PRO-500" --add "Rotary Pump" "Quiet operation and consistent pressure"

# 3. Add product images
python3 add_product_images.py --product "PRO-500" --add \
  "https://cdn.example.com/pro500-front.jpg" \
  "https://cdn.example.com/pro500-side.jpg" \
  --alt "Profitec Pro 500 front view" "Profitec Pro 500 side view"

# 4. Publish when ready
python3 update_status.py --product "PRO-500" --status ACTIVE
```

## Error Handling

All tools follow these patterns:
1. Validate inputs before API calls
2. Check for GraphQL userErrors in responses
3. Provide clear error messages
4. Support multiple identifier formats
5. Exit with appropriate codes (0=success, 1=error)

## Best Practices

1. **Always test with get_product.py first** to verify identifiers
2. **Use DRAFT status** when creating products
3. **Check for existing products** before creating duplicates
4. **Add features ONE AT A TIME** - never batch them
5. **Include COGS** for all products
6. **Set proper inventory policies** based on product type
7. **Use Canadian English** in all content

## Troubleshooting

### Common Issues
- **401 Unauthorized**: Check SHOPIFY_ACCESS_TOKEN
- **Product Not Found**: Try different identifier (ID, SKU, handle)
- **GraphQL Errors**: Use shopify-dev MCP for syntax checking
- **Rate Limiting**: Add delays between bulk operations

### Debug Mode
```bash
export DEBUG=true
python3 [tool_name].py [arguments]
```

## Important Reminders
- `manage_features_json.py` is DEPRECATED - use `manage_features_metaobjects.py`
- `productVariantUpdate` is DEPRECATED - use `productVariantsBulkUpdate`
- Features cannot be added during product creation - always add them after
- US pricing requires price list ID: `gid://shopify/PriceList/18798805026`
- Default prices are always in CAD