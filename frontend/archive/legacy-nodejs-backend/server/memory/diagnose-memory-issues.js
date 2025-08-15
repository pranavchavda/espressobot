#!/usr/bin/env node

/**
 * Memory System Diagnostic Tool
 * Checks for null embeddings and other potential issues
 */

import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.join(__dirname, 'data', 'espressobot_memory.db');

try {
  console.log('🔍 Diagnosing Memory System Issues...');
  console.log(`Database path: ${dbPath}`);
  
  const db = new Database(dbPath);
  
  // Check total memories
  const totalStmt = db.prepare('SELECT COUNT(*) as count FROM memories');
  const totalMemories = totalStmt.get().count;
  console.log(`\n📊 Total memories: ${totalMemories}`);
  
  // Check for null embeddings
  const nullEmbeddingStmt = db.prepare('SELECT COUNT(*) as count FROM memories WHERE embedding IS NULL');
  const nullEmbeddings = nullEmbeddingStmt.get().count;
  console.log(`❌ Memories with null embeddings: ${nullEmbeddings}`);
  
  // Check for empty embeddings
  const emptyEmbeddingStmt = db.prepare("SELECT COUNT(*) as count FROM memories WHERE embedding = ''");
  const emptyEmbeddings = emptyEmbeddingStmt.get().count;
  console.log(`❌ Memories with empty embeddings: ${emptyEmbeddings}`);
  
  // Check for invalid JSON embeddings
  const allMemoriesStmt = db.prepare("SELECT id, embedding FROM memories WHERE embedding IS NOT NULL AND embedding != ''");
  const allMemories = allMemoriesStmt.all();
  
  let invalidJsonCount = 0;
  let invalidArrayCount = 0;
  const problematicMemories = [];
  
  for (const memory of allMemories) {
    try {
      const embedding = JSON.parse(memory.embedding);
      
      if (!Array.isArray(embedding)) {
        invalidArrayCount++;
        problematicMemories.push({
          id: memory.id,
          issue: 'Not an array',
          type: typeof embedding
        });
      } else if (embedding.length === 0) {
        problematicMemories.push({
          id: memory.id,
          issue: 'Empty array',
          length: embedding.length
        });
      } else if (embedding.length < 100) { // OpenAI embeddings are typically 1536 dimensions
        problematicMemories.push({
          id: memory.id,
          issue: 'Suspiciously short array',
          length: embedding.length
        });
      }
    } catch (error) {
      invalidJsonCount++;
      problematicMemories.push({
        id: memory.id,
        issue: 'Invalid JSON',
        error: error.message
      });
    }
  }
  
  console.log(`❌ Memories with invalid JSON embeddings: ${invalidJsonCount}`);
  console.log(`❌ Memories with non-array embeddings: ${invalidArrayCount}`);
  console.log(`⚠️  Total problematic memories: ${problematicMemories.length}`);
  
  if (problematicMemories.length > 0) {
    console.log('\n🔧 Problematic memories:');
    problematicMemories.slice(0, 10).forEach((mem, i) => {
      console.log(`  ${i + 1}. ID: ${mem.id} - Issue: ${mem.issue}`);
      if (mem.length !== undefined) console.log(`     Length: ${mem.length}`);
      if (mem.error) console.log(`     Error: ${mem.error}`);
    });
    
    if (problematicMemories.length > 10) {
      console.log(`     ... and ${problematicMemories.length - 10} more`);
    }
  }
  
  // Check for memories by user
  const userStmt = db.prepare(`
    SELECT user_id, COUNT(*) as count,
           SUM(CASE WHEN embedding IS NULL THEN 1 ELSE 0 END) as null_embeddings
    FROM memories 
    GROUP BY user_id
    ORDER BY count DESC
  `);
  const userStats = userStmt.all();
  
  console.log('\n👥 Memories by user:');
  userStats.forEach(user => {
    console.log(`  ${user.user_id}: ${user.count} memories (${user.null_embeddings} null embeddings)`);
  });
  
  db.close();
  
  // Recommendations
  console.log('\n💡 Recommendations:');
  
  if (nullEmbeddings > 0 || emptyEmbeddings > 0 || invalidJsonCount > 0) {
    console.log('  ❗ Found memories with missing or invalid embeddings');
    console.log('  🔧 Run the cleanup script to remove these problematic entries');
    console.log('  📝 Consider regenerating embeddings for important memories');
  }
  
  if (problematicMemories.length === 0) {
    console.log('  ✅ No critical embedding issues found');
    console.log('  ✅ Memory system should be stable');
  }
  
  console.log('\n✨ Diagnosis complete!');
  
} catch (error) {
  console.error('❌ Error running diagnostics:', error);
  process.exit(1);
}