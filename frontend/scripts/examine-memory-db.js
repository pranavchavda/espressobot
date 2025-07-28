#!/usr/bin/env node

import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const memoryDbPath = path.join(__dirname, '..', 'server', 'memory', 'data', 'espressobot_memory.db');

async function examineMemoryDb() {
  console.log('🔍 Examining memory database...');
  console.log('📁 Path:', memoryDbPath);
  
  try {
    const db = new Database(memoryDbPath);
    
    // Get table info
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
    console.log('📊 Tables found:', tables.map(t => t.name));
    
    // Get schema for memories table
    const schema = db.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name='memories'").get();
    console.log('📋 Memories table schema:');
    console.log(schema?.sql);
    
    // Get data counts
    const memoryCount = db.prepare("SELECT COUNT(*) as count FROM memories").get();
    console.log(`🧠 Total memories: ${memoryCount.count}`);
    
    // Get sample data
    if (memoryCount.count > 0) {
      const samples = db.prepare("SELECT id, user_id, content, created_at FROM memories LIMIT 5").all();
      console.log('📝 Sample memories:');
      samples.forEach(memory => {
        console.log(`  - ID: ${memory.id}`);
        console.log(`    User: ${memory.user_id}`);
        console.log(`    Content: ${memory.content.substring(0, 100)}...`);
        console.log(`    Created: ${memory.created_at}`);
        console.log('');
      });
    }
    
    // Get user distribution
    const userStats = db.prepare("SELECT user_id, COUNT(*) as count FROM memories GROUP BY user_id").all();
    console.log('👥 Memory distribution by user:');
    userStats.forEach(stat => {
      console.log(`  - User ${stat.user_id}: ${stat.count} memories`);
    });
    
    db.close();
    
  } catch (error) {
    console.error('❌ Error examining memory database:', error);
  }
}

examineMemoryDb();