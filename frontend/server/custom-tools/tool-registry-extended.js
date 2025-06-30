import PythonToolWrapper from './python-tool-wrapper.js';
import { createToolWrapper } from '../native-tools/base-tool.js';
import { runPythonScript } from './python-script-runner.js';

class ExtendedToolRegistry {
  constructor() {
    this.pythonWrapper = new PythonToolWrapper();
    this.nativeTools = new Map();
    this.tools = this.initializeTools();
  }

  registerNativeTool(toolInstance) {
    const metadata = toolInstance.metadata;
    this.nativeTools.set(metadata.name, toolInstance);
    
    const toolConfig = {
      name: metadata.name,
      description: metadata.description,
      inputSchema: metadata.inputSchema,
      type: 'native',
      handler: async (args) => toolInstance.run(args)
    };
    
    const existingIndex = this.tools.findIndex(t => t.name === metadata.name);
    if (existingIndex >= 0) {
      this.tools[existingIndex] = toolConfig;
    } else {
      this.tools.push(toolConfig);
    }
  }

  /**
   * Register a generic tool (used by Shopify Dev MCP tools and OpenAI SDK tools)
   */
  registerTool(name, toolInstance) {
    // Handle OpenAI SDK tool format
    if (toolInstance._spec) {
      const spec = toolInstance._spec;
      const toolConfig = {
        name: spec.name,
        description: spec.description || '',
        inputSchema: spec.parameters || {},
        type: 'openai-sdk',
        handler: async (args) => toolInstance.execute(args)
      };
      
      const existingIndex = this.tools.findIndex(t => t.name === spec.name);
      if (existingIndex >= 0) {
        this.tools[existingIndex] = toolConfig;
      } else {
        this.tools.push(toolConfig);
      }
    } else {
      // Original MCP tool format
      const toolConfig = {
        name: name,
        description: toolInstance.description || '',
        inputSchema: toolInstance.parameters ? toolInstance.parameters.shape : {},
        type: 'mcp',
        handler: async (args) => toolInstance.execute(args)
      };
      
      const existingIndex = this.tools.findIndex(t => t.name === name);
      if (existingIndex >= 0) {
        this.tools[existingIndex] = toolConfig;
      } else {
        this.tools.push(toolConfig);
      }
    }
  }

  initializeTools() {
    return [
      // Core tools from original registry
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
        type: 'python',
        handler: async (args) => {
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
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            metafields: { type: 'boolean', description: 'Include metafields', default: false }
          },
          required: ['identifier']
        },
        type: 'python',
        handler: async (args) => {
          const options = { metafields: args.metafields };
          return this.pythonWrapper.executeTool('get_product', options, [args.identifier]);
        }
      },
      {
        name: 'product_create_full',
        description: 'Create a new product with all details including variants, images, SEO, etc.',
        inputSchema: {
          type: 'object',
          properties: {
            title: { type: 'string', description: 'Product title' },
            handle: { type: 'string', description: 'URL handle (auto-generated if not provided)' },
            description: { type: 'string', description: 'Product description' },
            product_type: { type: 'string', description: 'Product type' },
            vendor: { type: 'string', description: 'Product vendor' },
            tags: { type: 'array', items: { type: 'string' }, description: 'Product tags' },
            price: { type: 'string', description: 'Default price' },
            compare_at_price: { type: 'string', description: 'Compare at price' },
            sku: { type: 'string', description: 'Default SKU' },
            inventory_quantity: { type: 'number', description: 'Starting inventory' },
            track_inventory: { type: 'boolean', default: true },
            images: { type: 'array', items: { type: 'string' }, description: 'Image URLs' },
            seo_title: { type: 'string', description: 'SEO title' },
            seo_description: { type: 'string', description: 'SEO description' },
            publish: { type: 'boolean', default: false, description: 'Publish immediately' }
          },
          required: ['title']
        },
        type: 'python',
        handler: async (args) => this.pythonWrapper.executeTool('create_full_product', args)
      },
      {
        name: 'update_pricing',
        description: 'Update product or variant pricing',
        inputSchema: {
          type: 'object',
          properties: {
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            price: { type: 'string', description: 'New price' },
            compare_at_price: { type: 'string', description: 'Compare at price' },
            cost: { type: 'string', description: 'Cost per item' }
          },
          required: ['identifier', 'price']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.price) options.price = args.price;
          if (args.compare_at_price !== undefined) options['compare-at'] = args.compare_at_price;
          if (args.cost) options.cost = args.cost;
          
          return this.pythonWrapper.executeTool('update_pricing_wrapper', options, [args.identifier]);
        }
      },
      {
        name: 'manage_tags',
        description: 'Add or remove tags from a product',
        inputSchema: {
          type: 'object',
          properties: {
            action: { type: 'string', enum: ['add', 'remove', 'set'], description: 'Tag action' },
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            tags: { type: 'array', items: { type: 'string' }, description: 'Tags to manage' }
          },
          required: ['action', 'identifier', 'tags']
        },
        type: 'python',
        handler: async (args) => {
          return this.pythonWrapper.executeTool('manage_tags', 
            { [args.action]: args.tags.join(',') }, 
            [args.identifier]
          );
        }
      },
      {
        name: 'update_product_status',
        description: 'Update product status (ACTIVE, DRAFT, ARCHIVED)',
        inputSchema: {
          type: 'object',
          properties: {
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            status: { type: 'string', enum: ['ACTIVE', 'DRAFT', 'ARCHIVED'], description: 'New status' }
          },
          required: ['identifier', 'status']
        },
        type: 'python',
        handler: async (args) => {
          return this.pythonWrapper.executeTool('update_status', 
            { status: args.status }, 
            [args.identifier]
          );
        }
      },
      {
        name: 'run_graphql_query',
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
        handler: async (args) => {
          const options = args.variables ? { variables: JSON.stringify(args.variables) } : {};
          return this.pythonWrapper.executeTool('graphql_query', options, [args.query]);
        }
      },
      {
        name: 'run_graphql_mutation',
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
        handler: async (args) => {
          const options = args.variables ? { variables: JSON.stringify(args.variables) } : {};
          return this.pythonWrapper.executeTool('graphql_mutation', options, [args.mutation]);
        }
      },
      {
        name: 'manage_inventory_policy',
        description: 'Update inventory policy for products',
        inputSchema: {
          type: 'object',
          properties: {
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            policy: { type: 'string', enum: ['DENY', 'CONTINUE'], description: 'Inventory policy' },
            apply_to_all: { type: 'boolean', default: true, description: 'Apply to all variants' }
          },
          required: ['identifier', 'policy']
        },
        type: 'python',
        handler: async (args) => {
          const options = {
            policy: args.policy,
            all: args.apply_to_all
          };
          return this.pythonWrapper.executeTool('manage_inventory_policy', options, [args.identifier]);
        }
      },
      {
        name: 'pplx',
        description: 'Query Perplexity AI for research or information',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Search query' },
            model: { type: 'string', default: 'llama-3.1-sonar-small-128k-online' },
            temperature: { type: 'number', default: 0.2 },
            max_tokens: { type: 'number', default: 1000 }
          },
          required: ['query']
        },
        type: 'python',
        handler: async (args) => {
          const { query, ...options } = args;
          return this.pythonWrapper.executeTool('pplx', options, [query]);
        }
      },
      {
        name: 'bulk_price_update',
        description: 'Update prices for multiple products from CSV file or inline data',
        inputSchema: {
          type: 'object',
          properties: {
            csv_file: { type: 'string', description: 'Path to CSV file' },
            updates: { 
              type: 'array', 
              description: 'Array of price updates',
              items: { 
                type: 'object',
                properties: {
                  identifier: { type: 'string' },
                  price: { type: 'string' },
                  compare_at_price: { type: 'string' }
                }
              }
            }
          },
          oneOf: [
            { required: ['csv_file'] },
            { required: ['updates'] }
          ]
        },
        type: 'python',
        handler: async (args) => {
          if (args.csv_file) {
            return this.pythonWrapper.executeTool('bulk_price_update', {}, [args.csv_file]);
          } else {
            // Create temporary CSV
            const csv = 'identifier,price,compare_at_price\\n' + 
              args.updates.map(u => `${u.identifier},${u.price},${u.compare_at_price || ''}`).join('\\n');
            // This would need special handling to write temp file
            throw new Error('Inline updates not yet implemented. Please use CSV file.');
          }
        }
      },
      {
        name: 'create_combo',
        description: 'Create machine+grinder combo products',
        inputSchema: {
          type: 'object',
          properties: {
            product1: { type: 'string', description: 'First product identifier' },
            product2: { type: 'string', description: 'Second product identifier' },
            sku_suffix: { type: 'string', description: 'Custom suffix for combo SKU' },
            discount: { type: 'number', description: 'Fixed discount amount' },
            discount_percent: { type: 'number', description: 'Percentage discount' },
            price: { type: 'number', description: 'Set specific price for combo' },
            publish: { type: 'boolean', default: false, description: 'Publish immediately' },
            prefix: { type: 'string', default: 'COMBO', description: 'SKU prefix' },
            serial: { type: 'string', description: 'Serial/tracking number' }
          },
          required: ['product1', 'product2']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.sku_suffix) options['sku-suffix'] = args.sku_suffix;
          if (args.discount) options.discount = args.discount;
          if (args.discount_percent) options['discount-percent'] = args.discount_percent;
          if (args.price) options.price = args.price;
          if (args.publish) options.publish = true;
          if (args.prefix) options.prefix = args.prefix;
          if (args.serial) options.serial = args.serial;
          
          options.product1 = args.product1;
          options.product2 = args.product2;
          
          return this.pythonWrapper.executeTool('create_combo', options);
        }
      },
      {
        name: 'create_open_box',
        description: 'Create open box listing from existing product',
        inputSchema: {
          type: 'object',
          properties: {
            identifier: { type: 'string', description: 'Product identifier' },
            discount_percent: { type: 'number', default: 15, description: 'Discount percentage' },
            condition: { type: 'string', default: 'Open Box - Like New', description: 'Condition description' },
            quantity: { type: 'number', default: 1, description: 'Available quantity' },
            images: { type: 'array', items: { type: 'string' }, description: 'Additional image URLs' }
          },
          required: ['identifier']
        },
        type: 'python',
        handler: async (args) => {
          const options = {
            discount: args.discount_percent,
            condition: args.condition,
            quantity: args.quantity
          };
          if (args.images && args.images.length > 0) {
            options.images = args.images.join(',');
          }
          return this.pythonWrapper.executeTool('create_open_box', options, [args.identifier]);
        }
      },
      {
        name: 'manage_variant_links',
        description: 'Link or unlink product variants',
        inputSchema: {
          type: 'object',
          properties: {
            action: { type: 'string', enum: ['link', 'unlink'], description: 'Link action' },
            variant_ids: { type: 'array', items: { type: 'string' }, description: 'Variant IDs to link/unlink' }
          },
          required: ['action', 'variant_ids']
        },
        type: 'python',
        handler: async (args) => {
          const options = {
            [args.action]: args.variant_ids.join(',')
          };
          return this.pythonWrapper.executeTool('manage_variant_links', options);
        }
      },
      {
        name: 'add_product_images',
        description: 'Add images to an existing product',
        inputSchema: {
          type: 'object',
          properties: {
            identifier: { type: 'string', description: 'Product identifier' },
            images: { type: 'array', items: { type: 'string' }, description: 'Image URLs to add' },
            position: { type: 'number', description: 'Starting position for images' }
          },
          required: ['identifier', 'images']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.position) options.position = args.position;
          return this.pythonWrapper.executeTool('add_product_images', options, 
            [args.identifier, ...args.images]
          );
        }
      },
      {
        name: 'manage_redirects',
        description: 'Create or manage URL redirects',
        inputSchema: {
          type: 'object',
          properties: {
            action: { type: 'string', enum: ['create', 'delete', 'list'], description: 'Redirect action' },
            path: { type: 'string', description: 'Source path' },
            target: { type: 'string', description: 'Target URL' }
          },
          required: ['action']
        },
        type: 'python',
        handler: async (args) => {
          const options = { [args.action]: true };
          const positional = [];
          if (args.path) positional.push(args.path);
          if (args.target) positional.push(args.target);
          return this.pythonWrapper.executeTool('manage_redirects', options, positional);
        }
      },
      {
        name: 'upload_to_skuvault',
        description: 'Upload product data to SkuVault',
        inputSchema: {
          type: 'object',
          properties: {
            identifier: { type: 'string', description: 'Product identifier' },
            update_inventory: { type: 'boolean', default: false },
            update_prices: { type: 'boolean', default: false }
          },
          required: ['identifier']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.update_inventory) options['update-inventory'] = true;
          if (args.update_prices) options['update-prices'] = true;
          return this.pythonWrapper.executeTool('upload_to_skuvault', options, [args.identifier]);
        }
      },
      
      // The new Python script runner tool
      {
        name: 'run_python_script',
        description: 'Execute arbitrary Python code with full system access. Use this for complex operations not covered by other tools.',
        inputSchema: {
          type: 'object',
          properties: {
            code: { 
              type: 'string', 
              description: 'Python code to execute. Has access to all system libraries and can import from python-tools directory.' 
            }
          },
          required: ['code']
        },
        type: 'script',
        handler: async (args) => {
          try {
            const result = await runPythonScript(args.code);
            return {
              success: result.success,
              output: result.output,
              error: result.error,
              exitCode: result.exitCode
            };
          } catch (error) {
            return {
              success: false,
              error: error.message
            };
          }
        }
      },
      
      // Additional tools not previously included
      {
        name: 'manage_map_sales',
        description: 'Manage MAP (Minimum Advertised Price) sales based on calendar data',
        inputSchema: {
          type: 'object',
          properties: {
            command: { 
              type: 'string', 
              enum: ['check', 'apply', 'revert', 'summary'],
              description: 'Action to perform' 
            },
            calendar: { 
              type: 'string', 
              default: 'resources/breville_espresso_sales_2025_enhanced.md',
              description: 'Path to enhanced calendar file' 
            },
            date: { type: 'string', description: 'Specific date (YYYY-MM-DD) for check/apply' },
            date_range: { type: 'string', description: 'Date range for revert (e.g., "30 May - 05 Jun")' },
            dry_run: { type: 'boolean', default: false, description: 'Preview changes without applying' }
          },
          required: ['command']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.calendar) options.calendar = args.calendar;
          if (args.dry_run) options['dry-run'] = true;
          if (args.date) options.date = args.date;
          
          const positional = [args.command];
          if (args.command === 'revert' && args.date_range) {
            positional.push(args.date_range);
          }
          
          return this.pythonWrapper.executeTool('manage_map_sales', options, positional);
        }
      },
      {
        name: 'manage_miele_sales',
        description: 'Manage Miele MAP sales based on the 2025 calendar',
        inputSchema: {
          type: 'object',
          properties: {
            action: { 
              type: 'string', 
              enum: ['check', 'apply', 'revert', 'status'],
              description: 'Action to perform' 
            },
            date: { type: 'string', description: 'Override date (YYYY-MM-DD)' },
            dry_run: { type: 'boolean', default: false, description: 'Preview mode' }
          },
          required: ['action']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.date) options.date = args.date;
          if (args.dry_run) options['dry-run'] = true;
          
          return this.pythonWrapper.executeTool('manage_miele_sales', options, [args.action]);
        }
      },
      {
        name: 'manage_skuvault_kits',
        description: 'Manage SkuVault kits (bundles/combos)',
        inputSchema: {
          type: 'object',
          properties: {
            action: { 
              type: 'string', 
              enum: ['create', 'update', 'remove', 'list', 'get', 'create-bulk'],
              description: 'Kit management action' 
            },
            kit_sku: { type: 'string', description: 'Kit SKU' },
            components: { type: 'string', description: 'Components in format "SKU1:QTY1,SKU2:QTY2"' },
            title: { type: 'string', description: 'Kit title' },
            file: { type: 'string', description: 'CSV file for bulk operations' }
          },
          required: ['action']
        },
        type: 'python',
        handler: async (args) => {
          const options = { action: args.action };
          if (args.kit_sku) options['kit-sku'] = args.kit_sku;
          if (args.components) options.components = args.components;
          if (args.title) options.title = args.title;
          if (args.file) options.file = args.file;
          
          return this.pythonWrapper.executeTool('manage_skuvault_kits', options);
        }
      },
      {
        name: 'update_skuvault_prices',
        description: 'Update SkuVault prices from Shopify or CSV',
        inputSchema: {
          type: 'object',
          properties: {
            source: { 
              type: 'string', 
              enum: ['shopify', 'csv'],
              default: 'shopify',
              description: 'Price data source' 
            },
            csv_file: { type: 'string', description: 'CSV file path (if source is csv)' },
            sku: { type: 'string', description: 'Update specific SKU only' },
            dry_run: { type: 'boolean', default: false, description: 'Preview changes' }
          }
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.source) options.source = args.source;
          if (args.csv_file) options['csv-file'] = args.csv_file;
          if (args.sku) options.sku = args.sku;
          if (args.dry_run) options['dry-run'] = true;
          
          return this.pythonWrapper.executeTool('update_skuvault_prices', options);
        }
      },
      {
        name: 'update_skuvault_prices_v2',
        description: 'Update SkuVault prices (version 2 with enhanced features)',
        inputSchema: {
          type: 'object',
          properties: {
            source: { 
              type: 'string', 
              enum: ['shopify', 'csv'],
              default: 'shopify',
              description: 'Price data source' 
            },
            csv_file: { type: 'string', description: 'CSV file path (if source is csv)' },
            sku: { type: 'string', description: 'Update specific SKU only' },
            dry_run: { type: 'boolean', default: false, description: 'Preview changes' },
            force: { type: 'boolean', default: false, description: 'Force update even if prices match' }
          }
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.source) options.source = args.source;
          if (args.csv_file) options['csv-file'] = args.csv_file;
          if (args.sku) options.sku = args.sku;
          if (args.dry_run) options['dry-run'] = true;
          if (args.force) options.force = true;
          
          return this.pythonWrapper.executeTool('update_skuvault_prices_v2', options);
        }
      },
      {
        name: 'update_skuvault_costs',
        description: 'Update SkuVault costs from CSV file',
        inputSchema: {
          type: 'object',
          properties: {
            csv_file: { type: 'string', description: 'CSV file with SKU and cost columns' },
            dry_run: { type: 'boolean', default: false, description: 'Preview changes' }
          },
          required: ['csv_file']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.dry_run) options['dry-run'] = true;
          
          return this.pythonWrapper.executeTool('update_skuvault_costs', options, [args.csv_file]);
        }
      },
      {
        name: 'update_skuvault_costs_v2',
        description: 'Update SkuVault costs (version 2 with validation)',
        inputSchema: {
          type: 'object',
          properties: {
            csv_file: { type: 'string', description: 'CSV file with SKU and cost columns' },
            dry_run: { type: 'boolean', default: false, description: 'Preview changes' },
            validate_only: { type: 'boolean', default: false, description: 'Only validate without updating' }
          },
          required: ['csv_file']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.dry_run) options['dry-run'] = true;
          if (args.validate_only) options['validate-only'] = true;
          
          return this.pythonWrapper.executeTool('update_skuvault_costs_v2', options, [args.csv_file]);
        }
      },
      {
        name: 'create_product',
        description: 'Create a simple product with single variant in Shopify',
        inputSchema: {
          type: 'object',
          properties: {
            title: { type: 'string', description: 'Product title' },
            vendor: { type: 'string', description: 'Product vendor' },
            product_type: { type: 'string', description: 'Product type' },
            description: { type: 'string', description: 'Product description' },
            tags: { type: 'array', items: { type: 'string' }, description: 'Product tags' },
            price: { type: 'string', default: '0.00', description: 'Product price' },
            sku: { type: 'string', description: 'SKU' },
            barcode: { type: 'string', description: 'Barcode' },
            weight: { type: 'number', description: 'Weight' },
            weight_unit: { type: 'string', default: 'KILOGRAMS', enum: ['KILOGRAMS', 'POUNDS', 'GRAMS', 'OUNCES'] },
            inventory_quantity: { type: 'number', default: 0, description: 'Starting inventory' },
            track_inventory: { type: 'boolean', default: true, description: 'Track inventory' },
            status: { type: 'string', default: 'DRAFT', enum: ['DRAFT', 'ACTIVE'], description: 'Product status' }
          },
          required: ['title', 'vendor', 'product_type']
        },
        type: 'python',
        handler: async (args) => {
          // Use create_full_product instead of broken create_product
          // create_full_product requires price, so ensure it's set
          const options = {
            title: args.title,
            vendor: args.vendor,
            type: args.product_type,
            price: args.price || '0.00',
            status: args.status || 'DRAFT'
          };
          
          // Optional parameters
          if (args.description) options.description = args.description;
          if (args.tags && args.tags.length > 0) options.tags = args.tags.join(',');
          if (args.sku) options.sku = args.sku;
          if (args.barcode) options.barcode = args.barcode;
          if (args.weight) options.weight = args.weight;
          if (args.weight_unit) options['weight-unit'] = args.weight_unit;
          // Note: create_full_product doesn't support inventory quantity directly
          // It would need to be set via a separate update
          
          return this.pythonWrapper.executeTool('create_full_product', options);
        }
      },
      {
        name: 'manage_features_json',
        description: 'Manage product features box metafield (JSON format)',
        inputSchema: {
          type: 'object',
          properties: {
            action: { 
              type: 'string', 
              enum: ['add', 'update', 'remove', 'reorder', 'get', 'clear'],
              description: 'Feature management action' 
            },
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            feature: { type: 'string', description: 'Feature text to add/update' },
            index: { type: 'number', description: 'Feature index (0-based)' },
            new_index: { type: 'number', description: 'New position for reorder' }
          },
          required: ['action', 'identifier']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.feature) options.feature = args.feature;
          if (args.index !== undefined) options.index = args.index;
          if (args.new_index !== undefined) options['new-index'] = args.new_index;
          
          return this.pythonWrapper.executeTool('manage_features_json', 
            options, 
            [args.action, args.identifier]
          );
        }
      },
      {
        name: 'manage_features_metaobjects',
        description: 'Manage product features box using Shopify metaobjects',
        inputSchema: {
          type: 'object',
          properties: {
            action: { 
              type: 'string', 
              enum: ['add', 'update', 'remove', 'reorder', 'get', 'clear', 'migrate'],
              description: 'Feature management action' 
            },
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            feature: { type: 'string', description: 'Feature text to add/update' },
            index: { type: 'number', description: 'Feature index (0-based)' },
            new_index: { type: 'number', description: 'New position for reorder' }
          },
          required: ['action', 'identifier']
        },
        type: 'python',
        handler: async (args) => {
          const options = {};
          if (args.feature) options.feature = args.feature;
          if (args.index !== undefined) options.index = args.index;
          if (args.new_index !== undefined) options['new-index'] = args.new_index;
          
          return this.pythonWrapper.executeTool('manage_features_metaobjects', 
            options, 
            [args.action, args.identifier]
          );
        }
      },
      {
        name: 'update_status',
        description: 'Update product status in Shopify',
        inputSchema: {
          type: 'object',
          properties: {
            identifier: { type: 'string', description: 'Product ID, handle, SKU, or title' },
            status: { type: 'string', enum: ['ACTIVE', 'DRAFT', 'ARCHIVED'], description: 'New status' }
          },
          required: ['identifier', 'status']
        },
        type: 'python',
        handler: async (args) => {
          return this.pythonWrapper.executeTool('update_status', 
            { status: args.status }, 
            [args.identifier]
          );
        }
      },
      {
        name: 'graphql_query',
        description: 'Execute a GraphQL query against Shopify Admin API',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'GraphQL query' },
            variables: { type: 'object', description: 'Query variables' }
          },
          required: ['query']
        },
        type: 'python',
        handler: async (args) => {
          const options = args.variables ? { variables: JSON.stringify(args.variables) } : {};
          return this.pythonWrapper.executeTool('graphql_query', options, [args.query]);
        }
      },
      {
        name: 'graphql_mutation',
        description: 'Execute a GraphQL mutation against Shopify Admin API',
        inputSchema: {
          type: 'object',
          properties: {
            mutation: { type: 'string', description: 'GraphQL mutation' },
            variables: { type: 'object', description: 'Mutation variables' }
          },
          required: ['mutation']
        },
        type: 'python',
        handler: async (args) => {
          const options = args.variables ? { variables: JSON.stringify(args.variables) } : {};
          return this.pythonWrapper.executeTool('graphql_mutation', options, [args.mutation]);
        }
      },
      {
        name: 'test_connection',
        description: 'Test Shopify API connection and credentials',
        inputSchema: {
          type: 'object',
          properties: {}
        },
        type: 'python',
        handler: async () => {
          return this.pythonWrapper.executeTool('test_connection', {});
        }
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

export default ExtendedToolRegistry;