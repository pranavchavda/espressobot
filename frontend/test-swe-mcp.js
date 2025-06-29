import { run } from '@openai/agents';
import { sweAgent } from './server/agents/swe-agent.js';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

async function testSWEWithMCP() {
  console.log('Testing SWE Agent with MCP servers...\n');
  
  try {
    // Test 1: Use Shopify Dev MCP to introspect GraphQL schema
    console.log('Test 1: Introspecting Shopify GraphQL schema for Product type');
    const result1 = await run(sweAgent, 
      "Use the Shopify Dev MCP to introspect the ProductInput type in the GraphQL schema. I want to understand what fields are available when creating a product."
    );
    console.log('Result:', result1.finalOutput || result1);
    console.log('\n---\n');
    
    // Test 2: Search Shopify documentation
    console.log('Test 2: Searching Shopify documentation');
    const result2 = await run(sweAgent,
      "Use the Shopify Dev MCP to search for documentation about productUpdate mutation. I need to know how to update product metafields."
    );
    console.log('Result:', result2.finalOutput || result2);
    console.log('\n---\n');
    
    // Test 3: Use Context7 to explore a library
    console.log('Test 3: Using Context7 to explore a library');
    const result3 = await run(sweAgent,
      "Use Context7 MCP to explore the documentation for the 'requests' Python library. I want to understand how to make authenticated API calls."
    );
    console.log('Result:', result3.finalOutput || result3);
    
  } catch (error) {
    console.error('Error:', error);
  }
}

// Run the test
testSWEWithMCP();