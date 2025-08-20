import { BaseTool } from './base-tool.js';

/**
 * Native JavaScript implementation of get_product tool
 * Gets detailed information about a specific product
 */
export class GetProductTool extends BaseTool {
  get metadata() {
    return {
      name: 'get_product',
      description: 'Get detailed information about a specific product',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'Product ID (numeric or GID format)' },
          handle: { type: 'string', description: 'Product handle (URL slug)' },
          sku: { type: 'string', description: 'Product SKU' }
        },
        oneOf: [
          { required: ['id'] },
          { required: ['handle'] },
          { required: ['sku'] }
        ]
      }
    };
  }

  /**
   * Execute the get product operation
   */
  async execute(args) {
    const { id, handle, sku } = args;
    
    this.log('Getting product details', { id, handle, sku });
    
    let productId = null;
    
    // Determine how to find the product
    if (id) {
      productId = this.shopifyClient.normalizeId(id);
    } else if (handle) {
      productId = await this.shopifyClient.resolveProductId(handle);
    } else if (sku) {
      productId = await this.shopifyClient.resolveProductId(sku);
    }
    
    if (!productId) {
      throw new Error(`Product not found with identifier: ${id || handle || sku}`);
    }
    
    // Query for comprehensive product details
    const query = `
      query getProduct($id: ID!) {
        product(id: $id) {
          id
          title
          handle
          descriptionHtml
          vendor
          productType
          status
          tags
          createdAt
          updatedAt
          publishedAt
          totalInventory
          priceRangeV2 {
            minVariantPrice {
              amount
              currencyCode
            }
            maxVariantPrice {
              amount
              currencyCode
            }
          }
          images(first: 10) {
            edges {
              node {
                id
                url
                altText
                width
                height
              }
            }
          }
          variants(first: 100) {
            edges {
              node {
                id
                title
                sku
                price
                compareAtPrice
                barcode
                inventoryQuantity
                inventoryPolicy
                weight
                weightUnit
                selectedOptions {
                  name
                  value
                }
                inventoryItem {
                  id
                  tracked
                  inventoryLevels(first: 10) {
                    edges {
                      node {
                        id
                        available
                        location {
                          id
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          }
          options {
            id
            name
            position
            values
          }
          seo {
            title
            description
          }
          metafields(first: 50) {
            edges {
              node {
                id
                namespace
                key
                value
                type
              }
            }
          }
        }
      }
    `;
    
    const variables = { id: productId };
    const data = await this.shopifyClient.query(query, variables);
    
    if (!data.product) {
      throw new Error(`Product not found with ID: ${productId}`);
    }
    
    // Transform the response
    const product = data.product;
    
    // Clean up nested structures
    if (product.images) {
      product.images = product.images.edges.map(e => e.node);
    }
    
    if (product.variants) {
      product.variants = product.variants.edges.map(e => {
        const variant = e.node;
        if (variant.inventoryItem?.inventoryLevels) {
          variant.inventoryLevels = variant.inventoryItem.inventoryLevels.edges.map(l => ({
            available: l.node.available,
            locationId: l.node.location.id,
            locationName: l.node.location.name
          }));
        }
        return variant;
      });
    }
    
    if (product.metafields) {
      product.metafields = product.metafields.edges.map(e => e.node);
    }
    
    if (product.priceRangeV2) {
      product.priceRange = {
        min: parseFloat(product.priceRangeV2.minVariantPrice.amount),
        max: parseFloat(product.priceRangeV2.maxVariantPrice.amount),
        currency: product.priceRangeV2.minVariantPrice.currencyCode
      };
      delete product.priceRangeV2;
    }
    
    return product;
  }
}

// Export singleton instance
export const getProductTool = new GetProductTool();