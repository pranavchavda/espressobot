import { BaseTool } from './base-tool.js';
import { formatPrice } from '../shopify/shopify-client.js';

/**
 * Native JavaScript implementation of update_pricing tool
 * Updates product or variant pricing
 */
export class UpdatePricingTool extends BaseTool {
  get metadata() {
    return {
      name: 'update_pricing',
      description: 'Update product or variant pricing',
      inputSchema: {
        type: 'object',
        properties: {
          product_id: { type: 'string', description: 'Product ID' },
          variant_id: { type: 'string', description: 'Variant ID' },
          price: { type: 'string', description: 'New price (e.g., "19.99")' },
          compare_at_price: { type: 'string', description: 'Compare at price for showing discounts' },
          cost: { type: 'string', description: 'Cost per item (for profit calculations)' }
        },
        oneOf: [
          { required: ['product_id', 'price'] },
          { required: ['variant_id', 'price'] }
        ]
      }
    };
  }

  /**
   * Execute the pricing update
   */
  async execute(args) {
    const { product_id, variant_id, price, compare_at_price, cost } = args;
    
    this.log('Updating pricing', args);
    
    // Normalize IDs
    const productId = product_id ? this.shopifyClient.normalizeId(product_id) : null;
    let variantId = variant_id;
    
    if (variantId && !variantId.startsWith('gid://')) {
      variantId = `gid://shopify/ProductVariant/${variantId}`;
    }
    
    // If only product_id is provided, we need to update all variants
    if (productId && !variantId) {
      return this.updateProductPricing(productId, price, compare_at_price, cost);
    } else if (variantId) {
      return this.updateVariantPricing(productId, variantId, price, compare_at_price, cost);
    } else {
      throw new Error('Either product_id or variant_id must be provided');
    }
  }

  /**
   * Update pricing for all variants of a product
   */
  async updateProductPricing(productId, price, compareAtPrice, cost) {
    // First, get all variants
    const query = `
      query getProductVariants($id: ID!) {
        product(id: $id) {
          id
          title
          variants(first: 100) {
            edges {
              node {
                id
              }
            }
          }
        }
      }
    `;
    
    const data = await this.shopifyClient.query(query, { id: productId });
    
    if (!data.product) {
      throw new Error(`Product not found: ${productId}`);
    }
    
    // Prepare variant updates
    const variants = data.product.variants.edges.map(edge => {
      const variantInput = {
        id: edge.node.id,
        price: formatPrice(price)
      };
      
      if (compareAtPrice !== undefined) {
        variantInput.compareAtPrice = compareAtPrice ? formatPrice(compareAtPrice) : null;
      }
      
      return variantInput;
    });
    
    // Update all variants
    const mutation = `
      mutation updateProductPricing($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
          product {
            id
            title
          }
          productVariants {
            id
            title
            price
            compareAtPrice
          }
          userErrors {
            field
            message
          }
        }
      }
    `;
    
    const variables = {
      productId,
      variants
    };
    
    const result = await this.shopifyClient.mutate(mutation, variables);
    
    // Handle cost update if provided
    if (cost !== undefined) {
      await this.updateVariantsCost(variants.map(v => v.id), cost);
    }
    
    return {
      product: result.productVariantsBulkUpdate.product,
      variants: result.productVariantsBulkUpdate.productVariants,
      updatedCount: result.productVariantsBulkUpdate.productVariants.length
    };
  }

  /**
   * Update pricing for a specific variant
   */
  async updateVariantPricing(productId, variantId, price, compareAtPrice, cost) {
    // If we don't have productId, we need to get it from the variant
    if (!productId) {
      const variantQuery = `
        query getVariantProduct($id: ID!) {
          productVariant(id: $id) {
            product {
              id
            }
          }
        }
      `;
      
      const variantData = await this.shopifyClient.query(variantQuery, { id: variantId });
      if (!variantData.productVariant) {
        throw new Error(`Variant not found: ${variantId}`);
      }
      productId = variantData.productVariant.product.id;
    }
    
    // Build variant input
    const variantInput = {
      id: variantId,
      price: formatPrice(price)
    };
    
    if (compareAtPrice !== undefined) {
      variantInput.compareAtPrice = compareAtPrice ? formatPrice(compareAtPrice) : null;
    }
    
    // Execute mutation
    const mutation = `
      mutation updateVariantPricing($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
          product {
            id
            title
          }
          productVariants {
            id
            title
            price
            compareAtPrice
          }
          userErrors {
            field
            message
          }
        }
      }
    `;
    
    const variables = {
      productId,
      variants: [variantInput]
    };
    
    const result = await this.shopifyClient.mutate(mutation, variables);
    
    // Handle cost update if provided
    if (cost !== undefined) {
      await this.updateVariantsCost([variantId], cost);
    }
    
    return {
      product: result.productVariantsBulkUpdate.product,
      variant: result.productVariantsBulkUpdate.productVariants[0]
    };
  }

  /**
   * Update inventory item cost (separate mutation)
   */
  async updateVariantsCost(variantIds, cost) {
    // Get inventory items for all variants
    const query = `
      query getInventoryItems($ids: [ID!]!) {
        nodes(ids: $ids) {
          ... on ProductVariant {
            id
            inventoryItem {
              id
            }
          }
        }
      }
    `;
    
    const data = await this.shopifyClient.query(query, { ids: variantIds });
    
    // Update cost for each inventory item
    const updates = [];
    for (const variant of data.nodes) {
      if (variant?.inventoryItem) {
        const mutation = `
          mutation updateCost($id: ID!, $input: InventoryItemInput!) {
            inventoryItemUpdate(id: $id, input: $input) {
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
        `;
        
        const variables = {
          id: variant.inventoryItem.id,
          input: {
            cost: formatPrice(cost)
          }
        };
        
        try {
          const result = await this.shopifyClient.mutate(mutation, variables);
          updates.push(result.inventoryItemUpdate.inventoryItem);
        } catch (error) {
          this.log('Warning: Could not update cost for inventory item', error.message);
        }
      }
    }
    
    return updates;
  }
}

// Export singleton instance
export const updatePricingTool = new UpdatePricingTool();