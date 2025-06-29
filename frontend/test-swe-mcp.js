import { run } from '@openai/agents';
import { sweAgent } from './server/agents/swe-agent.js';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

async function testSWEWithMCP() {
  console.log('Testing SWE Agent with MCP servers...\n');
  
  try {
    // Test 1: Create a tool using Shopify API documentation
    console.log('Test 1: Create a tool using Shopify Dev MCP');
    console.log('Prompt: Use the Shopify Dev MCP to look up the productCreate mutation and create a tool that validates product input');
    
    const result1 = await run(sweAgent, 
      `Use the Shopify Dev MCP to introspect the ProductInput type schema, then create an ad-hoc tool called 'validate_product_input' that validates a product's data before creation. The tool should check required fields based on the actual GraphQL schema.`
    );
    console.log('Result:', result1.finalOutput || result1);
    console.log('\n---\n');
    
    // Test 2: Use Context7 to explore a library
    console.log('Test 2: Use Context7 MCP to explore a library');
    console.log('Prompt: Use Context7 to explore the requests library and create a simple HTTP client tool');
    
    const result2 = await run(sweAgent,
      `Use Context7 to explore the Python requests library documentation, then create an ad-hoc tool called 'simple_http_client' that makes GET and POST requests with proper error handling.`
    );
    console.log('Result:', result2.finalOutput || result2);
    
  } catch (error) {
    console.error('Error:', error);
    console.error('Stack:', error.stack);
  }
}

// Run the test
testSWEWithMCP();