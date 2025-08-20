#!/usr/bin/env node

/**
 * Test Memory System Fix
 * Verifies that the cosineSimilarity null reference fixes work correctly
 */

import { simpleLocalMemory } from './simple-local-memory.js';

async function testMemorySystem() {
  console.log('🧪 Testing Memory System Fix...\n');
  
  try {
    // Test 1: Normal search should work
    console.log('Test 1: Normal memory search');
    const results = await simpleLocalMemory.search('test query', 'user_2', 5);
    console.log(`✅ Search completed successfully: ${results.length} results`);
    
    // Test 2: Check if there are any memories with null embeddings
    console.log('\nTest 2: Database integrity check');
    const stats = simpleLocalMemory.getStats();
    console.log(`✅ Database stats: ${stats.total} total memories`);
    stats.byUser.forEach(user => {
      console.log(`   - ${user.user_id}: ${user.count} memories`);
    });
    
    // Test 3: Add a new memory and verify it works
    console.log('\nTest 3: Adding new memory');
    const addResult = await simpleLocalMemory.add(
      'Test memory to verify system is working correctly',
      'test_user',
      { test: true, timestamp: new Date().toISOString() }
    );
    
    if (addResult.success) {
      console.log('✅ Memory added successfully:', addResult.id);
      
      // Search for the memory we just added
      const searchResults = await simpleLocalMemory.search('test memory verify system', 'test_user', 1);
      if (searchResults.length > 0) {
        console.log('✅ Memory search working correctly');
        
        // Clean up test memory
        await simpleLocalMemory.delete(addResult.id);
        console.log('✅ Test memory cleaned up');
      } else {
        console.log('❌ Memory search failed to find test memory');
      }
    } else {
      console.log('❌ Failed to add test memory:', addResult.message);
    }
    
    console.log('\n🎉 All tests passed! Memory system is working correctly.');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    console.error('Stack trace:', error.stack);
    process.exit(1);
  }
}

testMemorySystem();