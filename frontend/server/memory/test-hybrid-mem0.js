/**
 * Test script for hybrid memory implementation
 */

import { memoryOperations } from './memory-operations-hybrid.js';

async function testHybridMemory() {
  console.log('Testing Hybrid Memory Implementation...\n');
  
  const testUserId = 'user_hybrid_test';
  
  try {
    // Test 1: Add a memory
    console.log('1. Adding test memory...');
    const result = await memoryOperations.add(
      'User prefers Ethiopian coffee and orders monthly in bulk quantities',
      testUserId,
      { category: 'preferences', test: true }
    );
    console.log('Add result:', result);
    
    // Test 2: Search for the memory
    console.log('\n2. Searching for coffee memory...');
    const searchResults = await memoryOperations.search('Ethiopian coffee', testUserId);
    console.log('Search results:', searchResults);
    
    // Test 3: Get all memories
    console.log('\n3. Getting all memories...');
    const allMemories = await memoryOperations.getAll(testUserId);
    console.log(`Found ${allMemories.length} total memories`);
    
    console.log('\n✅ Hybrid memory test completed!');
    
  } catch (error) {
    console.error('❌ Hybrid memory test failed:', error);
  }
}

testHybridMemory().catch(console.error);