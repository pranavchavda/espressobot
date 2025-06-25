import fetch from 'node-fetch';

/**
 * Native JavaScript Shopify Admin API GraphQL Client
 * Ported from Python base.py for better performance and integration
 */
export class ShopifyClient {
  constructor() {
    this.shopUrl = process.env.SHOPIFY_SHOP_URL;
    this.accessToken = process.env.SHOPIFY_ACCESS_TOKEN;
    this.debug = process.env.DEBUG?.toLowerCase() === 'true';
    
    if (!this.shopUrl || !this.accessToken) {
      throw new Error('Missing required environment variables: SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN');
    }
    
    // Normalize shop URL
    this.shopUrl = this.shopUrl.replace(/\/$/, '');
    if (!this.shopUrl.startsWith('https://')) {
      this.shopUrl = `https://${this.shopUrl}`;
    }
    
    this.graphqlUrl = `${this.shopUrl}/admin/api/2025-01/graphql.json`;
    this.headers = {
      'X-Shopify-Access-Token': this.accessToken,
      'Content-Type': 'application/json'
    };
  }

  /**
   * Execute a GraphQL query or mutation
   * @param {string} query - GraphQL query or mutation
   * @param {Object} variables - GraphQL variables
   * @returns {Promise<Object>} GraphQL response data
   */
  async executeGraphQL(query, variables = {}) {
    const payload = { query, variables };
    
    if (this.debug) {
      console.log('GraphQL Request:', JSON.stringify(payload, null, 2));
    }
    
    try {
      const response = await fetch(this.graphqlUrl, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${await response.text()}`);
      }
      
      const result = await response.json();
      
      if (this.debug) {
        console.log('GraphQL Response:', JSON.stringify(result, null, 2));
      }
      
      // Check for GraphQL errors
      if (result.errors) {
        const errorMessage = result.errors.map(e => e.message).join(', ');
        throw new Error(`GraphQL Errors: ${errorMessage}`);
      }
      
      return result;
      
    } catch (error) {
      console.error('API Request Error:', error.message);
      throw error;
    }
  }

  /**
   * Check for userErrors in mutation response
   * @param {Object} data - GraphQL response data
   * @param {string} operation - Operation name for error context
   * @returns {boolean} True if no errors, throws if errors found
   */
  checkUserErrors(data, operation) {
    for (const key of Object.values(data.data || {})) {
      if (typeof key === 'object' && key !== null && 'userErrors' in key) {
        const errors = key.userErrors;
        if (errors && errors.length > 0) {
          const errorMessages = errors.map(error => 
            `${error.field || 'General'}: ${error.message || 'Unknown error'}`
          ).join('; ');
          throw new Error(`User Errors in ${operation}: ${errorMessages}`);
        }
      }
    }
    return true;
  }

  /**
   * Normalize ID to GID format if needed
   * @param {string} identifier - Product ID, handle, or GID
   * @returns {string} Normalized GID
   */
  normalizeId(identifier) {
    if (identifier.startsWith('gid://')) {
      return identifier;
    }
    if (/^\d+$/.test(identifier)) {
      return `gid://shopify/Product/${identifier}`;
    }
    return identifier;
  }

  /**
   * Resolve product by ID, handle, SKU, or title
   * @param {string} identifier - Product identifier
   * @returns {Promise<string|null>} Product GID or null if not found
   */
  async resolveProductId(identifier) {
    // Try as direct ID first
    if (identifier.startsWith('gid://') || /^\d+$/.test(identifier)) {
      return this.normalizeId(identifier);
    }
    
    // Try by handle
    const handleQuery = `
      query getProductByHandle($handle: String!) {
        productByHandle(handle: $handle) {
          id
        }
      }
    `;
    
    try {
      const result = await this.executeGraphQL(handleQuery, { handle: identifier });
      if (result.data?.productByHandle) {
        return result.data.productByHandle.id;
      }
    } catch (error) {
      // Continue to next method
    }
    
    // Try by SKU or title
    const searchQuery = `sku:"${identifier}" OR title:"${identifier}"`;
    const searchQueryGQL = `
      query searchProduct($query: String!) {
        products(first: 1, query: $query) {
          edges {
            node {
              id
              title
              variants(first: 10) {
                edges {
                  node {
                    sku
                  }
                }
              }
            }
          }
        }
      }
    `;
    
    const result = await this.executeGraphQL(searchQueryGQL, { query: searchQuery });
    const edges = result.data?.products?.edges || [];
    
    if (edges.length > 0) {
      const product = edges[0].node;
      // Verify SKU match if searching by SKU
      if (identifier.toUpperCase() === identifier) {
        for (const variant of product.variants?.edges || []) {
          if (variant.node.sku?.toUpperCase() === identifier.toUpperCase()) {
            return product.id;
          }
        }
      }
      // Otherwise return first match
      return product.id;
    }
    
    return null;
  }

  /**
   * Convenience method for GraphQL queries
   */
  async query(query, variables) {
    const result = await this.executeGraphQL(query, variables);
    return result.data;
  }

  /**
   * Convenience method for GraphQL mutations
   */
  async mutate(mutation, variables) {
    const result = await this.executeGraphQL(mutation, variables);
    // Check for user errors in the response
    const mutationName = mutation.match(/mutation\s+(\w+)/)?.[1] || 'mutation';
    this.checkUserErrors(result, mutationName);
    return result.data;
  }
}

// Utility functions
export function parseTags(tagsInput) {
  if (!tagsInput) return [];
  if (Array.isArray(tagsInput)) return tagsInput;
  return tagsInput.split(',').map(tag => tag.trim()).filter(Boolean);
}

export function formatPrice(price) {
  if (!price) return '0.00';
  const numPrice = parseFloat(price);
  return isNaN(numPrice) ? '0.00' : numPrice.toFixed(2);
}

// Singleton instance
let clientInstance = null;

export function getShopifyClient() {
  if (!clientInstance) {
    clientInstance = new ShopifyClient();
  }
  return clientInstance;
}