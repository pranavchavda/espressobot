/**
 * Products Agent - Specialized agent for product operations with Products MCP Server
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Products Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Products server configuration
const PRODUCTS_SERVER = {
  name: 'Products Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-products-server.py')],
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
async function getProductsServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(PRODUCTS_SERVER);
  
  console.log('[Products Agent] Connecting to Products Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Products Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create a Products-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to products server
  const mcpServer = await getProductsServer();
  
  // Build system prompt with product-specific expertise
  let systemPrompt = `You are a Products specialist agent with deep expertise in Shopify product management.

Your task: ${task}

You have access to the Products Server which provides:
- **get_product**: Retrieve detailed product information by SKU, handle, or ID
- **search_products**: Search products with various filters (title, vendor, status, etc.)
- **create_product**: Create new products with basic information
- **update_status**: Change product status (ACTIVE, DRAFT, ARCHIVED)
- **update_variant_weight**: Update product variant weight by SKU with proper units (GRAMS, KILOGRAMS, OUNCES, POUNDS)

**Note**: GraphQL operations (graphql_query, graphql_mutation) have been moved to a dedicated GraphQL Agent for safety and proper documentation research. For complex operations requiring GraphQL, recommend using the GraphQL Agent.

## Your Expertise:
- Product lifecycle management (creation, updates, archiving)
- SKU and inventory tracking
- Product search and filtering
- Weight management for shipping calculations
- Understanding product attributes (vendor, type, tags, etc.)
- Basic product operations (no GraphQL - refer to GraphQL Agent for complex operations)

## Business Context:
- Products are the core of iDrinkCoffee.com's catalog
- SKUs must be unique across all products
- Product status affects visibility (DRAFT for prep, ACTIVE for sale)
- Collections organize products for navigation and marketing

## Best Practices:
- Always verify product exists before updating
- Use search_products for bulk operations to find multiple items
- When creating products, consider required fields: title, vendor, product_type
- Return clear, actionable results with product IDs and handles
- For complex operations (collections, metafields), recommend GraphQL Agent

## Common Tasks:
- Finding products: Use search_products with appropriate filters
- Getting details: Use get_product with SKU, handle, or ID
- Basic product management: Create, update status, modify weights
- **For collections/complex operations**: Recommend using GraphQL Agent with proper documentation research`;

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
    agentRole: 'Products specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with products server
  const agent = new Agent({
    name: 'Products Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    // toolUseBehavior removed to prevent loops
  });

  return agent;
}

/**
 * Execute a products-related task
 */
export async function executeProductsTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Products Agent] Starting task execution...');
    console.log('[Products Agent] Task:', task);
    
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
    
    console.log('[Products Agent] Task completed successfully');
    
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
      console.log(`[Products Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'products',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Products Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}