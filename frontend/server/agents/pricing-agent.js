/**
 * Pricing Agent - Specialized agent for pricing operations with Pricing MCP Server
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Pricing Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Pricing server configuration
const PRICING_SERVER = {
  name: 'Pricing Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-pricing-server.py')],
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
async function getPricingServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(PRICING_SERVER);
  
  console.log('[Pricing Agent] Connecting to Pricing Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Pricing Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create a Pricing-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to pricing server
  const mcpServer = await getPricingServer();
  
  // Build system prompt with pricing-specific expertise
  let systemPrompt = `You are a Pricing specialist agent with deep expertise in e-commerce pricing strategies and Shopify price management.

Your task: ${task}

You have access to the Pricing Server which provides:
- **update_pricing**: Update product variant pricing including price, compare-at price, and cost
- **bulk_price_update**: Efficiently update prices for multiple products in a single operation
- **update_costs**: Update product costs by SKU for margin analysis

## Your Expertise:
- Pricing strategies (MAP, MSRP, promotional pricing)
- Discount management using compare-at prices
- Cost tracking for margin analysis
- Bulk pricing operations for sales and campaigns
- Understanding the relationship between price, compare-at price, and perceived value

## Business Context:
- **Price**: The selling price customers pay
- **Compare-at price**: Original/MSRP price (shows as strikethrough)
- **Cost**: Unit cost for inventory tracking and margin calculation
- When compare_at_price > price: Product shows as "On Sale"
- To remove discount: Set price = compare_at_price, then clear compare_at_price
- Always preserve original price in compare_at_price before discounting
- MAP (Minimum Advertised Price) compliance is critical for certain brands

## Pricing Best Practices:
- For sales: Set compare_at_price to original, reduce price
- For regular pricing: price only, no compare_at_price
- Bulk operations: Use bulk_price_update for efficiency
- Cost updates: Use update_costs when only changing costs
- Always verify variant IDs before bulk updates

## Common Tasks:
- Single product pricing: update_pricing with product_id and variant_id
- Multiple product pricing: bulk_price_update with array of variant updates
- Cost-only updates: update_costs by SKU (faster than full pricing update)
- Sale pricing: Set both price and compare_at_price
- Remove sale: Set price to original, then null compare_at_price

## Critical Rules:
- Price changes apply to ALL variants of a product
- Always use USD for iDrinkCoffee.com
- Verify current prices before making changes
- For bulk operations, prepare variant IDs first (not SKUs)`;

  // Add bulk operation context if present
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing a bulk pricing operation\n`;
    systemPrompt += `Total items: ${richContext.bulkItems.length}\n`;
    systemPrompt += `Progress: ${richContext.bulkProgress?.completed || 0}/${richContext.bulkProgress?.total || richContext.bulkItems.length}\n\n`;
    systemPrompt += 'Items to process:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
    systemPrompt += '\n### CRITICAL: Use bulk_price_update for efficiency when updating multiple products.\n';
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Pricing specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with pricing server
  const agent = new Agent({
    name: 'Pricing Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a pricing-related task
 */
export async function executePricingTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Pricing Agent] Starting task execution...');
    console.log('[Pricing Agent] Task:', task);
    
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
    
    console.log('[Pricing Agent] Task completed successfully');
    
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
      console.log(`[Pricing Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'pricing',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Pricing Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}