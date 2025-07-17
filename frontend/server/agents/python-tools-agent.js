/**
 * Python Tools Agent - Uses Python MCP server with proper OpenAI SDK pattern
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio, setTracingDisabled } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';

// CRITICAL: Disable tracing to prevent massive costs from tool schemas
// Each tools/list call returns 28 tools with full schemas = 4k+ lines
setTracingDisabled(true);
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
  const baseInstructions = `You are a Python Tools Agent specialized in Shopify operations for iDrinkCoffee.com.

You have access to Python-based tools for:
- Product management (search, create, update)
- Inventory and pricing operations
- Image management
- Metafields and features
- Sales and promotions
- SkuVault integration
- And many more Shopify operations

Always use the appropriate tool for the task. Be precise and efficient.

## AUTONOMOUS EXECUTION MODE
- Execute tasks immediately without asking for confirmation
- Use tools directly when you have clear instructions
- Only ask questions if critical data is missing
- Provide results, not progress updates`;

  let systemPrompt = baseInstructions;
  
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
  
  // Add current tasks if available in context
  if (richContext?.currentTasks && richContext.currentTasks.length > 0) {
    systemPrompt += '\n\n## Current Tasks:\n';
    richContext.currentTasks.forEach((task, idx) => {
      const status = task.status === 'completed' ? '[x]' : 
                    task.status === 'in_progress' ? '[🔄]' : '[ ]';
      systemPrompt += `${idx}. ${status} ${task.title || task.description}\n`;
    });
    
    systemPrompt += '\n\n## CRITICAL: Task Progress Tracking\n';
    systemPrompt += 'If you are assigned to work on one of these tasks, you MUST inform the orchestrator of your progress.\n';
    systemPrompt += 'When you complete your work, communicate back to the orchestrator what you accomplished.\n';
    systemPrompt += 'The orchestrator will handle updating the task status - this is the user\'s primary source of truth.\n';
  }
  
  // Add bulk operation context if available
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing a bulk operation of type: ${richContext.bulkOperationType || 'update'}\n`;
    if (richContext.bulkProgress) {
      systemPrompt += `Progress: ${richContext.bulkProgress.completed}/${richContext.bulkProgress.total} items completed\n`;
      systemPrompt += `Current item index: ${richContext.bulkProgress.current_index}\n`;
    }
    systemPrompt += '\n### Items to process:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
    systemPrompt += '\n### CRITICAL: You MUST process these items immediately without asking for clarification.\n';
    systemPrompt += 'Use the appropriate tools to complete the bulk operation on ALL items listed above.\n';
  }

  // Build final instructions with agency context
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Python Tools specialist',
    conversationId,
    taskDescription: task
  });

  // Create the agent with the MCP server
  const agent = new Agent({
    name: 'Python Tools Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    toolUseBehavior: 'run_llm_again'
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
      console.log(`[Python Tools Agent] Attempt ${attempt}/${retries} - Executing task with ${timeout/1000}s timeout...`);
      
      // Create a timeout promise
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Task execution timed out after ${timeout/1000} seconds`));
        }, timeout);
      });
      
      // Race between the actual execution and timeout
      const executionPromise = run(agent, task, { maxTurns });
      const result = await Promise.race([executionPromise, timeoutPromise]);
      
      console.log('[Python Tools Agent] Task completed successfully');
      return result;
      
    } catch (error) {
      const isTimeoutError = error.message.includes('timeout') || 
                           error.message.includes('terminated') || 
                           error.message.includes('ECONNRESET');
      
      console.log(`[Python Tools Agent] Attempt ${attempt} failed:`, error.message);
      
      if (isTimeoutError && attempt < retries) {
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000); // Exponential backoff, max 5s
        console.log(`[Python Tools Agent] Network/timeout error, retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      // If it's the last attempt or not a timeout error, throw it
      throw error;
    }
  }
}

/**
 * Execute a task using the Python tools agent
 */
export async function executePythonToolsTask(task, conversationId = null, richContext = null) {
  try {
    console.log('[Python Tools Agent] Creating agent for task:', task.substring(0, 100) + '...');
    const agent = await createPythonToolsAgent(task, conversationId, richContext);
    
    // Execute with timeout and retry logic
    return await executeWithTimeout(agent, task, {
      maxTurns: 10,
      timeout: 120000, // 2 minutes
      retries: 3
    });
    
  } catch (error) {
    console.error('[Python Tools Agent] Task failed after all retries:', error);
    
    // Return a graceful error response instead of throwing
    return {
      success: false,
      error: error.message,
      errorType: error.message.includes('timeout') ? 'timeout' : 'execution',
      message: `Python Tools Agent failed: ${error.message}`
    };
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