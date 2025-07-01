# API Technical Reference

## Important Notes

- **ALL Shopify REST endpoints are deprecated** - Use GraphQL exclusively
- Always verify with current API documentation for version-specific fields
- Check for `userErrors` in all mutation responses

## Variant Cost and SKU Management

As of 2025-04 Shopify API:
- Variant cost (COGS) is managed on the **Inventory Item**, not the Product or Variant
- SKU is also managed via the Inventory Item

### Update Variant Cost

```graphql
mutation {
  inventoryItemUpdate(
    id: "gid://shopify/InventoryItem/xxxxxxx",
    input: {
      cost: "54.99"  # String representing currency amount
    }
  ) {
    inventoryItem {
      id
      unitCost {
        amount
        currencyCode
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

### Update SKU

```graphql
mutation {
  inventoryItemUpdate(
    id: "gid://shopify/InventoryItem/xxxxxxx",
    input: {
      sku: "NEW-SKU-123"
    }
  ) {
    inventoryItem {
      id
      sku
    }
    userErrors {
      field
      message
    }
  }
}
```

## Product Creation

### Create Product with Variant

```graphql
mutation {
  productCreate(input: {
    title: "Product Name",
    vendor: "Brand Name",
    productType: "Category",
    descriptionHtml: "<p>Description</p>",
    status: DRAFT,
    tags: ["tag1", "tag2"]
  }) {
    product {
      id
      variants(first: 1) {
        edges {
          node {
            id
            inventoryItem {
              id
            }
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

### Create Variant for Existing Product

```graphql
mutation {
  productVariantsBulkCreate(
    productId: "gid://shopify/Product/123",
    variants: [{
      price: "99.99",
      optionValues: [{ optionName: "Title", name: "Default Title" }],
      inventoryItem: {
        sku: "SKU-123"
      }
    }]
  ) {
    productVariants {
      id
      inventoryItem {
        id
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

## Media Management

### Upload Product Images

```graphql
mutation {
  productCreateMedia(
    productId: "gid://shopify/Product/123",
    media: [{
      originalSource: "https://example.com/image.jpg",
      mediaContentType: IMAGE,
      alt: "Product front view"
    }]
  ) {
    media {
      alt
      mediaContentType
      status
    }
    mediaUserErrors {
      field
      message
    }
  }
}
```

## Options Management

### Add Product Options

Always use `productOptionsCreate` for adding options:

```graphql
mutation {
  productOptionsCreate(
    productId: "gid://shopify/Product/123",
    options: [{
      name: "Size",
      values: [
        { name: "Small" },
        { name: "Medium" },
        { name: "Large" }
      ]
    }]
  ) {
    userErrors {
      field
      message
      code
    }
    product {
      id
      options {
        name
        optionValues {
          name
        }
      }
    }
  }
}
```

## Price Management

### Update Variant Price

```graphql
mutation {
  productVariantsBulkUpdate(
    productId: "gid://shopify/Product/123",
    variants: [{
      id: "gid://shopify/ProductVariant/456",
      price: "149.99"
    }]
  ) {
    userErrors {
      field
      message
    }
  }
}
```

### Price Lists (for USD pricing)

For US/USD prices, use price list ID: `gid://shopify/PriceList/18798805026`

```graphql
mutation {
  priceListFixedPriceAdd(
    priceListId: "gid://shopify/PriceList/18798805026",
    prices: [{
      variantId: "gid://shopify/ProductVariant/456",
      price: {
        amount: "99.99",
        currencyCode: USD
      }
    }]
  ) {
    userErrors {
      field
      message
    }
  }
}
```

## Metafields

### Set Metafield

```graphql
mutation {
  productUpdate(input: {
    id: "gid://shopify/Product/123",
    metafields: [{
      namespace: "buybox",
      key: "content",
      value: "Your content here",
      type: "multi_line_text_field"
    }]
  }) {
    userErrors {
      field
      message
    }
  }
}
```

## Tags Management

### Add Tags

Use `tagsAdd` instead of `productUpdate` for safety:

```graphql
mutation {
  tagsAdd(
    id: "gid://shopify/Product/123",
    tags: ["new-tag-1", "new-tag-2"]
  ) {
    userErrors {
      field
      message
    }
  }
}
```

### Remove Tags

```graphql
mutation {
  tagsRemove(
    id: "gid://shopify/Product/123",
    tags: ["tag-to-remove"]
  ) {
    userErrors {
      field
      message
    }
  }
}
```

## Publishing

### Publish to Channels

Required channels for iDrinkCoffee.com:
- Online Store: `gid://shopify/Channel/46590273`
- Point of Sale: `gid://shopify/Channel/46590337`
- Google & YouTube: `gid://shopify/Channel/22067970082`
- Facebook & Instagram: `gid://shopify/Channel/44906577954`
- Shop: `gid://shopify/Channel/93180952610`
- Hydrogen: `gid://shopify/Channel/231226015778`
- Attentive: `gid://shopify/Channel/255970312226`

```graphql
mutation {
  publishablePublish(
    id: "gid://shopify/Product/123",
    input: {
      publicationId: "gid://shopify/Channel/46590273"
    }
  ) {
    userErrors {
      field
      message
    }
  }
}
```

## Error Handling

Always check for errors in responses:

1. GraphQL errors (network/syntax issues)
2. `userErrors` field (business logic errors)
3. Validate data before mutations
4. Use proper GID format: `gid://shopify/Type/ID`

## Best Practices

1. Use atomic operations where possible
2. Batch similar operations
3. Always include field selections for object types
4. Store and reuse IDs (product, variant, inventory item)
5. Test mutations in development first
6. Use proper error handling and logging