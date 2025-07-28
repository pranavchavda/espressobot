#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';

const client = new PrismaClient();

async function examineFragments() {
  console.log('🔍 Examining fragment data structure...');
  
  try {
    // Get a sample of memories to see their structure
    const memories = await client.memories.findMany({
      take: 10,
      orderBy: { created_at: 'desc' }
    });
    
    console.log(`\n📊 Found ${memories.length} recent memories:`);
    
    memories.forEach((memory, index) => {
      console.log(`\n${index + 1}. Memory ID: ${memory.id}`);
      console.log(`   User: ${memory.user_id}`);
      console.log(`   Content length: ${memory.content.length} chars`);
      console.log(`   Content preview: "${memory.content.substring(0, 100)}..."`);
      console.log(`   Metadata: ${memory.metadata || 'null'}`);
      console.log(`   Has embedding: ${memory.embedding ? 'Yes' : 'No'}`);
      console.log(`   Created: ${memory.created_at}`);
    });
    
    // Look for patterns in metadata
    console.log('\n🏷️  Analyzing metadata patterns...');
    const memoriesWithMetadata = await client.memories.findMany({
      where: {
        metadata: { not: null }
      },
      take: 5
    });
    
    console.log(`Found ${memoriesWithMetadata.length} memories with metadata:`);
    memoriesWithMetadata.forEach((memory, index) => {
      console.log(`\n${index + 1}. ID: ${memory.id}`);
      console.log(`   Metadata: ${memory.metadata}`);
      try {
        const parsed = JSON.parse(memory.metadata);
        console.log(`   Parsed metadata:`, parsed);
      } catch (e) {
        console.log(`   Metadata is not JSON: ${memory.metadata}`);
      }
    });
    
    // Check for different user types
    console.log('\n👥 User distribution:');
    const userStats = await client.memories.groupBy({
      by: ['user_id'],
      _count: { user_id: true }
    });
    
    userStats.forEach(stat => {
      console.log(`   ${stat.user_id}: ${stat._count.user_id} memories`);
    });
    
    // Look for specific patterns that might indicate fragments
    const possibleFragments = await client.memories.findMany({
      where: {
        OR: [
          { content: { contains: 'fragment', mode: 'insensitive' } },
          { content: { contains: 'prompt', mode: 'insensitive' } },
          { user_id: 'system_prompts' }
        ]
      },
      take: 5
    });
    
    console.log(`\n🧩 Found ${possibleFragments.length} possible fragments:`);
    possibleFragments.forEach((memory, index) => {
      console.log(`\n${index + 1}. ID: ${memory.id}`);
      console.log(`   User: ${memory.user_id}`);
      console.log(`   Content: "${memory.content.substring(0, 150)}..."`);
    });
    
  } catch (error) {
    console.error('❌ Error examining fragments:', error);
  } finally {
    await client.$disconnect();
  }
}

examineFragments();