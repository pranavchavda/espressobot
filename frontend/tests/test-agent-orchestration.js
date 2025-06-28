import { Agent, run, MCPServerStdio } from '@openai/agents';

async function testMCPIntegration() {
  console.log('Testing MCP client integration with agent orchestration...');
  
  // Ensure we have OpenAI API key - replace with proper key in production
  process.env.OPENAI_API_KEY = process.env.OPENAI_API_KEY;
  // Initialize the MCP server with stdio wrapper using npx directly with shell:true option
  console.log('Creating MCP server with stdio wrapper...');
  
  // Prepare environment with proper inheritance
  const childEnv = { ...process.env };
  childEnv.MCP_BEARER_TOKEN = process.env.MCP_BEARER_TOKEN;
  
  const mcpServer = new MCPServerStdio({
    name: 'Shopify MCP Server',
    command: 'npx',
    args: [
      '-y',
      '@pranavchavda/shopify-mcp-stdio-client@latest'
    ],
    env: childEnv,
    shell: true // Use shell to resolve path issues
  });
  
  // Connect to the MCP server
  console.log('Connecting to MCP server...');
  await mcpServer.connect();
  
  try {
    // Create the test agent with the MCP server
    console.log('Creating test agent with MCP server...');
    const testAgent = new Agent({
      name: 'ShopifyBot',
      instructions: `You are a helpful assistant that can use Shopify tools to help users find and manage products.`,
      model: process.env.EXECUTOR_MODEL || 'gpt-4o',
      mcpServers: [mcpServer]
    });
    
    // Simulate the agent orchestration flow
    console.log('\nSimulating agent orchestration flow:');
    console.log('1. User query: "Find me some coffee products"');
    
    // Execute the agent using the run function
    console.log('2. Running agent with query...');
    const userMessage = 'Find me some coffee products';
    console.log(`Sending query: "${userMessage}"`);
    
    const result = await run(testAgent, userMessage);
    
    console.log('\n3. Agent response:');
    console.log(result.finalOutput || result.output || 'No response received');
    
    console.log('\n\nAgent orchestration simulation completed successfully!');
    return 'Success';
  } catch (error) {
    console.error('Error during MCP integration test:', error);
    return 'Failed';
  } finally {
    // Close the MCP server connection
    console.log('Closing MCP server connection...');
    await mcpServer.close();
  }
}

// Run the test
testMCPIntegration()
  .then(result => console.log('Test result:', result))
  .catch(error => console.error('Test failed:', error));
