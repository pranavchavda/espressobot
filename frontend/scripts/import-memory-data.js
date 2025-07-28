#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const client = new PrismaClient();

async function importMemoryData() {
  console.log('📥 Importing memory data to Supabase...');
  
  try {
    // Read exported data
    const exportPath = path.join(__dirname, 'memory-export.json');
    const data = JSON.parse(fs.readFileSync(exportPath, 'utf8'));
    
    console.log(`📊 Found ${data.totalRecords} total records to import`);
    
    // Import memories
    console.log('🧠 Importing memories...');
    for (const memory of data.memories) {
      // Convert embedding from SQLite format to PostgreSQL Buffer
      let embeddingBuffer = null;
      if (memory.embedding) {
        if (typeof memory.embedding === 'object') {
          // Convert object with numeric keys to Buffer
          const values = Object.keys(memory.embedding)
            .sort((a, b) => parseInt(a) - parseInt(b))
            .map(key => memory.embedding[key]);
          embeddingBuffer = Buffer.from(values);
        } else if (Buffer.isBuffer(memory.embedding)) {
          embeddingBuffer = memory.embedding;
        } else {
          embeddingBuffer = Buffer.from(memory.embedding);
        }
      }
      
      // Skip memories with null/undefined IDs
      if (!memory.id) {
        console.log('⚠️  Skipping memory with null ID');
        continue;
      }
      
      await client.memories.upsert({
        where: { id: memory.id },
        update: {
          user_id: memory.user_id,
          content: memory.content,
          embedding: embeddingBuffer,
          metadata: memory.metadata,
          updated_at: new Date(memory.updated_at || memory.created_at)
        },
        create: {
          id: memory.id,
          user_id: memory.user_id,
          content: memory.content,
          embedding: embeddingBuffer,
          metadata: memory.metadata,
          created_at: new Date(memory.created_at),
          updated_at: new Date(memory.updated_at || memory.created_at)
        }
      });
    }
    console.log(`✅ Imported ${data.memories.length} memories`);
    
    // Import tool cache if any
    if (data.tool_cache && data.tool_cache.length > 0) {
      console.log('🔧 Importing tool cache...');
      for (const cache of data.tool_cache) {
        await client.tool_result_cache.create({
          data: {
            tool_name: cache.tool_name,
            input_hash: cache.input_hash,
            result: cache.result,
            created_at: new Date(cache.created_at),
            last_accessed: new Date(cache.last_accessed || cache.created_at)
          }
        });
      }
      console.log(`✅ Imported ${data.tool_cache.length} tool cache entries`);
    }
    
    console.log('🎉 Memory data import completed successfully!');
    console.log('📋 Summary:');
    console.log(`  - 🧠 Memories: ${data.memories.length}`);
    console.log(`  - 🔧 Tool cache: ${data.tool_cache.length}`);
    console.log('📋 Next step: Update memory system to use PostgreSQL');
    
  } catch (error) {
    console.error('❌ Import failed:', error);
    throw error;
  } finally {
    await client.$disconnect();
  }
}

importMemoryData();