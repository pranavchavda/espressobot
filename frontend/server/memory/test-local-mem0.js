/**
 * Test script for local Mem0 OSS implementation
 */

import { memoryOperations } from './memory-operations-local.js';

async function testLocalMem0() {
  console.log('Testing Mem0 OSS Local Implementation...\n');
  
  const testUserId = 'user_test_local';
  const conversationId = 'conv_test_123';
  
  try {
    // Test 1: Add memories
    console.log('1. Adding test memories...');
    
    const memory1 = await memoryOperations.add(
      'User prefers dark roast coffee and usually orders in bulk',
      testUserId,
      { conversationId, category: 'preferences' }
    );
    console.log('Added memory 1:', memory1);
    
    const memory2 = await memoryOperations.add(
      'User manages inventory for multiple warehouse locations',
      testUserId,
      { conversationId, category: 'business' }
    );
    console.log('Added memory 2:', memory2);
    
    const memory3 = await memoryOperations.add(
      'User frequently uses bulk pricing updates for coffee products',
      testUserId,
      { conversationId, category: 'workflow' }
    );
    console.log('Added memory 3:', memory3);
    
    // Test 2: Search memories
    console.log('\n2. Searching memories...');
    
    const searchResults1 = await memoryOperations.search('coffee', testUserId);
    console.log('Search "coffee":', searchResults1);
    
    const searchResults2 = await memoryOperations.search('inventory', testUserId);
    console.log('Search "inventory":', searchResults2);
    
    const searchResults3 = await memoryOperations.search('bulk pricing', testUserId);
    console.log('Search "bulk pricing":', searchResults3);
    
    // Test 3: Get all memories
    console.log('\n3. Getting all memories...');
    const allMemories = await memoryOperations.getAll(testUserId);
    console.log(`Total memories: ${allMemories.length}`);
    allMemories.forEach((mem, idx) => {
      console.log(`  ${idx + 1}. ${mem.memory} (score: ${mem.score || 'N/A'})`);
    });
    
    // Test 4: Update a memory (if we have IDs)
    if (allMemories.length > 0) {
      console.log('\n4. Updating a memory...');
      const memoryToUpdate = allMemories[0];
      const updateResult = await memoryOperations.update(
        memoryToUpdate.id,
        'User strongly prefers dark roast coffee, especially Ethiopian varieties, and orders in bulk monthly'
      );
      console.log('Update result:', updateResult);
    }
    
    // Test 5: Memory extraction from conversation
    console.log('\n5. Testing memory extraction...');
    const conversation = `
User: Show me all the dark roast coffees you have
Assistant: I found 15 dark roast coffee products. Would you like to see them sorted by price or popularity?
User: Sort by price, and only show the Ethiopian ones
Assistant: Here are 3 Ethiopian dark roast coffees sorted by price...
User: Great, I'll take 50 bags of the Yirgacheffe. Apply my usual 15% bulk discount.
Assistant: Order created with 15% bulk discount applied.
    `;
    
    const summary = memoryOperations.extractMemorySummary(conversation, {
      conversationId: 'test_conv_456',
      agent: 'Product Search Agent'
    });
    
    const extractedMemory = await memoryOperations.add(summary, testUserId, {
      conversationId: 'test_conv_456',
      type: 'conversation_summary'
    });
    console.log('Extracted memory:', extractedMemory);
    
    // Test 6: Check persistence by searching again
    console.log('\n6. Verifying persistence...');
    const persistenceCheck = await memoryOperations.search('Ethiopian Yirgacheffe', testUserId);
    console.log('Persistence check:', persistenceCheck);
    
    // Optional: Clean up test data
    // console.log('\n7. Cleaning up test data...');
    // await memoryOperations.deleteAll(testUserId);
    // console.log('Test data cleaned up');
    
    console.log('\n✅ All tests completed successfully!');
    console.log('Mem0 OSS is working with local storage.');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

// Run tests
testLocalMem0().catch(console.error);