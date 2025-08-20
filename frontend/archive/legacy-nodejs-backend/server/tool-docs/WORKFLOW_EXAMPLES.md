# Workflow Examples

This document provides practical examples of common workflows for managing the iDrinkCoffee.com Shopify store.

## Table of Contents
1. [Product Search and Update](#1-product-search-and-update)
2. [Creating Products](#2-creating-products)
3. [Open Box Listings](#3-open-box-listings)
4. [Creating Combo Products](#4-creating-combo-products)
5. [Bulk Operations](#5-bulk-operations)
6. [Bulk Price Updates](#6-bulk-price-updates)
7. [SkuVault Integration](#7-skuvault-integration)
8. [URL Redirect Management](#8-url-redirect-management)
9. [Product Image Management](#9-product-image-management)
10. [Product Features System](#product-features-system)
11. [GraphQL Examples](#graphql-examples)

## 1. Product Search and Update

### Search for products
```bash
python /home/pranav/espressobot/frontend/python-tools/search_products.py "tag:sale status:active"
```

### Get specific product details
```bash
python /home/pranav/espressobot/frontend/python-tools/get_product.py "gid://shopify/Product/123456789"
```

### Update pricing
```bash
python /home/pranav/espressobot/frontend/python-tools/update_pricing.py --product-id "123456789" --variant-id "987654321" --price "29.99" --compare-at "39.99"
```

### Add tags
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_tags.py --action add --product-id "123456789" --tags "sale,featured"
```

### Toggle oversell settings
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_inventory_policy.py --identifier "SKU123" --policy deny
python /home/pranav/espressobot/frontend/python-tools/manage_inventory_policy.py --identifier "product-handle" --policy allow
```

### Update product status
```bash
python /home/pranav/espressobot/frontend/python-tools/update_status.py --product "SKU123" --status ACTIVE
python /home/pranav/espressobot/frontend/python-tools/update_status.py --product "product-handle" --status DRAFT
```

### Manage product features (ALWAYS use metaobjects for new products)
```bash
# List features
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "profitec-move" --list

# Add features (one at a time!)
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "PRO-MOVE-B" --add "E61 Group Head" "Commercial-grade temperature stability"

# Update feature
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "7779055304738" --update 2 "Updated Feature" "New description"

# Remove feature
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "product-handle" --remove 3

# Reorder features
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "SKU123" --reorder 3,1,2,4,5
```

**IMPORTANT**: Features must be added one at a time, not as a batch
```bash
# Correct:
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "7991004168226" --add "SCA Certified" "Meets specialty coffee standards"
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "7991004168226" --add "Custom Brewing" "Control temperature and flow rate"

# Incorrect (will combine all into one feature):
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "7991004168226" --add "Feature 1" "Desc 1" "Feature 2" "Desc 2"
```

### Migrate legacy products from JSON to metaobjects
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "eureka-mignon-manuale" --migrate-from-json
```

## 2. Creating Products

### Simple product (basic tool)
```bash
python /home/pranav/espressobot/frontend/python-tools/create_product.py --title "Product Name" --vendor "Brand" --type "Category" --price "99.99"
```

### Complete product with all metafields (recommended)
```bash
python /home/pranav/espressobot/frontend/python-tools/create_full_product.py \
  --title "DeLonghi Dedica Style" \
  --vendor "DeLonghi" \
  --type "Espresso Machines" \
  --price "249.99" \
  --sku "EC685M" \
  --cost "150.00" \
  --buybox "Experience café-quality espresso in a compact design..." \
  --tags "icon-Steam-Wand,icon-Single-Boiler"
```

**IMPORTANT**: Features should be added AFTER product creation using manage_features_metaobjects.py
The create_full_product.py tool does NOT support features parameter

### From JSON configuration file
```bash
python /home/pranav/espressobot/frontend/python-tools/create_full_product.py --from-json product_config.json
```

### After creating the product, add features one by one:
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "EC685M" --add "15 Bar Pressure" "Professional-grade extraction pressure"
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "EC685M" --add "Thermoblock Heating" "Rapid heat-up time for quick brewing"
```

## 3. Open Box Listings

### Create with automatic 10% discount
```bash
python /home/pranav/espressobot/frontend/python-tools/create_open_box.py --identifier "EC685M" --serial "ABC123" --condition "Excellent"
```

### Create with specific discount percentage
```bash
python /home/pranav/espressobot/frontend/python-tools/create_open_box.py --identifier "BES870XL" --serial "XYZ789" --condition "Good" --discount 20
```

### Create with specific price
```bash
python /home/pranav/espressobot/frontend/python-tools/create_open_box.py --identifier "7234567890123" --serial "DEF456" --condition "Fair" --price 899.99
```

### Add a note about condition
```bash
python /home/pranav/espressobot/frontend/python-tools/create_open_box.py --identifier "delonghi-dedica" --serial "GHI789" --condition "Scratch & Dent" --discount 25 --note "Minor cosmetic damage on side panel"
```

### Create and publish immediately
```bash
python /home/pranav/espressobot/frontend/python-tools/create_open_box.py --identifier "EC685M" --serial "JKL012" --condition "Like New" --discount 5 --publish
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

## 4. Creating Combo Products

### Create single combo with fixed discount
```bash
python /home/pranav/espressobot/frontend/python-tools/create_combo.py --product1 breville-barista-express --product2 eureka-mignon-specialita --discount 200
```

### Create combo with percentage discount
```bash
python /home/pranav/espressobot/frontend/python-tools/create_combo.py --product1 BES870XL --product2 EUREKA-SPEC --discount-percent 15
```

### Create combo with custom SKU suffix and publish
```bash
python /home/pranav/espressobot/frontend/python-tools/create_combo.py --product1 7234567890123 --product2 9876543210987 --sku-suffix A1 --publish
```

### Create combo with custom prefix and serial number
```bash
python /home/pranav/espressobot/frontend/python-tools/create_combo.py --product1 BES870XL --product2 EUREKA-SPEC --prefix CD25 --serial 001
```

### Create multiple combos from CSV
```bash
python /home/pranav/espressobot/frontend/python-tools/create_combo.py --from-csv combos.csv
```

### Generate sample CSV template
```bash
python /home/pranav/espressobot/frontend/python-tools/create_combo.py --sample
```

The tool uses `productDuplicate` to create combos and:
- Automatically generates professional combo images by combining product photos
- Combines descriptions, tags, and metafields from both products
- Calculates combo pricing with optional discounts
- Generates SKU: `{Prefix}-{Serial}-{Suffix}` where Prefix defaults to "COMBO" and Serial defaults to YYMM
- Creates SkuVault kit configuration files automatically
- Supports bulk creation via CSV for efficiency

CSV format for bulk combo creation:
```csv
product1,product2,sku_suffix,discount_amount,discount_percent,publish,prefix,serial
breville-barista-express,eureka-mignon-specialita,BE-ES1,200,,false,COMBO,
BES870XL,GRIND-01,,,15,false,COMBO,
delonghi-dedica,eureka-mignon-grinder,DLG-1,100,,true,CD25,001
```

## 5. Bulk Operations

### Export all active products
```bash
python /home/pranav/espressobot/frontend/python-tools/export_products.py --status active --format csv
```

### Bulk price update from CSV
```bash
python /home/pranav/espressobot/frontend/python-tools/bulk_update.py --file price_updates.csv --operation pricing
```

### Add tag to multiple products
```bash
python /home/pranav/espressobot/frontend/python-tools/bulk_update.py --query "vendor:DeLonghi" --operation add-tag --value "italian-made"
```

## 6. Bulk Price Updates

### Create sample CSV template
```bash
python /home/pranav/espressobot/frontend/python-tools/bulk_price_update.py --sample
```

### Preview price changes (dry run)
```bash
python /home/pranav/espressobot/frontend/python-tools/bulk_price_update.py price_updates.csv --dry-run
```

### Apply price updates from CSV
```bash
python /home/pranav/espressobot/frontend/python-tools/bulk_price_update.py price_updates.csv
```

CSV format for bulk price updates:
- Required columns: `Variant ID`, `Price`
- Optional columns: `Compare At Price`, `Product Title`, `SKU`
- Example:
```csv
Product ID,Product Title,Variant ID,SKU,Price,Compare At Price
gid://shopify/Product/123,Coffee Grinder,gid://shopify/ProductVariant/456,GRIND-01,99.99,149.99
```

## 7. SkuVault Integration

### Upload single product to SkuVault
```bash
python /home/pranav/espressobot/frontend/python-tools/upload_to_skuvault.py --sku "COFFEE-001"
```

### Upload multiple products (comma-separated)
```bash
python /home/pranav/espressobot/frontend/python-tools/upload_to_skuvault.py --sku "COFFEE-001,GRINDER-002,MACHINE-003"
```

### Upload from file containing SKUs (one per line)
```bash
python /home/pranav/espressobot/frontend/python-tools/upload_to_skuvault.py --file skus_to_upload.txt
```

### Dry run to preview without uploading
```bash
python /home/pranav/espressobot/frontend/python-tools/upload_to_skuvault.py --sku "BES870XL" --dry-run
```

Required environment variables:
- `SKUVAULT_TENANT_TOKEN`: Your SkuVault tenant token
- `SKUVAULT_USER_TOKEN`: Your SkuVault user token

The tool automatically:
- Fetches product data from Shopify (title, vendor, price, cost, images)
- Formats data for SkuVault API
- Uploads products with proper classification and pricing
- Supports batch operations for efficiency

## 8. URL Redirect Management

### Create a redirect
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_redirects.py --action create --from "/old-product" --to "/new-product"
```

### List all redirects
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_redirects.py --action list
```

### List more redirects
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_redirects.py --action list --limit 100
```

### Delete a redirect
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_redirects.py --action delete --id "gid://shopify/UrlRedirect/123456789"
```

Common use cases:
- Redirecting archived products to replacements
- Handling old URLs after product renames
- Managing seasonal product redirects
- Consolidating duplicate product pages

## 9. Product Image Management

### Add single image
```bash
python /home/pranav/espressobot/frontend/python-tools/add_product_images.py --product "7779055304738" --add "https://example.com/image.jpg"
```

### Add multiple images with alt text
```bash
python /home/pranav/espressobot/frontend/python-tools/add_product_images.py --product "profitec-pro-600" --add \
  "https://example.com/front.jpg" \
  "https://example.com/side.jpg" \
  --alt "Front view" "Side view"
```

### List current images
```bash
python /home/pranav/espressobot/frontend/python-tools/add_product_images.py --product "BES870XL" --list
```

### Delete images by position
```bash
python /home/pranav/espressobot/frontend/python-tools/add_product_images.py --product "7779055304738" --delete 2,3
```

### Reorder images
```bash
python /home/pranav/espressobot/frontend/python-tools/add_product_images.py --product "profitec-pro-600" --reorder 3,1,2,4
```

### Clear all images
```bash
python /home/pranav/espressobot/frontend/python-tools/add_product_images.py --product "7779055304738" --clear
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
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "SKU123" --list

# Add features (one at a time - this is critical!)
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "7991004168226" --add "SCA Golden Cup Certified" "Meets Specialty Coffee Association standards"
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "7991004168226" --add "Customizable Brewing" "Control temperature, bloom time, and flow rate"

# Update a feature (by position number)
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "SKU123" --update 2 "Updated Title" "New description"

# Remove a feature (by position number)
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "SKU123" --remove 3

# Reorder features
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "SKU123" --reorder 3,1,2,4,5
```

### Common Pitfalls to Avoid
1. **Do NOT use manage_features_json.py for new products** - it's deprecated
2. **Do NOT try to add multiple features in one command** - they will be combined into a single feature
3. **Do NOT use the --features parameter in create_full_product.py** - it doesn't exist
4. **Always add features AFTER creating the product**, not during creation

### Migrating Legacy Products
If you encounter a product still using the JSON features system, migrate it:
```bash
python /home/pranav/espressobot/frontend/python-tools/manage_features_metaobjects.py --product "product-handle" --migrate-from-json
```

## GraphQL Examples

### Query Examples
```bash
# Get shop info
python /home/pranav/espressobot/frontend/python-tools/graphql_query.py '{ shop { name currencyCode } }'

# Get products with variants
python /home/pranav/espressobot/frontend/python-tools/graphql_query.py '{
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

# Query specific product by handle
python /home/pranav/espressobot/frontend/python-tools/graphql_query.py '{
  productByHandle(handle: "breville-barista-express") {
    id
    title
    metafields(first: 10) {
      edges {
        node {
          namespace
          key
          value
        }
      }
    }
  }
}'
```

### Mutation Examples
```bash
# Update product title
python /home/pranav/espressobot/frontend/python-tools/graphql_mutation.py '
mutation {
  productUpdate(input: {
    id: "gid://shopify/Product/123456789"
    title: "New Product Title"
  }) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}'

# Create metafield
python /home/pranav/espressobot/frontend/python-tools/graphql_mutation.py '
mutation {
  metafieldsSet(metafields: [{
    ownerId: "gid://shopify/Product/123456789"
    namespace: "custom"
    key: "info"
    type: "single_line_text_field"
    value: "Custom information"
  }]) {
    metafields {
      id
      value
    }
    userErrors {
      field
      message
    }
  }
}'
```

## CSV Formats

### Bulk Price Update CSV
```csv
Product ID,Product Title,Variant ID,SKU,Price,Compare At Price
gid://shopify/Product/123,Coffee Grinder,gid://shopify/ProductVariant/456,GRIND-01,99.99,149.99
```

### Combo Creation CSV
```csv
product1,product2,sku_suffix,discount_amount,discount_percent,publish,prefix,serial
breville-barista-express,eureka-mignon-specialita,BE-ES1,200,,false,COMBO,
BES870XL,GRIND-01,,,15,false,COMBO,
delonghi-dedica,eureka-mignon-grinder,DLG-1,100,,true,CD25,001
```

### SKU Upload List (one per line)
```
COFFEE-001
GRINDER-002
MACHINE-003
BES870XL
```

## Identifier Formats

### Product Identifiers
Products can be identified by:
- **Shopify ID**: `7779055304738` (numeric)
- **GraphQL ID**: `gid://shopify/Product/7779055304738`
- **Handle**: `breville-barista-express` (URL slug)
- **SKU**: `BES870XL` (from any variant)
- **Title**: Partial match on product title

### Variant Identifiers
- **Shopify ID**: `987654321` (numeric)
- **GraphQL ID**: `gid://shopify/ProductVariant/987654321`
- **SKU**: Unique variant SKU

### SKU Formats
- **Regular Products**: `VENDOR-MODEL` (e.g., `BES870XL`)
- **Open Box**: `OB-{YYMM}-{Serial}-{OriginalSKU}` (e.g., `OB-2501-ABC123-BES870XL`)
- **Combos**: `{Prefix}-{Serial}-{Suffix}` (e.g., `COMBO-2501-BE-ES1`)

## Best Practices

1. **Always use absolute paths** when calling Python tools
2. **Check tool existence** before running: `ls /home/pranav/espressobot/frontend/python-tools/`
3. **Use --help flag** to understand tool options: `python tool_name.py --help`
4. **Handle errors gracefully** - check exit codes and error messages
5. **Chain commands** with && for sequential operations
6. **Use quotes** for arguments containing spaces or special characters
7. **Verify results** after operations, especially for bulk updates