/**
 * Shared Knowledge Module for iDrinkCoffee.com
 * Migrated from ~/idc/CLAUDE.md
 * This module contains all domain-specific knowledge that agents need
 */

export const SHARED_KNOWLEDGE = {
  // Business Overview
  business: {
    name: "iDrinkCoffee.com",
    description: "Premium coffee equipment retailer specializing in espresso machines, grinders, and accessories",
    channels: {
      online: "iDrinkCoffee.com (primary sales channel)",
      wholesale: "B2B channel for commercial clients",
      retail: "Physical showroom in Montreal"
    }
  },

  // Product Management Rules
  productRules: {
    naming: {
      format: "[Brand] [Model/Series] [Type]",
      examples: [
        "Breville Barista Express Espresso Machine",
        "Baratza Encore Coffee Grinder",
        "Rocket Appartamento Espresso Machine"
      ],
      guidelines: [
        "Always include brand name first",
        "Use proper capitalization for brands",
        "Include product type (Espresso Machine, Grinder, etc.)",
        "Avoid redundant words"
      ]
    },
    
    sku: {
      format: "BRAND-MODEL-VARIANT",
      examples: [
        "BREV-BES870XL-SS (Breville Barista Express Stainless Steel)",
        "ROCK-APPART-WHT (Rocket Appartamento White)",
        "COMBO-GAGGIA-CLASSIC-BARATZA-ENCORE"
      ],
      special: {
        combos: "COMBO-[MACHINE]-[GRINDER]",
        openBox: "OB-[ORIGINAL-SKU]-[SERIAL]",
        refurbished: "REF-[ORIGINAL-SKU]",
        demo: "DEMO-[ORIGINAL-SKU]"
      }
    },

    tags: {
      required: [
        "Product type tag (e.g., 'Espresso Machine', 'Coffee Grinder')",
        "Brand tag",
        "Price range tag (e.g., 'Under $500', '$500-$1000')"
      ],
      special: {
        preorder: ["Preorder", "Preorder-[Month]-[Year]"],
        sale: ["On Sale", "Clearance"],
        exclusive: ["Online Exclusive", "iDrinkCoffee Exclusive"],
        bundle: ["Bundle", "Combo Deal"],
        openBox: ["Open Box", "Open Box Deal"]
      },
      operational: {
        inventory: ["__disable_inventory", "__preorder_auto"],
        visibility: ["__hidden", "__wholesale_only"],
        shipping: ["__free_shipping", "__oversized"]
      }
    },

    pricing: {
      rules: [
        "Never sell below MAP (Minimum Advertised Price)",
        "Compare at price should be MSRP",
        "Cost should be wholesale/dealer price",
        "Price must be between cost and MSRP"
      ],
      channels: {
        online: "Default price list",
        wholesale: "Wholesale price list (typically 20-30% below retail)",
        retail: "In-store price list (may differ from online)"
      }
    },

    inventory: {
      policies: {
        regular: "DENY - Don't allow purchase when out of stock",
        preorder: "CONTINUE - Allow purchase when out of stock",
        special: "Custom handling for demo/open box (qty: 1)"
      },
      tracking: {
        enabled: "Track inventory for all products except digital/services",
        warehouse: "Primary warehouse: Montreal",
        locations: ["Montreal Warehouse", "Showroom Floor", "Service Center"]
      }
    }
  },

  // Special Operations
  specialOperations: {
    preorders: {
      description: "Products available for purchase before stock arrives",
      process: [
        "Set inventory policy to CONTINUE",
        "Add __preorder_auto tag",
        "Set availability date in metafield",
        "Create preorder information in description",
        "Monitor and update ETA regularly"
      ],
      metafields: {
        namespace: "custom",
        key: "preorder_date",
        type: "date"
      }
    },

    mapSales: {
      description: "Minimum Advertised Price sales requiring special handling",
      process: [
        "Use in-cart pricing (hide sale price on collection pages)",
        "Add to MAP protected collection",
        "Use special messaging 'See price in cart'",
        "Track with __map_sale tag"
      ],
      tools: ["manage_map_sales", "Special GraphQL mutations"]
    },

    combos: {
      description: "Machine + Grinder bundles with special pricing",
      process: [
        "Create using create_combo tool",
        "Generates combined product with both items",
        "Applies discount (fixed or percentage)",
        "Links to source products via metafields",
        "Auto-generates combo images"
      ],
      naming: "[Machine Brand] [Machine] + [Grinder Brand] [Grinder] Combo"
    },

    openBox: {
      description: "Single unit sales of returned/display items",
      process: [
        "Create using create_open_box tool",
        "Adds serial number to title/SKU",
        "Sets quantity to 1",
        "Applies discount (default 15%)",
        "Adds condition information"
      ],
      conditions: ["Like New", "Excellent", "Good", "Fair"]
    }
  },

  // Metafields Structure
  metafields: {
    custom: {
      preorder_date: "Expected availability date",
      features: "Product features in JSON format",
      specifications: "Technical specifications",
      warranty_info: "Warranty details",
      bundle_products: "Linked products in bundles",
      condition_notes: "For open box/refurbished items",
      map_protected: "Boolean for MAP pricing",
      wholesale_eligible: "Boolean for B2B availability"
    },
    seo: {
      title: "Custom SEO title",
      description: "Meta description for search engines"
    },
    reviews: {
      rating: "Average rating",
      count: "Number of reviews"
    }
  },

  // Collections Structure
  collections: {
    automated: {
      "espresso-machines": "All espresso machines by tag",
      "coffee-grinders": "All grinders by tag",
      "on-sale": "Products with sale tag",
      "new-arrivals": "Products created in last 30 days",
      "best-sellers": "Top selling products",
      "preorder": "Products available for preorder",
      "open-box": "Open box deals"
    },
    manual: {
      "staff-picks": "Curated recommendations",
      "gift-guide": "Seasonal gift recommendations",
      "starter-packages": "Beginner-friendly bundles",
      "pro-series": "Commercial/prosumer equipment"
    },
    hidden: {
      "map-protected": "Products with MAP pricing",
      "wholesale-catalog": "B2B only products",
      "discontinued": "Products being phased out"
    }
  },

  // Channel Configuration
  channels: {
    "online-store": {
      name: "Online Store",
      published: "Default for all products",
      markets: ["Canada", "United States"]
    },
    "point-of-sale": {
      name: "Point of Sale",
      published: "In-store available products only",
      locations: ["Montreal Showroom"]
    },
    "wholesale": {
      name: "Wholesale",
      published: "B2B eligible products",
      requirements: "Wholesale account required"
    }
  },

  // Common Workflows
  workflows: {
    newProduct: [
      "1. Create product with product_create_full",
      "2. Set proper naming convention",
      "3. Add all required tags",
      "4. Set pricing (cost, price, compare_at_price)",
      "5. Upload product images",
      "6. Add metafields for features/specs",
      "7. Assign to collections",
      "8. Set channel visibility",
      "9. Configure inventory tracking",
      "10. Publish when ready"
    ],
    
    bulkOperations: [
      "Use bulk_price_update for multiple price changes",
      "Tag operations: Add seasonal tags, remove expired tags",
      "Status updates: Archive discontinued, activate seasonal",
      "Inventory updates: Sync with warehouse data"
    ],

    reporting: [
      "Low stock alerts for products < 5 units",
      "Price compliance checks (MAP violations)",
      "Tag audit for consistency",
      "SEO optimization opportunities",
      "Sales performance by category"
    ]
  },

  // Tool Best Practices
  toolUsage: {
    search: {
      tips: [
        "Use Shopify query syntax for precise results",
        "Common filters: 'status:active', 'tag:espresso-machine'",
        "Use 'inventory_quantity:>0' for in-stock items",
        "Combine filters: 'vendor:Breville AND tag:grinder'"
      ]
    },
    
    updates: {
      tips: [
        "Always verify product exists before updating",
        "Use SKU for unique identification when possible",
        "Batch similar updates for efficiency",
        "Check for MAP restrictions before price changes"
      ]
    },

    creation: {
      tips: [
        "Prepare all data before creation",
        "Use product_create_full for complete setup",
        "Set publish:false initially, review, then publish",
        "Always add cost for margin calculations"
      ]
    }
  },

  // Integration Points
  integrations: {
    skuvault: {
      purpose: "Warehouse management system",
      sync: ["Inventory levels", "Product costs", "SKU mapping"],
      tools: ["upload_to_skuvault", "manage_skuvault_kits"]
    },
    
    googleShopping: {
      purpose: "Product feed for Google Ads",
      requirements: ["GTIN/UPC", "Proper categorization", "High-quality images"],
      metafields: ["gtin", "google_product_category", "condition"]
    },

    emailMarketing: {
      purpose: "Klaviyo integration for campaigns",
      segments: ["Recent purchasers", "High-value customers", "Abandoned carts"],
      triggers: ["New product alerts", "Back in stock", "Price drops"]
    }
  },

  // Error Handling
  commonIssues: {
    "Product not found": "Try searching by SKU, handle, or ID",
    "Price below cost": "MAP violation - check restrictions",
    "Tag already exists": "Shopify prevents duplicate tags",
    "Inventory sync failed": "Check SKUVault connection",
    "Image upload failed": "Verify URL is accessible, check file size"
  }
};

// Export individual sections for easier access
export const {
  business,
  productRules,
  specialOperations,
  metafields,
  collections,
  channels,
  workflows,
  toolUsage,
  integrations,
  commonIssues
} = SHARED_KNOWLEDGE;