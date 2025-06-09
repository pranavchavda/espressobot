import { SseMCPServer } from './server/agents-new.js';

// Test the MCP client directly without requiring OpenAI API key
async function testMCPClient() {
  console.log('Testing MCP client directly...');
  
  // Initialize the MCP client
  const SHOPIFY_MCP_URL = 'https://webhook-listener-pranavchavda.replit.app/mcp';
  const SHOPIFY_ALLOWED_TOOLS = [
    'search_products',
    'get_collections',
    'get_single_product',
    'add_tags_to_product',
    'remove_tags_from_product'
  ];
  
  const mcpClient = new SseMCPServer(SHOPIFY_MCP_URL, SHOPIFY_ALLOWED_TOOLS);
  
  try {
    console.log('Connecting to MCP server...');
    await mcpClient.connect();
    
    console.log('Listing available tools...');
    const tools = await mcpClient.listTools();
    console.log('Available tools:', tools);
    
    console.log('Calling search_products tool...');
    const searchResult = await mcpClient.callTool('mcp6_search_products', {
      query: 'coffee',
      first: 3
    });
    console.log('Search result:', JSON.stringify(searchResult, null, 2));
    
    return 'MCP client test completed successfully!';
  } catch (error) {
    console.error('Error testing MCP client:', error);
    return 'MCP client test failed!';
  }
}

// Run the test
testMCPClient()
  .then(result => console.log('Test result:', result))
  .catch(error => console.error('Test error:', error));
