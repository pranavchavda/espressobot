# Variant Links Management Tool

A tool for managing product variant links in Shopify, allowing customers to easily switch between different colors/styles of the same product model.

## Installation

The tool is already installed in the `tools/` directory. No additional setup required.

## Usage Examples

### Link Products Together
Link multiple products (e.g., different colors of the same grinder):

```bash
# Using product IDs directly
python tools/manage_variant_links.py --action link --products "7105039564834,7105036746786,7105043136546"

# Using full GIDs
python tools/manage_variant_links.py --action link --products "gid://shopify/Product/7105039564834,gid://shopify/Product/7105036746786"

# Using a file
echo "7105039564834" > zero_products.txt
echo "7105036746786" >> zero_products.txt
echo "7105043136546" >> zero_products.txt
python tools/manage_variant_links.py --action link --file zero_products.txt
```

### Check Existing Links
See what products are linked to a specific product:

```bash
python tools/manage_variant_links.py --action check --product 7105039564834
```

Output example:
```
Product: Eureka Mignon Zero - Matte Black
Handle: eureka-mignon-zero-matte-black
Status: ACTIVE
--------------------------------------------------
Linked to 13 products:
  Eureka Mignon Zero - Black w/ Black Spout (ACTIVE)
  Eureka Mignon Zero - White w/ Black Spout (ACTIVE)
✓ Eureka Mignon Zero - Matte Black (ACTIVE)
  Eureka Mignon Zero - Chrome (ACTIVE)
  ...
```

### Sync a Variant Group
Use one product's links as the template for all products in its group:

```bash
# This ensures all linked products have identical varLinks
python tools/manage_variant_links.py --action sync --product 7105039564834
```

### Audit Variant Links
Check for consistency issues across your catalog:

```bash
# Audit all products
python tools/manage_variant_links.py --action audit

# Audit specific products
python tools/manage_variant_links.py --action audit --search "vendor:Eureka"
```

### Remove Variant Links
Unlink products (remove them from variant groups):

```bash
python tools/manage_variant_links.py --action unlink --products "7105039564834,7105036746786"
```

## Common Workflows

### Adding a New Color Variant

1. Create the new product in Shopify
2. Get the product ID
3. Check an existing variant's links:
   ```bash
   python tools/manage_variant_links.py --action check --product [existing_product_id]
   ```
4. Copy all the linked product IDs and add the new one
5. Link them all together:
   ```bash
   python tools/manage_variant_links.py --action link --products "[all_ids_including_new]"
   ```

### Fixing Broken Links

1. Audit the product group:
   ```bash
   python tools/manage_variant_links.py --action audit --search "title:*Zero*"
   ```
2. Identify products with inconsistent links
3. Use sync to fix them:
   ```bash
   python tools/manage_variant_links.py --action sync --product [good_product_id]
   ```

### Creating a New Variant Group

1. Identify all products that should be linked
2. Create a file with their IDs:
   ```bash
   cat > barista_express_variants.txt << EOF
   7234567890123
   7234567890124
   7234567890125
   EOF
   ```
3. Link them:
   ```bash
   python tools/manage_variant_links.py --action link --file barista_express_variants.txt
   ```

## Best Practices

1. **Always verify before linking** - Use `--action check` to see current links
2. **Keep groups consistent** - All products in a group should have identical varLinks
3. **Use meaningful search queries** - When auditing, use specific queries to focus on product lines
4. **Document your groups** - Keep a record of which products belong together

## Troubleshooting

### "Product not found" errors
- Ensure you're using the correct product ID format
- The tool accepts both short IDs (7105039564834) and full GIDs
- Check that the product exists and isn't deleted

### Links not showing on frontend
- Verify the theme is using the `new.varLinks` metafield
- Check that all products in the group have the same links
- Ensure products are active (not draft/archived)

### Sync not working
- The sample product must have existing varLinks
- All products in the links must still exist
- Use `--verbose` flag for detailed output

## Technical Details

- **Metafield Namespace:** `new`
- **Metafield Key:** `varLinks`
- **Metafield Type:** `list.product_reference`
- **Value Format:** JSON array of Shopify product GIDs