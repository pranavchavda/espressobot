#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const client = new PrismaClient();

async function importData() {
  console.log('📥 Importing data to Supabase...');
  
  try {
    // Read exported data
    const exportPath = path.join(__dirname, 'sqlite-export.json');
    const data = JSON.parse(fs.readFileSync(exportPath, 'utf8'));
    
    console.log(`📊 Found ${data.totalRecords} total records to import`);
    
    // Import in dependency order
    console.log('👥 Importing users...');
    for (const user of data.users) {
      await client.users.upsert({
        where: { id: user.id },
        update: user,
        create: user
      });
    }
    console.log(`✅ Imported ${data.users.length} users`);

    console.log('💬 Importing conversations...');
    for (const conversation of data.conversations) {
      await client.conversations.upsert({
        where: { id: conversation.id },
        update: conversation,
        create: conversation
      });
    }
    console.log(`✅ Imported ${data.conversations.length} conversations`);

    console.log('📝 Importing messages...');
    for (const message of data.messages) {
      await client.messages.upsert({
        where: { id: message.id },
        update: message,
        create: message
      });
    }
    console.log(`✅ Imported ${data.messages.length} messages`);

    console.log('🧠 Importing user memories...');
    for (const memory of data.user_memories) {
      await client.user_memories.upsert({
        where: { id: memory.id },
        update: memory,
        create: memory
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
      
      await client.embedding_cache.upsert({
        where: { id: cache.id },
        update: {
          ...cache,
          embedding_data: bufferData
        },
        create: {
          ...cache,
          embedding_data: bufferData
        }
      });
    }
    console.log(`✅ Imported ${data.embedding_cache.length} embedding cache entries`);

    console.log('🎯 Importing user memory embeddings...');
    for (const embedding of data.user_memory_embeddings) {
      await client.user_memory_embeddings.upsert({
        where: { id: embedding.id },
        update: embedding,
        create: embedding
      });
    }
    console.log(`✅ Imported ${data.user_memory_embeddings.length} user memory embeddings`);

    if (data.agent_runs.length > 0) {
      console.log('🤖 Importing agent runs...');
      for (const run of data.agent_runs) {
        await client.agent_runs.upsert({
          where: { id: run.id },
          update: run,
          create: run
        });
      }
      console.log(`✅ Imported ${data.agent_runs.length} agent runs`);
    }

    if (data.conversation_summaries.length > 0) {
      console.log('📊 Importing conversation summaries...');
      for (const summary of data.conversation_summaries) {
        await client.conversation_summaries.upsert({
          where: { id: summary.id },
          update: summary,
          create: summary
        });
      }
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