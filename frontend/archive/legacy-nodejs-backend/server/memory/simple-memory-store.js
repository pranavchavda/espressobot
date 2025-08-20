/**
 * Simple in-memory store for EspressoBot memories
 * This is a temporary solution until we can properly configure mem0
 */

import crypto from 'crypto';
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// In-memory storage (will be lost on restart)
const memoryStore = new Map();

/**
 * Generate embeddings using OpenAI
 */
async function generateEmbedding(text) {
  try {
    const response = await openai.embeddings.create({
      model: "text-embedding-3-small",
      input: text,
    });
    return response.data[0].embedding;
  } catch (error) {
    console.error('[Simple Memory] Error generating embedding:', error);
    return null;
  }
}

/**
 * Calculate cosine similarity between two vectors
 */
function cosineSimilarity(vec1, vec2) {
  // Null safety checks
  if (!vec1 || !vec2 || !Array.isArray(vec1) || !Array.isArray(vec2)) {
    console.warn('[SimpleMemoryStore] cosineSimilarity: Invalid vectors - one or both are null/undefined');
    return 0;
  }
  
  if (vec1.length !== vec2.length) {
    console.warn(`[SimpleMemoryStore] cosineSimilarity: Vector dimension mismatch - vec1: ${vec1.length}, vec2: ${vec2.length}`);
    return 0;
  }
  
  if (vec1.length === 0 || vec2.length === 0) {
    console.warn('[SimpleMemoryStore] cosineSimilarity: Empty vectors');
    return 0;
  }
  
  let dotProduct = 0;
  let norm1 = 0;
  let norm2 = 0;
  
  for (let i = 0; i < vec1.length; i++) {
    dotProduct += vec1[i] * vec2[i];
    norm1 += vec1[i] * vec1[i];
    norm2 += vec2[i] * vec2[i];
  }
  
  const denominator = Math.sqrt(norm1) * Math.sqrt(norm2);
  if (denominator === 0) {
    console.warn('[SimpleMemoryStore] cosineSimilarity: Zero norm detected');
    return 0;
  }
  
  return dotProduct / denominator;
}

/**
 * Extract important information from messages using GPT
 */
async function extractMemory(messages) {
  try {
    const response = await openai.chat.completions.create({
      model: "gpt-4.1-mini",
      temperature: 0.1,
      messages: [
        {
          role: "system",
          content: "Extract and summarize important information from the conversation that should be remembered. Focus on user preferences, habits, important facts, and actionable information. Return a concise summary."
        },
        {
          role: "user",
          content: messages
        }
      ]
    });
    
    return response.choices[0].message.content;
  } catch (error) {
    console.error('[Simple Memory] Error extracting memory:', error);
    return messages; // Fallback to raw messages
  }
}

export const simpleMemoryStore = {
  /**
   * Add a memory
   */
  async add(messages, userId, metadata = {}) {
    try {
      // Extract memory from messages
      const memoryText = await extractMemory(messages);
      
      // Generate embedding
      const embedding = await generateEmbedding(memoryText);
      if (!embedding) {
        throw new Error('Failed to generate embedding');
      }
      
      // Generate memory ID
      const memoryId = crypto.randomUUID();
      
      // Get user memories
      if (!memoryStore.has(userId)) {
        memoryStore.set(userId, []);
      }
      
      const userMemories = memoryStore.get(userId);
      
      // Add new memory
      const memory = {
        id: memoryId,
        memory: memoryText,
        embedding: embedding,
        metadata: {
          ...metadata,
          timestamp: new Date().toISOString(),
          source: 'espressobot'
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      userMemories.push(memory);
      
      return {
        success: true,
        memory_id: memoryId,
        message: "Memory added successfully"
      };
    } catch (error) {
      console.error('[Simple Memory] Add error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  },
  
  /**
   * Search memories by semantic similarity
   */
  async search(query, userId, limit = 5) {
    try {
      const userMemories = memoryStore.get(userId) || [];
      
      if (userMemories.length === 0) {
        return {
          success: true,
          memories: [],
          count: 0
        };
      }
      
      // Generate query embedding
      const queryEmbedding = await generateEmbedding(query);
      if (!queryEmbedding) {
        // Fallback to text search
        const filtered = userMemories.filter(m => 
          m.memory.toLowerCase().includes(query.toLowerCase())
        );
        
        return {
          success: true,
          memories: filtered.slice(0, limit).map(m => ({
            id: m.id,
            memory: m.memory,
            relevance: 1.0,
            metadata: m.metadata
          })),
          count: filtered.length
        };
      }
      
      // Calculate similarities
      const memoriesWithScores = userMemories.map(memory => {
        try {
          // Validate embedding before similarity calculation
          if (!memory.embedding || !Array.isArray(memory.embedding)) {
            console.warn(`[SimpleMemoryStore] Invalid embedding for memory ${memory.id}`);
            return {
              ...memory,
              score: 0
            };
          }
          
          return {
            ...memory,
            score: cosineSimilarity(queryEmbedding, memory.embedding)
          };
        } catch (error) {
          console.error(`[SimpleMemoryStore] Error calculating similarity for memory ${memory.id}:`, error);
          return {
            ...memory,
            score: 0
          };
        }
      });
      
      // Sort by score and take top results
      memoriesWithScores.sort((a, b) => b.score - a.score);
      
      const results = memoriesWithScores.slice(0, limit).map(m => ({
        id: m.id,
        memory: m.memory,
        relevance: m.score,
        metadata: m.metadata
      }));
      
      return {
        success: true,
        memories: results,
        count: results.length
      };
    } catch (error) {
      console.error('[Simple Memory] Search error:', error);
      return {
        success: false,
        error: error.message,
        memories: []
      };
    }
  },
  
  /**
   * Get all memories for a user
   */
  async getAll(userId) {
    try {
      const userMemories = memoryStore.get(userId) || [];
      
      return {
        success: true,
        memories: userMemories.map(m => ({
          id: m.id,
          memory: m.memory,
          metadata: m.metadata
        })),
        count: userMemories.length
      };
    } catch (error) {
      console.error('[Simple Memory] Get all error:', error);
      return {
        success: false,
        error: error.message,
        memories: []
      };
    }
  },
  
  /**
   * Update a memory
   */
  async update(memoryId, userId, text) {
    try {
      const userMemories = memoryStore.get(userId) || [];
      const memoryIndex = userMemories.findIndex(m => m.id === memoryId);
      
      if (memoryIndex === -1) {
        throw new Error('Memory not found');
      }
      
      // Generate new embedding
      const embedding = await generateEmbedding(text);
      if (!embedding) {
        throw new Error('Failed to generate embedding');
      }
      
      // Update memory
      userMemories[memoryIndex] = {
        ...userMemories[memoryIndex],
        memory: text,
        embedding: embedding,
        updatedAt: new Date().toISOString()
      };
      
      return {
        success: true,
        message: "Memory updated successfully"
      };
    } catch (error) {
      console.error('[Simple Memory] Update error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  },
  
  /**
   * Delete a memory
   */
  async delete(memoryId, userId) {
    try {
      const userMemories = memoryStore.get(userId) || [];
      const filteredMemories = userMemories.filter(m => m.id !== memoryId);
      
      if (filteredMemories.length === userMemories.length) {
        throw new Error('Memory not found');
      }
      
      memoryStore.set(userId, filteredMemories);
      
      return {
        success: true,
        message: "Memory deleted successfully"
      };
    } catch (error) {
      console.error('[Simple Memory] Delete error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  },
  
  /**
   * Reset all memories for a user
   */
  async reset(userId) {
    try {
      memoryStore.delete(userId);
      
      return {
        success: true,
        message: "All memories reset successfully"
      };
    } catch (error) {
      console.error('[Simple Memory] Reset error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
};