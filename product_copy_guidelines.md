## ☕ iDrinkCoffee.com Product Listing Guide

**Goal:** Create compelling, accurate product listings for iDrinkCoffee.com that match our brand and improve SEO.

**Remember to:**

- **Act human:** Write naturally and engagingly.
- **Be accurate:** Double-check all information before including it.
- **Follow instructions closely:** Adhere to the structure and formatting below.
- **Canadaian English:** Use Canadian English instead of American English.

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

## 3.4 The full list of tags:

### General Tags
consumer, commercial, WAR-ACC, WAR-CON, WAR-COM, WAR-SG, WAR-VIM, VIM

### Category/Collection Tags
NC_300ml, NC_Accessories5, NC_Appliances, NC_AutomaticDrip, NC_BaristaTools, NC_Baristatools, NC_BeanStorage, NC_Black, NC_BlackCoffee, NC_BlackTea, NC_Books, NC_BrandedCups, NC_Brandedcups, NC_BrewGrinders, NC_Brewgrinders, NC_BurrSets, NC_CaffeLatte, NC_CaféSyrups, NC_Cleaning, NC_Coffee, NC_CoffeeMakers, NC_CoffeeRoasters, NC_CoffeeandTea, NC_CofffeeandTea, NC_ColdBrew, NC_Decaffe, NC_Decaffeinated, NC_DecaffeinatedCoffee, NC_Descaling, NC_Distributors, NC_DosingCups, NC_DosingFunnels, NC_DoubleWalledGlassCups, NC_Drinkware, NC_DripCoffeeGrinders, NC_DualBoiler, NC_DualPurposeGrinders, NC_Dualpurposegrinders, NC_ElectricMilkFrothers, NC_EspressoCoffee, NC_EspressoGrinders, NC_EspressoMachines2, NC_EspressoMachines-DualBoiler, NC_EspressoMachinesUpgrades, NC_Espressogrinders, NC_FilterBaskets, NC_FilterBrewing, NC_Filters, NC_Flavoured, NC_FlowControl, NC_FrenchPress, NC_FreshCoffee, NC_FrothingPitchers, NC_FrozenBeverageDispensers, NC_Fruit, NC_Green, NC_GreenCoffee, NC_GreenTea, NC_Grinders6, NC_GroupGaskets, NC_Handgrinders, NC_HeatExchanger, NC_Heatexchanger, NC_Herbal, NC_HerbalTea, NC_Hoppers, NC_Kettles, NC_KnockBoxes, NC_LapelPins, NC_LatteArt, NC_Lever, NC_Maintainance, NC_Maintenance, NC_Manual, NC_ManualBrewing, NC_ManualDripOrPourOver, NC_ManualDriporpourover, NC_MilkAlternatives, NC_MilkContainers, NC_MokaPot, NC_Oolong, NC_Organic, NC_Other, NC_OtherGlassware, NC_PIDControllers, NC_Parts, NC_PorcelainCups, NC_PorcelainSaucers, NC_Portafilters, NC_PourOverDrippers, NC_PuEhr, NC_Rooibos, NC_Scales, NC_ServersandCarafes, NC_Shottimers, NC_ShowerScreens, NC_SingleBoiler, NC_Singleboiler, NC_SugarFreeSyrups, NC_SuperAutomatic, NC_Superautomatic, NC_Syrups, NC_Tamper, NC_TamperStands, NC_Tampers, NC_TampingStands, NC_Tea, NC_TeaKettles, NC_TeaPots, NC_Thermometers, NC_Travel, NC_TravelMug, NC_Upgrades, NC_Vacuum, NC_WaterTreatment, NC_White, NC_WoodUpgrade

### Other Tags
automatic-drip, automatic-tamper, bottomless-portafilter, bottomless-portafilters, burr-grinder, burrs, coffee maker, coffee makers, coffee tamper, coffee-aficionado, coffee-brewer, coffee-maker, coffee-makers, coffee-roaster, coffee-sensor, consolation15, consumable, double-boiler, drip-grinder, dripper, dual-purpose-grinder, electric-milk, electric-tamper, espress-machines, espresso-bean, espresso-grinder, green-coffee, grinder2, grinders, hand-grinder, heat-exchange, hemrousdiscount, herbal-tisanes, heycafe, hot-water-tower, icon- Stepless-Adjustment, icon-58mm-Portafilter2, icon-Analog-Controls, icon-Bypass-Doser, icon-Cappucinatore, icon-Conical-Burrs, icon-Digital-Controls, icon-Doserless, icon-Double-Boiler, icon-E61-Group-Head, icon-Flat-Burrs, icon-Heat-Exchanger, icon-One-Touch-Cappuccino, icon-PID, icon-Plumbed-In, icon-Programmable, icon-Rotary-Pump, icon-Shot-Timer, icon-Single-Boiler, icon-Sirai, icon-Steam-Wand, icon-Stepless-Adjustment, icon-Stepped-Adjustment, icon-Super-Automatic, icon-Thermoblock, icon-Vibration-Pump, icon-Water-Tank5, manual, manual-drip, manual-grinder, milk, non-dairy, server-filter, sugarfree, sugarfree_yes, super-automatic, superautomatic, superautomaticmachine, syrup, t-shirt, tags, tamper, tamper-handle, tamper-stand, tamping-stand, tea, tea-brewer, tea-kettle, tea-pot, teacup

### Roasted Coffee Tag Format
ELEVATION-*, HARVESTING-*, VARIETAL-*, ACIDITY-*, REGION-*, PROCESSING-*, NOTES-*, BLEND-*, ROAST-*, BREW-*, origin-*
For Notes, use # in lieu of commas. the #s will be rendered as commas. The notes are formatted this way so that they don't add as multiple tags on Shopify.

## 4. Coffee Product Listings (Escarpment Coffee Roasters)

- **Vendor:** `Escarpment Coffee Roasters`
- **Product Type:** `Fresh Coffee`
- **Skip Buy Box and FAQs** (unless specifically requested).

## 4.1 Required Tag Format:
   See the Roasted Coffee Tag Format section for the required tag format.

## 4.2 Metafield:

- **Namespace:** `coffee`
- **Key:** `seasonality`
- **Type:** `boolean`
- **Value:** `true` if seasonal; `false` if a standard offering.

## 5. Important Shopify Product Creation Rules

- **Status:** Always set to `DRAFT`.
- **Required Fields:** `title`, `body_html`, `vendor`, `product_type`, `tags`, `variants.price`, `variants.sku`
- **Image Alt Text:** Use relevant product feature or name.
- **Use MCP Tools:** When creating products, use `product_create()` with all metafields and tags instead of multiple GraphQL mutations. This ensures consistency and handles edge cases better.

## 6. Important Reminders

- **Cost of Goods (COGS):** Include the product cost for COGS calculations (if not provided, ask the user before creating the product).
- **Inventory Tracking:** Enable inventory tracking and set to "deny" for "Continue Selling" when out of stock.
- **Inventory Weight:** Set the inventory weight to the weight of the product in grams for Shopify.
- **Feature Boxes:** After creating a product, consider adding 2-4 feature boxes using `create_feature_box()` to highlight key benefits on the product page.

## 7. Exceptions

- For accessories, coffee and cleaning products, you can skip the Buy Box, FAQs, Tech Specs, and Features sections. Focus on a detailed overview (`body_html`).

## 8. Product Creation Workflow Using MCP Tools

1. **Search First:** Use `search_products(title_or_sku)` to check if a similar product exists
2. **Create Product:** Use `product_create()` with all necessary fields:
   - title, vendor, productType, bodyHtml
   - tags (all required tags from sections above)
   - variantPrice, variantSku
   - Optional: handle, buyboxContent, faqsJson, techSpecsJson, variantCost, variantWeight
3. **Add Feature Boxes:** Use `create_feature_box(product_id, title, text, image_url)` to add visual highlights
4. **Manage Tags:** Use `product_tags_add()` or `product_tags_remove()` for any tag adjustments
5. **Update if Needed:** Use `product_update()` for any modifications

## 9. Important notes for variant cost and sku

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
Use inventoryItemUpdate to set cost.
Always input cost as a string (e.g., "54.99").
Setting SKU and price is done via productVariantsBulkUpdate.
Cost is updatable via productVariantsBulkUpdate only via InventoryItem. You can also use inventoryItemUpdate to update the cost of a variant.
ALL SHOPIFY REST endpoints are deprecated; always use GraphQL.
Best Practice:
Always verify fields supported by your current Shopify Admin API version when automating product or inventory management. Refer to official Shopify GraphQL docs via available tools/MCP.

ALWAYS 
- Use the correct mutation for the data you wish to update.
- Always verify with the current API documentation if you have issues.
- Use the Introspetion tool and perplexity ask tool for help, if you make mistakes, get help, don't guess, or ask the user to do it or suggest alternatives.

---
## Anatomy of a Product (iDrinkCoffee)

A product in the iDrinkCoffee system is a Shopify product entity that is extensively enriched with custom metafields, tags, and references. These augmentations support advanced merchandising, dynamic UI, and business-specific workflows. The following describes the key fields and, in particular, the custom metafields that are central to iDrinkCoffee’s product model.

### Core Shopify Fields

- **id**: Unique identifier for the product.
- **title**: Product name.
- **handle**: URL slug for the product.
- **productType**: Shopify product type/category.
- **vendor**: Brand or manufacturer.
- **descriptionHtml / description**: Product description (HTML and plain text).
- **seo**: SEO metadata (`title`, `description`).
- **media**: Array of images and videos, each with URLs, alt text, and dimensions.
- **variants & options**: Standard Shopify variant structure.

### iDrinkCoffee-Specific Metafields

These metafields extend the product data model. Each metafield is defined by a `key` and `namespace`, and its structure is described below.

#### 1. **Breadcrumbs**
- Key/Namespace: `breadcrumb_reference` in `custom`
- **Type:** Reference to Shopify Collections
- Schema: `references`: Array of up to 10 collections; Each: `{ id, title, handle }`
- **Purpose:** Used for generating navigation breadcrumbs.

#### 2. **Sizes**
- Key/Namespace: `Weight`, `Height`, `Width`, `Depth` in `size`
- **Type:** Simple value metafields
- Schema: Each `{ key, value }` (e.g., `{ key: "Weight", value: "10kg" }`)
- **Purpose:** Specifies product dimensions for specs and shipping.

#### 3. **Rich Snippets HTML**
- Key/Namespace: `richsnippetshtml` in `yotpo`
- **Type:** String (HTML)
- Schema: `{ key, namespace, value }`
- **Purpose:** Stores SEO-optimized HTML for structured data (reviews, ratings, etc).

#### 4. **Variant Tooltips**
- Key/Namespace:
  - `variant_tooltip` in `custom` (single string)
  - `variantTooltips` in `custom` (JSON)
- **Type:** String or JSON
- Schema: `{ key, namespace, value }`. JSON maps option values to tooltip text.
- **Purpose:** Tooltip/help text for product options or variants.

#### 5. **Reviews Count**
- Key/Namespace: `reviews_count` in `yotpo`
- **Type:** Integer (as string)
- Schema: `{ key, namespace, value }`
- **Purpose:** Number of product reviews.

#### 6. **Features**
- Key/Namespace:
  - `featruresjson` in `content` (typo)
  - `featuresjson` in `content`
- **Type:** JSON (stringified)
- Schema: `{ key, namespace, value }` where `value` is a JSON string, e.g. `{"features":[{"copy": "Feature 1"}]}`
- **Purpose:** List of product features, shown in feature boxes.

#### 7. **Buy Box Content**
- Key/Namespace: `content` in `buybox`
- **Type:** String (HTML or Markdown)
- Schema: `{ key, namespace, value }`
- **Purpose:** Custom content for the buy box area.

#### 8. **FAQs**
- Key/Namespace: `content` in `faq`
- **Type:** String (HTML, Markdown, or JSON)
- Schema: `{ key, namespace, value }` where `value` is a JSON string, e.g. `{"faqs":[{"question": "Question 1", "answer": "Answer 1"}]} `
- **Purpose:** Frequently asked questions for the product.

#### 9. **Video**
- Key/Namespace:
  - `Video` in `littlerocket`
  - `video` in `littlerocket`
- **Type:** String (URL or embed code)
- Schema: `{ key, namespace, value }`
- **Purpose:** Product video(s).

#### 10. **Included Items**
- Key/Namespace: `included` in `littlerocket`
- **Type:** String (JSON or delimited list)
- Schema: `{ key, namespace, value }`
- **Purpose:** Lists accessories/items included with the product.

#### 11. **Specs**
- Key/Namespace: `techjson` in `specs`
- **Type:** JSON (stringified)
- Schema: `{ key, namespace, value }` where `value` is a JSON string of technical specs.
- **Purpose:** Technical specifications.

#### 12. **Sale End**
- Key/Namespace: `ShappifySaleEndDate` in `inventory`
- **Type:** String (ISO date)
- Schema: `{ key, namespace, value }`
- **Purpose:** End date for a sale or promotion.

#### 13. **Seasonality**
- Key/Namespace: `seasonality` in `coffee`
- **Type:** String (e.g., "seasonal")
- Schema: `{ key, namespace, value }`
- **Purpose:** Indicates if the product is seasonal.

#### 14. **Downloads**
- Key/Namespace: `downloads` in `custom`
- **Type:** Reference (to files)
- Schema: `{ key, namespace, value, type, references }`, `references`: Array of up to 20 files; Each: `{ id, url, previewImage: { url, height, width } }`
- **Purpose:** Downloadable product files (manuals, guides).

#### 15. **Features Box**
- Key/Namespace: `features_box` in `content`
- **Type:** Reference (to metaobjects)
- Schema: `{ key, namespace, value, references }`, `references`: Array of metaobjects; Each: `{ id, fields: [ { key, value, type, reference } ] }`
- **Purpose:** Rich feature highlights, often with images.

#### 16. **Promo CTA**
- Key/Namespace: `cta` in `promo`
- **Type:** Reference (to metaobject)
- Schema: `{ key, value, reference }`, `reference`: Metaobject with fields (images, text, links, etc.)
- **Purpose:** Promotional call-to-action.

#### 17. **Variant Links**
- Key/Namespace: `varLinks` in `new`
- **Type:** Reference (to products)
- Schema: `{ key, namespace, value, references }`, `references`: Array of up to 30 products; Each: `{ id, title, handle, variantPreviewName (metafield), featuredImage, availableForSale }`
- **Purpose:** Links to related/alternative products.

#### 18. **Complementary Products**
- Key/Namespace: `complementary_products` in `shopify--discovery--product_recommendation`
- **Type:** Reference (to products)
- Schema: `{ key, namespace, value, references }`, `references`: Array of up to 30 products; Each: `{ id, title, handle, featuredImage, availableForSale }`
- **Purpose:** Products recommended as complements.

### Tags

Product tags are used for business logic, filtering, and UI presentation. Examples include:
- Warranty tags (e.g., `WAR-SG`, `WAR-ACC`)
- Seasonal or promotional tags
- Feature-related tags


### Summary

The iDrinkCoffee product model is a Shopify product augmented with a rich set of metafields and tags. These enable advanced merchandising, dynamic UI, and deep integration with business processes. Agents should always check both core product fields and these custom metafields/tags to understand and manipulate product data accurately.

---

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
Use inventoryItemUpdate to set cost.
Always input cost as a string (e.g., "54.99").
Setting SKU and price is done via productVariantsBulkUpdate.
Cost is updatable via productVariantsBulkUpdate only via InventoryItem. You can also use inventoryItemUpdate to update the cost of a variant.
ALL SHOPIFY REST endpoints are deprecated; always use GraphQL.
Best Practice:
Always verify fields supported by your current Shopify Admin API version when automating product or inventory management. Refer to official Shopify GraphQL docs via available tools/MCP.

ALWAYS 
- Use the correct mutation for the data you wish to update.
- Always verify with the current API documentation if you have issues.
- Use the Introspetion tool and perplexity ask tool for help, if you make mistakes, get help, don't guess, or ask the user to do it or suggest alternatives.

---