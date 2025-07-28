/**
 * Simple Local Memory Implementation - PostgreSQL/Prisma Version
 * Uses Supabase PostgreSQL for storage and OpenAI embeddings for semantic search
 * Migrated from SQLite to PostgreSQL/Prisma
 */

import { PrismaClient } from '@prisma/client';
import { OpenAI } from 'openai';
import { createOpenAIWithRetry } from '../utils/openai-with-retry.js';

// Initialize Prisma client for PostgreSQL
const prisma = new PrismaClient();

// Initialize OpenAI
const openai = createOpenAIWithRetry();

// Helper function to calculate cosine similarity
function cosineSimilarity(a, b) {
  // Null safety checks
  if (!a || !b || !Array.isArray(a) || !Array.isArray(b)) {
    console.warn('[Memory] cosineSimilarity: Invalid embeddings - one or both are null/undefined');
    return 0;
  }

  if (a.length !== b.length) {
    console.warn('[Memory] cosineSimilarity: Embedding length mismatch', { lengthA: a.length, lengthB: b.length });
    return 0;
  }

  let dot = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  if (normA === 0 || normB === 0) {
    return 0;
  }

  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

// Helper function to convert Buffer to Float32Array
function bufferToFloatArray(buffer) {
  if (!buffer) return null;
  
  // Handle different buffer formats
  if (Buffer.isBuffer(buffer)) {
    // Convert bytes back to JSON string then parse
    const jsonStr = buffer.toString('utf8');
    try {
      return JSON.parse(jsonStr);
    } catch {
      // If not JSON, try to interpret as raw float data
      const floats = new Float32Array(buffer.buffer, buffer.byteOffset, buffer.byteLength / 4);
      return Array.from(floats);
    }
  }
  
  return buffer;
}

// Helper function to convert embedding array to Buffer
function floatArrayToBuffer(array) {
  if (!array) return null;
  // Store as JSON string in buffer for compatibility
  return Buffer.from(JSON.stringify(array), 'utf8');
}

/**
 * Create an embedding for a text
 */
async function createEmbedding(text) {
  try {
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: text,
      encoding_format: 'float'
    });
    
    return response.data[0].embedding;
  } catch (error) {
    console.error('[Memory] Error creating embedding:', error);
    throw error;
  }
}

/**
 * Search memories with different strategies
 */
async function searchMemories(query, userId, options = {}) {
  const {
    limit = 10,
    threshold = 0.1,
    strategy = 'hybrid', // 'exact', 'fuzzy', 'semantic', 'hybrid'
    useNano = false
  } = options;

  console.log(`[Memory] Searching memories for user ${userId} with strategy: ${strategy}`);

  let results = [];

  try {
    if (strategy === 'exact' || strategy === 'hybrid') {
      // Exact text search
      const exactResults = await prisma.memories.findMany({
        where: {
          user_id: userId,
          content: {
            contains: query,
            mode: 'insensitive'
          }
        },
        orderBy: { created_at: 'desc' },
        take: limit
      });

      results = exactResults.map(memory => ({
        ...memory,
        similarity: 1.0,
        strategy: 'exact'
      }));

      console.log(`[Memory] Found ${results.length} exact matches`);
    }

    if ((strategy === 'fuzzy' || strategy === 'hybrid') && results.length < limit) {
      // Fuzzy search using contains with individual words
      const remaining = limit - results.length;
      const words = query.toLowerCase().split(' ').filter(word => word.length > 2);
      
      let fuzzyResults = [];
      if (words.length > 0) {
        // Search for memories containing any of the words
        fuzzyResults = await prisma.memories.findMany({
          where: {
            user_id: userId,
            OR: words.map(word => ({
              content: {
                contains: word,
                mode: 'insensitive'
              }
            }))
          },
          orderBy: { created_at: 'desc' },
          take: remaining
        });
      }

      const newResults = fuzzyResults
        .filter(memory => !results.some(r => r.id === memory.id))
        .map(memory => ({
          ...memory,
          similarity: 0.8,
          strategy: 'fuzzy'
        }));

      results = [...results, ...newResults];
      console.log(`[Memory] Added ${newResults.length} fuzzy matches`);
    }

    if ((strategy === 'semantic' || strategy === 'hybrid') && results.length < limit) {
      // Semantic search using embeddings
      const queryEmbedding = await createEmbedding(query);
      const remaining = limit - results.length;

      // Get all memories with embeddings for this user
      const memoriesWithEmbeddings = await prisma.memories.findMany({
        where: {
          user_id: userId,
          embedding: { not: null }
        },
        orderBy: { created_at: 'desc' }
      });

      // Calculate similarities
      const semanticResults = memoriesWithEmbeddings
        .map(memory => {
          const embedding = bufferToFloatArray(memory.embedding);
          if (!embedding || !Array.isArray(embedding)) {
            return null;
          }

          const similarity = cosineSimilarity(queryEmbedding, embedding);
          return {
            ...memory,
            similarity,
            strategy: 'semantic'
          };
        })
        .filter(result => result && result.similarity >= threshold)
        .filter(memory => !results.some(r => r.id === memory.id))
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, remaining);

      results = [...results, ...semanticResults];
      console.log(`[Memory] Added ${semanticResults.length} semantic matches`);
    }

    // Sort by similarity and limit
    results = results
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, limit);

    console.log(`[Memory] Returning ${results.length} total results`);
    return results;

  } catch (error) {
    console.error('[Memory] Error searching memories:', error);
    throw error;
  }
}

/**
 * Add a new memory
 */
async function addMemory(content, userId, metadata = null, options = {}) {
  const { 
    useNano = false,
    skipEmbedding = false 
  } = options;

  console.log(`[Memory] Adding memory for user ${userId}. Content length: ${content.length}`);

  try {
    // Generate unique ID
    const id = `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Create embedding unless skipped
    let embedding = null;
    if (!skipEmbedding) {
      try {
        const embeddingArray = await createEmbedding(content);
        embedding = floatArrayToBuffer(embeddingArray);
      } catch (error) {
        console.warn('[Memory] Failed to create embedding, storing without embedding:', error.message);
      }
    }

    // Store memory
    const memory = await prisma.memories.create({
      data: {
        id,
        user_id: userId,
        content,
        embedding,
        metadata: metadata ? JSON.stringify(metadata) : null
      }
    });

    console.log(`[Memory] Successfully added memory ${id}`);
    return memory;

  } catch (error) {
    console.error('[Memory] Error adding memory:', error);
    throw error;
  }
}

/**
 * Update an existing memory
 */
async function updateMemory(memoryId, content, metadata = null, options = {}) {
  const { useNano = false } = options;

  console.log(`[Memory] Updating memory ${memoryId}`);

  try {
    // Create new embedding for updated content
    let embedding = null;
    try {
      const embeddingArray = await createEmbedding(content);
      embedding = floatArrayToBuffer(embeddingArray);
    } catch (error) {
      console.warn('[Memory] Failed to create embedding for update:', error.message);
    }

    // Update memory
    const memory = await prisma.memories.update({
      where: { id: memoryId },
      data: {
        content,
        embedding,
        metadata: metadata ? JSON.stringify(metadata) : null,
        updated_at: new Date()
      }
    });

    console.log(`[Memory] Successfully updated memory ${memoryId}`);
    return memory;

  } catch (error) {
    console.error('[Memory] Error updating memory:', error);
    throw error;
  }
}

/**
 * Delete a memory
 */
async function deleteMemory(memoryId) {
  console.log(`[Memory] Deleting memory ${memoryId}`);

  try {
    await prisma.memories.delete({
      where: { id: memoryId }
    });

    console.log(`[Memory] Successfully deleted memory ${memoryId}`);
    return true;

  } catch (error) {
    console.error('[Memory] Error deleting memory:', error);
    throw error;
  }
}

/**
 * Delete all memories for a user
 */
async function deleteUserMemories(userId) {
  console.log(`[Memory] Deleting all memories for user ${userId}`);

  try {
    const result = await prisma.memories.deleteMany({
      where: { user_id: userId }
    });

    console.log(`[Memory] Successfully deleted ${result.count} memories for user ${userId}`);
    return result.count;

  } catch (error) {
    console.error('[Memory] Error deleting user memories:', error);
    throw error;
  }
}

/**
 * Get all memories for a user
 */
async function getUserMemories(userId, options = {}) {
  const { limit = 100, offset = 0 } = options;

  try {
    const memories = await prisma.memories.findMany({
      where: { user_id: userId },
      orderBy: { created_at: 'desc' },
      take: limit,
      skip: offset
    });

    return memories;

  } catch (error) {
    console.error('[Memory] Error getting user memories:', error);
    throw error;
  }
}

/**
 * Get memory statistics
 */
async function getMemoryStats() {
  try {
    const totalCount = await prisma.memories.count();
    
    const userStats = await prisma.memories.groupBy({
      by: ['user_id'],
      _count: {
        user_id: true
      }
    });

    return {
      total: totalCount,
      byUser: userStats.map(stat => ({
        user_id: stat.user_id,
        count: stat._count.user_id
      }))
    };

  } catch (error) {
    console.error('[Memory] Error getting memory stats:', error);
    throw error;
  }
}

// Create a compatible object that matches the old SQLite interface
const simpleLocalMemory = {
  // New interface (preferred)
  searchMemories,
  addMemory,
  updateMemory,
  deleteMemory,
  deleteUserMemories,
  getUserMemories,
  getMemoryStats,
  createEmbedding,
  
  // Legacy interface for backward compatibility
  search: async (query, userId, limit = 10) => {
    return await searchMemories(query, userId, { limit, strategy: 'hybrid' });
  },
  
  getAll: async (userId = null, limit = 100) => {
    if (userId) {
      return await getUserMemories(userId, { limit });
    } else {
      // Get all memories for all users
      const stats = await getMemoryStats();
      const allMemories = [];
      
      for (const userStat of stats.byUser) {
        const userMemories = await getUserMemories(userStat.user_id, { limit: 1000 });
        allMemories.push(...userMemories);
      }
      
      return allMemories.slice(0, limit);
    }
  },
  
  getStats: async () => {
    return await getMemoryStats();
  },
  
  update: async (memoryId, content, metadata = null) => {
    return await updateMemory(memoryId, content, metadata);
  },
  
  delete: async (memoryId) => {
    return await deleteMemory(memoryId);
  },
  
  deleteAll: async (userId) => {
    return await deleteUserMemories(userId);
  }
};

// Export both individual functions and the original object for backward compatibility
export {
  searchMemories,
  addMemory,
  updateMemory,
  deleteMemory,
  deleteUserMemories,
  getUserMemories,
  getMemoryStats,
  createEmbedding,
  simpleLocalMemory
};

// Also export as default for compatibility
export default simpleLocalMemory;