/**
 * External MCP Agent - Manages all external MCP servers from mcp-servers.json
 */

import { Agent } from '@openai/agents';
import MCPServerManager from '../tools/mcp-server-manager.js';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('External MCP Agent');

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
export async function createExternalMCPAgent(task = '', conversationId = null, richContext = null) {
  // Initialize servers if needed
  await initializeExternalServers();
  
  // Get all external MCP servers
  console.log(`[External MCP Agent] Available external servers: ${externalServers.join(', ')}`);
  
  const mcpServers = externalServers.map(name => {
    const server = serverManager.getServer(name);
    if (server) {
      console.log(`  ✓ Found server: ${name}`);
      return server;
    } else {
      console.log(`  ✗ Server not found: ${name}`);
      return null;
    }
  }).filter(Boolean);
  
  if (mcpServers.length === 0) {
    console.log('[External MCP Agent] No external MCP servers available');
    console.log('[External MCP Agent] Note: HTTP MCP servers are not yet supported by the OpenAI agents SDK');
    return null;
  }
  
  console.log(`[External MCP Agent] Using ${mcpServers.length} server(s) for this agent`);
  
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

  instructions += `\n\nUse the appropriate tools to complete the requested task efficiently.

## AUTONOMOUS EXECUTION MODE
- Execute tasks immediately without asking for confirmation
- Use tools directly when you have clear instructions
- Only ask questions if critical data is missing
- Provide results, not progress updates`;

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

  // Build final instructions with agency context
  const finalInstructions = await buildAgentInstructions(instructions, {
    agentRole: 'External Tools specialist',
    conversationId,
    taskDescription: task
  });

  // Create the agent
  const agent = new Agent({
    name: 'External MCP Agent',
    instructions: finalInstructions,
    mcpServers: mcpServers,
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    // toolUseBehavior removed to prevent loops
  });

  return agent;
}

/**
 * Execute a task with timeout and retry logic
 */
async function executeWithTimeout(agent, task, options = {}) {
  const { run } = await import('@openai/agents');
  const { maxTurns = 10, timeout = 120000, retries = 3 } = options; // 2 minute timeout, 3 retries
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`[External MCP Agent] Attempt ${attempt}/${retries} - Executing task with ${timeout/1000}s timeout...`);
      
      // Create a timeout promise
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Task execution timed out after ${timeout/1000} seconds`));
        }, timeout);
      });
      
      // Race between the actual execution and timeout
      const executionPromise = run(agent, task, { maxTurns });
      const result = await Promise.race([executionPromise, timeoutPromise]);
      
      console.log('[External MCP Agent] Task completed successfully');
      
      // Extract meaningful output instead of returning entire state
      let finalOutput = '';
      
      // Check for final output first
      if (result.finalOutput) {
        finalOutput = result.finalOutput;
      } 
      // Check for message outputs in generated items
      else if (result.state && result.state._generatedItems) {
        const messages = result.state._generatedItems
          .filter(item => item.type === 'message_output_item')
          .map(item => item.rawItem?.content?.[0]?.text || '')
          .filter(text => text);
        
        if (messages.length > 0) {
          finalOutput = messages[messages.length - 1];
        }
      }
      // Check for the new structure based on the example
      else if (result.state && result.state.currentStep && result.state.currentStep.output) {
        finalOutput = result.state.currentStep.output;
      }
      
      // Log token usage if available
      if (result.state?.context?.usage) {
        const usage = result.state.context.usage;
        console.log(`[External MCP Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
      }
      
      return {
        success: true,
        result: finalOutput || 'Task completed but no output generated',
        agent: 'external-mcp',
        tokenUsage: result.state?.context?.usage || null
      };
      
    } catch (error) {
      const isTimeoutError = error.message.includes('timeout') || 
                           error.message.includes('terminated') || 
                           error.message.includes('ECONNRESET');
      
      console.log(`[External MCP Agent] Attempt ${attempt} failed:`, error.message);
      
      if (isTimeoutError && attempt < retries) {
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000); // Exponential backoff, max 5s
        console.log(`[External MCP Agent] Network/timeout error, retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      // If it's the last attempt or not a timeout error, throw it
      throw error;
    }
  }
}

/**
 * Execute a task using external MCP tools
 */
export async function executeExternalMCPTask(task, richContext = null) {
  try {
    console.log('[External MCP Agent] Creating agent for task:', task.substring(0, 100) + '...');
    const agent = await createExternalMCPAgent(task, richContext);
    
    if (!agent) {
      throw new Error('No external MCP servers available');
    }
    
    // Execute with timeout and retry logic
    return await executeWithTimeout(agent, task, {
      maxTurns: 10,
      timeout: 120000, // 2 minutes
      retries: 3
    });
    
  } catch (error) {
    console.error('[External MCP Agent] Task failed after all retries:', error);
    
    // Return a graceful error response instead of throwing
    return {
      success: false,
      error: error.message,
      errorType: error.message.includes('timeout') ? 'timeout' : 'execution',
      message: `External MCP Agent failed: ${error.message}`
    };
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