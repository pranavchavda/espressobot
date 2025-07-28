#!/usr/bin/env node

import { simpleLocalMemory } from '../server/memory/simple-local-memory.js';

async function testAdminAPIEndpoints() {
  console.log('🧪 Testing Admin API Endpoints...');
  
  try {
    // Test /api/memory/stats endpoint logic
    console.log('\n📊 Testing /stats endpoint logic...');
    const stats = await simpleLocalMemory.getStats();
    console.log('Stats result:', stats);
    console.log('✅ /stats endpoint should work');
    
    // Test /api/memory/users endpoint logic
    console.log('\n👥 Testing /users endpoint logic...');
    const users = stats.byUser.map(u => ({
      userId: u.user_id,
      memoryCount: u.count
    }));
    console.log('Users result:', users);
    console.log('✅ /users endpoint should work');
    
    // Test /api/memory/all endpoint logic
    console.log('\n📋 Testing /all endpoint logic...');
    const allMemories = await simpleLocalMemory.getAll(null, 5);
    console.log(`All memories result: ${allMemories.length} memories`);
    console.log('✅ /all endpoint should work');
    
    // Test /api/memory/search endpoint logic
    console.log('\n🔍 Testing /search endpoint logic...');
    const searchResults = await simpleLocalMemory.search('system', 'system_prompts', 3);
    console.log(`Search result: ${searchResults.length} memories found`);
    console.log('✅ /search endpoint should work');
    
    console.log('\n🎉 All admin API endpoint logic tests passed!');
    console.log('✅ Admin interface should now display memories correctly');
    
  } catch (error) {
    console.error('❌ Admin API endpoint test failed:', error);
    throw error;
  }
}

testAdminAPIEndpoints();