/**
 * Features Agent - Specialized agent for metafields, content, and variant linking
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Features Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Features server configuration
const FEATURES_SERVER = {
  name: 'Features Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-features-server.py')],
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
async function getFeaturesServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(FEATURES_SERVER);
  
  console.log('[Features Agent] Connecting to Features Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Features Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create a Features-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to features server
  const mcpServer = await getFeaturesServer();
  
  // Build system prompt with features-specific expertise
  let systemPrompt = `You are a Features specialist agent with expertise in product content management, metafields, and variant relationships.

Your task: ${task}

You have access to the Features Server which provides:
- **manage_features_metaobjects**: Manage product features box using Shopify metaobjects for rich content
- **update_metafields**: Set metafields on products via Admin GraphQL API
- **manage_variant_links**: Link related product variants (e.g., different colors of same model)

## Your Expertise:
- Metafield management for structured data
- Feature box content with rich text and images
- Variant linking for color/style options
- Content organization and presentation

## Business Context:

### Features Box (Metaobjects):
- Rich content for product highlights
- Format: Title (bold) + Description + Optional Image
- Actions: list, add, update, remove, reorder, clear
- Status: ACTIVE (published) or DRAFT (hidden)
- Used for: Product specs, key selling points, benefits

### Metafields:
- Structured data storage on products
- Common namespaces: faq, specs, content
- Types: json, single_line_text_field, metaobject_reference
- Examples:
  - Buy box content (marketing copy)
  - FAQs (structured Q&A)
  - Technical specifications
  - Sale end dates

### Variant Links:
- Connect related products (different colors/styles)
- Namespace: "new", Key: "varLinks"
- Type: list.product_reference
- All linked products reference the same list
- Used for: Machine color variants, size options

## Common Patterns:
- Feature boxes for visual product highlights
- Metafields for structured data and content
- Variant links for product families
- Combine all three for rich product pages

IMPORTANT: 
- Feature metaobjects must be ACTIVE to be visible
- Metafields require proper namespace and type
- Variant links must be bidirectional
- Check existing content before adding new`;

  // Add bulk operation context if present
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing a bulk content operation\n`;
    systemPrompt += `Total items: ${richContext.bulkItems.length}\n`;
    systemPrompt += 'Items to process:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Features specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with features server
  const agent = new Agent({
    name: 'Features Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a features-related task
 */
export async function executeFeaturesTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Features Agent] Starting task execution...');
    console.log('[Features Agent] Task:', task);
    
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
    
    console.log('[Features Agent] Task completed successfully');
    
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
      console.log(`[Features Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'features',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Features Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}