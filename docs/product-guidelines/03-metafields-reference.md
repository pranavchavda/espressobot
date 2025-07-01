# Metafields Reference

This document provides a complete reference for all metafields used in the iDrinkCoffee.com product system.

## Core Content Metafields

### Buy Box Content
- **Namespace:** `buybox`
- **Key:** `content`
- **Type:** `multi_line_text_field`
- **Purpose:** Short sales pitch displayed prominently
- **Example:** "Experience café-quality espresso at home..."

### Features JSON
- **Namespace:** `content`
- **Key:** `featuresjson` (also `featruresjson` - typo variant)
- **Type:** `json`
- **Format:**
```json
{
  "features": [
    {
      "copy": "**Complete Control**\nThis machine comes with everything you need for precision brewing",
    }
  ]
}
```

### Features Box
- **Namespace:** `content`
- **Key:** `features_box`
- **Type:** Reference to metaobjects
- **Purpose:** Rich feature highlights with images
- **Important:** Metaobjects must be published (status: ACTIVE) to display on storefront
- **Publishing:** By default, metaobjects are created in DRAFT status. Use the `metaobjectUpdate` mutation to set `capabilities.publishable.status` to "ACTIVE"

### FAQs
- **Namespace:** `faq`
- **Key:** `content`
- **Type:** `json`
- **Format:**
```json
{
  "faqs": [
    {
      "question": "How does the temperature control work?",
      "answer": "The Jump features a multifunction switch..."
    }
  ]
}
```

## Technical Specifications

### Tech Specs JSON
- **Namespace:** `specs`
- **Key:** `techjson`
- **Type:** `json`
- **Format:**
```json
{
  "manufacturer": "Profitec",
  "boiler_type": "Single Boiler",
  "size": "12",
  "power": "1200W",
  "other_specs": "Additional specifications"
}
```

### Size Dimensions
- **Namespace:** `size`
- **Keys:** `Weight`, `Height`, `Width`, `Depth`
- **Type:** Simple value metafields
- **Example:** `{ key: "Weight", value: "10kg" }`

## Display & Organization

### Variant Preview Name
- **Namespace:** `ext`
- **Key:** `variantPreviewName`
- **Type:** `single_line_text_field`
- **Purpose:** Primary identifier for variants (e.g., "Black", "Stainless Steel")

### Variant Tooltips
- **Namespace:** `custom`
- **Keys:** `variant_tooltip` (string), `variantTooltips` (JSON)
- **Type:** String or JSON
- **Purpose:** Help text for product options

### Breadcrumb Reference
- **Namespace:** `custom`
- **Key:** `breadcrumb_reference`
- **Type:** Reference to Collections
- **Purpose:** Navigation breadcrumbs

## Media & Downloads

### Video
- **Namespace:** `littlerocket`
- **Keys:** `Video`, `video`
- **Type:** String (URL or embed code)

### Downloads
- **Namespace:** `custom`
- **Key:** `downloads`
- **Type:** Reference to files
- **Purpose:** Product manuals, guides

### Included Items
- **Namespace:** `littlerocket`
- **Key:** `included`
- **Type:** String (JSON or delimited list)
- **Purpose:** Lists accessories included with product

## Sales & Inventory

### Sale End Date
- **Namespace:** `inventory`
- **Key:** `ShappifySaleEndDate`
- **Type:** String (ISO date)
- **Format:** `2023-08-04T03:00:00Z`
- **Purpose:** Promotion end dates

### Seasonality (Coffee)
- **Namespace:** `coffee`
- **Key:** `seasonality`
- **Type:** `boolean`
- **Purpose:** Indicates seasonal availability

## Reviews & Social Proof

### Reviews Count
- **Namespace:** `yotpo`
- **Key:** `reviews_count`
- **Type:** Integer (as string)

### Rich Snippets HTML
- **Namespace:** `yotpo`
- **Key:** `richsnippetshtml`
- **Type:** String (HTML)
- **Purpose:** SEO-optimized structured data

## Product Relationships

### Variant Links
- **Namespace:** `new`
- **Key:** `varLinks`
- **Type:** Reference to products
- **Purpose:** Links to related/alternative products

### Complementary Products
- **Namespace:** `shopify--discovery--product_recommendation`
- **Key:** `complementary_products`
- **Type:** Reference to products
- **Purpose:** Recommended complementary items

### Promo CTA
- **Namespace:** `promo`
- **Key:** `cta`
- **Type:** Reference to metaobject
- **Purpose:** Promotional call-to-action

## Setting Metafields

Use the `set_metafield.py` tool:
```bash
python tools/set_metafield.py \
  --product-id "123456789" \
  --namespace "buybox" \
  --key "content" \
  --value "Your compelling buy box content..." \
  --type "multi_line_text_field"
```

For JSON metafields:
```bash
python tools/set_metafield.py \
  --product-id "123456789" \
  --namespace "faq" \
  --key "content" \
  --value '{"faqs":[{"question":"Q1","answer":"A1"}]}' \
  --type "json"
```