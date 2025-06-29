import { runDynamicOrchestrator } from './server/dynamic-bash-orchestrator.js';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

async function testSWEWithMCP() {
  console.log('Testing SWE Agent with MCP via orchestrator handoff...\n');
  
  try {
    // Test: Ask orchestrator to create a tool that requires MCP access
    const prompt = `Please use the SWE Agent to create a new tool called 'validate_shopify_product' that:
    1. Uses the Shopify Dev MCP to introspect the ProductInput GraphQL type
    2. Creates a validation tool that checks if a product JSON matches the Shopify schema
    3. The tool should validate required fields based on the actual GraphQL schema
    4. Save it as an ad-hoc tool in the tmp/ directory`;
    
    console.log('Prompt:', prompt);
    console.log('\n--- Running Orchestrator ---\n');
    
    const result = await runDynamicOrchestrator(prompt);
    
    console.log('\n--- Result ---');
    console.log('Final output:', result.finalOutput || result);
    
  } catch (error) {
    console.error('Error:', error);
    console.error('Stack:', error.stack);
  }
}

// Run the test
testSWEWithMCP();