# Coffee Product Guidelines

Special guidelines for Escarpment Coffee Roasters and other coffee products.

## Coffee Product Basics

- **Vendor:** `Escarpment Coffee Roasters`
- **Product Type:** `Fresh Coffee`
- **Status:** Always start with `DRAFT`

## Simplified Content Requirements

For coffee products, you can skip:
- Buy Box
- FAQs
- Tech Specs
- Features sections

Focus on creating a detailed and engaging overview in the `body_html`.

## Coffee-Specific Tags

### Required Tag Format

All coffee products must use structured tags with specific prefixes:

- `ELEVATION-{value}` - Growing elevation
- `HARVESTING-{value}` - Harvest method/time
- `VARIETAL-{value}` - Coffee variety
- `ACIDITY-{value}` - Acidity level
- `REGION-{value}` - Origin region
- `PROCESSING-{value}` - Processing method
- `NOTES-{value}` - Tasting notes (use # instead of commas)
- `BLEND-{value}` - Blend information
- `ROAST-{value}` - Roast level
- `BREW-{value}` - Recommended brewing method
- `origin-{value}` - Country of origin

### Example Tags

```
ROAST-Medium
REGION-Colombia
PROCESSING-Washed
NOTES-Chocolate#Caramel#Brown Sugar
ELEVATION-1600-1800m
VARIETAL-Caturra#Castillo
origin-colombia
```

**Important:** For NOTES tags, use # to separate values. These will be rendered as commas on the site.

## Seasonality Metafield

All coffee products should have a seasonality indicator:

- **Namespace:** `coffee`
- **Key:** `seasonality`
- **Type:** `boolean`
- **Value:** 
  - `true` for seasonal/limited offerings
  - `false` for standard year-round offerings

## Creating Coffee Products

### Using create_product.py

```bash
python tools/create_product.py \
  --title "Colombia La Esperanza" \
  --vendor "Escarpment Coffee Roasters" \
  --type "Fresh Coffee" \
  --price "22.99" \
  --description "A bright, complex Colombian coffee..." \
  --tags "ROAST-Medium,REGION-Colombia,NOTES-Chocolate#Caramel#Citrus,origin-colombia"
```

### Setting Seasonality

```bash
python tools/set_metafield.py \
  --product-id "123456789" \
  --namespace "coffee" \
  --key "seasonality" \
  --value "true" \
  --type "boolean"
```

## Best Practices

1. **Descriptive Names:** Use origin and farm/coop name when available
   - Good: "Colombia La Esperanza"
   - Better: "Colombia La Esperanza - Huila Region"

2. **Detailed Descriptions:** Include:
   - Origin story
   - Flavor profile
   - Processing details
   - Recommended brewing methods
   - Producer information

3. **Accurate Tags:** Research and verify:
   - Exact growing regions
   - Processing methods
   - Elevation ranges
   - Varietals

4. **Inventory Management:**
   - Coffee is perishable - manage inventory carefully
   - Consider using "Continue selling when out of stock" for pre-orders

## Example Coffee Product

```
Title: Ethiopia Yirgacheffe - Konga Cooperative
Vendor: Escarpment Coffee Roasters
Product Type: Fresh Coffee
Price: $24.99

Description:
This exceptional washed Ethiopian coffee from the Konga Cooperative showcases 
the best of Yirgacheffe's renowned terroir. Grown at 1850-2100 meters, these 
heirloom varietals produce a clean, bright cup with distinctive floral aromatics 
and sparkling citrus acidity. Notes of bergamot, lemon zest, and jasmine dance 
with a delicate honey sweetness and silky body.

Tags:
- ROAST-Light
- REGION-Yirgacheffe
- PROCESSING-Washed
- ELEVATION-1850-2100m
- VARIETAL-Heirloom
- NOTES-Bergamot#Lemon#Jasmine#Honey
- BREW-Pour Over#V60
- origin-ethiopia
- NC_FreshCoffee
- escarpment coffee roasters
```