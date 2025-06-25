import { Agent, MCPServerStdio } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { shopifyTools } from '../custom-tools-definitions.js';
import { extendedShopifyTools } from '../custom-tools-definitions-extended.js';
import { ENHANCED_PRODUCT_CREATION_INSTRUCTIONS } from './enhanced-instructions.js';

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
  console.warn('   Product Creation Agent will run without documentation access');
});

// Filter tools specific to product creation
const productCreationTools = [
  ...shopifyTools.filter(tool => 
    ['product_create_full'].includes(tool.name)
  ),
  ...extendedShopifyTools.filter(tool =>
    ['create_combo', 'create_open_box', 'pplx', 'upload_to_skuvault'].includes(tool.name)
  )
];

// Use enhanced instructions with domain knowledge
const productCreationInstructions = ENHANCED_PRODUCT_CREATION_INSTRUCTIONS;

// Create the Product Creation Agent
export const productCreationAgent = new Agent({
  name: 'Product_Creation_Agent',
  instructions: productCreationInstructions,
  handoffDescription: 'Hand off to Product Creation Agent for creating new products, bundles, or combo listings',
  model: 'gpt-4.1-mini',  // Using gpt-4.1-mini as it doesn't need heavy reasoning
  tools: productCreationTools,
  mcpServers: [shopifyDevMCP],  // Add MCP server for documentation access
  modelSettings: {
    temperature: 0.3,  // Lower temperature for consistent product creation
    parallelToolCalls: false,
  }
});

// Cleanup on process exit
process.on('SIGINT', async () => {
  await shopifyDevMCP.close();
  process.exit();
});

console.log(`✅ Product Creation Agent initialized with ${productCreationTools.length} specialized tools`);