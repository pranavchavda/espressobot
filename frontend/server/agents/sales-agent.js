/**
 * Sales Agent - Specialized agent for MAP sales and promotional campaigns
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Sales Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Sales server configuration
const SALES_SERVER = {
  name: 'Sales Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-sales-server.py')],
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
async function getSalesServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(SALES_SERVER);
  
  console.log('[Sales Agent] Connecting to Sales Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Sales Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create a Sales-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to sales server
  const mcpServer = await getSalesServer();
  
  // Build system prompt with sales-specific expertise
  let systemPrompt = `You are a Sales specialist agent with expertise in MAP (Minimum Advertised Price) compliance and promotional campaign management.

Your task: ${task}

You have access to the Sales Server which provides:
- **manage_miele_sales**: Manage MAP sales for Miele products based on approved windows
- **manage_map_sales**: Apply or revert Breville MAP sales using the 2025 enhanced calendar

## Your Expertise:
- MAP compliance for premium brands (Miele, Breville)
- Sale window management based on manufacturer agreements
- Price application and reversion for promotional periods
- Understanding brand-specific pricing rules and restrictions

## Business Context:

### MAP Sales Overview:
- MAP (Minimum Advertised Price) sets the lowest price we can advertise
- Sales must comply with manufacturer-approved windows
- Some products may be excluded from certain sales
- Sales typically run 7-14 days

### Miele Sales:
- Products: CM5310, CM6160, CM6360, CM7750
- Sales use MAP-approved prices only
- Tags applied: miele-sale, sale-YYYY-MM
- Compare-at price shows original MSRP
- Check current/upcoming sales before applying

### Breville Sales:
- Uses 2025 enhanced sales calendar
- Actions: check, apply, revert, summary
- Supports dry_run for preview
- Date-based operations for scheduled sales

### Sale Process:
1. Check active sales for the date
2. Apply sale prices with appropriate tags
3. Set compare-at price to show discount
4. Revert prices after sale ends

IMPORTANT: 
- Always check for active sales before applying
- Use dry_run=true to preview changes
- Sales are date-sensitive - verify dates
- Some products excluded from certain sales
- Track sales with monthly tags (sale-YYYY-MM)`;

  // Add any additional context
  if (richContext?.saleDate) {
    systemPrompt += `\n\n### Current Sale Context:\n`;
    systemPrompt += `Sale Date: ${richContext.saleDate}\n`;
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Sales specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with sales server
  const agent = new Agent({
    name: 'Sales Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a sales-related task
 */
export async function executeSalesTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Sales Agent] Starting task execution...');
    console.log('[Sales Agent] Task:', task);
    
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
    
    console.log('[Sales Agent] Task completed successfully');
    
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
      console.log(`[Sales Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'sales',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Sales Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}