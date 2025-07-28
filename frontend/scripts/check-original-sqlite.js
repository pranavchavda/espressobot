#!/usr/bin/env node

import Database from 'better-sqlite3';

async function checkOriginalSQLite() {
  console.log('🔍 Checking original SQLite database...');
  
  try {
    const db = new Database('prisma/dev.db');
    
    // Check tables
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
    console.log('📊 Tables found:', tables.map(t => t.name));
    
    // Check data counts
    const users = db.prepare("SELECT COUNT(*) as count FROM users").get();
    console.log(`👥 Users: ${users.count}`);
    
    const conversations = db.prepare("SELECT COUNT(*) as count FROM conversations").get();
    console.log(`💬 Conversations: ${conversations.count}`);
    
    const messages = db.prepare("SELECT COUNT(*) as count FROM messages").get();
    console.log(`📝 Messages: ${messages.count}`);
    
    const userMemories = db.prepare("SELECT COUNT(*) as count FROM user_memories").get();
    console.log(`🧠 User Memories: ${userMemories.count}`);
    
    const embeddingCache = db.prepare("SELECT COUNT(*) as count FROM embedding_cache").get();
    console.log(`🔗 Embedding Cache: ${embeddingCache.count}`);
    
    // Check if we have conversation summaries or agent runs
    try {
      const summaries = db.prepare("SELECT COUNT(*) as count FROM conversation_summaries").get();
      console.log(`📊 Conversation Summaries: ${summaries.count}`);
    } catch (e) {
      console.log('📊 Conversation Summaries: Table not found');
    }
    
    try {
      const agentRuns = db.prepare("SELECT COUNT(*) as count FROM agent_runs").get();
      console.log(`🤖 Agent Runs: ${agentRuns.count}`);
    } catch (e) {
      console.log('🤖 Agent Runs: Table not found');
    }
    
    console.log('\n📋 Total records in SQLite:', 
      users.count + conversations.count + messages.count + userMemories.count + embeddingCache.count);
    
    db.close();
    
  } catch (error) {
    console.error('❌ Error checking SQLite database:', error);
  }
}

checkOriginalSQLite();