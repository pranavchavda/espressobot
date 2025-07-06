import MCPOnlyToolRegistry from './custom-tools/tool-registry-mcp-only.js';
import { registerNativeTools } from './native-tools/index.js';
import { memoryTool } from './tools/memory-tool.js';
import { getMCPTools } from './tools/mcp-client.js';

/**
 * Discovers available tools from custom tool implementations
 * Integrates with MCP-based tool discovery for comprehensive coverage
 */
export class CustomToolDiscovery {
  constructor() {
    this.toolRegistry = new MCPOnlyToolRegistry();
    this.shopifyTools = [];
    this.shopifyDevTools = [];
    this.todoTools = [];
    this.allTools = [];
  }

  /**
   * Initialize and discover tools from custom implementations
   */
  async discoverTools() {
    console.log('🔍 Starting custom tool discovery...');

    try {
      // Register native JavaScript tools if enabled
      registerNativeTools(this.toolRegistry);
      
      // Register memory tool
      this.toolRegistry.registerTool('memory_operations', memoryTool);
      
      // Get all custom tools
      const customTools = this.toolRegistry.getTools();
      
      // Add MCP tools (dynamically discovered from MCP server)
      const mcpTools = await this.getMcpToolsFromServer();
      
      // Categorize tools
      this.shopifyTools = [
        ...customTools.map(tool => ({
          name: tool.name,
          description: tool.description,
          category: 'shopify',
          inputSchema: tool.inputSchema
        })),
        ...mcpTools
      ];
      
      // For now, we'll include placeholder dev tools until we implement them
      this.shopifyDevTools = this.getFallbackShopifyDevTools();
      
      // Todo tools are now handled in the agent directly, not via external tools
      this.todoTools = [];
      
      // Combine all tools
      this.allTools = [...this.shopifyTools, ...this.shopifyDevTools];
      
      console.log(`✅ Tool discovery complete. Found ${this.allTools.length} total tools:`);
      console.log(`   - Shopify tools: ${this.shopifyTools.length}`);
      console.log(`   - Shopify Dev tools: ${this.shopifyDevTools.length}`);
      
      return {
        shopifyTools: this.shopifyTools,
        shopifyDevTools: this.shopifyDevTools,
        todoTools: this.todoTools,
        allTools: this.allTools
      };
    } catch (error) {
      console.error('❌ Tool discovery failed:', error.message);
      throw error;
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
   * Get MCP tool descriptions from live MCP server
   */
  async getMcpToolsFromServer() {
    try {
      console.log('🔍 Discovering MCP tools from server...');
      const mcpTools = await getMCPTools();
      
      console.log(`✅ Found ${mcpTools.length} MCP tools:`, mcpTools.map(t => t.name).join(', '));
      
      // Convert MCP tool format to our internal format
      return mcpTools.map(tool => ({
        name: tool.name,
        description: tool.description || `MCP tool: ${tool.name}`,
        category: 'mcp',
        inputSchema: tool.inputSchema
      }));
      
    } catch (error) {
      console.warn('⚠️ Failed to discover MCP tools, using fallback:', error.message);
      // Return empty array if MCP server is not available
      return [];
    }
  }

  /**
   * Get tools in OpenAI function format
   */
  getOpenAIFunctions() {
    return this.toolRegistry.getOpenAIFunctions();
  }

  /**
   * Execute a tool by name
   */
  async executeTool(toolName, args) {
    return this.toolRegistry.executeTool(toolName, args);
  }

  /**
   * Fallback Shopify Dev tools (until we implement custom versions)
   */
  getFallbackShopifyDevTools() {
    return [
      { 
        name: 'search_dev_docs', 
        description: 'Search Shopify.dev documentation', 
        category: 'shopify-dev',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Search query' }
          },
          required: ['query']
        }
      },
      { 
        name: 'introspect_admin_schema', 
        description: 'Access Shopify Admin GraphQL schema', 
        category: 'shopify-dev',
        inputSchema: {
          type: 'object',
          properties: {
            type: { type: 'string', description: 'Type name to introspect' }
          }
        }
      },
      { 
        name: 'fetch_docs_by_path', 
        description: 'Retrieve documents by path', 
        category: 'shopify-dev',
        inputSchema: {
          type: 'object',
          properties: {
            path: { type: 'string', description: 'Documentation path' }
          },
          required: ['path']
        }
      },
      { 
        name: 'get_started', 
        description: 'Explore Shopify APIs', 
        category: 'shopify-dev',
        inputSchema: {
          type: 'object',
          properties: {}
        }
      }
    ];
  }
}

// Global instance for reuse
export const customToolDiscovery = new CustomToolDiscovery();

// Default export for the class
export default CustomToolDiscovery;