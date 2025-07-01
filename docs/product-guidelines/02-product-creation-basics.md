# Product Creation Basics

## Core Requirements

Every product listing must include:
- Title (Format: `{Brand} {Product Name} {Descriptors}`)
- Vendor (brand name)
- Product Type
- Body HTML (detailed overview)
- At least one variant with price and SKU
- Appropriate tags
- Cost of goods (COGS)
- Status: DRAFT (always start with draft)

## Standard Product Components

### 1. Buy Box (`buybox.content`)
- **Type:** `multi_line_text_field`
- **Purpose:** Short, attention-grabbing sales pitch
- **Tone:** Creative, confident, engaging (think J. Peterman style)
- **Example:** "Imagine the perfect espresso, crafted by you. The Sanremo YOU Espresso Machine puts the power of a professional barista in your hands..."

### 2. Overview (body_html)
- Detailed, engaging paragraph introducing the product
- Focus on key features, design, performance, and value
- Conversational "kitchen conversation" style

### 3. Features Section
- Bolded subtitles for each feature
- Concise descriptions
- Can be stored as JSON in `content.featuresjson` metafield

### 4. FAQs (`faq.content`)
- 5-7 common customer questions
- Clear, professional answers in complete sentences
- No warranty information in FAQs
- Stored as JSON

### 5. Tech Specs (`specs.techjson`)
- Technical details: manufacturer, boiler type, size, power, etc.
- Stored as JSON

### 6. Variant Preview Name (`ext.variantPreviewName`)
- Primary identifier for product variant (color, model)
- Used when creating separate products for each variant

## Product Creation Workflow

1. **Search First**
   ```bash
   python tools/search_products.py "product name or sku"
   ```

2. **Create Product**
   ```bash
   python tools/create_product.py \
     --title "Brand Product Name" \
     --vendor "Brand" \
     --type "Category" \
     --price "99.99" \
     --description "Detailed description..."
   ```

3. **Add Metafields**
   - Buy box content
   - FAQs
   - Technical specifications
   - Features

4. **Add Tags**
   - Product type tags
   - Brand tags
   - Feature tags
   - Warranty tags

5. **Create Feature Boxes** (optional)
   - 2-4 visual highlights for the product page
   - **Important:** Feature box metaobjects must be published (status: ACTIVE) to display
   - New metaobjects default to DRAFT status and won't show on storefront until activated

## Inventory Settings

- **Tracking:** Enable inventory tracking
- **Policy:** Set to "DENY" (stop selling when out of stock)
- **Weight:** Set in grams for shipping calculations
- **Cost:** Include COGS for profitability tracking

## Image Guidelines

- Use descriptive alt text
- Include multiple angles/views
- Show product in use when possible
- Use `productCreateMedia` mutation for uploads

## Exceptions

For accessories, coffee, and cleaning products:
- Can skip Buy Box, FAQs, Tech Specs, and Features sections
- Focus on detailed overview in body_html