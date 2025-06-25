import { Agent, MCPServerStdio } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { shopifyTools } from '../custom-tools-definitions.js';
import { extendedShopifyTools } from '../custom-tools-definitions-extended.js';
import { ENHANCED_PRODUCT_UPDATE_INSTRUCTIONS } from './enhanced-instructions.js';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create Shopify Dev MCP Server for documentation and schema access
const shopifyDevMCP = new MCPServerStdio({
  name: 'Shopify Dev Docs',
  fullCommand: 'npx -y @shopify/dev-mcp',
  cacheToolsList: true  // Cache tools list for performance
});

// Initialize MCP connection (non-blocking)
shopifyDevMCP.connect().catch(err => {
  console.warn('⚠️ Shopify Dev MCP server connection failed:', err.message);
  console.warn('   Product Update Agent will run without documentation access');
});

// Filter tools specific to product updates
const productUpdateTools = [
  ...shopifyTools.filter(tool => 
    ['search_products', 'get_product', 'update_pricing', 'manage_tags', 
     'update_product_status', 'manage_inventory_policy', 'bulk_price_update'].includes(tool.name)
  ),
  ...extendedShopifyTools.filter(tool =>
    ['run_full_shopify_graphql_query', 'run_full_shopify_graphql_mutation', 
     'manage_variant_links', 'manage_map_sales'].includes(tool.name)
  )
];

// Use enhanced instructions with domain knowledge
const productUpdateInstructions = ENHANCED_PRODUCT_UPDATE_INSTRUCTIONS;

// Create the Product Update Agent
export const productUpdateAgent = new Agent({
  name: 'Product_Update_Agent',
  instructions: productUpdateInstructions,
  handoffDescription: 'Hand off to Product Update Agent for modifying existing products, bulk updates, or inventory management',
  model: 'gpt-4.1-mini',  // Using gpt-4.1-mini as it supports vision
  tools: productUpdateTools,
  mcpServers: [shopifyDevMCP],  // Add MCP server for documentation access
  modelSettings: {
    temperature: 0.3,  // Lower temperature for consistent updates
    parallelToolCalls: false,
  }
});

// Cleanup on process exit
process.on('SIGINT', async () => {
  await shopifyDevMCP.close();
  process.exit();
});

console.log(`✅ Product Update Agent initialized with ${productUpdateTools.length} specialized tools`);