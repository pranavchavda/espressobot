import { Agent, MCPServerStdio, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

async function testDirectMCP() {
  console.log('Testing direct MCP integration with OpenAI agents SDK...\n');

  // Create Shopify Dev MCP Server
  const shopifyDevMCP = new MCPServerStdio({
    name: 'Shopify Dev Docs',
    fullCommand: 'npx -y @shopify/dev-mcp',
    cacheToolsList: true
  });

  try {
    // Connect to the MCP server
    console.log('Connecting to Shopify Dev MCP server...');
    await shopifyDevMCP.connect();
    console.log('✅ Connected successfully!\n');

    // Create a simple test agent
    const testAgent = new Agent({
      name: 'MCP_Test_Agent',
      instructions: 'You are a test agent with access to Shopify documentation. Use the available tools to answer questions.',
      model: 'gpt-4-turbo-preview',
      mcpServers: [shopifyDevMCP]
    });

    // Test 1: List available tools
    console.log('Test 1: Search documentation');
    const result1 = await run(testAgent, 'Search the Shopify docs for information about product metafields');
    console.log('Result:', result1.finalOutput, '\n');

    // Test 2: Introspect schema
    console.log('Test 2: Introspect GraphQL schema');
    const result2 = await run(testAgent, 'What fields are available on the Product type in the GraphQL schema?');
    console.log('Result:', result2.finalOutput, '\n');

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    // Clean up
    console.log('Closing MCP connection...');
    await shopifyDevMCP.close();
    console.log('✅ Connection closed');
  }
}

// Run the test
testDirectMCP().catch(console.error);