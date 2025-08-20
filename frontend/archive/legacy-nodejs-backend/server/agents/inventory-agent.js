/**
 * Inventory Agent - Specialized agent for inventory and tagging operations
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Inventory Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Inventory server configuration
const INVENTORY_SERVER = {
  name: 'Inventory Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-inventory-server.py')],
  env: {
    ...process.env,
    PYTHONPATH: path.join(__dirname, '../../python-tools')
  }
};

// Cache server connection
let serverInstance = null;

/**
 * Get or create MCP server connection
 */
async function getInventoryServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(INVENTORY_SERVER);
  
  console.log('[Inventory Agent] Connecting to Inventory Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Inventory Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create an Inventory-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to inventory server
  const mcpServer = await getInventoryServer();
  
  // Build system prompt with inventory-specific expertise
  let systemPrompt = `You are an Inventory specialist agent with expertise in stock management, product organization, and URL management.

Your task: ${task}

You have access to the Inventory Server which provides:
- **manage_inventory_policy**: Control whether products can be oversold (DENY/ALLOW)
- **manage_tags**: Add, remove, or replace tags on products for organization
- **manage_redirects**: Create, list, or delete URL redirects for SEO

## Your Expertise:
- Inventory policy management (preventing/allowing overselling)
- Product tagging for organization and automation
- URL redirect management for SEO and user experience
- Understanding the impact of inventory policies on customer experience

## Business Context:

### Inventory Policies:
- **DENY (default)**: Prevents overselling - customers cannot buy when out of stock
  - Use for: Physical inventory, limited stock items
- **ALLOW/CONTINUE**: Allows overselling - customers can buy even when out of stock
  - Use for: Pre-orders, made-to-order items, digital products
- Policy applies to ALL variants of a product

### Product Tags:
- Used for organization, filtering, and automation
- Common tags: "espresso-machines", "grinders", "sale", "new-arrival"
- Tags are case-sensitive - maintain consistency
- Some tags trigger automations (e.g., "sale" shows sale badge)

### URL Redirects:
- Maintain SEO when changing URLs
- Handle discontinued products gracefully
- Support marketing campaigns
- Maximum 10,000 redirects per store
- Paths should start with "/" (e.g., "/old-product")

IMPORTANT: 
- Check current inventory levels before changing policies
- Use consistent tag naming conventions
- Verify old URLs exist before creating redirects
- For bulk tagging, use manage_tags with action="add" repeatedly`;

  // Add bulk operation context if present
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing a bulk operation\n`;
    systemPrompt += `Total items: ${richContext.bulkItems.length}\n`;
    systemPrompt += `Progress: ${richContext.bulkProgress?.completed || 0}/${richContext.bulkProgress?.total || richContext.bulkItems.length}\n\n`;
    systemPrompt += 'Items to process:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
    systemPrompt += '\n### CRITICAL: Process all items systematically.\n';
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Inventory specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with inventory server
  const agent = new Agent({
    name: 'Inventory Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    // toolUseBehavior removed to prevent loops
  });

  return agent;
}

/**
 * Execute an inventory-related task
 */
export async function executeInventoryTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Inventory Agent] Starting task execution...');
    console.log('[Inventory Agent] Task:', task);
    
    // Create agent
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
    
    console.log('[Inventory Agent] Task completed successfully');
    
    // Extract meaningful output
    let finalOutput = '';
    
    if (result.finalOutput) {
      finalOutput = result.finalOutput;
    } else if (result.state && result.state._generatedItems) {
      const messages = result.state._generatedItems
        .filter(item => item.type === 'message_output_item')
        .map(item => item.rawItem?.content?.[0]?.text || '')
        .filter(text => text);
      
      if (messages.length > 0) {
        finalOutput = messages[messages.length - 1];
      }
    } else if (result.state && result.state.currentStep && result.state.currentStep.output) {
      finalOutput = result.state.currentStep.output;
    }
    
    // Log token usage
    if (result.state?.context?.usage) {
      const usage = result.state.context.usage;
      console.log(`[Inventory Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'inventory',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Inventory Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}