import { customToolDiscovery } from './custom-tool-discovery.js';

console.log('🧪 Testing search_products tool\n');

// Initialize tools
await customToolDiscovery.discoverTools();

// Test cases for search_products
const testCases = [
  {
    name: "Basic search",
    args: { query: "status:active", first: 5 }
  },
  {
    name: "Search coffee products",
    args: { query: "coffee", first: 10 }
  },
  {
    name: "Search by price range",
    args: { query: "variants.price:>100 AND variants.price:<500", first: 5 }
  }
];

for (const test of testCases) {
  console.log(`\n📋 Test: ${test.name}`);
  console.log(`   Query: ${JSON.stringify(test.args)}`);
  
  try {
    const result = await customToolDiscovery.executeTool('search_products', test.args);
    
    if (result.error) {
      console.log(`   ❌ Error: ${result.error}`);
    } else if (Array.isArray(result)) {
      console.log(`   ✅ Success! Found ${result.length} products`);
      if (result.length > 0) {
        const product = result[0];
        console.log(`   First result: ${product.title || 'No title'} (${product.sku || 'No SKU'})`);
      }
    } else if (result.products && Array.isArray(result.products)) {
      console.log(`   ✅ Success! Found ${result.products.length} products`);
      if (result.products.length > 0) {
        const product = result.products[0];
        console.log(`   First result: ${product.title} (${product.sku})`);
      }
    } else {
      console.log(`   ⚠️  Unexpected result format:`, JSON.stringify(result).substring(0, 200));
    }
  } catch (error) {
    console.log(`   ❌ Execution error: ${error.message}`);
    if (error.stack) {
      console.log(`   Stack trace:`, error.stack.split('\n').slice(0, 3).join('\n'));
    }
  }
}

console.log('\n✅ Testing complete!');
process.exit(0);