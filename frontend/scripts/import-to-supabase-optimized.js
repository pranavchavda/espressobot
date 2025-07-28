#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const client = new PrismaClient();

async function importData() {
  console.log('📥 Importing data to Supabase (optimized)...');
  
  try {
    // Read exported data
    const exportPath = path.join(__dirname, 'sqlite-export.json');
    const data = JSON.parse(fs.readFileSync(exportPath, 'utf8'));
    
    console.log(`📊 Found ${data.totalRecords} total records to import`);
    
    // Clear existing data first
    console.log('🧹 Clearing existing data...');
    await client.user_memory_embeddings.deleteMany();
    await client.embedding_cache.deleteMany();
    await client.user_memories.deleteMany();
    await client.conversation_summaries.deleteMany();
    await client.agent_runs.deleteMany();
    await client.messages.deleteMany();
    await client.conversations.deleteMany();
    await client.users.deleteMany();
    
    // Import in dependency order with batch operations
    console.log('👥 Importing users...');
    if (data.users.length > 0) {
      await client.users.createMany({
        data: data.users,
        skipDuplicates: true
      });
    }
    console.log(`✅ Imported ${data.users.length} users`);

    console.log('💬 Importing conversations...');
    if (data.conversations.length > 0) {
      await client.conversations.createMany({
        data: data.conversations,
        skipDuplicates: true
      });
    }
    console.log(`✅ Imported ${data.conversations.length} conversations`);

    console.log('📝 Importing messages in batches...');
    const batchSize = 100;
    for (let i = 0; i < data.messages.length; i += batchSize) {
      const batch = data.messages.slice(i, i + batchSize);
      await client.messages.createMany({
        data: batch,
        skipDuplicates: true
      });
      console.log(`   Imported batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(data.messages.length/batchSize)}`);
    }
    console.log(`✅ Imported ${data.messages.length} messages`);

    console.log('🧠 Importing user memories...');
    if (data.user_memories.length > 0) {
      await client.user_memories.createMany({
        data: data.user_memories,
        skipDuplicates: true
      });
    }
    console.log(`✅ Imported ${data.user_memories.length} user memories`);

    console.log('🔗 Importing embedding cache...');
    for (const cache of data.embedding_cache) {
      // Convert embedding_data from object to Buffer for PostgreSQL
      const embeddingData = cache.embedding_data;
      let bufferData;
      
      if (typeof embeddingData === 'object' && embeddingData !== null) {
        // Convert object with numeric keys to Buffer
        const values = Object.keys(embeddingData).sort((a, b) => parseInt(a) - parseInt(b)).map(key => embeddingData[key]);
        bufferData = Buffer.from(values);
      } else {
        bufferData = embeddingData;
      }
      
      await client.embedding_cache.create({
        data: {
          ...cache,
          embedding_data: bufferData
        }
      });
    }
    console.log(`✅ Imported ${data.embedding_cache.length} embedding cache entries`);

    console.log('🎯 Importing user memory embeddings...');
    if (data.user_memory_embeddings.length > 0) {
      await client.user_memory_embeddings.createMany({
        data: data.user_memory_embeddings,
        skipDuplicates: true
      });
    }
    console.log(`✅ Imported ${data.user_memory_embeddings.length} user memory embeddings`);

    if (data.agent_runs.length > 0) {
      console.log('🤖 Importing agent runs...');
      await client.agent_runs.createMany({
        data: data.agent_runs,
        skipDuplicates: true
      });
      console.log(`✅ Imported ${data.agent_runs.length} agent runs`);
    }

    if (data.conversation_summaries.length > 0) {
      console.log('📊 Importing conversation summaries...');
      await client.conversation_summaries.createMany({
        data: data.conversation_summaries,
        skipDuplicates: true
      });
      console.log(`✅ Imported ${data.conversation_summaries.length} conversation summaries`);
    }

    console.log('🎉 Import completed successfully!');
    console.log('📋 Next steps:');
    console.log('1. Test the application with the new database');
    console.log('2. Update production .env with the same Supabase DATABASE_URL');
    console.log('3. Once verified, you can safely archive the SQLite database');
    
  } catch (error) {
    console.error('❌ Import failed:', error);
    throw error;
  } finally {
    await client.$disconnect();
  }
}

importData();