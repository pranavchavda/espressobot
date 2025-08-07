/**
 * Integrations Agent - Specialized agent for external systems integration
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Integrations Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Integrations server configuration
const INTEGRATIONS_SERVER = {
  name: 'Integrations Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-integrations-server.py')],
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
async function getIntegrationsServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(INTEGRATIONS_SERVER);
  
  console.log('[Integrations Agent] Connecting to Integrations Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Integrations Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create an Integrations-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to integrations server
  const mcpServer = await getIntegrationsServer();
  
  // Build system prompt with integrations-specific expertise
  let systemPrompt = `You are an Integrations specialist agent with expertise in connecting Shopify with external systems and services.

Your task: ${task}

You have access to the Integrations Server which provides:
- **upload_to_skuvault**: Upload products from Shopify to SkuVault inventory management
- **manage_skuvault_kits**: Create, update, and manage product kits in SkuVault
- **send_review_request**: Send Yotpo review request emails to customers
- **perplexity_research**: Research products, competitors, and industry information using Perplexity AI

## Your Expertise:
- System integration and data synchronization
- Inventory management systems (SkuVault)
- Review platform integration (Yotpo)
- Market research and competitive analysis
- API authentication and error handling

## Tool Details:

### SkuVault Integration:
- **upload_to_skuvault**: Sync product data from Shopify
  - Fetches product by SKU from Shopify
  - Maps fields: title, vendor, price, cost, images
  - Supports batch uploads and dry run mode
  - Use for: Initial setup, new products, updates

- **manage_skuvault_kits**: Bundle management
  - Create kits with components (e.g., "SKU1:1,SKU2:1")
  - Actions: create, update, remove, get, list
  - Kit SKUs typically use COMBO- or BUNDLE- prefix
  - Use for: Machine+grinder combos, starter packs

### Yotpo Reviews:
- Send review requests 7-14 days after delivery
- Requires Yotpo Product ID (numeric, not SKU)
- Supports single or bulk recipients
- Spam filter option (max 5 emails per 30 days)
- Tracks valid/rejected emails

### Perplexity Research:
- Real-time web research with citations
- Models: sonar (fast), sonar-pro (detailed)
- Use cases:
  - Competitor pricing research
  - Product specifications lookup
  - Industry trends and news
  - Technical troubleshooting

## Business Context:
- SkuVault manages physical inventory
- Yotpo drives social proof through reviews
- Research informs pricing and product decisions
- Integration accuracy is critical for operations

IMPORTANT: 
- Verify SKUs exist before syncing
- Check API credentials are configured
- Use dry_run for testing operations
- Research before setting prices`;

  // Add bulk operation context if present
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing a bulk sync operation\n`;
    systemPrompt += `Total items: ${richContext.bulkItems.length}\n`;
    systemPrompt += 'Items to sync:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Integrations specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with integrations server
  const agent = new Agent({
    name: 'Integrations Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    // toolUseBehavior removed to prevent loops
  });

  return agent;
}

/**
 * Execute an integrations-related task
 */
export async function executeIntegrationsTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Integrations Agent] Starting task execution...');
    console.log('[Integrations Agent] Task:', task);
    
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
    
    console.log('[Integrations Agent] Task completed successfully');
    
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
      console.log(`[Integrations Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'integrations',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Integrations Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}