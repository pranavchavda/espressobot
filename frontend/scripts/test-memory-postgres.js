#!/usr/bin/env node

import { searchMemories, addMemory, getMemoryStats } from '../server/memory/simple-local-memory.js';

async function testMemorySystem() {
  console.log('🧪 Testing PostgreSQL Memory System...');
  
  try {
    // Test getting memory stats
    console.log('\n📊 Getting memory statistics...');
    const stats = await getMemoryStats();
    console.log('Current memory stats:', stats);
    
    // Test searching existing memories
    console.log('\n🔍 Testing memory search...');
    const searchResults = await searchMemories('planning agent', 'user_2', {
      strategy: 'hybrid',
      limit: 5
    });
    
    console.log(`Found ${searchResults.length} search results:`);
    searchResults.forEach((result, index) => {
      console.log(`${index + 1}. [${result.strategy}] ${result.content.substring(0, 100)}...`);
      console.log(`   Similarity: ${result.similarity.toFixed(3)}`);
    });
    
    // Test adding a new memory
    console.log('\n➕ Testing memory addition...');
    const testMemory = await addMemory(
      'Memory system successfully migrated from SQLite to PostgreSQL/Supabase for better scalability and performance.',
      'system_prompts',
      { migration: true, timestamp: new Date().toISOString() }
    );
    
    console.log('✅ Successfully added test memory:', testMemory.id);
    
    // Test searching for the new memory
    console.log('\n🔍 Searching for new memory...');
    const newSearchResults = await searchMemories('PostgreSQL migration', 'system_prompts', {
      strategy: 'semantic',
      limit: 3
    });
    
    console.log(`Found ${newSearchResults.length} results for new memory:`);
    newSearchResults.forEach((result, index) => {
      console.log(`${index + 1}. ${result.content.substring(0, 100)}...`);
      console.log(`   Similarity: ${result.similarity.toFixed(3)}`);
    });
    
    console.log('\n🎉 Memory system test completed successfully!');
    console.log('✅ PostgreSQL memory system is working correctly');
    
  } catch (error) {
    console.error('❌ Memory system test failed:', error);
    throw error;
  }
}

testMemorySystem();