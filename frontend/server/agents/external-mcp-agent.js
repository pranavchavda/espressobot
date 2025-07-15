/**
 * External MCP Agent - Manages all external MCP servers from mcp-servers.json
 */

import { Agent } from '@openai/agents';
import MCPServerManager from '../tools/mcp-server-manager.js';

let serverManager = null;
let externalServers = [];

/**
 * Initialize external MCP servers
 */
async function initializeExternalServers() {
  if (!serverManager) {
    console.log('[External MCP Agent] Initializing MCP Server Manager...');
    serverManager = new MCPServerManager();
    
    // Load external servers from config
    await serverManager.initializeServers();
    
    // Get all non-built-in servers
    const allServerNames = serverManager.getServerNames();
    externalServers = allServerNames.filter(name => name !== 'python-tools');
    
    console.log(`[External MCP Agent] Found ${externalServers.length} external servers:`, externalServers);
    
    // Start watching for config changes
    await serverManager.watchConfiguration();
  }
  
  return serverManager;
}

/**
 * Create an External MCP Agent with all configured external servers
 */
export async function createExternalMCPAgent(task = '', richContext = null) {
  // Initialize servers if needed
  await initializeExternalServers();
  
  // Get all external MCP servers
  const mcpServers = externalServers.map(name => serverManager.getServer(name)).filter(Boolean);
  
  if (mcpServers.length === 0) {
    console.log('[External MCP Agent] No external MCP servers configured');
    return null;
  }
  
  // Build agent instructions with available tools
  let instructions = `You are an External Tools Agent with access to various MCP servers.

Available MCP servers and their capabilities:`;

  for (const serverName of externalServers) {
    const server = serverManager.getServer(serverName);
    if (server) {
      const tools = await server.listTools();
      instructions += `\n\n${serverName}:`;
      tools.forEach(tool => {
        instructions += `\n- ${tool.name}: ${tool.description || 'No description'}`;
      });
    }
  }

  instructions += `\n\nUse the appropriate tools to complete the requested task efficiently.`;

  // Add context if provided
  if (richContext) {
    if (richContext.userProfile) {
      instructions += `\n\nUser Profile:\n${richContext.userProfile}`;
    }
    if (richContext.relevantMemories && richContext.relevantMemories.length > 0) {
      instructions += `\n\nRelevant Context:\n${richContext.relevantMemories.join('\n')}`;
    }
  }

  // Add the specific task
  if (task) {
    instructions += `\n\nCurrent Task: ${task}`;
  }

  // Create the agent
  const agent = new Agent({
    name: 'External MCP Agent',
    instructions: instructions,
    mcpServers: mcpServers,
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a task using external MCP tools
 */
export async function executeExternalMCPTask(task, richContext = null) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[External MCP Agent] Creating agent for task:', task.substring(0, 100) + '...');
    const agent = await createExternalMCPAgent(task, richContext);
    
    if (!agent) {
      throw new Error('No external MCP servers available');
    }
    
    console.log('[External MCP Agent] Executing task...');
    const result = await run(agent, task, { maxTurns: 10 });
    
    console.log('[External MCP Agent] Task completed successfully');
    return result;
    
  } catch (error) {
    console.error('[External MCP Agent] Task failed:', error);
    throw error;
  }
}

/**
 * Get list of available external MCP tools
 */
export async function getExternalMCPTools() {
  await initializeExternalServers();
  
  const allTools = [];
  for (const serverName of externalServers) {
    const server = serverManager.getServer(serverName);
    if (server) {
      const tools = await server.listTools();
      allTools.push(...tools.map(tool => ({
        ...tool,
        server: serverName
      })));
    }
  }
  
  return allTools;
}

/**
 * Check if a specific tool is available in external MCP servers
 */
export async function hasExternalMCPTool(toolName) {
  const tools = await getExternalMCPTools();
  return tools.some(tool => tool.name === toolName);
}

/**
 * Close all external MCP server connections
 */
export async function closeExternalMCPServers() {
  if (serverManager) {
    console.log('[External MCP Agent] Closing all external MCP servers...');
    await serverManager.close();
    serverManager = null;
    externalServers = [];
  }
}