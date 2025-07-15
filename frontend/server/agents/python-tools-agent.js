/**
 * Python Tools Agent - Uses Python MCP server with proper OpenAI SDK pattern
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let pythonMCPServer = null;

/**
 * Get or create the Python MCP server connection
 */
async function getPythonMCPServer() {
  if (!pythonMCPServer) {
    pythonMCPServer = new MCPServerStdio({
      name: 'EspressoBot Python Tools',
      command: 'python3',
      args: [path.join(__dirname, '../../python-tools/mcp-server.py')],
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1'
      },
      cacheToolsList: true
    });
    
    console.log('[Python Tools Agent] Connecting to Python MCP server...');
    await pythonMCPServer.connect();
    
    const tools = await pythonMCPServer.listTools();
    console.log(`[Python Tools Agent] Connected! ${tools.length} tools available:`, 
      tools.map(t => t.name).join(', '));
  }
  
  return pythonMCPServer;
}

/**
 * Create a Python tools agent with rich context
 */
export async function createPythonToolsAgent(task = '', conversationId = null, richContext = null) {
  // Get the MCP server
  const mcpServer = await getPythonMCPServer();
  
  // Build the agent prompt with context
  let systemPrompt = `You are a Python Tools Agent specialized in Shopify operations for iDrinkCoffee.com.

You have access to Python-based tools for:
- Product management (search, create, update)
- Inventory and pricing operations
- Image management
- Metafields and features
- Sales and promotions
- SkuVault integration
- And many more Shopify operations

Always use the appropriate tool for the task. Be precise and efficient.`;

  // Add rich context if provided
  if (richContext) {
    if (richContext.userProfile) {
      systemPrompt += `\n\nUser Profile:\n${richContext.userProfile}`;
    }
    if (richContext.relevantMemories && richContext.relevantMemories.length > 0) {
      systemPrompt += `\n\nRelevant Context:\n${richContext.relevantMemories.join('\n')}`;
    }
    if (richContext.recentProducts && richContext.recentProducts.length > 0) {
      systemPrompt += `\n\nRecently Accessed Products:\n${richContext.recentProducts.map(p => `- ${p.title} (${p.sku})`).join('\n')}`;
    }
  }

  // Add the specific task
  if (task) {
    systemPrompt += `\n\nCurrent Task: ${task}`;
  }

  // Create the agent with the MCP server
  const agent = new Agent({
    name: 'Python Tools Agent',
    instructions: systemPrompt,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a task using the Python tools agent
 */
export async function executePythonToolsTask(task, conversationId = null, richContext = null) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Python Tools Agent] Creating agent for task:', task.substring(0, 100) + '...');
    const agent = await createPythonToolsAgent(task, conversationId, richContext);
    
    console.log('[Python Tools Agent] Executing task...');
    const result = await run(agent, task, { maxTurns: 10 });
    
    console.log('[Python Tools Agent] Task completed successfully');
    return result;
    
  } catch (error) {
    console.error('[Python Tools Agent] Task failed:', error);
    throw error;
  }
}

/**
 * Close the Python MCP server connection
 */
export async function closePythonMCPServer() {
  if (pythonMCPServer) {
    console.log('[Python Tools Agent] Closing Python MCP server...');
    await pythonMCPServer.close();
    pythonMCPServer = null;
  }
}