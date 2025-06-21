#!/usr/bin/env node
import { customToolDiscovery } from './server/custom-tool-discovery.js';

console.log('Testing Custom Tool Discovery...\n');

async function testTools() {
  try {
    // Discover tools
    console.log('1. Discovering tools...');
    const result = await customToolDiscovery.discoverTools();
    console.log(`   Found ${result.allTools.length} total tools`);
    console.log(`   Shopify tools: ${result.shopifyTools.length}`);
    console.log(`   Shopify Dev tools: ${result.shopifyDevTools.length}`);
    
    // List tool names
    console.log('\n2. Available tools:');
    result.allTools.forEach(tool => {
      console.log(`   - ${tool.name}: ${tool.description}`);
    });
    
    // Get OpenAI function format
    console.log('\n3. Getting OpenAI function format...');
    const functions = customToolDiscovery.getOpenAIFunctions();
    console.log(`   Generated ${functions.length} OpenAI function definitions`);
    
    // Test a simple tool execution (search_products)
    console.log('\n4. Testing search_products tool...');
    try {
      const searchResult = await customToolDiscovery.executeTool('search_products', {
        query: 'title:*coffee*',
        first: 5
      });
      console.log('   Search result:', JSON.stringify(searchResult, null, 2).substring(0, 200) + '...');
    } catch (err) {
      console.error('   Error executing search_products:', err.message);
      console.log('   Note: This error is expected if Shopify credentials are not configured');
    }
    
    console.log('\n✅ Custom tool discovery test completed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

// Run the test
testTools().catch(console.error);