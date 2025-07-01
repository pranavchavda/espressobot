# Variant Linking Guide

## Overview
Variant linking allows customers to easily switch between different color/style variants of the same product model. This is implemented using the `varLinks` metafield which creates a product reference list connecting all variants together.

## Technical Details

### Metafield Specification
- **Namespace:** `new`
- **Key:** `varLinks`
- **Type:** `list.product_reference`
- **Value:** JSON array of product GIDs

### Example
```json
[
  "gid://shopify/Product/7958408724514",
  "gid://shopify/Product/7958408691746",
  "gid://shopify/Product/7105036746786"
]
```

## When to Use Variant Linking

Variant linking should be used when:
1. Multiple products represent the same model in different colors/finishes
2. Products share the same specifications but differ only in appearance
3. You want customers to easily browse all available options

### Good Candidates
- Grinders in different colors (e.g., Eureka Zero in Black, White, Chrome)
- Espresso machines with different finishes (e.g., Stainless, Black, White)
- Same model with minor variations (e.g., with/without specific accessories)

### Not Suitable For
- Different models (e.g., don't link Zero to Zero 65 AP)
- Different generations of the same product
- Open box or return items (keep these separate)

## Implementation Process

### 1. Identify Product Groups
Group products that should be linked together:
- Same model
- Same specifications
- Different colors/finishes only

### 2. Collect Product IDs
Gather all product GIDs that should be linked:
```bash
python tools/search_products.py "Eureka Zero" --limit 20
```

### 3. Use the Variant Linking Tool
```bash
python tools/manage_variant_links.py --action link --products "product1_id,product2_id,product3_id"
```

Or use a file:
```bash
python tools/manage_variant_links.py --action link --file product_ids.txt
```

### 4. Verify Links
```bash
python tools/manage_variant_links.py --action check --product "product_id"
```

## Best Practices

### 1. Consistency
- All products in a group should have the exact same varLinks
- If you add a new variant, update ALL products in the group

### 2. Naming Conventions
- Use consistent title format: "{Brand} {Model} - {Color/Variant}"
- Examples:
  - "Eureka Mignon Zero - Chrome"
  - "Breville Barista Express - Stainless Steel"

### 3. Maintenance
- When adding new colors/variants, immediately link them
- When discontinuing a variant, consider keeping it in varLinks if it's still findable via search
- Regularly audit variant groups to ensure consistency

### 4. Special Cases
- **Limited Editions:** Can be included if they're the same model
- **Regional Variants:** Include if customers might want to know about them
- **Different Voltages:** Generally keep separate (110V vs 220V)

## Common Issues and Solutions

### Issue: Incomplete Linking
**Symptom:** Some products show fewer color options than others
**Solution:** Re-run the linking tool with all product IDs

### Issue: Wrong Products Linked
**Symptom:** Different models appearing in variant selector
**Solution:** Create separate variant groups, use the unlink action

### Issue: Broken Links
**Symptom:** Variant selector shows errors or missing products
**Solution:** Check if linked products still exist, remove deleted product IDs

## Frontend Implementation

The theme should use the varLinks metafield to display a color/variant selector:

```liquid
{% if product.metafields.new.varLinks %}
  <div class="variant-selector">
    {% for linked_product_id in product.metafields.new.varLinks.value %}
      {% assign linked_product = linked_product_id | get_product %}
      <a href="{{ linked_product.url }}" 
         class="{% if linked_product.id == product.id %}active{% endif %}">
        {{ linked_product.title | split: ' - ' | last }}
      </a>
    {% endfor %}
  </div>
{% endif %}
```

## Examples

### Example 1: Eureka Zero Grinders
All colors of the Eureka Mignon Zero are linked:
- Black, White, Chrome, Anthracite (original colors)
- Red, Yellow, Silver, Pale Blue, Blue (new colors)
- Special editions (Black w/ Black Spout, White w/ Black Spout)

### Example 2: Espresso Machines
Different finishes of the same model:
- Breville Barista Express - Stainless Steel
- Breville Barista Express - Black Sesame
- Breville Barista Express - Red Velvet

## Automation Opportunities

1. **Auto-link on Creation:** When creating products with matching model names
2. **Bulk Operations:** Link entire collections based on product naming patterns
3. **Sync Checking:** Regular audits to ensure all variant groups are properly synced
4. **Report Generation:** List all variant groups and their linking status