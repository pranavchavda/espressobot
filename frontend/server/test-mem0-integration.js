/**
 * Test script for mem0 integration
 * Tests memory add, search, and retrieval functionality
 */

import { memoryOperations } from './tools/memory-tool.js';

async function testMemoryOperations() {
  console.log('🧪 Testing mem0 integration...\n');
  
  const testConversationId = 'test-conv-' + Date.now();
  
  try {
    // Test 1: Add a memory
    console.log('1️⃣ Testing memory addition...');
    const addResult = await memoryOperations.add(
      'User: I prefer coffee products from Blue Bottle, especially their espresso blends.\nAssistant: I\'ll remember your preference for Blue Bottle coffee products.',
      testConversationId,
      {
        type: 'preference',
        category: 'coffee',
        brand: 'Blue Bottle'
      }
    );
    console.log('Add result:', addResult);
    
    // Test 2: Add another memory
    console.log('\n2️⃣ Adding another memory...');
    const addResult2 = await memoryOperations.add(
      'User: I usually order products in bulk, around 50-100 units.\nAssistant: I\'ve noted your preference for bulk orders of 50-100 units.',
      testConversationId,
      {
        type: 'ordering_pattern',
        quantity: 'bulk'
      }
    );
    console.log('Add result 2:', addResult2);
    
    // Wait for indexing
    console.log('\n⏳ Waiting 2 seconds for memory indexing...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test 3: Search for coffee-related memories
    console.log('\n3️⃣ Searching for coffee memories...');
    const searchResult = await memoryOperations.search(
      'coffee',
      testConversationId,
      3
    );
    console.log('Search result:', JSON.stringify(searchResult, null, 2));
    
    // Test 4: Search for ordering patterns
    console.log('\n4️⃣ Searching for ordering patterns...');
    const searchResult2 = await memoryOperations.search(
      'How many units should I order?',
      testConversationId,
      3
    );
    console.log('Search result 2:', JSON.stringify(searchResult2, null, 2));
    
    // Test 5: Get all memories
    console.log('\n5️⃣ Getting all memories...');
    const allMemories = await memoryOperations.getAll(testConversationId);
    console.log('All memories:', JSON.stringify(allMemories, null, 2));
    
    // Test 6: Test cross-conversation isolation
    console.log('\n6️⃣ Testing conversation isolation...');
    const differentConvResult = await memoryOperations.search(
      'coffee products',
      'different-conversation-id',
      3
    );
    console.log('Different conversation search (should be empty):', differentConvResult);
    
    // Cleanup: Reset test memories
    console.log('\n🧹 Cleaning up test memories...');
    const resetResult = await memoryOperations.reset(testConversationId);
    console.log('Reset result:', resetResult);
    
    console.log('\n✅ All tests completed successfully!');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error);
    process.exit(1);
  }
}

// Run tests
console.log('Starting mem0 integration tests...\n');
testMemoryOperations().then(() => {
  console.log('\n🎉 Test suite completed!');
  process.exit(0);
}).catch(error => {
  console.error('Test suite error:', error);
  process.exit(1);
});