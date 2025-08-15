/**
 * Shopify Orders Agent
 * Specializes in order analytics, sales reports, and business intelligence
 */

import { Agent, run } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import { z } from 'zod';
import { readFile } from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import logger from '../logger.js';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Shopify Orders Agent');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Orders MCP server configuration
const ORDERS_SERVER = {
  name: 'Orders Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-orders-server.py')],
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
async function getOrdersServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(ORDERS_SERVER);
  
  console.log('[Shopify Orders Agent] Connecting to Orders Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Shopify Orders Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

// Create specialized task execution function
async function executeOrdersTask(task, conversationId, options = {}) {
  try {
    console.log('[Shopify Orders Agent] Starting task execution...');
    console.log('[Shopify Orders Agent] Task:', task);
    
    // Connect to orders server
    const ordersServer = await getOrdersServer();
    
    // Create the orders agent with specialized prompt
    const agent = new Agent({
      name: 'Shopify Orders Agent',
      model: 'gpt-4o',
      instructions: `You are a Shopify Orders Analytics specialist for iDrinkCoffee.com.

## Your Expertise:
- Order analytics and sales reporting
- Revenue analysis and financial metrics
- Customer purchase behavior
- Product performance tracking
- Business intelligence insights

## Available Tools:
- analytics_order_summary: Get order analytics including count, revenue, and product performance for a date range
- analytics_daily_sales: Get today's or recent daily sales summary quickly
- analytics_revenue_report: Generate detailed revenue reports with breakdowns by period, channel, and customer type

## Key Context:
- iDrinkCoffee.com processes 100-200+ orders daily
- High-volume coffee equipment retailer
- Focus on actionable insights and trends
- Currency: USD

## Response Guidelines:
1. **For daily sales**: Provide clear summary with comparisons
2. **For analytics**: Focus on actionable insights
3. **For reports**: Structure data clearly with key metrics first
4. **For trends**: Highlight significant changes and patterns

## Performance Considerations:
- The tools handle pagination automatically
- Large date ranges may take longer to process
- Daily data is most current; historical data may be cached

Current date: ${new Date().toLocaleDateString('en-US', { 
  weekday: 'long', 
  year: 'numeric', 
  month: 'long', 
  day: 'numeric' 
})}

IMPORTANT: Always provide insights along with raw data. Help the user understand what the numbers mean for their business.`,
      temperature: 0.7,
      mcpServers: [ordersServer]
    });

    // Execute the task with proper options
    const result = await run(agent, task, {
      maxTurns: 10,
      onChunk: (chunk) => {
        // Optional: handle streaming if needed
        if (chunk.type === 'text') {
          console.log('[Shopify Orders Agent] Text:', chunk.text);
        }
      }
    });
    
    // Extract meaningful output from result
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
    
    // Log execution summary
    console.log('[Shopify Orders Agent] Task completed');
    
    return {
      success: true,
      output: finalOutput
    };
    
  } catch (error) {
    console.error('[Shopify Orders Agent] Error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Export the function for use by orchestrator
export { executeOrdersTask };

// Export default agent info for MCP server manager
export default {
  name: 'Shopify Orders Agent',
  description: 'Specialized agent for Shopify order analytics and sales reporting',
  capabilities: [
    'Daily sales summaries',
    'Order analytics with product breakdowns',
    'Revenue reports and financial analysis',
    'Period comparisons (WoW, MoM, YoY)',
    'Customer behavior insights',
    'Channel performance tracking'
  ],
  tools: [
    'analytics_daily_sales',
    'analytics_order_summary',
    'analytics_revenue_report'
  ]
};