import { z } from 'zod';
import { Agent, run, MCPServerStdio } from '@openai/agents';
import { webSearchTool } from '@openai/agents-openai';

// --- Shopify MCP server configuration ---
// Ensure OpenAI API key is set
process.env.OPENAI_API_KEY = process.env.OPENAI_API_KEY;
// Define the Shopify MCP server configuration using MCPServerStdio
// Prepare environment with proper inheritance
const childEnv = { ...process.env };
childEnv.MCP_BEARER_TOKEN = process.env.MCP_BEARER_TOKEN;

// Create the MCP server with shell:true to resolve path issues
const shopifyMCPServer = new MCPServerStdio({
  name: 'Shopify MCP Server',
  command: 'npx',
  args: [
    '-y',
    '@pranavchavda/shopify-mcp-stdio-client@latest'
  ],
  env: childEnv,
  shell: true // Use shell to resolve path issues
});

// Initialize the MCP server connection
async function initializeMCPServer() {
  try {
    await shopifyMCPServer.connect();
    console.log('Successfully connected to Shopify MCP server');
    return true;
  } catch (error) {
    console.error('Failed to connect to Shopify MCP server:', error);
    return false;
  }
}

// Close the MCP server connection
async function closeMCPServer() {
  try {
    await shopifyMCPServer.close();
    console.log('Successfully closed Shopify MCP server connection');
    return true;
  } catch (error) {
    console.error('Failed to close Shopify MCP server connection:', error);
    return false;
  }
}

// Log when initializing for debugging purposes
console.log('Initialized Shopify MCP server with stdio wrapper');

// List of allowed Shopify tools for reference
const SHOPIFY_ALLOWED_TOOLS = [
  {
    name: 'mcp6_search_products',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query string' },
        first: { type: 'integer', description: 'Number of products to fetch', default: 10 }
      },
      required: ['query']
    }
  },
  {
    name: 'mcp6_get_single_product',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: 'Product ID to retrieve' }
      },
      required: ['id']
    }
  },
  {
    name: 'mcp6_get_collections',
    inputSchema: {
      type: 'object',
      properties: {
        first: { type: 'number', description: 'Number of collections to retrieve', default: 10 }
      }
    }
  },
  {
    name: 'mcp6_add_product_to_collection',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'string', description: 'Product ID to add to collection' },
        collectionId: { type: 'string', description: 'Collection ID to add product to' }
      },
      required: ['productId', 'collectionId']
    }
  },
  {
    name: 'mcp6_set_metafield',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'string', description: 'Product ID to set metafield on' },
        namespace: { type: 'string', description: 'Metafield namespace' },
        key: { type: 'string', description: 'Metafield key' },
        value: { type: 'string', description: 'Metafield value' },
        type: { type: 'string', description: 'Metafield type (e.g., single_line_text_field)' }
      },
      required: ['productId', 'namespace', 'key', 'value', 'type']
    }
  },
  {
    name: 'mcp6_add_tags_to_product',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: 'The ID of a resource to add tags to' },
        tags: { type: 'array', items: { type: 'string' }, description: 'A list of tags to add to the resource' }
      },
      required: ['id', 'tags']
    }
  },
  {
    name: 'mcp6_remove_tags_from_product',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: 'The ID of a resource to remove tags from' },
        tags: { type: 'array', items: { type: 'string' }, description: 'A list of tags to remove from the resource' }
      },
      required: ['id', 'tags']
    }
  },
  {
    name: 'mcp6_update_pricing',
    inputSchema: {
      type: 'object',
      properties: {
        productId: { type: 'string', description: 'Product ID (with or without gid:// prefix)' },
        id: { type: 'string', description: 'Variant ID to update' },
        price: { type: 'string', description: 'New price for the variant' },
        compareAtPrice: { type: 'string', description: 'Optional compare at price (sale price)' },
        cost: { type: 'string', description: 'Optional cost for inventory item' }
      },
      required: ['productId', 'id']
    }
  }
];

// We don't need a custom MCP server class anymore as we're using the built-in MCPServer from @openai/agents

// Tool name references for convenience
const SHOPIFY_TOOL_NAMES = [
  'mcp6_remove_tags_from_product',
  'mcp6_add_tags_to_product',
  'mcp6_run_full_shopify_graphql_mutation',
  'mcp6_run_full_shopify_graphql_query',
  'mcp6_upload_to_sku_vault',
  'mcp6_update_pricing',
  'mcp6_product_create_full',
  'mcp6_add_product_to_collection',
  'mcp6_get_collections',
  'mcp6_set_metafield',
  'mcp6_variant_create',
  'mcp6_product_create_test',
  'mcp6_get_single_product',
  'mcp6_search_products'
];

// --- Shopify Executor Agent ---
export const shopifyExecutorAgent = new Agent({
  name: 'ShopifyExecutorAgentInternal',
  model: process.env.EXECUTOR_MODEL || 'gpt-4.1-mini',
  instructions: `You are a Shopify operations specialist. Input: JSONRPC style call with 'name' (tool name) and 'arguments'. Use exact tool names from the MCP server. Output must be the raw JSON response.`,
  mcpServers: [shopifyMCPServer]
});
export const ShopifyToolExecutor = shopifyExecutorAgent.asTool(
  'ShopifyToolExecutor',
  'Invokes a Shopify MCP server tool; input { name, arguments } and returns the tool output.'
);

// --- Web Search Executor Agent ---
export const webSearchExecutorAgent = new Agent({
  name: 'WebSearchExecutorAgentInternal',
  model: process.env.EXECUTOR_MODEL || 'gpt-4.1-mini',
  instructions: 'You are a web search specialist. Input { query }; return raw search results JSON.',
  tools: [ webSearchTool() ],
  tool_use_behavior: 'stop_on_first_tool'
});
export const WebSearchToolExecutor = webSearchExecutorAgent.asTool(
  'WebSearchToolExecutor',
  'Performs web search; input { query } and returns results.'
);

// --- Planner Agent ---
export const plannerAgent = new Agent({
  name: 'PlannerAgent',
  model: process.env.PLANNER_AGENT_MODEL || 'gpt-4.1-mini',
  instructions: `You are an expert planner.
Available tools: ${SHOPIFY_TOOL_NAMES.join(', ')}, ${WebSearchToolExecutor.name}.
Break user queries into tasks: { id, agent_tool_name, args, description }.
Use ShopifyToolExecutor for product-like queries first; otherwise use WebSearchToolExecutor.
Respond JSON: { tasks: [ ... ] }.`,
  mcpServers: [shopifyMCPServer]
});
export const plan = plannerAgent.asTool(
  'plan',
  'Break a user query into a plan of tasks; input { originalQuery, conversationHistory }.'
);

// --- Task Dispatcher Agent ---
export const taskDispatcherAgent = new Agent({
  name: 'TaskDispatcherAgent',
  model: process.env.DISPATCHER_MODEL || 'gpt-4o-mini',
  instructions: `You are a Task Dispatcher.
Input: array of tasks { id, agent_tool_name, args, description }.
Execute each tool and return [{ task_id, result, success }].`,
  tools: [ WebSearchToolExecutor, ShopifyToolExecutor ]
});
export const dispatch = taskDispatcherAgent.asTool(
  'dispatch',
  'Execute a plan of tasks; input array of tasks and return results.'
);

// --- Synthesizer Agent ---
export const synthesizerAgent = new Agent({
  name: 'SynthesizerAgent',
  model: process.env.SYNTHESIZER_MODEL || 'gpt-4o-mini',
  tools: [ dispatch ],
  instructions: `You are EspressoBot. Compose a final human-friendly response using the original query, history, and dispatch results.
Output natural language text only.`,
  mcpServers: [shopifyMCPServer] // Add MCP server to ensure proper tool access
});

// Export the MCP initialization and closing functions for use in orchestrator
export { initializeMCPServer, closeMCPServer };
