/**
 * Python Tools Agent V2 - Uses specialized MCP servers to reduce token usage
 * Dynamically selects appropriate server(s) based on task keywords
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio, setTracingDisabled } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';

// CRITICAL: Disable tracing to prevent massive costs from tool schemas
setTracingDisabled(true);

import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// MCP server configurations
const MCP_SERVERS = {
  products: {
    name: 'Products Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-products-server.py')],
    keywords: ['product', 'search', 'create', 'status', 'sku', 'handle', 'vendor', 'graphql', 'mutation', 'query', 'collection', 'smart collection']
  },
  pricing: {
    name: 'Pricing Server', 
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-pricing-server.py')],
    keywords: ['price', 'pricing', 'cost', 'discount', 'sale', 'margin', 'bulk price']
  },
  inventory: {
    name: 'Inventory Server',
    command: 'python3', 
    args: [path.join(__dirname, '../../python-tools/mcp-inventory-server.py')],
    keywords: ['inventory', 'stock', 'policy', 'tag', 'redirect', 'oversell']
  },
  sales: {
    name: 'Sales Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-sales-server.py')], 
    keywords: ['miele', 'map', 'sale', 'breville', 'campaign']
  },
  features: {
    name: 'Features Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-features-server.py')],
    keywords: ['feature', 'metafield', 'metaobject', 'content', 'description']
  },
  media: {
    name: 'Media Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-media-server.py')],
    keywords: ['image', 'media', 'photo', 'picture', 'upload', 'add image']
  },
  integrations: {
    name: 'Integrations Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-integrations-server.py')],
    keywords: ['skuvault', 'review', 'research', 'perplexity', 'integration', 'external']
  },
  'product-management': {
    name: 'Product Management Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-product-management-server.py')],
    keywords: ['create full', 'update full', 'variant', 'combo', 'open box', 'bundle']
  },
  utility: {
    name: 'Utility Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-utility-server.py')],
    keywords: ['memory', 'remember', 'recall', 'search memory']
  }
};

// Cache for MCP server connections
const serverCache = new Map();

/**
 * Determine which MCP servers are needed based on task keywords
 */
function selectServersForTask(task) {
  const taskLower = task.toLowerCase();
  const selectedServers = [];
  
  for (const [serverKey, config] of Object.entries(MCP_SERVERS)) {
    // Check if any keyword matches the task
    if (config.keywords.some(keyword => taskLower.includes(keyword))) {
      selectedServers.push(serverKey);
    }
  }
  
  // Default to products server if no specific match
  if (selectedServers.length === 0) {
    console.log('[Python Tools Agent V2] No specific server match, defaulting to products server');
    selectedServers.push('products');
  }
  
  console.log(`[Python Tools Agent V2] Selected servers for task: ${selectedServers.join(', ')}`);
  return selectedServers;
}

/**
 * Get or create MCP server connection
 */
async function getMCPServer(serverKey) {
  if (serverCache.has(serverKey)) {
    return serverCache.get(serverKey);
  }
  
  const config = MCP_SERVERS[serverKey];
  if (!config) {
    throw new Error(`Unknown MCP server: ${serverKey}`);
  }
  
  const server = new MCPServerStdio({
    name: config.name,
    command: config.command,
    args: config.args,
    env: {
      ...process.env,
      PYTHONPATH: path.join(__dirname, '../../python-tools')
    }
  });
  
  console.log(`[Python Tools Agent V2] Connecting to ${config.name}...`);
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Python Tools Agent V2] ${config.name} connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverCache.set(serverKey, server);
  return server;
}

/**
 * Create an agent with selected MCP servers
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Select appropriate servers based on task
  const serverKeys = selectServersForTask(task);
  
  // Connect to selected servers
  const mcpServers = [];
  for (const serverKey of serverKeys) {
    const server = await getMCPServer(serverKey);
    mcpServers.push(server);
  }
  
  // Build system prompt with context
  let systemPrompt = `You are a Python Tools specialist agent with access to Shopify Admin API tools.

Your task: ${task}

Connected MCP Servers: ${serverKeys.map(k => MCP_SERVERS[k].name).join(', ')}

Each server provides specialized tools and may also offer:
- Resources: Use resources/list and resources/read to access business rules and reference data
- Prompts: Use prompts/list and prompts/get for guided workflows

IMPORTANT: 
- Check available resources for business rules before executing operations
- Use prompts for complex workflows when available
- Each server only has 3-4 related tools, reducing token usage`;

  // Add bulk operation context if present
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing a bulk operation of type: ${richContext.bulkOperationType || 'update'}\n`;
    systemPrompt += `Total items: ${richContext.bulkItems.length}\n`;
    systemPrompt += `Progress: ${richContext.bulkProgress?.completed || 0}/${richContext.bulkProgress?.total || richContext.bulkItems.length}\n\n`;
    systemPrompt += 'Items to process:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
    systemPrompt += '\n### CRITICAL: You MUST process these items immediately without asking for clarification.\n';
    systemPrompt += 'Use the appropriate tools to complete the bulk operation on ALL items listed above.\n';
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Python Tools specialist (optimized)',
    conversationId,
    taskDescription: task
  });

  // Create agent with selected MCP servers
  const agent = new Agent({
    name: 'Python Tools Agent V2',
    instructions,
    mcpServers, // Multiple servers based on task
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a Python tools task with specialized MCP servers
 */
export async function executePythonToolsTaskV2(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Python Tools Agent V2] Starting task execution...');
    console.log('[Python Tools Agent V2] Task:', task);
    
    // Create agent with appropriate servers
    const agent = await createAgent(task, conversationId, richContext);
    
    // Execute with timeout
    const maxTurns = 10;
    const timeout = 120000; // 2 minutes
    
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Task execution timed out after ${timeout/1000} seconds`));
      }, timeout);
    });
    
    const executionPromise = run(agent, task, { maxTurns });
    const result = await Promise.race([executionPromise, timeoutPromise]);
    
    console.log('[Python Tools Agent V2] Task completed successfully');
    
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
      console.log(`[Python Tools Agent V2] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'python-tools-v2',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Python Tools Agent V2] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}

// Export for testing server selection
export { selectServersForTask };