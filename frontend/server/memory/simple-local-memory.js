/**
 * Simple Local Memory Implementation
 * Uses SQLite for storage and OpenAI embeddings for semantic search
 * More reliable than the mem0ai OSS package
 */

import Database from 'better-sqlite3';
import { OpenAI } from 'openai';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Ensure data directory exists
const dataDir = path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, 'espressobot_memory.db');
const db = new Database(dbPath);

// Initialize OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Initialize database schema
db.exec(`
  CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
  
  CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id);
  CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at);
`);

// Helper function to calculate cosine similarity
function cosineSimilarity(a, b) {
  if (a.length !== b.length) return 0;
  
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

// Generate embeddings using OpenAI
async function generateEmbedding(text) {
  try {
    // Truncate text to stay within token limits
    // Rough estimate: 1 token ≈ 4 characters for English text
    // 8192 token limit, use 7000 to be safe = ~28000 characters
    const maxLength = 28000;
    const truncatedText = text.length > maxLength 
      ? text.substring(0, maxLength) + '...' 
      : text;
    
    if (text.length > maxLength) {
      console.log(`[Memory] Truncated embedding input from ${text.length} to ${maxLength} characters`);
    }
    
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: truncatedText
    });
    return response.data[0].embedding;
  } catch (error) {
    console.error('Error generating embedding:', error);
    return null;
  }
}

class SimpleLocalMemory {
  /**
   * Add a memory
   */
  async add(content, userId, metadata = {}) {
    try {
      const id = `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const embedding = await generateEmbedding(content);
      
      if (!embedding) {
        throw new Error('Failed to generate embedding');
      }
      
      // Store embedding as JSON string
      const embeddingBlob = JSON.stringify(embedding);
      const metadataStr = JSON.stringify(metadata);
      
      const stmt = db.prepare(`
        INSERT INTO memories (id, user_id, content, embedding, metadata)
        VALUES (?, ?, ?, ?, ?)
      `);
      
      stmt.run(id, userId, content, embeddingBlob, metadataStr);
      
      console.log(`Memory added: ${id} for user ${userId}`);
      return {
        id,
        memory: content,
        metadata,
        success: true
      };
    } catch (error) {
      console.error('Error adding memory:', error);
      throw error;
    }
  }

  /**
   * Search memories
   */
  async search(query, userId, limit = 10) {
    try {
      const queryEmbedding = await generateEmbedding(query);
      if (!queryEmbedding) {
        throw new Error('Failed to generate query embedding');
      }
      
      // Get all memories for user
      const stmt = db.prepare(`
        SELECT id, content, embedding, metadata, created_at
        FROM memories 
        WHERE user_id = ?
        ORDER BY created_at DESC
      `);
      
      const memories = stmt.all(userId);
      
      // Calculate similarities
      const results = memories.map(mem => {
        const memEmbedding = JSON.parse(mem.embedding);
        const similarity = cosineSimilarity(queryEmbedding, memEmbedding);
        
        return {
          id: mem.id,
          memory: mem.content,
          score: similarity,
          metadata: JSON.parse(mem.metadata || '{}'),
          createdAt: mem.created_at
        };
      });
      
      // Sort by similarity and limit results
      const sortedResults = results
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .filter(r => r.score > 0.1); // Filter out very low similarity
      
      console.log(`Found ${sortedResults.length} memories for query "${query}"`);
      return sortedResults;
    } catch (error) {
      console.error('Error searching memories:', error);
      return [];
    }
  }

  /**
   * Get a specific memory by ID
   */
  async get(memoryId) {
    try {
      const stmt = db.prepare(`
        SELECT id, user_id, content, metadata, created_at
        FROM memories 
        WHERE id = ?
      `);
      
      const memory = stmt.get(memoryId);
      
      if (!memory) {
        return null;
      }
      
      return {
        id: memory.id,
        userId: memory.user_id,
        memory: memory.content,
        metadata: JSON.parse(memory.metadata || '{}'),
        createdAt: memory.created_at
      };
    } catch (error) {
      console.error('Error getting memory:', error);
      return null;
    }
  }

  /**
   * Get all memories for a user
   */
  async getAll(userId, limit = 100) {
    try {
      let stmt, memories;
      
      if (userId) {
        stmt = db.prepare(`
          SELECT id, user_id, content, metadata, created_at
          FROM memories 
          WHERE user_id = ?
          ORDER BY created_at DESC
          LIMIT ?
        `);
        memories = stmt.all(userId, limit);
      } else {
        // Get all memories from all users
        stmt = db.prepare(`
          SELECT id, user_id, content, metadata, created_at
          FROM memories 
          ORDER BY created_at DESC
          LIMIT ?
        `);
        memories = stmt.all(limit);
      }
      
      return memories.map(mem => ({
        id: mem.id,
        userId: mem.user_id,
        memory: mem.content,
        metadata: JSON.parse(mem.metadata || '{}'),
        createdAt: mem.created_at
      }));
    } catch (error) {
      console.error('Error getting all memories:', error);
      return [];
    }
  }

  /**
   * Update a memory
   */
  async update(memoryId, content) {
    try {
      const embedding = await generateEmbedding(content);
      if (!embedding) {
        throw new Error('Failed to generate embedding');
      }
      
      const embeddingBlob = JSON.stringify(embedding);
      
      const stmt = db.prepare(`
        UPDATE memories 
        SET content = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `);
      
      const result = stmt.run(content, embeddingBlob, memoryId);
      
      if (result.changes === 0) {
        throw new Error('Memory not found');
      }
      
      return { success: true, message: 'Memory updated successfully' };
    } catch (error) {
      console.error('Error updating memory:', error);
      throw error;
    }
  }

  /**
   * Delete a memory
   */
  async delete(memoryId) {
    try {
      const stmt = db.prepare('DELETE FROM memories WHERE id = ?');
      const result = stmt.run(memoryId);
      
      if (result.changes === 0) {
        throw new Error('Memory not found');
      }
      
      return { success: true, message: 'Memory deleted successfully' };
    } catch (error) {
      console.error('Error deleting memory:', error);
      throw error;
    }
  }

  /**
   * Delete all memories for a user
   */
  async deleteAll(userId) {
    try {
      const stmt = db.prepare('DELETE FROM memories WHERE user_id = ?');
      const result = stmt.run(userId);
      
      return { 
        success: true, 
        message: `Deleted ${result.changes} memories for user ${userId}` 
      };
    } catch (error) {
      console.error('Error deleting all memories:', error);
      throw error;
    }
  }

  /**
   * Extract memory summary (simple implementation)
   */
  extractMemorySummary(conversationText, context = {}) {
    // Simple extraction - in production this could use LLM for better extraction
    const lines = conversationText.trim().split('\n').filter(line => line.trim());
    const summary = lines
      .filter(line => line.includes('User:') || line.includes('Assistant:'))
      .join(' ')
      .replace(/User:|Assistant:/g, '')
      .trim();
    
    const metadata = {
      timestamp: new Date().toISOString(),
      conversationId: context.conversationId || 'unknown',
      agent: context.agent || 'unknown',
      extractedFrom: 'conversation'
    };
    
    return { content: summary, metadata };
  }

  /**
   * Get database statistics
   */
  getStats() {
    try {
      const totalStmt = db.prepare('SELECT COUNT(*) as total FROM memories');
      const userStmt = db.prepare('SELECT user_id, COUNT(*) as count FROM memories GROUP BY user_id');
      
      const total = totalStmt.get().total;
      const byUser = userStmt.all();
      
      return { total, byUser };
    } catch (error) {
      console.error('Error getting stats:', error);
      return { total: 0, byUser: [] };
    }
  }
}

// Export singleton instance
export const simpleLocalMemory = new SimpleLocalMemory();

console.log('Simple Local Memory initialized with SQLite storage');