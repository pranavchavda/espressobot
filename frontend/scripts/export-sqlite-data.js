#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const client = new PrismaClient();

async function exportData() {
  console.log('📊 Exporting data from SQLite...');
  
  try {
    // Export all tables
    const users = await client.users.findMany();
    const conversations = await client.conversations.findMany();
    const messages = await client.messages.findMany();
    const userMemories = await client.user_memories.findMany();
    const embeddingCache = await client.embedding_cache.findMany();
    const userMemoryEmbeddings = await client.user_memory_embeddings.findMany();
    const agentRuns = await client.agent_runs.findMany();
    const conversationSummaries = await client.conversation_summaries.findMany();

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
    console.log(`📊 Conversation Summaries: ${conversationSummaries.length}`);
    
    return exportData;
  } catch (error) {
    console.error('❌ Export failed:', error);
    throw error;
  } finally {
    await client.$disconnect();
  }
}

exportData();