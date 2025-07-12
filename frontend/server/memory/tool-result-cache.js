/**
 * Tool Result Cache
 * Conversation-scoped cache for tool call results with semantic search
 * Prevents redundant API calls by storing and retrieving tool outputs
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

const dbPath = path.join(dataDir, 'tool_result_cache.db');
const db = new Database(dbPath);

// Initialize OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Initialize database schema
db.exec(`
  CREATE TABLE IF NOT EXISTS tool_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    input_params TEXT NOT NULL,
    input_embedding BLOB,
    output_result TEXT NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME
  );
  
  CREATE INDEX IF NOT EXISTS idx_conversation_id ON tool_results(conversation_id);
  CREATE INDEX IF NOT EXISTS idx_tool_name ON tool_results(tool_name);
  CREATE INDEX IF NOT EXISTS idx_expires_at ON tool_results(expires_at);
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
    const maxLength = 8000;
    const truncatedText = text.length > maxLength 
      ? text.substring(0, maxLength) + '...' 
      : text;
    
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: truncatedText
    });
    return response.data[0].embedding;
  } catch (error) {
    console.error('[ToolCache] Error generating embedding:', error);
    return null;
  }
}

class ToolResultCache {
  /**
   * Store a tool result in the cache
   */
  async store(conversationId, toolName, inputParams, outputResult, metadata = {}) {
    try {
      // Create a searchable string from input params
      const inputString = typeof inputParams === 'string' 
        ? inputParams 
        : JSON.stringify(inputParams, null, 2);
      
      // Generate embedding for semantic search
      const embedding = await generateEmbedding(`${toolName} ${inputString}`);
      
      // Set expiration (24 hours from now)
      const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
      
      const stmt = db.prepare(`
        INSERT INTO tool_results (
          conversation_id, tool_name, input_params, input_embedding, 
          output_result, metadata, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `);
      
      const result = stmt.run(
        conversationId,
        toolName,
        inputString,
        embedding ? Buffer.from(new Float32Array(embedding).buffer) : null,
        typeof outputResult === 'string' ? outputResult : JSON.stringify(outputResult),
        JSON.stringify(metadata),
        expiresAt
      );
      
      console.log(`[ToolCache] Stored ${toolName} result for conversation ${conversationId}`);
      return result.lastInsertRowid;
    } catch (error) {
      console.error('[ToolCache] Error storing result:', error);
      return null;
    }
  }
  
  /**
   * Search for cached tool results
   */
  async search(conversationId, query, options = {}) {
    const {
      toolName = null,
      limit = 5,
      similarityThreshold = 0.8
    } = options;
    
    try {
      // Clean up expired entries first
      this.cleanupExpired();
      
      // Generate embedding for the search query
      const queryEmbedding = await generateEmbedding(query);
      if (!queryEmbedding) {
        console.log('[ToolCache] Could not generate embedding, falling back to text search');
        return this.textSearch(conversationId, query, { toolName, limit });
      }
      
      console.log('[ToolCache] Generated query embedding successfully');
      
      // Get all results for this conversation
      let sql = `
        SELECT * FROM tool_results 
        WHERE conversation_id = ? 
        AND expires_at > datetime('now')
      `;
      const params = [conversationId];
      
      if (toolName) {
        sql += ' AND tool_name = ?';
        params.push(toolName);
      }
      
      const results = db.prepare(sql).all(...params);
      
      // Calculate similarity scores
      const scoredResults = results.map(result => {
        if (!result.input_embedding) {
          console.log('[ToolCache] No embedding for result:', result.tool_name);
          return null;
        }
        
        const embedding = new Float32Array(result.input_embedding.buffer);
        const similarity = cosineSimilarity(queryEmbedding, Array.from(embedding));
        
        console.log(`[ToolCache] Similarity for ${result.tool_name}: ${similarity}`);
        
        return {
          ...result,
          similarity,
          output_result: JSON.parse(result.output_result),
          metadata: JSON.parse(result.metadata || '{}')
        };
      }).filter(r => r && r.similarity >= similarityThreshold);
      
      // Sort by similarity and return top results
      scoredResults.sort((a, b) => b.similarity - a.similarity);
      return scoredResults.slice(0, limit);
      
    } catch (error) {
      console.error('[ToolCache] Error searching:', error);
      return [];
    }
  }
  
  /**
   * Fallback text search when embeddings are not available
   */
  textSearch(conversationId, query, options = {}) {
    const { toolName = null, limit = 5 } = options;
    
    try {
      let sql = `
        SELECT * FROM tool_results 
        WHERE conversation_id = ? 
        AND expires_at > datetime('now')
        AND (input_params LIKE ? OR output_result LIKE ?)
      `;
      const params = [conversationId, `%${query}%`, `%${query}%`];
      
      if (toolName) {
        sql += ' AND tool_name = ?';
        params.push(toolName);
      }
      
      sql += ' ORDER BY created_at DESC LIMIT ?';
      params.push(limit);
      
      const results = db.prepare(sql).all(...params);
      
      return results.map(result => ({
        ...result,
        output_result: JSON.parse(result.output_result),
        metadata: JSON.parse(result.metadata || '{}'),
        similarity: 0.5 // Default similarity for text matches
      }));
      
    } catch (error) {
      console.error('[ToolCache] Error in text search:', error);
      return [];
    }
  }
  
  /**
   * Get exact match for tool call
   */
  getExactMatch(conversationId, toolName, inputParams) {
    try {
      const inputString = typeof inputParams === 'string' 
        ? inputParams 
        : JSON.stringify(inputParams, null, 2);
      
      const result = db.prepare(`
        SELECT * FROM tool_results 
        WHERE conversation_id = ? 
        AND tool_name = ?
        AND input_params = ?
        AND expires_at > datetime('now')
        ORDER BY created_at DESC
        LIMIT 1
      `).get(conversationId, toolName, inputString);
      
      if (result) {
        return {
          ...result,
          output_result: JSON.parse(result.output_result),
          metadata: JSON.parse(result.metadata || '{}')
        };
      }
      
      return null;
    } catch (error) {
      console.error('[ToolCache] Error getting exact match:', error);
      return null;
    }
  }
  
  /**
   * Clean up expired entries
   */
  cleanupExpired() {
    try {
      const result = db.prepare(`
        DELETE FROM tool_results 
        WHERE expires_at <= datetime('now')
      `).run();
      
      if (result.changes > 0) {
        console.log(`[ToolCache] Cleaned up ${result.changes} expired entries`);
      }
    } catch (error) {
      console.error('[ToolCache] Error cleaning up:', error);
    }
  }
  
  /**
   * Clear all results for a conversation
   */
  clearConversation(conversationId) {
    try {
      const result = db.prepare(`
        DELETE FROM tool_results 
        WHERE conversation_id = ?
      `).run(conversationId);
      
      console.log(`[ToolCache] Cleared ${result.changes} entries for conversation ${conversationId}`);
      return result.changes;
    } catch (error) {
      console.error('[ToolCache] Error clearing conversation:', error);
      return 0;
    }
  }
  
  /**
   * Get statistics for a conversation
   */
  getStats(conversationId) {
    try {
      const stats = db.prepare(`
        SELECT 
          COUNT(*) as total_cached,
          COUNT(DISTINCT tool_name) as unique_tools,
          MIN(created_at) as oldest_entry,
          MAX(created_at) as newest_entry
        FROM tool_results 
        WHERE conversation_id = ?
        AND expires_at > datetime('now')
      `).get(conversationId);
      
      const toolBreakdown = db.prepare(`
        SELECT tool_name, COUNT(*) as count
        FROM tool_results 
        WHERE conversation_id = ?
        AND expires_at > datetime('now')
        GROUP BY tool_name
        ORDER BY count DESC
      `).all(conversationId);
      
      return {
        ...stats,
        tool_breakdown: toolBreakdown
      };
    } catch (error) {
      console.error('[ToolCache] Error getting stats:', error);
      return null;
    }
  }
}

// Create singleton instance
const toolResultCache = new ToolResultCache();

// Set up periodic cleanup (every hour)
setInterval(() => {
  toolResultCache.cleanupExpired();
}, 60 * 60 * 1000);

export { toolResultCache };

console.log('[ToolResultCache] Initialized with SQLite backend and semantic search');