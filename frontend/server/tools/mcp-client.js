/**
 * MCP Client for EspressoBot Python Tools
 */

import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let mcpToolsServer = null;
let mcpInitialized = false;

/**
 * Initialize MCP tools server
 */
export async function initializeMCPTools() {
  if (mcpInitialized) {
    return mcpToolsServer;
  }

  console.log('[MCP Client] Initializing Python tools MCP server...');
  
  try {
    // Create MCP server connection
    mcpToolsServer = new MCPServerStdio({
      name: 'EspressoBot Python Tools',
      command: 'python3',
      args: [path.join(__dirname, '../../python-tools/mcp-server.py')],
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1'  // Ensure Python output is not buffered
      },
      cacheToolsList: true
    });
    
    // Connect to the server
    console.log('[MCP Client] Connecting to Python tools MCP server...');
    await mcpToolsServer.connect();
    
    // List available tools
    const tools = await mcpToolsServer.listTools();
    console.log(`[MCP Client] Connected! Found ${tools.length} tools:`, 
      tools.map(t => t.name).join(', '));
    
    mcpInitialized = true;
    return mcpToolsServer;
    
  } catch (error) {
    console.error('[MCP Client] Failed to initialize MCP tools:', error);
    mcpToolsServer = null;
    mcpInitialized = false;
    throw error;
  }
}

/**
 * Call an MCP tool directly
 */
export async function callMCPTool(toolName, args = {}) {
  // Check if we need to reconnect
  if (!mcpInitialized || !mcpToolsServer) {
    await initializeMCPTools();
  }
  
  console.log(`[MCP Client] Calling tool: ${toolName}`, args);
  
  try {
    const mcpResponse = await mcpToolsServer.callTool({
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
      
      // Clean up existing connection
      await cleanupMCPTools();
      
      // Reconnect
      try {
        await initializeMCPTools();
        console.log('[MCP Client] Reconnected successfully, retrying tool call...');
        
        // Retry the tool call
        const result = await mcpToolsServer.callTool({
          name: toolName,
          arguments: args
        });
        
        console.log(`[MCP Client] Tool ${toolName} completed successfully after reconnect`);
        return result;
        
      } catch (reconnectError) {
        console.error('[MCP Client] Reconnection failed:', reconnectError);
        throw reconnectError;
      }
    }
    
    throw error;
  }
}

/**
 * Get list of available MCP tools
 */
export async function getMCPTools() {
  if (!mcpInitialized || !mcpToolsServer) {
    await initializeMCPTools();
  }
  
  return await mcpToolsServer.listTools();
}

/**
 * Clean up MCP connection
 */
export async function cleanupMCPTools() {
  if (mcpToolsServer) {
    console.log('[MCP Client] Cleaning up MCP tools connection...');
    try {
      await mcpToolsServer.close();
    } catch (error) {
      console.error('[MCP Client] Error closing MCP server:', error);
    }
    mcpToolsServer = null;
    mcpInitialized = false;
  }
}