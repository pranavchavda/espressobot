import { initializeMCPTools, callMCPTool } from './server/tools/mcp-client.js';

async function test() {
  console.log('Testing MCP connection...');
  
  try {
    // Initialize MCP
    await initializeMCPTools();
    console.log('MCP initialized successfully');
    
    // Call search tool
    console.log('\nSearching for Mexican Altura...');
    const result = await callMCPTool('search_products', {
      query: 'Mexican Altura',
      limit: 5
    });
    
    console.log('\nFull raw result:', result);
    console.log('\nResult keys:', Object.keys(result || {}));
    console.log('\nResult entries:', Object.entries(result || {}));
    console.log('\nResult is array?', Array.isArray(result));
    console.log('\nResult toString:', result?.toString());
    
    // Check if result has the expected structure
    if (result && result.result) {
      console.log(`\nFound ${result.result.length} products:`);
      result.result.forEach(p => {
        console.log(`- ${p.title} - $${p.price} - ${p.handle}`);
      });
    } else {
      console.log('\nUnexpected result structure');
    }
    
  } catch (error) {
    console.error('Error:', error);
  }
  
  process.exit(0);
}

test();