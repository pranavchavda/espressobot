# iDrinkCoffee.com Business Rules

## Preorder Management

### Adding Products to Preorder
When asked to add something to preorder:
1. Add the "preorder-2-weeks" tag
2. Add shipping estimate tag: "shipping-nis-{Month}" or "shipping-nis-Week-of-{Date}"
3. Set inventory policy to ALLOW (without asking)
4. Example: `shipping-nis-April`, `shipping-nis-July-2025`, `shipping-nis-Week-of-April-21`

### Removing Products from Preorder
When removing from preorder:
1. Remove "preorder-2-weeks" tag
2. Remove any tags beginning with "shipping-nis"
3. Ask user if they want to set inventory policy to DENY

## Pricing Rules

### Currency Defaults
- All prices are in CAD by default
- No price list needed for CAD pricing

### US/USD Pricing
- Use price list ID: `gid://shopify/PriceList/18798805026`
- Only use price lists when currency is specified or non-CAD

## Sale Management

### Sale End Dates
- Use metafield: `inventory.ShappifySaleEndDate`
- Format: `2023-08-04T03:00:00Z` (ISO 8601)
- Single line text field type

## Publishing Channels
Products must be visible on ALL these channels when published:
- Online Store — `gid://shopify/Channel/46590273`
- Point of Sale — `gid://shopify/Channel/46590337`
- Google & YouTube — `gid://shopify/Channel/22067970082`
- Facebook & Instagram — `gid://shopify/Channel/44906577954`
- Shop — `gid://shopify/Channel/93180952610`
- Hydrogen — `gid://shopify/Channel/231226015778`
- Hydrogen — `gid://shopify/Channel/231226048546`
- Hydrogen — `gid://shopify/Channel/231776157730`
- Attentive — `gid://shopify/Channel/255970312226`

## Product Conventions

### Naming Format
- Pattern: `{Brand} {Product Name} {Descriptors}`
- Example: "Breville Barista Express Espresso Machine - Brushed Stainless Steel"

### Open Box Products
- SKU: `OB-{YYMM}-{Serial}-{OriginalSKU}`
- Title: `{Original Title} |{Serial}| - {Condition}`
- Auto-add tags: `open-box`, `ob-{YYMM}`
- Default status: DRAFT (unless --publish used)

### Combo Products
- SKU: `{Prefix}-{Serial}-{Suffix}`
- Prefix defaults to "COMBO"
- Serial defaults to YYMM
- Auto-generates professional combo images
- Creates SkuVault kit configurations

## Tag Conventions

### Product Type Tags
- `espresso-machines`, `grinders`, `accessories`

### Warranty Tags
- `WAR-VIM+VIM`, `WAR-ACC`, `consumer`, `commercial`

### Theme Tags
- `NC_EspressoMachines`, `NC_DualBoiler`, `icon-E61-Group-Head`

### Status Tags
- `clearance`, `sale`, `featured`, `new-arrival`

## Metafield Standards

### Namespace: `content`
Common keys:
- `features_box` - Product features HTML
- `faqs` - FAQ accordion HTML
- `buy_box` - Purchase information
- `technical_specifications` - Specs table
- `product_features` - Metaobject references (for features)

## Important Technical Notes

### Deprecated Methods
- `manage_features_json.py` → Use `manage_features_metaobjects.py`
- `productVariantUpdate` → Use `productVariantsBulkUpdate`
- `tagsAdd`/`tagsRemove` preferred over `productUpdate` for tag operations

### Features System
- ALWAYS use metaobjects for new products
- Features MUST be added ONE AT A TIME after product creation
- Never batch feature additions
- The `create_full_product.py` tool does NOT support features parameter

### Search Optimization
- For known handles/unique keys, use query parameter or filter argument
- This retrieves only relevant items instead of full lists

## Vendor-Specific Notes

### CD2025 Sale Scripts
Located in `tools/tmp/`:
- `apply_cd2025_discounts.py` - Applies discounts based on cd2025-X tags
- `remove_cd2025_discounts.py` - Reverses discounts when sale ends
- Only applies to products not already on sale
- Processes efficiently with parallel processing

## Best Practices

1. Always create products in DRAFT status
2. Include COGS (cost) for all products
3. Enable inventory tracking with "deny" policy by default
4. Use Canadian English in all content
5. Each variant is created as a separate product (not using Shopify's variant system)
6. Check for existing products before creating duplicates
7. Verify identifiers with get_product.py before updates