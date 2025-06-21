import { tool } from '@openai/agents';
import { z } from 'zod';
import { customToolDiscovery } from './custom-tool-discovery.js';

// Initialize custom tool discovery
await customToolDiscovery.discoverTools();

// Define tools with proper Zod schemas for OpenAI agents
export const searchProductsTool = tool({
  name: 'search_products',
  description: 'Search for products in the Shopify store',
  parameters: z.object({
    query: z.string().describe('Search query using Shopify query syntax'),
    first: z.number().default(10).describe('Number of results to return'),
    after: z.string().default('').describe('Cursor for pagination')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('search_products', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const getProductTool = tool({
  name: 'get_product',
  description: 'Get detailed information about a specific product',
  parameters: z.object({
    id: z.string().default('').describe('Product ID'),
    handle: z.string().default('').describe('Product handle'),
    sku: z.string().default('').describe('Product SKU')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('get_product', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const createProductTool = tool({
  name: 'product_create_full',
  description: 'Create a new product with all details',
  parameters: z.object({
    title: z.string().describe('Product title'),
    description: z.string().default('').describe('Product description'),
    product_type: z.string().default('').describe('Product type'),
    vendor: z.string().default('').describe('Product vendor'),
    tags: z.array(z.string()).default([]).describe('Product tags'),
    variants: z.array(z.object({
      title: z.string().default('Default Title'),
      price: z.string().default('0.00'),
      sku: z.string().default(''),
      inventory_quantity: z.number().default(0)
    })).default([])
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('product_create_full', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const updatePricingTool = tool({
  name: 'update_pricing',
  description: 'Update product or variant pricing',
  parameters: z.object({
    product_id: z.string().default('').describe('Product ID'),
    variant_id: z.string().default('').describe('Variant ID'),
    price: z.string().describe('New price'),
    compare_at_price: z.string().default('').describe('Compare at price')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('update_pricing', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const addTagsTool = tool({
  name: 'add_tags_to_product',
  description: 'Add tags to a product',
  parameters: z.object({
    product_id: z.string().describe('Product ID'),
    tags: z.array(z.string()).describe('Tags to add')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('add_tags_to_product', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const removeTagsTool = tool({
  name: 'remove_tags_from_product',
  description: 'Remove tags from a product',
  parameters: z.object({
    product_id: z.string().describe('Product ID'),
    tags: z.array(z.string()).describe('Tags to remove')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('remove_tags_from_product', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const updateProductStatusTool = tool({
  name: 'update_product_status',
  description: 'Update product status (ACTIVE, DRAFT, ARCHIVED)',
  parameters: z.object({
    product_id: z.string().describe('Product ID'),
    status: z.enum(['ACTIVE', 'DRAFT', 'ARCHIVED']).describe('New status')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('update_product_status', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const graphqlQueryTool = tool({
  name: 'run_full_shopify_graphql_query',
  description: 'Execute a custom GraphQL query against Shopify Admin API',
  parameters: z.object({
    query: z.string().describe('GraphQL query'),
    variables: z.object({}).default({}).describe('Query variables')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('run_full_shopify_graphql_query', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const graphqlMutationTool = tool({
  name: 'run_full_shopify_graphql_mutation',
  description: 'Execute a custom GraphQL mutation against Shopify Admin API',
  parameters: z.object({
    mutation: z.string().describe('GraphQL mutation'),
    variables: z.object({}).default({}).describe('Mutation variables')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('run_full_shopify_graphql_mutation', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

// Export all tools as an array
export const shopifyTools = [
  searchProductsTool,
  getProductTool,
  createProductTool,
  updatePricingTool,
  addTagsTool,
  removeTagsTool,
  updateProductStatusTool,
  graphqlQueryTool,
  graphqlMutationTool
];