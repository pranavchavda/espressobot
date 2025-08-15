/**
 * Test Tool Result Cache functionality
 * Tests caching and retrieval of tool results
 */

import { toolResultCache } from '../memory/tool-result-cache.js';

async function testToolCache() {
  console.log('=== Testing Tool Result Cache ===\n');
  
  const testConversationId = 'test-conv-' + Date.now();
  
  // Test 1: Store a get_product result
  console.log('Test 1: Storing get_product result');
  const productData = {
    id: 'gid://shopify/Product/123456',
    title: 'Test Product',
    handle: 'test-product',
    variants: [{
      id: 'gid://shopify/ProductVariant/789',
      sku: 'TEST-123',
      price: '49.99',
      compareAtPrice: '59.99'
    }]
  };
  
  const storeResult = await toolResultCache.store(
    testConversationId,
    'get_product',
    { identifier: 'TEST-123' },
    productData,
    { source: 'test' }
  );
  
  console.log('Store result:', storeResult ? 'Success' : 'Failed');
  
  // Test 2: Search for the cached result
  console.log('\nTest 2: Searching for cached product data');
  const searchResults = await toolResultCache.search(
    testConversationId,
    'product data for SKU TEST-123',
    { toolName: 'get_product', similarityThreshold: 0.5 }
  );
  
  console.log('Search results:', searchResults.length);
  if (searchResults.length > 0) {
    console.log('First result similarity:', searchResults[0].similarity);
    console.log('Cached data matches:', 
      searchResults[0].output_result.variants[0].sku === 'TEST-123'
    );
  }
  
  // Test 3: Exact match retrieval
  console.log('\nTest 3: Testing exact match retrieval');
  const exactMatch = await toolResultCache.getExactMatch(
    testConversationId,
    'get_product',
    { identifier: 'TEST-123' }
  );
  
  console.log('Exact match found:', exactMatch !== null);
  
  // Test 4: Store another tool result
  console.log('\nTest 4: Storing update_pricing result');
  await toolResultCache.store(
    testConversationId,
    'update_pricing',
    { 
      product_id: 'gid://shopify/Product/123456',
      variant_id: 'gid://shopify/ProductVariant/789',
      price: 39.99
    },
    { success: true, message: 'Price updated' }
  );
  
  // Test 5: Get statistics
  console.log('\nTest 5: Getting cache statistics');
  const stats = await toolResultCache.getStats(testConversationId);
  console.log('Cache stats:', stats);
  
  // Test 6: Semantic search across multiple results
  console.log('\nTest 6: Semantic search for "price update TEST-123"');
  const priceSearchResults = await toolResultCache.search(
    testConversationId,
    'price update TEST-123',
    { similarityThreshold: 0.4 }  // Lower threshold to catch both results
  );
  
  console.log('Found results:', priceSearchResults.length);
  priceSearchResults.forEach((result, i) => {
    console.log(`  ${i+1}. ${result.tool_name} (similarity: ${result.similarity.toFixed(3)})`);
  });
  
  // Test 7: Clear conversation cache
  console.log('\nTest 7: Clearing conversation cache');
  const cleared = await toolResultCache.clearConversation(testConversationId);
  console.log('Cleared entries:', cleared);
  
  // Verify cache is empty
  const afterClear = await toolResultCache.getStats(testConversationId);
  console.log('Cache after clear:', afterClear.total_cached === 0 ? 'Empty' : 'Not empty');
  
  console.log('\n=== All tests completed ===');
}

// Run tests
testToolCache().catch(console.error);