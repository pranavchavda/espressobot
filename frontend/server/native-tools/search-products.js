import { BaseTool } from './base-tool.js';

/**
 * Native JavaScript implementation of search_products tool
 * Searches for products using Shopify's search syntax
 */
export class SearchProductsTool extends BaseTool {
  get metadata() {
    return {
      name: 'search_products',
      description: 'Search for products in the Shopify store',
      inputSchema: {
        type: 'object',
        properties: {
          query: { 
            type: 'string', 
            description: 'Search query using Shopify query syntax (e.g., "coffee", "tag:sale", "vendor:Breville")' 
          },
          first: { 
            type: 'number', 
            description: 'Number of results to return', 
            default: 10 
          },
          fields: {
            type: 'array',
            items: { type: 'string' },
            description: 'Fields to include in response (id, title, handle, vendor, status, tags, price, inventory, variants, seo)',
            default: ['id', 'title', 'handle', 'vendor', 'status', 'tags', 'price']
          }
        },
        required: ['query']
      }
    };
  }

  /**
   * Build GraphQL field selections based on requested fields
   */
  buildFieldSelections(fields) {
    const selections = [];
    
    // Always include basic fields
    const basicFields = ['id', 'title', 'handle', 'vendor', 'status', 'tags', 'productType'];
    const requestedBasics = basicFields.filter(f => fields.includes(f) || fields.includes('all'));
    selections.push(...requestedBasics);
    
    // Add price information
    if (fields.includes('price') || fields.includes('all')) {
      selections.push(`
        priceRangeV2 {
          minVariantPrice {
            amount
            currencyCode
          }
        }
      `);
    }
    
    // Add inventory
    if (fields.includes('inventory') || fields.includes('all')) {
      selections.push('totalInventory');
    }
    
    // Add variants
    if (fields.includes('variants') || fields.includes('all')) {
      selections.push(`
        variants(first: 5) {
          edges {
            node {
              id
              title
              sku
              price
              inventoryQuantity
            }
          }
        }
      `);
    }
    
    // Add SEO
    if (fields.includes('seo') || fields.includes('all')) {
      selections.push(`
        seo {
          title
          description
        }
      `);
    }
    
    return selections.join('\n');
  }

  /**
   * Execute the search
   */
  async execute(args) {
    const { query, first = 10, fields = this.metadata.inputSchema.properties.fields.default } = args;
    
    this.log(`Searching for products: query="${query}", limit=${first}`);
    
    const fieldSelections = this.buildFieldSelections(fields);
    
    const graphqlQuery = `
      query searchProducts($query: String!, $first: Int!) {
        products(first: $first, query: $query) {
          edges {
            node {
              ${fieldSelections}
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    `;
    
    const variables = {
      query,
      first
    };
    
    const data = await this.shopifyClient.query(graphqlQuery, variables);
    
    // Transform the response to a cleaner format
    const products = data.products.edges.map(edge => {
      const product = edge.node;
      
      // Clean up the product object
      if (product.priceRangeV2) {
        product.price = product.priceRangeV2.minVariantPrice.amount;
        product.currency = product.priceRangeV2.minVariantPrice.currencyCode;
        delete product.priceRangeV2;
      }
      
      if (product.variants) {
        product.variants = product.variants.edges.map(v => v.node);
      }
      
      return product;
    });
    
    return {
      products,
      count: products.length,
      hasNextPage: data.products.pageInfo.hasNextPage,
      endCursor: data.products.pageInfo.endCursor
    };
  }
}

// Export singleton instance
export const searchProductsTool = new SearchProductsTool();