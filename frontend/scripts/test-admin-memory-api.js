#!/usr/bin/env node

import { simpleLocalMemory } from '../server/memory/simple-local-memory.js';

async function testAdminMemoryAPI() {
  console.log('🧪 Testing Admin Memory API compatibility...');
  
  try {
    // Test getStats (used by admin)
    console.log('\n📊 Testing getStats()...');
    const stats = await simpleLocalMemory.getStats();
    console.log('Stats:', stats);
    
    // Test getAll without userId (used by admin)
    console.log('\n📋 Testing getAll() without userId...');
    const allMemories = await simpleLocalMemory.getAll(null, 5);
    console.log(`Found ${allMemories.length} total memories`);
    
    // Test getAll with userId (used by admin)
    console.log('\n👤 Testing getAll() with userId...');
    const userMemories = await simpleLocalMemory.getAll('user_2', 3);
    console.log(`Found ${userMemories.length} memories for user_2`);
    
    // Test search (used by admin)
    console.log('\n🔍 Testing search()...');
    const searchResults = await simpleLocalMemory.search('planning', 'user_2', 3);
    console.log(`Found ${searchResults.length} search results`);
    searchResults.forEach((result, index) => {
      console.log(`  ${index + 1}. ${result.content.substring(0, 80)}...`);
    });
    
    console.log('\n🎉 Admin Memory API compatibility test passed!');
    console.log('✅ All legacy methods are working correctly');
    
  } catch (error) {
    console.error('❌ Admin Memory API test failed:', error);
    throw error;
  }
}

testAdminMemoryAPI();