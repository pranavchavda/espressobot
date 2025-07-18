/**
 * Product Management Agent - Specialized agent for complex product creation and management
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Product Management Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Product Management server configuration
const PRODUCT_MANAGEMENT_SERVER = {
  name: 'Product Management Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-product-management-server.py')],
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
async function getProductManagementServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(PRODUCT_MANAGEMENT_SERVER);
  
  console.log('[Product Management Agent] Connecting to Product Management Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Product Management Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create a Product Management-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to product management server
  const mcpServer = await getProductManagementServer();
  
  // Build system prompt with product management expertise
  let systemPrompt = `You are a Product Management specialist agent with expertise in complex product creation, variants, and product combinations.

Your task: ${task}

You have access to the Product Management Server which provides:
- **add_variants_to_product**: Add multiple variants to existing products with options
- **create_full_product**: Create fully-configured products with metafields and tags
- **update_full_product**: Comprehensively update products including variants and media
- **create_combo**: Create combo products by combining two products with special pricing
- **create_open_box**: Create open box versions of existing products

## Your Expertise:
- Complex product creation with all attributes
- Variant management and option configuration
- Product bundling and combinations
- Open box and refurbished product handling
- Comprehensive product updates

## Tool Capabilities:

### create_full_product:
- Complete product setup following iDrinkCoffee conventions
- Auto-generates tags based on product type/vendor
- Sets up metafields (buy box, FAQs, specs)
- Configures inventory tracking (DENY policy)
- Publishes to all sales channels
- Supports: Espresso Machines, Grinders, Fresh Coffee, Accessories

### add_variants_to_product:
- Bulk add variants with different options
- Set individual prices and SKUs
- Configure inventory per variant
- Example: Size variants (Small, Medium, Large)

### update_full_product:
- Comprehensive updates preserving existing data
- Update basic info, variants, media, metafields
- Atomic updates using productSet mutation
- Supports local file uploads for images

### create_combo:
- Combines two products with special pricing
- Auto-generates combo images
- Flexible pricing: fixed discount, percentage, or specific
- SKU format: {prefix}-{serial}-{suffix}
- Default 10-20% discount

### create_open_box:
- Duplicates product with condition notes
- SKU format: OB-{YYMM}-{Serial}-{OriginalSKU}
- Title format: {Original} |{Serial}| - {Condition}
- Conditions: Excellent, Good, Fair, Scratch & Dent

## Business Rules:
- Products start as DRAFT unless specified
- SKUs must be unique across all products
- Variants inherit product-level settings
- Combos typically offer 10-20% discount
- Open box items track age with YYMM in SKU

IMPORTANT: 
- Use create_full_product for new products
- Use update_full_product for major changes
- Verify SKU uniqueness before creation
- Set appropriate product type for auto-tagging`;

  // Add bulk operation context if present
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing bulk product creation/updates\n`;
    systemPrompt += `Total items: ${richContext.bulkItems.length}\n`;
    systemPrompt += 'Products to process:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Product Management specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with product management server
  const agent = new Agent({
    name: 'Product Management Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a product management task
 */
export async function executeProductManagementTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Product Management Agent] Starting task execution...');
    console.log('[Product Management Agent] Task:', task);
    
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
    
    console.log('[Product Management Agent] Task completed successfully');
    
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
      console.log(`[Product Management Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'product-management',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Product Management Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}