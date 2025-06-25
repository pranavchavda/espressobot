/**
 * Test script for native JavaScript tools
 * Run with: node test-native-tools.js
 */

import 'dotenv/config';
import { searchProductsTool } from './server/native-tools/search-products.js';
import PythonToolWrapper from './server/custom-tools/python-tool-wrapper.js';

console.log('===== NATIVE TOOLS TEST =====');
console.log('Environment check:');
console.log('- SHOPIFY_SHOP_URL:', process.env.SHOPIFY_SHOP_URL ? '✅ Set' : '❌ Not set');
console.log('- SHOPIFY_ACCESS_TOKEN:', process.env.SHOPIFY_ACCESS_TOKEN ? '✅ Set' : '❌ Not set');
console.log('- USE_NATIVE_TOOLS:', process.env.USE_NATIVE_TOOLS || 'Not set (defaults to false)');
console.log('');

// Test function to compare native vs Python tool
async function testSearchProducts() {
  const query = 'status:active';
  const args = { query, first: 3 };
  
  console.log(`Testing search_products with query: "${query}"`);
  console.log('');
  
  // Test native tool
  console.log('1. Testing NATIVE JavaScript tool:');
  console.time('Native tool execution');
  try {
    const nativeResult = await searchProductsTool.run(args);
    console.timeEnd('Native tool execution');
    console.log('Native tool result:', JSON.stringify(nativeResult, null, 2));
  } catch (error) {
    console.timeEnd('Native tool execution');
    console.error('Native tool error:', error.message);
  }
  
  console.log('\n' + '='.repeat(50) + '\n');
  
  // Test Python tool for comparison
  console.log('2. Testing PYTHON tool (for comparison):');
  console.time('Python tool execution');
  try {
    const pythonWrapper = new PythonToolWrapper();
    const pythonResult = await pythonWrapper.searchProducts(query, { first: 3 });
    console.timeEnd('Python tool execution');
    console.log('Python tool result:', JSON.stringify(pythonResult, null, 2));
  } catch (error) {
    console.timeEnd('Python tool execution');
    console.error('Python tool error:', error.message);
  }
}

// Run the test
testSearchProducts().catch(console.error);