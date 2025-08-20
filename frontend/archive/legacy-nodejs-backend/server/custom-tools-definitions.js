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
    after: z.string().nullable().default(null).describe('Cursor for pagination')
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
    id: z.string().nullable().default(null).describe('Product ID'),
    handle: z.string().nullable().default(null).describe('Product handle'),
    sku: z.string().nullable().default(null).describe('Product SKU')
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
    description: z.string().nullable().default(null).describe('Product description'),
    product_type: z.string().nullable().default(null).describe('Product type'),
    vendor: z.string().nullable().default(null).describe('Product vendor'),
    tags: z.array(z.string()).default([]).describe('Product tags'),
    variants: z.array(z.object({
      title: z.string().nullable().default('Default Title'),
      price: z.string().nullable().default('0.00'),
      sku: z.string().nullable().default(null),
      inventory_quantity: z.number().nullable().default(0)
    })).nullable().default([])
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
    product_id: z.string().nullable().default(null).describe('Product ID'),
    variant_id: z.string().nullable().default(null).describe('Variant ID'),
    price: z.string().describe('New price'),
    compare_at_price: z.string().nullable().default(null).describe('Compare at price')
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
    variables: z.record(z.any()).nullable().default(null).describe('Query variables')
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
    variables: z.record(z.any()).nullable().default(null).describe('Mutation variables')
  }),
  execute: async (args) => {
    try {
      // Check if mutation uses variables but none provided
      const mutation = args.mutation;
      const variables = args.variables || {};
      
      // Simple check for variable declarations in mutation
      const hasVariableDeclarations = mutation.includes('$') && mutation.includes(':');
      const hasRequiredVariables = mutation.includes('!') && mutation.includes('$');
      
      if (hasRequiredVariables && (!variables || Object.keys(variables).length === 0)) {
        return JSON.stringify({ 
          error: 'Mutation declares required variables but none were provided. Please provide the required variables for this mutation.',
          mutation: mutation,
          hint: 'Look for variables like $input in your mutation and provide them in the variables object.'
        });
      }
      
      // Pass through to the actual tool with cleaned up args
      const toolArgs = {
        mutation: args.mutation,
        variables: variables
      };
      
      const result = await customToolDiscovery.executeTool('run_full_shopify_graphql_mutation', toolArgs);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const updateFullProductTool = tool({
  name: 'update_full_product',
  description: 'Comprehensively update an existing Shopify product with title, description, variants, media, metafields, and more',
  parameters: z.object({
    product_id: z.string().describe('Product identifier (SKU, handle, or product ID)'),
    title: z.string().nullable().default(null).describe('Product title'),
    description_html: z.string().nullable().default(null).describe('Product description (HTML supported)'),
    product_type: z.string().nullable().default(null).describe('Product type'),
    vendor: z.string().nullable().default(null).describe('Product vendor/brand'),
    status: z.enum(['ACTIVE', 'ARCHIVED', 'DRAFT']).nullable().default(null).describe('Product status'),
    handle: z.string().nullable().default(null).describe('URL handle'),
    tags: z.array(z.string()).nullable().default(null).describe('Product tags'),
    seo: z.object({
      title: z.string().nullable().default(null),
      description: z.string().nullable().default(null)
    }).nullable().default(null).describe('SEO settings'),
    variants: z.array(z.object({
      id: z.string().nullable().default(null).describe('Variant ID (for updating existing variant)'),
      price: z.string().nullable().default(null),
      compare_at_price: z.string().nullable().default(null),
      sku: z.string().nullable().default(null),
      barcode: z.string().nullable().default(null),
      weight: z.number().nullable().default(null),
      weight_unit: z.enum(['GRAMS', 'KILOGRAMS', 'POUNDS', 'OUNCES']).nullable().default(null),
      inventory_quantity: z.number().nullable().default(null),
      inventory_policy: z.enum(['DENY', 'CONTINUE']).nullable().default(null),
      taxable: z.boolean().nullable().default(null),
      option_values: z.array(z.object({
        option_name: z.string(),
        value: z.string()
      })).nullable().default(null).describe('Option values for new variants')
    })).nullable().default(null).describe('Product variants (update existing by ID or create new)'),
    media: z.array(z.object({
      original_source: z.string().nullable().default(null).describe('Image URL'),
      file_path: z.string().nullable().default(null).describe('Local file path to upload'),
      alt: z.string().nullable().default(null).describe('Alt text for accessibility'),
      media_content_type: z.enum(['IMAGE', 'VIDEO', 'MODEL_3D']).nullable().default('IMAGE').describe('Media type')
    })).nullable().default(null).describe('Media files (URLs or local files)'),
    metafields: z.array(z.object({
      namespace: z.string(),
      key: z.string(),
      type: z.string(),
      value: z.string()
    })).nullable().default(null).describe('Product metafields')
  }),
  execute: async (args) => {
    try {
      const result = await customToolDiscovery.executeTool('update_full_product', args);
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
  updateFullProductTool,
  graphqlQueryTool,
  graphqlMutationTool
];