import PythonToolWrapper from './python-tool-wrapper.js';
import { createToolWrapper } from '../native-tools/base-tool.js';

class CustomToolRegistry {
  constructor() {
    this.pythonWrapper = new PythonToolWrapper();
    this.nativeTools = new Map(); // Store native tool instances
    this.tools = this.initializeTools();
  }

  /**
   * Register a native JavaScript tool
   * @param {BaseTool} toolInstance - Instance of a native tool
   */
  registerNativeTool(toolInstance) {
    const metadata = toolInstance.metadata;
    this.nativeTools.set(metadata.name, toolInstance);
    
    // Add to tools array with native handler
    const toolConfig = {
      name: metadata.name,
      description: metadata.description,
      inputSchema: metadata.inputSchema,
      type: 'native',
      handler: async (args) => toolInstance.run(args)
    };
    
    // Replace existing tool or add new one
    const existingIndex = this.tools.findIndex(t => t.name === metadata.name);
    if (existingIndex >= 0) {
      this.tools[existingIndex] = toolConfig;
    } else {
      this.tools.push(toolConfig);
    }
  }

  initializeTools() {
    return [
      {
        name: 'search_products',
        description: 'Search for products in the Shopify store',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Search query using Shopify query syntax' },
            first: { type: 'number', description: 'Number of results to return', default: 10 },
            after: { type: 'string', description: 'Cursor for pagination' }
          },
          required: ['query']
        },
        type: 'python', // Mark as Python tool
        handler: async (args) => {
          // Extract query as positional argument
          const { query, ...options } = args;
          return this.pythonWrapper.executeTool('search_products', 
            { limit: options.first || 10 }, 
            [query]
          );
        }
      },
      {
        name: 'get_product',
        description: 'Get detailed information about a specific product',
        inputSchema: {
          type: 'object',
          properties: {
            id: { type: 'string', description: 'Product ID' },
            handle: { type: 'string', description: 'Product handle' },
            sku: { type: 'string', description: 'Product SKU' }
          },
          oneOf: [
            { required: ['id'] },
            { required: ['handle'] },
            { required: ['sku'] }
          ]
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.getProduct(args)
      },
      {
        name: 'product_create_full',
        description: 'Create a new product with all details',
        inputSchema: {
          type: 'object',
          properties: {
            title: { type: 'string', description: 'Product title' },
            description: { type: 'string', description: 'Product description' },
            product_type: { type: 'string', description: 'Product type' },
            vendor: { type: 'string', description: 'Product vendor' },
            tags: { type: 'array', items: { type: 'string' }, description: 'Product tags' },
            variants: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  title: { type: 'string' },
                  price: { type: 'string' },
                  sku: { type: 'string' },
                  inventory_quantity: { type: 'number' }
                }
              }
            }
          },
          required: ['title']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.createProduct(args)
      },
      {
        name: 'update_pricing',
        description: 'Update product or variant pricing',
        inputSchema: {
          type: 'object',
          properties: {
            product_id: { type: 'string', description: 'Product ID' },
            variant_id: { type: 'string', description: 'Variant ID' },
            price: { type: 'string', description: 'New price' },
            compare_at_price: { type: 'string', description: 'Compare at price' }
          },
          oneOf: [
            { required: ['product_id', 'price'] },
            { required: ['variant_id', 'price'] }
          ]
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.updatePricing(args)
      },
      {
        name: 'add_tags_to_product',
        description: 'Add tags to a product',
        inputSchema: {
          type: 'object',
          properties: {
            product_id: { type: 'string', description: 'Product ID' },
            tags: { type: 'array', items: { type: 'string' }, description: 'Tags to add' }
          },
          required: ['product_id', 'tags']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.manageTags(args.product_id, args.tags, [])
      },
      {
        name: 'remove_tags_from_product',
        description: 'Remove tags from a product',
        inputSchema: {
          type: 'object',
          properties: {
            product_id: { type: 'string', description: 'Product ID' },
            tags: { type: 'array', items: { type: 'string' }, description: 'Tags to remove' }
          },
          required: ['product_id', 'tags']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.manageTags(args.product_id, [], args.tags)
      },
      {
        name: 'update_product_status',
        description: 'Update product status (ACTIVE, DRAFT, ARCHIVED)',
        inputSchema: {
          type: 'object',
          properties: {
            product_id: { type: 'string', description: 'Product ID' },
            status: { type: 'string', enum: ['ACTIVE', 'DRAFT', 'ARCHIVED'], description: 'New status' }
          },
          required: ['product_id', 'status']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.updateStatus(args.product_id, args.status)
      },
      {
        name: 'run_full_shopify_graphql_query',
        description: 'Execute a custom GraphQL query against Shopify Admin API',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'GraphQL query' },
            variables: { type: 'object', description: 'Query variables' }
          },
          required: ['query']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.runGraphQLQuery(args.query, args.variables || {})
      },
      {
        name: 'run_full_shopify_graphql_mutation',
        description: 'Execute a custom GraphQL mutation against Shopify Admin API',
        inputSchema: {
          type: 'object',
          properties: {
            mutation: { type: 'string', description: 'GraphQL mutation' },
            variables: { type: 'object', description: 'Mutation variables' }
          },
          required: ['mutation']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.runGraphQLMutation(args.mutation, args.variables || {})
      },
      {
        name: 'manage_inventory_policy',
        description: 'Update inventory policy for products',
        inputSchema: {
          type: 'object',
          properties: {
            product_id: { type: 'string', description: 'Product ID to update' },
            policy: { type: 'string', enum: ['DENY', 'CONTINUE'], description: 'Inventory policy' },
            apply_to_all_variants: { type: 'boolean', default: true, description: 'Apply to all variants' }
          },
          required: ['product_id', 'policy']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.executeTool('manage_inventory_policy', args)
      },
      {
        name: 'manage_tags',
        description: 'Add or remove multiple tags from a product',
        inputSchema: {
          type: 'object',
          properties: {
            product_id: { type: 'string', description: 'Product ID' },
            add_tags: { type: 'array', items: { type: 'string' }, default: [] },
            remove_tags: { type: 'array', items: { type: 'string' }, default: [] }
          },
          required: ['product_id']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.executeTool('manage_tags', args)
      },
      {
        name: 'pplx',
        description: 'Query Perplexity AI for research or information',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Search query' },
            focus: { type: 'string', enum: ['web', 'academic', 'writing', 'wolfram', 'youtube', 'reddit'], default: 'web' }
          },
          required: ['query']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.executeTool('pplx', args)
      },
      {
        name: 'bulk_price_update',
        description: 'Update prices for multiple products in bulk',
        inputSchema: {
          type: 'object',
          properties: {
            updates: { 
              type: 'array', 
              items: { 
                type: 'object',
                properties: {
                  product_id: { type: 'string' },
                  variant_id: { type: 'string' },
                  sku: { type: 'string' },
                  price: { type: 'string' },
                  compare_at_price: { type: 'string' }
                }
              }
            },
            price_list_id: { type: 'string', description: 'Price list ID for specific markets' }
          },
          required: ['updates']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.executeTool('bulk_price_update', args)
      },
      {
        name: 'create_combo',
        description: 'Create a combo/bundle product',
        inputSchema: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            product_ids: { type: 'array', items: { type: 'string' } },
            combo_price: { type: 'string' },
            description: { type: 'string', default: '' }
          },
          required: ['title', 'product_ids', 'combo_price']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.executeTool('create_combo', args)
      },
      {
        name: 'create_open_box',
        description: 'Create an open box variant of a product',
        inputSchema: {
          type: 'object',
          properties: {
            product_id: { type: 'string' },
            discount_percentage: { type: 'number', default: 15 },
            condition_notes: { type: 'string', default: 'Open box - inspected and certified' },
            inventory_quantity: { type: 'number', default: 1 }
          },
          required: ['product_id']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.executeTool('create_open_box', args)
      }
    ];
  }

  getTools() {
    return this.tools.map(tool => ({
      name: tool.name,
      description: tool.description,
      inputSchema: tool.inputSchema
    }));
  }

  async executeTool(toolName, args) {
    const tool = this.tools.find(t => t.name === toolName);
    if (!tool) {
      throw new Error(`Tool ${toolName} not found`);
    }
    return tool.handler(args);
  }

  // Convert to OpenAI function format
  getOpenAIFunctions() {
    return this.tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema
      }
    }));
  }
}

export default CustomToolRegistry;