import { MCPServerStdio } from '@openai/agents';

/**
 * Discovers available tools from MCP servers and returns formatted tool information
 * for use in agent instructions
 */
export class MCPToolDiscovery {
  constructor() {
    this.shopifyTools = [];
    this.shopifyDevTools = [];
    this.todoTools = [];
    this.allTools = [];

    // Allow skipping remote discovery to avoid long start-up timeouts
    this.skipDiscovery = process.env.SKIP_MCP_DISCOVERY === 'true';
  }

  /**
   * Initialize and discover tools from all MCP servers
   */
  async discoverTools() {
    console.log('🔍 Starting MCP tool discovery...');

    if (this.skipDiscovery) {
      console.log('⚠️ SKIP_MCP_DISCOVERY=true – using fallback hardcoded tools');
      return this.getFallbackTools();
    }

    try {
      // Discover Shopify tools
      await this.discoverShopifyTools();
      
      // Discover Shopify Dev tools
      await this.discoverShopifyDevTools();
      
      // Discover Todo tools  
      await this.discoverTodoTools();
      
      // Combine all tools
      this.allTools = [...this.shopifyTools, ...this.shopifyDevTools, ...this.todoTools];
      
      console.log(`✅ Tool discovery complete. Found ${this.allTools.length} total tools:`);
      console.log(`   - Shopify tools: ${this.shopifyTools.length}`);
      console.log(`   - Shopify Dev tools: ${this.shopifyDevTools.length}`);
      console.log(`   - Todo tools: ${this.todoTools.length}`);
      
      // If no tools were discovered, that's an issue we need to debug
      if (this.allTools.length === 0) {
        console.error('❌ No tools discovered from any MCP server - this indicates a problem');
      }
      
      return {
        shopifyTools: this.shopifyTools,
        todoTools: this.todoTools,
        allTools: this.allTools
      };
    } catch (error) {
      console.error('❌ Tool discovery failed:', error.message);
      // Return fallback hardcoded tools if discovery fails
      return this.getFallbackTools();
    }
  }


  /**
   * Discover tools from Shopify MCP server
   */
  async discoverShopifyTools() {
    const MCP_SERVER_URL = 'https://webhook-listener-pranavchavda.replit.app/';
    console.log('MCP_SERVER_URL: ' + MCP_SERVER_URL);
    console.log('🛍️ Discovering Shopify MCP tools...');
    console.log(JSON.stringify(process.env));
    const childEnv = { ...process.env };
    const shopifyMCPServer = new MCPServerStdio({
      name: 'Shopify MCP Server Discovery',
      command: 'npx',
      args: ['-y', '@pranavchavda/shopify-mcp-stdio-client'],
      env: childEnv + MCP_SERVER_URL,
      shell: true,
    });

    try {
      await shopifyMCPServer.connect();
      console.log('   Connected to Shopify MCP server');
      
      // List available tools - this should return an array directly
      const tools = await shopifyMCPServer.listTools();
      console.log('   Raw tools response:', tools);
      
      if (Array.isArray(tools)) {
        this.shopifyTools = tools.map(tool => ({
          name: tool.name,
          description: tool.description || `Shopify operation: ${tool.name}`,
          category: 'shopify',
          inputSchema: tool.inputSchema
        }));
        
        console.log(`   Found ${this.shopifyTools.length} Shopify tools:`, 
          this.shopifyTools.map(t => t.name).join(', '));
      } else {
        console.log('   Tools response is not an array:', typeof tools);
        this.shopifyTools = [];
      }
      
      await shopifyMCPServer.close();
    } catch (error) {
      console.error('❌ Failed to discover Shopify tools:', error.message);
      throw error; // Don't use fallback, let the error propagate
    }
  }

  /**
   * Discover tools from Shopify Dev MCP server
   */
  async discoverShopifyDevTools() {
    console.log('📚 Discovering Shopify Dev MCP tools...');
    
    const childEnv = { ...process.env };
    const shopifyDevMCPServer = new MCPServerStdio({
      name: 'Shopify Dev MCP Server Discovery',
      command: 'npx',
      args: ['-y', '@shopify/dev-mcp@latest'],
      env: childEnv,
      shell: true,
    });

    try {
      await shopifyDevMCPServer.connect();
      console.log('   Connected to Shopify Dev MCP server');
      
      // List available tools - this should return an array directly
      const tools = await shopifyDevMCPServer.listTools();
      console.log('   Raw tools response:', tools);
      
      if (Array.isArray(tools)) {
        this.shopifyDevTools = tools.map(tool => ({
          name: tool.name,
          description: tool.description || `Shopify Dev operation: ${tool.name}`,
          category: 'shopify-dev',
          inputSchema: tool.inputSchema
        }));
        
        console.log(`   Found ${this.shopifyDevTools.length} Shopify Dev tools:`, 
          this.shopifyDevTools.map(t => t.name).join(', '));
      } else {
        console.log('   Tools response is not an array:', typeof tools);
        this.shopifyDevTools = [];
      }
      
      await shopifyDevMCPServer.close();
    } catch (error) {
      console.error('❌ Failed to discover Shopify Dev tools:', error.message);
      // Use fallback tools instead of throwing
      this.shopifyDevTools = this.getFallbackShopifyDevTools();
    }
  }

  /**
   * Discover tools from Todo MCP server
   */
  async discoverTodoTools() {
    console.log('📝 Discovering Todo MCP tools...');
    
    const childEnv = { ...process.env };
    const todoMCPServer = new MCPServerStdio({
      name: 'Todo MCP Server Discovery',
      command: '/home/pranav/.nvm/versions/node/v22.13.0/bin/npx',
      args: ['-y', '@pranavchavda/todo-mcp-server'],
      env: childEnv,
      shell: true,
    });
    console.log(JSON.stringify(childEnv));

    try {
      await todoMCPServer.connect();
      console.log('   Connected to Todo MCP server');
      
      // List available tools - this should return an array directly
      const tools = await todoMCPServer.listTools();
      console.log('   Raw tools response:', tools);
      
      if (Array.isArray(tools)) {
        this.todoTools = tools.map(tool => ({
          name: tool.name,
          description: tool.description || `Todo operation: ${tool.name}`,
          category: 'todo',
          inputSchema: tool.inputSchema
        }));
        
        console.log(`   Found ${this.todoTools.length} Todo tools:`, 
          this.todoTools.map(t => t.name).join(', '));
      } else {
        console.log('   Tools response is not an array:', typeof tools);
        this.todoTools = [];
      }
      
      await todoMCPServer.close();
    } catch (error) {
      console.error('❌ Failed to discover Todo tools:', error.message);
      throw error; // Don't use fallback, let the error propagate
    }
  }

  /**
   * Get formatted tool list for planner agent instructions
   */
  getFormattedToolsForPlanner() {
    const shopifyToolsList = this.shopifyTools.map(tool => 
      `        - ${tool.name}: ${tool.description}`
    ).join('\n');

    const todoToolsList = this.todoTools.map(tool => 
      `        - ${tool.name}: ${tool.description}`
    ).join('\n');

    return {
      shopifyTools: shopifyToolsList,
      todoTools: todoToolsList,
      shopifyToolNames: this.shopifyTools.map(t => t.name),
      todoToolNames: this.todoTools.map(t => t.name)
    };
  }

  /**
   * Get fallback tools if discovery fails
   */
  getFallbackTools() {
    console.log('📋 Using fallback hardcoded tools');
    
    return {
      shopifyTools: this.getFallbackShopifyTools(),
      shopifyDevTools: this.getFallbackShopifyDevTools(),
      todoTools: this.getFallbackTodoTools(),
      allTools: [...this.getFallbackShopifyTools(), ...this.getFallbackShopifyDevTools(), ...this.getFallbackTodoTools()]
    };
  }

  /**
   * Fallback Shopify tools (hardcoded)
   */
  getFallbackShopifyTools() {
    return [
      { name: 'search_products', description: 'Search for products by query', category: 'shopify' },
      { name: 'get_product', description: 'Get product details by ID', category: 'shopify' },
      { name: 'get_collections', description: 'List product collections', category: 'shopify' },
      { name: 'add_tags_to_product', description: 'Add tags to a product', category: 'shopify' },
      { name: 'remove_tags_from_product', description: 'Remove tags from a product', category: 'shopify' },
      { name: 'product_create_full', description: 'Create a new product', category: 'shopify' },
      { name: 'update_pricing', description: 'Update product variant prices', category: 'shopify' },
      { name: 'add_product_to_collection', description: 'Add product to collection', category: 'shopify' },
      { name: 'set_metafield', description: 'Set metafields on objects', category: 'shopify' },
      { name: 'run_full_shopify_graphql_query', description: 'Run custom GraphQL queries', category: 'shopify' },
      { name: 'run_full_shopify_graphql_mutation', description: 'Run custom GraphQL mutations', category: 'shopify' }
    ];
  }

  /**
   * Fallback Shopify Dev tools (hardcoded)
   */
  getFallbackShopifyDevTools() {
    return [
      { name: 'search_dev_docs', description: 'Search Shopify.dev documentation', category: 'shopify-dev' },
      { name: 'introspect_admin_schema', description: 'Access Shopify Admin GraphQL schema', category: 'shopify-dev' },
      { name: 'fetch_docs_by_path', description: 'Retrieve documents by path', category: 'shopify-dev' },
      { name: 'get_started', description: 'Explore Shopify APIs', category: 'shopify-dev' }
    ];
  }

  /**
   * Fallback Todo tools (hardcoded)
   */
  getFallbackTodoTools() {
    return [
      { name: 'create_todo', description: 'Create a new todo item', category: 'todo' },
      { name: 'list_todos', description: 'List all todo items', category: 'todo' },
      { name: 'update_todo', description: 'Update a todo item', category: 'todo' },
      { name: 'delete_todo', description: 'Delete a todo item', category: 'todo' },
      { name: 'mark_completed', description: 'Mark todo as completed', category: 'todo' }
    ];
  }
}

// Global instance for reuse
export const mcpToolDiscovery = new MCPToolDiscovery();