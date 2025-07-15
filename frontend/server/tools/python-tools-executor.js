/**
 * Python Tools Executor - Bridge between orchestrator and Python tools agent
 * 
 * This module provides a way for the orchestrator to execute Python tools
 * using the proper MCP pattern (via an agent) instead of direct tool calls.
 */

import { executePythonToolsTask } from '../agents/python-tools-agent.js';

/**
 * Execute a Python tool using the agent pattern
 * 
 * @param {string} toolName - Name of the tool to execute
 * @param {object} args - Arguments for the tool
 * @param {object} context - Optional context (conversationId, richContext)
 * @returns {Promise<any>} - Tool execution result
 */
export async function executePythonTool(toolName, args, context = {}) {
  console.log(`[Python Tools Executor] Executing ${toolName} via agent`);
  
  // Build a natural language task from the tool call
  const task = buildTaskFromToolCall(toolName, args);
  
  try {
    // Execute via Python tools agent
    const result = await executePythonToolsTask(
      task,
      context.conversationId,
      context.richContext
    );
    
    // Extract the actual result from the agent response
    // The agent returns a RunResult, we need to extract the actual data
    if (result && result.state && result.state._generatedItems) {
      // Look for tool output in generated items
      const toolOutputs = result.state._generatedItems.filter(
        item => item.type === 'tool_call_output'
      );
      
      if (toolOutputs.length > 0) {
        // Return the last tool output (most recent)
        const lastOutput = toolOutputs[toolOutputs.length - 1];
        return lastOutput.output;
      }
    }
    
    // Fallback: return the full result
    return result;
    
  } catch (error) {
    console.error(`[Python Tools Executor] Failed to execute ${toolName}:`, error);
    throw error;
  }
}

/**
 * Convert a tool call to a natural language task
 */
function buildTaskFromToolCall(toolName, args) {
  // Map of tool names to task templates
  const taskTemplates = {
    // Product operations
    'get_product': (args) => `Get product details for ${args.identifier}`,
    'search_products': (args) => `Search for products with query "${args.query}"${args.limit ? ` (limit: ${args.limit})` : ''}`,
    'create_product': (args) => `Create a new product with title "${args.title}" from vendor "${args.vendor}"`,
    'update_status': (args) => `Update product ${args.product} status to ${args.status}`,
    
    // Pricing operations
    'update_pricing': (args) => `Update pricing for product ${args.product_id} variant ${args.variant_id} to $${args.price}${args.compare_at_price ? ` (compare at: $${args.compare_at_price})` : ''}`,
    'bulk_price_update': (args) => `Update prices for ${args.updates.length} products`,
    
    // Inventory operations
    'manage_inventory_policy': (args) => `Set inventory policy for ${args.identifier} to ${args.policy}`,
    
    // Tag operations
    'manage_tags': (args) => `${args.action} tags ${JSON.stringify(args.tags)} for product ${args.product}`,
    
    // Image operations
    'add_product_images': (args) => `${args.action} images for product ${args.product_id}`,
    
    // Memory operations
    'memory_operations': (args) => {
      switch (args.operation) {
        case 'search': return `Search memories for "${args.query}"`;
        case 'add': return `Add memory: "${args.content}"`;
        case 'list': return `List recent memories`;
        case 'delete': return `Delete memory with ID ${args.memory_id}`;
        default: return `Perform ${args.operation} memory operation`;
      }
    },
    
    // Research operations
    'perplexity_research': (args) => `Research: "${args.query}"`,
    
    // Default template
    '_default': (args) => `Execute ${toolName} with parameters: ${JSON.stringify(args)}`
  };
  
  // Get the appropriate template
  const template = taskTemplates[toolName] || taskTemplates._default;
  
  // Build the task
  return template(args);
}

/**
 * Check if a tool is a Python MCP tool
 */
export function isPythonMCPTool(toolName) {
  const pythonTools = [
    'memory_operations', 'manage_features_metaobjects', 'manage_inventory_policy',
    'graphql_query', 'graphql_mutation', 'perplexity_research', 'send_review_request',
    'manage_miele_sales', 'manage_map_sales', 'manage_redirects', 'bulk_price_update',
    'update_pricing', 'upload_to_skuvault', 'manage_skuvault_kits', 'add_product_images',
    'create_open_box', 'manage_tags', 'get_product', 'add_variants_to_product',
    'create_full_product', 'update_status', 'create_product', 'get_product_native',
    'search_products', 'create_combo', 'manage_variant_links', 'update_full_product'
  ];
  
  return pythonTools.includes(toolName);
}