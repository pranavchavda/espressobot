/**
 * MCP Client that integrates with MCP Server Manager
 */

import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { fileURLToPath } from 'url';
import MCPServerManager from './mcp-server-manager.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let serverManager = null;
let mcpInitialized = false;

/**
 * Initialize MCP tools and external servers
 */
export async function initializeMCPTools() {
  if (mcpInitialized) {
    return serverManager;
  }

  console.log('[MCP Client] Initializing MCP Server Manager...');
  
  try {
    // Create server manager instance
    serverManager = new MCPServerManager();
    
    // Define specialized MCP servers
    const specializedServers = [
      { 
        name: 'products', 
        file: 'mcp-products-server.py',
        description: 'Product operations (get, search, create, update)' 
      },
      { 
        name: 'pricing', 
        file: 'mcp-pricing-server.py',
        description: 'Pricing operations (update, bulk update, costs)'
      },
      { 
        name: 'inventory', 
        file: 'mcp-inventory-server.py',
        description: 'Inventory management (policy, tags, redirects)'
      },
      { 
        name: 'sales', 
        file: 'mcp-sales-server.py',
        description: 'Sales operations (MAP sales, Miele sales)'
      },
      { 
        name: 'features', 
        file: 'mcp-features-server.py',
        description: 'Product features (metafields, variant links, content)'
      },
      { 
        name: 'media', 
        file: 'mcp-media-server.py',
        description: 'Media operations (image management)'
      },
      { 
        name: 'integrations', 
        file: 'mcp-integrations-server.py',
        description: 'External integrations (SkuVault, reviews, research)'
      },
      { 
        name: 'product-management', 
        file: 'mcp-product-management-server.py',
        description: 'Advanced product operations (combos, open box, full creation)'
      },
      { 
        name: 'utility', 
        file: 'mcp-utility-server.py',
        description: 'Utility operations (memory management)'
      },
      { 
        name: 'orders', 
        file: 'mcp-orders-server.py',
        description: 'Order analytics (daily sales, revenue reports, order data)'
      }
    ];
    
    // Initialize all specialized servers
    console.log('[MCP Client] Initializing specialized MCP servers...');
    
    for (const serverConfig of specializedServers) {
      try {
        const server = new MCPServerStdio({
          name: `EspressoBot ${serverConfig.name} Server`,
          command: 'python3',
          args: [path.join(__dirname, '../../python-tools', serverConfig.file)],
          env: {
            ...process.env,
            PYTHONUNBUFFERED: '1'
          },
          cacheToolsList: true
        });
        
        console.log(`[MCP Client] Connecting to ${serverConfig.name} server...`);
        await server.connect();
        
        // Register as built-in server
        serverManager.registerBuiltInServer(serverConfig.name, server);
        console.log(`[MCP Client] ✓ ${serverConfig.name} server connected - ${serverConfig.description}`);
        
      } catch (error) {
        console.error(`[MCP Client] Failed to initialize ${serverConfig.name} server:`, error);
        // Continue with other servers even if one fails
      }
    }
    
    // Initialize external servers from config
    await serverManager.initializeServers();
    
    // Start watching configuration for changes
    await serverManager.watchConfiguration();
    
    // List all available servers
    const serverNames = serverManager.getServerNames();
    console.log(`[MCP Client] Initialized ${serverNames.length} MCP servers:`, serverNames.join(', '));
    
    // List tools from all servers
    for (const serverName of serverNames) {
      const server = serverManager.getServer(serverName);
      const tools = await server.listTools();
      console.log(`[MCP Client] Server '${serverName}' has ${tools.length} tools:`, 
        tools.map(t => t.name).join(', '));
    }
    
    mcpInitialized = true;
    return serverManager;
    
  } catch (error) {
    console.error('[MCP Client] Failed to initialize MCP tools:', error);
    serverManager = null;
    mcpInitialized = false;
    throw error;
  }
}

/**
 * Call an MCP tool from any registered server
 */
export async function callMCPTool(toolName, args = {}) {
  // Check if we need to initialize
  if (!mcpInitialized || !serverManager) {
    await initializeMCPTools();
  }
  
  console.log(`[MCP Client] Calling tool: ${toolName}`, args);
  
  // Find which server has this tool
  let targetServer = null;
  let toolFound = false;
  
  for (const server of serverManager.getAllServers()) {
    const tools = await server.listTools();
    if (tools.some(t => t.name === toolName)) {
      targetServer = server;
      toolFound = true;
      // Debug: log which server was selected
      const serverName = serverManager.getServerNames().find(name => serverManager.getServer(name) === server);
      console.log(`[MCP Client] Found tool '${toolName}' on server '${serverName}'`);
      break;
    }
  }
  
  if (!toolFound) {
    throw new Error(`Tool '${toolName}' not found in any MCP server`);
  }
  
  try {
    const mcpResponse = await targetServer.callTool({
      name: toolName,
      arguments: args
    });
    
    console.log(`[MCP Client] Tool ${toolName} completed successfully`);
    
    // Handle MCP protocol response format
    // MCP returns results in content[0].text as JSON string
    if (mcpResponse && Array.isArray(mcpResponse) && mcpResponse.length > 0) {
      // OpenAI SDK might return the content array directly
      const firstItem = mcpResponse[0];
      if (firstItem && firstItem.type === 'text' && firstItem.text) {
        console.log(`[MCP Client] Parsing MCP content[0].text format`);
        try {
          return JSON.parse(firstItem.text);
        } catch (e) {
          console.log(`[MCP Client] Failed to parse as JSON, returning raw text`);
          return firstItem.text;
        }
      }
      console.log(`[MCP Client] Response is array but not MCP format, returning as-is`);
      return mcpResponse;
    } else if (typeof mcpResponse === 'object' && mcpResponse !== null) {
      console.log(`[MCP Client] Response is an object with keys: ${Object.keys(mcpResponse).join(', ')}`);
      // Check for wrapped results
      if (mcpResponse.content) {
        console.log(`[MCP Client] Using content field`);
        return mcpResponse.content;
      } else if (mcpResponse.result) {
        console.log(`[MCP Client] Using result field`);
        return mcpResponse.result;
      }
      return mcpResponse;
    } else {
      console.log(`[MCP Client] Unexpected response type: ${typeof mcpResponse}`);
      return mcpResponse;
    }
    
  } catch (error) {
    console.error(`[MCP Client] Tool ${toolName} failed:`, error);
    
    // If connection was lost, try to reconnect once
    if (error.message?.includes('Not connected') || error.code === -32000) {
      console.log('[MCP Client] Connection lost, attempting to reconnect...');
      
      // Reinitialize all servers
      await cleanupMCPTools();
      await initializeMCPTools();
      
      // Find the server again
      for (const server of serverManager.getAllServers()) {
        const tools = await server.listTools();
        if (tools.some(t => t.name === toolName)) {
          targetServer = server;
          break;
        }
      }
      
      console.log('[MCP Client] Reconnected successfully, retrying tool call...');
      
      // Retry the tool call
      const result = await targetServer.callTool({
        name: toolName,
        arguments: args
      });
      
      console.log(`[MCP Client] Tool ${toolName} completed successfully after reconnect`);
      return result;
    }
    
    throw error;
  }
}

/**
 * Get list of all available MCP tools from all servers
 */
export async function getMCPTools() {
  if (!mcpInitialized || !serverManager) {
    await initializeMCPTools();
  }
  
  // Aggregate tools from all servers
  const allTools = [];
  
  for (const serverName of serverManager.getServerNames()) {
    const server = serverManager.getServer(serverName);
    const tools = await server.listTools();
    
    // Add server name to each tool for tracking
    const toolsWithServer = tools.map(tool => ({
      ...tool,
      _serverName: serverName
    }));
    
    allTools.push(...toolsWithServer);
  }
  
  return allTools;
}

/**
 * Clean up all MCP connections
 */
export async function cleanupMCPTools() {
  if (serverManager) {
    console.log('[MCP Client] Cleaning up all MCP connections...');
    try {
      await serverManager.close();
    } catch (error) {
      console.error('[MCP Client] Error closing MCP servers:', error);
    }
    serverManager = null;
    mcpInitialized = false;
  }
}