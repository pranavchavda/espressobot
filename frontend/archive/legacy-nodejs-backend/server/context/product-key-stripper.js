/**
 * Strip unused product keys to reduce context size
 * Based on analysis, 78% of product keys are never referenced by agents
 */

// Keys that are commonly used by agents and should be preserved
const ESSENTIAL_PRODUCT_KEYS = new Set([
  // Core identification
  'id',
  'title',
  'handle',
  'sku',
  'vendor',
  'productType',
  'status',
  
  // Pricing (critical for most operations)
  'price',
  'compareAtPrice',
  'priceRange',
  
  // Inventory
  'inventoryQuantity',
  'inventoryPolicy',
  'totalInventory',
  
  // Essential metadata
  'tags',
  'descriptionHtml',
  
  // For variants
  'variants',
  'selectedOptions',
  
  // Images (but simplified)
  'images',
  
  // Key metafields
  'metafields'
]);

// Keys to always remove (never used by agents)
const KEYS_TO_REMOVE = new Set([
  'admin_graphql_api_id', // Internal Shopify ID
  'created_at',
  'updated_at',
  'published_at',
  'publishedAt',
  'createdAt',
  'updatedAt',
  'templateSuffix',
  'publishedScope',
  'legacyResourceId',
  'onlineStoreUrl',
  'onlineStorePreviewUrl',
  'requiresSellingPlan',
  'sellingPlanGroups',
  'tracksInventory',
  'continueSellingWhenOutOfStock',
  'availableForSale',
  'featuredMedia',
  'media',
  'collections',
  'productPublications',
  'resourcePublications',
  'resourcePublicationOnCurrentPublication',
  'privateMetafields',
  'storefrontId',
  'fulfillmentService',
  'inventoryManagement',
  'taxable',
  'taxCode',
  'harmonizedSystemCode',
  'originCountry',
  'inventoryItem', // Nested complex object
  'presentmentPrices',
  'inventoryLevels' // Keep only essential inventory data
]);

/**
 * Strip a single product object to essential keys only
 */
export function stripProductKeys(product) {
  if (!product || typeof product !== 'object') {
    return product;
  }
  
  const stripped = {};
  
  // Copy only essential keys
  for (const key of ESSENTIAL_PRODUCT_KEYS) {
    if (key in product) {
      stripped[key] = product[key];
    }
  }
  
  // Special handling for complex fields
  
  // Simplify images - keep only URL and alt text
  if (stripped.images && Array.isArray(stripped.images)) {
    stripped.images = stripped.images.map(img => ({
      url: img.url || img.src,
      alt: img.altText || img.alt || ''
    }));
  }
  
  // Strip variants recursively
  if (stripped.variants && Array.isArray(stripped.variants)) {
    stripped.variants = stripped.variants.map(variant => stripVariantKeys(variant));
  }
  
  // Keep only important metafields
  if (stripped.metafields && Array.isArray(stripped.metafields)) {
    stripped.metafields = stripped.metafields.filter(mf => 
      mf.namespace === 'custom' || 
      mf.namespace === 'new' ||
      mf.key === 'varLinks' ||
      mf.key === 'features_box'
    );
  }
  
  return stripped;
}

/**
 * Strip variant keys to essentials
 */
function stripVariantKeys(variant) {
  if (!variant || typeof variant !== 'object') {
    return variant;
  }
  
  return {
    id: variant.id,
    title: variant.title,
    sku: variant.sku,
    price: variant.price,
    compareAtPrice: variant.compareAtPrice,
    inventoryQuantity: variant.inventoryQuantity,
    inventoryPolicy: variant.inventoryPolicy,
    barcode: variant.barcode,
    weight: variant.weight,
    weightUnit: variant.weightUnit,
    selectedOptions: variant.selectedOptions,
    available: variant.available !== undefined ? variant.available : variant.inventoryQuantity > 0
  };
}

/**
 * Strip an array of products
 */
export function stripProductArray(products) {
  if (!Array.isArray(products)) {
    return products;
  }
  
  return products.map(product => stripProductKeys(product));
}

/**
 * Estimate size reduction from stripping
 */
export function estimateSizeReduction(product) {
  const original = JSON.stringify(product).length;
  const stripped = JSON.stringify(stripProductKeys(product)).length;
  const reduction = original - stripped;
  const percentage = Math.round((reduction / original) * 100);
  
  return {
    original,
    stripped,
    reduction,
    percentage
  };
}