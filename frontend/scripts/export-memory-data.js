#!/usr/bin/env node

import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function exportMemoryData() {
  console.log('🧠 Exporting memory data from SQLite...');
  
  try {
    // Export memories from memory database
    const memoryDbPath = path.join(__dirname, '..', 'server', 'memory', 'data', 'espressobot_memory.db');
    const memoryDb = new Database(memoryDbPath);
    
    const memories = memoryDb.prepare("SELECT * FROM memories").all();
    console.log(`✅ Found ${memories.length} memories`);
    
    // Export tool cache from tool cache database
    const toolCacheDbPath = path.join(__dirname, '..', 'server', 'memory', 'data', 'tool_result_cache.db');
    let toolCache = [];
    
    if (fs.existsSync(toolCacheDbPath)) {
      try {
        const toolCacheDb = new Database(toolCacheDbPath);
        const tables = toolCacheDb.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
        console.log('🔧 Tool cache tables:', tables.map(t => t.name));
        
        if (tables.some(t => t.name === 'tool_results')) {
          toolCache = toolCacheDb.prepare("SELECT * FROM tool_results").all();
          console.log(`✅ Found ${toolCache.length} tool cache entries`);
        }
        toolCacheDb.close();
      } catch (error) {
        console.log('⚠️  Tool cache database not readable, skipping...');
      }
    } else {
      console.log('⚠️  Tool cache database not found, skipping...');
    }
    
    memoryDb.close();
    
    const exportData = {
      memories,
      tool_cache: toolCache,
      exportedAt: new Date().toISOString(),
      totalRecords: memories.length + toolCache.length
    };
    
    // Save to JSON file
    const exportPath = path.join(__dirname, 'memory-export.json');
    fs.writeFileSync(exportPath, JSON.stringify(exportData, null, 2));
    
    console.log(`✅ Memory data exported to ${exportPath}`);
    console.log(`📊 Total records: ${exportData.totalRecords}`);
    console.log(`🧠 Memories: ${memories.length}`);
    console.log(`🔧 Tool cache: ${toolCache.length}`);
    
    // Show user distribution
    const userStats = {};
    memories.forEach(memory => {
      userStats[memory.user_id] = (userStats[memory.user_id] || 0) + 1;
    });
    
    console.log('👥 Memory distribution by user:');
    Object.entries(userStats).forEach(([userId, count]) => {
      console.log(`  - ${userId}: ${count} memories`);
    });
    
    return exportData;
  } catch (error) {
    console.error('❌ Export failed:', error);
    throw error;
  }
}

exportMemoryData();