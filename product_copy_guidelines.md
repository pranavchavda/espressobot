## ☕ iDrinkCoffee.com Product Listing Guide for AI

**Goal:** Create compelling, accurate product listings for iDrinkCoffee.com that match our brand and improve SEO.



**Remember to:**

- **Act human:** Write naturally and engagingly.
- **Be accurate:** Double-check all information before including it.
- **Follow instructions closely:** Adhere to the structure and formatting below.- **Canadaian English:** Use Canadian English instead of American English.

## 1. Gather Product Information

- If the product details aren't provided, use the web search tool to find accurate, up-to-date information.
- **Important:** Always fact-check the information you find.

- **Product Naming Convention:** If the exact name of the listing isn't provided, it is usually the Brand name followed by the product name and a descriptor if needed - E.g "Profitec Jump Espresso Machine - Stainless Steel"


## 2. Build the Product Listing

Each listing must include these components in the specified order:

## 2.1 Buy Box (`buybox.content`)

- **Metafield:**
  - **Namespace:** `buybox`
  - **Key:** `content`
  - **Type:** `multi_line_text_field`
- **What it is:** A short, attention-grabbing sales pitch (think J. Peterman). It's the first thing customers see.
- **Tone:** Creative, confident, and engaging.
- **Example:** "Imagine the perfect espresso, crafted by you. The Sanremo YOU Espresso Machine puts the power of a professional barista in your hands, offering unmatched control and a truly personalized brewing experience."

## 2.2 Overview (body_html)

- **What it is:** A detailed, engaging paragraph that introduces the product.
- **Focus:** Highlight key features, design, performance, and value.
- **Tone:** Conversational ("kitchen conversation" style), but informative.

## 2.3 Features Section

- Use bolded subtitles for each feature, followed by a concise description.

- **Optional: JSON Format**

  - **Metafield:**
    - **Namespace:** `content`
    - **Key:** `featuresjson`
    - **Type:** `json`
  - **Example:**

  ```
  json{"features":
  [
    {
      "title": "Complete Control",
      "description": "Paddle allows control over pressure with 6 presets and 12 fully customizable profiles."
    },
    {
      "title": "Double Boiler",
      "description": "AISI 316 stainless steel provides reliable temperature stability for both brew and steam."
    }
  ]
  }
  ```

## 2.4 FAQs (`faq.content`)

- **Metafield:**

  - **Namespace:** `faq`
  - **Key:** `content`
  - **Type:** `json`

- **What it is:** A list of 5-7 common customer questions with clear, professional answers.

- **Important:**

  - Answer in complete sentences.
  - Do not include warranty information here.
  - Use the web search tool to research common questions related to the product.

- **Example:**

  ```
  json{"faqs":
  [
    {
      "question": "How does the temperature control system work on the Profitec Jump?",
      "answer": "The Jump features a multifunction switch that allows you to select between three PID-controlled boiler temperatures. This switch is conveniently located underneath the machine and also controls pre-infusion and ECO mode settings."
    },
    {
      "question": "Can the Profitec Jump be used for commercial purposes?",
      "answer": "No, the Profitec Jump is not designed for commercial use. This machine is considered a prosumer-grade machine."
    }
  
  ]
  }
  ```

## 2.5 Tech Specs (`specs.techjson`)

- **Metafield:**
  - **Namespace:** `specs`
  - **Key:** `techjson`
  - **Type:** `json`
- **What it is:** Technical details about the product.
- **Must include:** Manufacturer, boiler type, size, power, and other relevant specifications.

- **Example:**

```
json
{
    "manufacturer": "Profitec",
    "boiler_type": "Single Boiler",
    "size": "12",
    "power": "1200W",
    "other_specs": "Other relevant specifications"
}
```

## 2.6 Variant Preview Name (`ext.variantPreviewName`)

- **Metafield:**
  - **Namespace:** `ext`
  - **Key:** `variantPreviewName`
  - **Type:** `single_line_text_field`
- **What it is:** The primary identifier for a product variant (e.g., color, model).
- **Example:** `Black`, `White`, etc.
- **Important:** iDrinkCoffee.com creates a separate product listing for each variant, instead of using Shopify's built-in variant system. This is only important when more than one listing is being added as variants of each other

## 3. Add Tags

Tags are crucial for filtering and internal search. Use **both** standard and specific tags.

## 3.1 Product Type Tags:

- **Espresso Machines:** `espresso-machines`, `Espresso Machines`
- **Grinders:** `grinders`, `grinder`
- **Accessories:** `accessories`, `WAR-ACC`
- **Consumables:** `WAR-CON`
- **Commercial Use:** `WAR-COM`, `commercial`
- **PARTS:** `WAR-PAR`
- **Consumer Use (Machines/Grinders):** `WAR-SG`, `consumer`
- **WAR\* Tags:** These control warranty and messaging on product pages (e.g., "Commercial use only").

## 3.2 Brand/Vendor Tags:

- Add the vendor name in lowercase.
- **Espresso Machines or Grinders:** ascaso, bezzera, bellezza, ecm, gaggia, profitec, magister, quick mill, coffee brain, jura, sanremo, rancilio - add `VIM` and `WAR-VIM`

## 3.3 Thematic Tags:

- `NC_EspressoMachines`, `NC_DualBoiler`, `NC_Steam-Wand`, `icon-E61-Group-Head`, `super-automatic`, `burr-grinder`, etc.
- Match tags to the product's features and functions.
- Use `manual-drip` or `dual-purpose-grinder` when appropriate.

## 4. Coffee Product Listings (Escarpment Coffee Roasters)

- **Vendor:** `Escarpment Coffee Roasters`
- **Product Type:** `Fresh Coffee`
- **Skip Buy Box and FAQs** (unless specifically requested).

## 4.1 Required Tag Format:

Use these key-value style tags:

```
ELEVATION-3300 feet
HARVESTING-Hand-Picking
VARIETAL-Bourbon
ACIDITY-Very Low
REGION-Tanzania
PROCESSING-Washed
NOTES-Balanced# Light Acidity# Winey Taste
BLEND-Single Origin
ROAST-Medium
BREW-Filter
origin-tanzania
```

## 4.2 Metafield:

- **Namespace:** `coffee`
- **Key:** `seasonality`
- **Type:** `boolean`
- **Value:** `true` if seasonal; `false` if a standard offering.

## 5. Shopify Product Creation Rules

- **Status:** Always set to `DRAFT`.
- **Required Fields:** `title`, `body_html`, `vendor`, `product_type`, `tags`, `variants.price`, `variants.sku`
- **Image Alt Text:** Use relevant product feature or name.

## 6. Important Reminders

- **Cost of Goods (COGS):** Include the product cost for COGS calculations (when available).
- **Inventory Tracking:** Enable inventory tracking and set to "deny" for "Continue Selling" when out of stock.
- **Product Status:** Always set the product status to `DRAFT` unless instructed otherwise.
- **Inventory Weight:** Set the inventory weight to the weight of the product in grams for Shopify.

## 7. Exceptions

- For accessories, coffee and cleaning products, you can skip the Buy Box, FAQs, Tech Specs, and Features sections. Focus on a detailed overview (`body_html`).

## Notes:

✅ Variant Creation (Single Variant Products)
mutation {
  productVariantsBulkCreate(productId: "gid://shopify/Product/<ProductID>", variants: [
    {
      price: "<Price>",
      optionValues: [{ optionName: "Title", name: "Default Title" }],
      inventoryItem: {
        sku: "<YourSKU>"
      }
    }
  ]) {
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
✅ Media Upload (Image)
mutation {
  productCreateMedia(productId: "gid://shopify/Product/<ProductID>", media: [
    {
      originalSource: "<IMAGE_URL>",
      mediaContentType: IMAGE
    }
  ]) {
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
✅ Variant Price Update
mutation {
  productVariantsBulkUpdate(productId: "gid://shopify/Product/<ProductID>", variants: [
    {
      id: "gid://shopify/ProductVariant/<VariantID>",
      price: "<NewPrice>"
    }
  ]) {
    userErrors {
      field
      message
    }
  }
}
✅ SKU Update (via Inventory Item)
mutation {
  inventoryItemUpdate(id: "gid://shopify/InventoryItem/<InventoryItemID>", input: {
    sku: "<NewSKU>"
  }) {
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
✅ To add an option (such as “Size”) to an existing product, always use the productOptionsCreate mutation.
Do not rely on productUpdate, productSet, or older/deprecated mutations for adding options.
Example Mutation:

mutation {
  productOptionsCreate(
    productId: "gid://shopify/Product/xxxxxxxxxxxx",
    options: [
      {
        name: "Size",
        values: [
          { name: "S" },
          { name: "M" },
          { name: "L" },
          { name: "XL" },
          { name: "2XL" }
        ]
      }
    ]
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

## Important notes for variant cost and sku

Shopify Product Guide Addendum: Managing Variant Cost
How to Update the Variant Cost in Shopify (2025+)
As of 2025-04 and later Shopify API versions:

The variant’s “cost” (COGS/unit cost) is managed on the Inventory Item, not the Product or Variant directly.
Use the inventoryItemUpdate GraphQL mutation to update the cost of any variant.
The correct mutation and structure is:
```
mutation {
  inventoryItemUpdate(
    id: "gid://shopify/InventoryItem/xxxxxxx",   # InventoryItem GID for the variant
    input: {
      cost: "YOUR_COST_VALUE"                   # Use a string representing the currency amount
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
**Steps**:

Fetch the variant’s InventoryItem ID (each variant has one).
Use inventoryItemUpdate (not productVariantsBulkUpdate or any product/variant mutation) to set cost.
Always input cost as a string (e.g., "54.99").
Setting SKU and price is done via productVariantsBulkUpdate.
Cost is not updatable via productVariantsBulkUpdate—ignore any docs/examples that try to do so.
REST endpoints for cost are deprecated; always use GraphQL.
Best Practice:
Always verify fields supported by your current Shopify Admin API version when automating product or inventory management. Refer to official Shopify GraphQL docs for the latest.

ALWAYS 
- Use the correct mutation for the data you wish to update.
- Always verify with the current API documentation if you have issues.
- Use the Introspetion tool and perplexity ask tool for help, if you make mistakes, get help, don't guess, or ask the user to do it or suggest alternatives.