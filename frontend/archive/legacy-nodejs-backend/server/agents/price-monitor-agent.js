/**
 * Price Monitor Agent - Specialized agent for price monitoring operations
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Price Monitor Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Price Monitor server configuration
const PRICE_MONITOR_SERVER = {
  name: 'Price Monitor Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-price-monitor-server.py')],
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
async function getPriceMonitorServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(PRICE_MONITOR_SERVER);
  
  console.log('[Price Monitor Agent] Connecting to Price Monitor Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Price Monitor Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create Price Monitor Agent instance
 */
export async function createPriceMonitorAgent() {
  const server = await getPriceMonitorServer();
  
  // Build specialized instructions for price monitoring
  const instructions = buildAgentInstructions({
    role: 'Price Monitor Agent',
    domain: 'Price Monitoring & MAP Compliance',
    expertise: [
      'Price monitoring and MAP violation detection',
      'Competitor price tracking and analysis',
      'Product matching between iDC and competitors',
      'Shopify product synchronization',
      'Alert generation and management',
      'Competitive intelligence operations'
    ],
    responsibilities: [
      'Monitor competitor pricing for MAP violations',
      'Sync product data from Shopify to price monitor',
      'Trigger competitor scraping operations',
      'Match products between iDC and competitor catalogs',
      'Generate and manage price alerts',
      'Provide insights on competitive pricing landscape'
    ],
    guidelines: [
      'Always check operation status before starting new operations',
      'Use dry_run mode first when generating alerts to preview results',
      'Sync iDC products before matching to ensure current data',
      'Filter alerts by severity to prioritize serious violations',
      'Monitor scraping job status for completion',
      'Provide clear summaries of operation results'
    ],
    tools_context: 'Use price monitoring tools to execute complete workflows from data sync to alert generation',
    current_datetime: new Date().toISOString()
  });

  const agent = new Agent({
    name: 'Price Monitor Agent',
    model: 'gpt-4o-mini',
    instructions: instructions,
    mcpServers: [server],
    debug: false
  });

  console.log('[Price Monitor Agent] Created successfully');
  return agent;
}

/**
 * Create agent for task execution
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Get server connection
  const mcpServer = await getPriceMonitorServer();
  
  // Build specialized instructions
  const instructions = `You are a Price Monitor specialist agent with expertise in MAP compliance and competitive intelligence for EspressoBot.

Your task: ${task}

You have access to the Price Monitor Server which provides:
- **price_monitor_alerts_data**: Access price alerts with comprehensive filtering and sorting

## Your Expertise:
- MAP (Minimum Advertised Price) violation detection
- Competitor price tracking and analysis
- Product matching between iDC and competitors
- Shopify product synchronization workflows
- Alert generation and management
- Competitive intelligence operations

## Price Monitoring Operations:

### Available Tools:
- **price_monitor_alerts_data**: Get filtered alerts data
  - Filter by status (active, resolved, dismissed)
  - Filter by severity (minor, moderate, severe)
  - Filter by brand or competitor
  - Sort by recency, severity, or impact

### Key Features:
- Real-time MAP violation detection
- Severity-based alert classification
- Comprehensive product and pricing data
- Multi-channel competitor monitoring
- Automated compliance tracking

## Best Practices:
- Always prioritize severe violations that impact revenue
- Filter by status="active" to focus on unresolved issues
- Sort by "impact" to see most costly violations first
- Include detailed product information (SKU, brand, prices, competitor URLs)
- **CRITICAL: Manually verify product matches** - The matching algorithm may incorrectly match different products (e.g., ECM Mechanika vs ECM Synchronika). Always compare:
  - Product titles and model numbers
  - Key specifications and features
  - Actual product similarity beyond brand name
  - Alert the user if matches seem incorrect
- Provide actionable insights for pricing decisions with verified matches only

## Response Format:
When presenting MAP violations, include for each violation:
- **iDC Product**: Title, SKU, Vendor, Current Price, MAP Price, Product Type
- **Competitor**: Name, Product Title, Price, URL to product page (if available)
- **Violation Details**: Amount below MAP, percentage violation, severity
- **Product Match Verification**: Your assessment of whether the products actually match
- **Links**: Always include iDC product URL; include competitor URL (either direct product link or generated search URL) to help users find and verify the competitor product

## Task Context:
${JSON.stringify(richContext, null, 2)}

Execute the price monitoring operations to complete this task efficiently and provide detailed, verifiable results.`;

  // Debug context size and content
  console.log('[Price Monitor Agent] Instructions length:', instructions.length);
  console.log('[Price Monitor Agent] Rich context size:', JSON.stringify(richContext).length);
  console.log('[Price Monitor Agent] FULL INSTRUCTIONS:');
  console.log('='.repeat(80));
  console.log(instructions);
  console.log('='.repeat(80));
  console.log('[Price Monitor Agent] RICH CONTEXT:');
  console.log(JSON.stringify(richContext, null, 2));
  
  // Create agent with price monitor server
  const agent = new Agent({
    name: 'Price Monitor Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    // toolUseBehavior removed to prevent loops
  });
  
  return agent;
}

/**
 * Execute a price monitor task
 */
export async function executePriceMonitorTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Price Monitor Agent] Starting task execution...');
    console.log('[Price Monitor Agent] Task:', task);
    
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
    
    console.log('[Price Monitor Agent] Task completed successfully');
    
    return {
      success: true,
      output: result.output || 'Price monitoring task completed successfully.',
      agent: 'price-monitor'
    };
    
  } catch (error) {
    console.error('[Price Monitor Agent] Task execution error:', error);
    return {
      success: false,
      error: error.message,
      agent: 'price-monitor'
    };
  }
}

// Export for use in orchestrator
export { getPriceMonitorServer };