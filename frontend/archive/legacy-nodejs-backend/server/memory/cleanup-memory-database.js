#!/usr/bin/env node

/**
 * Memory Database Cleanup Tool
 * Removes memories with null/invalid embeddings that could cause cosineSimilarity errors
 */

import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.join(__dirname, 'data', 'espressobot_memory.db');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

async function main() {
  try {
    console.log('🧹 Memory Database Cleanup Tool');
    console.log(`Database path: ${dbPath}`);
    
    const db = new Database(dbPath);
    
    // Create backup timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    console.log(`\n📋 Starting cleanup at ${timestamp}`);
    
    // Find problematic memories
    const nullEmbeddingStmt = db.prepare('SELECT id, user_id, content FROM memories WHERE embedding IS NULL');
    const nullEmbeddings = nullEmbeddingStmt.all();
    
    const emptyEmbeddingStmt = db.prepare("SELECT id, user_id, content FROM memories WHERE embedding = ''");
    const emptyEmbeddings = emptyEmbeddingStmt.all();
    
    const allMemoriesStmt = db.prepare("SELECT id, user_id, content, embedding FROM memories WHERE embedding IS NOT NULL AND embedding != ''");
    const allMemories = allMemoriesStmt.all();
    
    const invalidJsonMemories = [];
    const invalidArrayMemories = [];
    const shortArrayMemories = [];
    
    for (const memory of allMemories) {
      try {
        const embedding = JSON.parse(memory.embedding);
        
        if (!Array.isArray(embedding)) {
          invalidArrayMemories.push(memory);
        } else if (embedding.length === 0) {
          shortArrayMemories.push(memory);
        } else if (embedding.length < 100) { // Suspiciously short for OpenAI embeddings
          shortArrayMemories.push(memory);
        }
      } catch (error) {
        invalidJsonMemories.push(memory);
      }
    }
    
    const totalProblematic = nullEmbeddings.length + emptyEmbeddings.length + 
                           invalidJsonMemories.length + invalidArrayMemories.length + 
                           shortArrayMemories.length;
    
    console.log(`\n📊 Found problematic memories:`);
    console.log(`  ❌ Null embeddings: ${nullEmbeddings.length}`);
    console.log(`  ❌ Empty embeddings: ${emptyEmbeddings.length}`);
    console.log(`  ❌ Invalid JSON embeddings: ${invalidJsonMemories.length}`);
    console.log(`  ❌ Non-array embeddings: ${invalidArrayMemories.length}`);
    console.log(`  ⚠️  Suspiciously short embeddings: ${shortArrayMemories.length}`);
    console.log(`  🔥 Total to remove: ${totalProblematic}`);
    
    if (totalProblematic === 0) {
      console.log('\n✅ No problematic memories found. Database is clean!');
      db.close();
      rl.close();
      return;
    }
    
    // Show sample problematic memories
    console.log('\n📝 Sample problematic memories:');
    [...nullEmbeddings, ...emptyEmbeddings, ...invalidJsonMemories, ...invalidArrayMemories, ...shortArrayMemories]
      .slice(0, 5)
      .forEach((mem, i) => {
        console.log(`  ${i + 1}. ${mem.id} (${mem.user_id}): "${mem.content.substring(0, 50)}..."`);
      });
    
    // Ask for confirmation
    const confirm = await askQuestion(`\n❓ Do you want to delete these ${totalProblematic} problematic memories? (yes/no): `);
    
    if (confirm.toLowerCase() !== 'yes' && confirm.toLowerCase() !== 'y') {
      console.log('❌ Cleanup cancelled');
      db.close();
      rl.close();
      return;
    }
    
    console.log('\n🧹 Starting cleanup...');
    
    // Delete problematic memories
    const deleteStmt = db.prepare('DELETE FROM memories WHERE id = ?');
    let deletedCount = 0;
    
    const allProblematic = [
      ...nullEmbeddings,
      ...emptyEmbeddings,
      ...invalidJsonMemories,
      ...invalidArrayMemories,
      ...shortArrayMemories
    ];
    
    // Begin transaction for atomic operation
    const transaction = db.transaction(() => {
      for (const memory of allProblematic) {
        try {
          deleteStmt.run(memory.id);
          deletedCount++;
        } catch (error) {
          console.error(`❌ Error deleting memory ${memory.id}:`, error);
        }
      }
    });
    
    transaction();
    
    console.log(`✅ Deleted ${deletedCount} problematic memories`);
    
    // Show final stats
    const finalStmt = db.prepare('SELECT COUNT(*) as count FROM memories');
    const finalCount = finalStmt.get().count;
    console.log(`📊 Remaining memories: ${finalCount}`);
    
    db.close();
    rl.close();
    
    console.log('\n🎉 Cleanup completed successfully!');
    console.log('✅ Memory system should now be free of null reference issues');
    
  } catch (error) {
    console.error('❌ Error during cleanup:', error);
    rl.close();
    process.exit(1);
  }
}

main();