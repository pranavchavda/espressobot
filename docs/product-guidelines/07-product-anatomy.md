# Product Anatomy

A complete reference for the iDrinkCoffee product data model, including all Shopify fields and custom metafields.

## Core Shopify Fields

- **id**: Unique identifier (GID format)
- **title**: Product name
- **handle**: URL slug
- **productType**: Category (e.g., "Espresso Machines")
- **vendor**: Brand/manufacturer
- **descriptionHtml**: Main product description (HTML)
- **status**: DRAFT, ACTIVE, or ARCHIVED
- **tags**: Array of tag strings
- **seo**: SEO metadata object
  - `title`: SEO title
  - `description`: SEO description
- **media**: Product images and videos
- **variants**: Product variants with pricing
- **options**: Product options (size, color, etc.)

## Custom Metafield Structure

Each metafield is identified by namespace and key:

### Content Metafields

#### Buy Box
- **Location**: `buybox.content`
- **Type**: multi_line_text_field
- **Purpose**: Premium sales copy

#### Features JSON
- **Location**: `content.featuresjson`
- **Type**: json
- **Schema**: `{"features": [{"title": "", "description": ""}]}`

#### Features Box
- **Location**: `content.features_box`
- **Type**: metaobject reference
- **Purpose**: Visual feature highlights
- **Note**: Metaobjects must be published (status: ACTIVE) to display on storefront

#### FAQs
- **Location**: `faq.content`
- **Type**: json
- **Schema**: `{"faqs": [{"question": "", "answer": ""}]}`

### Technical Specifications

#### Tech Specs
- **Location**: `specs.techjson`
- **Type**: json
- **Schema**: Variable by product type

#### Dimensions
- **Location**: `size.{Weight|Height|Width|Depth}`
- **Type**: single_line_text_field
- **Example**: "10kg", "45cm"

### Display & Variants

#### Variant Preview Name
- **Location**: `ext.variantPreviewName`
- **Type**: single_line_text_field
- **Purpose**: Display name for variant (e.g., "Black")

#### Variant Tooltips
- **Location**: `custom.variantTooltips`
- **Type**: json
- **Purpose**: Help text for options

#### Variant Links
- **Location**: `new.varLinks`
- **Type**: product reference list
- **Purpose**: Related product variants

### Navigation & Discovery

#### Breadcrumbs
- **Location**: `custom.breadcrumb_reference`
- **Type**: collection reference list
- **Purpose**: Navigation hierarchy

#### Complementary Products
- **Location**: `shopify--discovery--product_recommendation.complementary_products`
- **Type**: product reference list

### Media & Downloads

#### Video
- **Location**: `littlerocket.video`
- **Type**: single_line_text_field
- **Content**: URL or embed code

#### Downloads
- **Location**: `custom.downloads`
- **Type**: file reference list
- **Purpose**: Manuals, guides

#### Included Items
- **Location**: `littlerocket.included`
- **Type**: single_line_text_field
- **Purpose**: What's in the box

### Sales & Inventory

#### Sale End Date
- **Location**: `inventory.ShappifySaleEndDate`
- **Type**: single_line_text_field
- **Format**: ISO 8601 date

#### Coffee Seasonality
- **Location**: `coffee.seasonality`
- **Type**: boolean
- **Purpose**: Seasonal availability flag

### Reviews & SEO

#### Reviews Count
- **Location**: `yotpo.reviews_count`
- **Type**: number_integer
- **Purpose**: Review count display

#### Rich Snippets
- **Location**: `yotpo.richsnippetshtml`
- **Type**: multi_line_text_field
- **Purpose**: Structured data markup

### Promotional

#### Promo CTA
- **Location**: `promo.cta`
- **Type**: metaobject reference
- **Purpose**: Call-to-action banner

## Data Relationships

```
Product
├── Variants[]
│   └── InventoryItem (SKU, Cost)
├── Metafields{}
│   ├── Content (buybox, features, FAQs)
│   ├── Technical (specs, dimensions)
│   ├── Display (tooltips, preview names)
│   └── References (variants, complementary)
├── Tags[]
│   ├── Category (NC_*, product types)
│   ├── Features (icon-*, capabilities)
│   ├── Warranty (WAR-*)
│   └── Status (sale, preorder, etc.)
└── Media[]
    ├── Images
    └── Videos
```

## Example Product Query

```graphql
query getProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    vendor
    productType
    descriptionHtml
    tags
    seo {
      title
      description
    }
    variants(first: 10) {
      edges {
        node {
          id
          price
          sku
          inventoryItem {
            id
            unitCost {
              amount
            }
          }
        }
      }
    }
    metafields(first: 50) {
      edges {
        node {
          namespace
          key
          value
          type
          reference {
            ... on Product {
              id
              title
            }
            ... on Collection {
              id
              title
            }
          }
        }
      }
    }
  }
}
```

## Key Conventions

1. **Variant Management**: Each color/model variant is a separate product
2. **GID Format**: Always use full GID: `gid://shopify/Product/123456789`
3. **Draft Status**: All new products start as DRAFT
4. **Tag Naming**: Lowercase for brands, specific formats for features
5. **Metafield Types**: Use appropriate types (json, boolean, reference)
6. **Cost Management**: Update via InventoryItem, not variant