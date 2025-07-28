#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// We need to create clients with explicit connection strings
// since the schema is set to PostgreSQL now

async function createSqliteClient() {
  // Temporarily import sqlite3 for direct access
  const Database = await import('better-sqlite3');
  return Database.default('./prisma/dev.db');
}

async function createPostgresClient() {
  return new PrismaClient({
    datasources: {
      db: {
        url: process.env.SUPABASE_DATABASE_URL
      }
    }
  });
}

async function exportData() {
  console.log('📊 Exporting data from SQLite...');
  
  try {
    // Export all tables
    const users = await sqliteClient.users.findMany();
    const conversations = await sqliteClient.conversations.findMany();
    const messages = await sqliteClient.messages.findMany();
    const userMemories = await sqliteClient.user_memories.findMany();
    const embeddingCache = await sqliteClient.embedding_cache.findMany();
    const userMemoryEmbeddings = await sqliteClient.user_memory_embeddings.findMany();
    const agentRuns = await sqliteClient.agent_runs.findMany();
    const conversationSummaries = await sqliteClient.conversation_summaries.findMany();

    const exportData = {
      users,
      conversations,
      messages,
      user_memories: userMemories,
      embedding_cache: embeddingCache,
      user_memory_embeddings: userMemoryEmbeddings,
      agent_runs: agentRuns,
      conversation_summaries: conversationSummaries,
      exportedAt: new Date().toISOString(),
      totalRecords: users.length + conversations.length + messages.length + userMemories.length + embeddingCache.length + userMemoryEmbeddings.length + agentRuns.length + conversationSummaries.length
    };

    // Save to JSON file
    const exportPath = path.join(__dirname, 'sqlite-export.json');
    fs.writeFileSync(exportPath, JSON.stringify(exportData, null, 2));
    
    console.log(`✅ Data exported to ${exportPath}`);
    console.log(`📈 Total records: ${exportData.totalRecords}`);
    console.log(`👥 Users: ${users.length}`);
    console.log(`💬 Conversations: ${conversations.length}`);
    console.log(`📝 Messages: ${messages.length}`);
    console.log(`🧠 User Memories: ${userMemories.length}`);
    console.log(`🔗 Embedding Cache: ${embeddingCache.length}`);
    console.log(`🎯 Agent Runs: ${agentRuns.length}`);
    
    return exportData;
  } catch (error) {
    console.error('❌ Export failed:', error);
    throw error;
  }
}

async function importData(data) {
  console.log('📥 Importing data to Supabase...');
  
  try {
    // Import in dependency order
    console.log('👥 Importing users...');
    for (const user of data.users) {
      await postgresClient.users.upsert({
        where: { id: user.id },
        update: user,
        create: user
      });
    }

    console.log('💬 Importing conversations...');
    for (const conversation of data.conversations) {
      await postgresClient.conversations.upsert({
        where: { id: conversation.id },
        update: conversation,
        create: conversation
      });
    }

    console.log('📝 Importing messages...');
    for (const message of data.messages) {
      await postgresClient.messages.upsert({
        where: { id: message.id },
        update: message,
        create: message
      });
    }

    console.log('🧠 Importing user memories...');
    for (const memory of data.user_memories) {
      await postgresClient.user_memories.upsert({
        where: { id: memory.id },
        update: memory,
        create: memory
      });
    }

    console.log('🔗 Importing embedding cache...');
    for (const cache of data.embedding_cache) {
      await postgresClient.embedding_cache.upsert({
        where: { id: cache.id },
        update: cache,
        create: cache
      });
    }

    console.log('🎯 Importing user memory embeddings...');
    for (const embedding of data.user_memory_embeddings) {
      await postgresClient.user_memory_embeddings.upsert({
        where: { id: embedding.id },
        update: embedding,
        create: embedding
      });
    }

    console.log('🤖 Importing agent runs...');
    for (const run of data.agent_runs) {
      await postgresClient.agent_runs.upsert({
        where: { id: run.id },
        update: run,
        create: run
      });
    }

    console.log('📊 Importing conversation summaries...');
    for (const summary of data.conversation_summaries) {
      await postgresClient.conversation_summaries.upsert({
        where: { id: summary.id },
        update: summary,
        create: summary
      });
    }

    console.log('✅ Import completed successfully!');
  } catch (error) {
    console.error('❌ Import failed:', error);
    throw error;
  }
}

async function migrate() {
  if (!process.env.SUPABASE_DATABASE_URL) {
    console.error('❌ SUPABASE_DATABASE_URL environment variable is required');
    console.log('Example: SUPABASE_DATABASE_URL="postgresql://postgres:[password]@[host]:[port]/postgres"');
    process.exit(1);
  }

  try {
    console.log('🚀 Starting migration from SQLite to Supabase...');
    
    // Export from SQLite
    const data = await exportData();
    
    // Import to Supabase
    await importData(data);
    
    console.log('🎉 Migration completed successfully!');
    console.log('📋 Next steps:');
    console.log('1. Update your .env files with the Supabase DATABASE_URL');
    console.log('2. Test the application with the new database');
    console.log('3. Once verified, you can safely archive the SQLite database');
    
  } catch (error) {
    console.error('💥 Migration failed:', error);
    process.exit(1);
  } finally {
    await sqliteClient.$disconnect();
    await postgresClient.$disconnect();
  }
}

// Run if called directly
migrate();