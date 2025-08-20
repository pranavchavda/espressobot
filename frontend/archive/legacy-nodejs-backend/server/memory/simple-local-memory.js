/**
 * Simple Local Memory Implementation - PostgreSQL/Prisma Version
 * Uses Supabase PostgreSQL for storage and OpenAI embeddings for semantic search
 * Migrated from SQLite to PostgreSQL/Prisma
 */

import { OpenAI } from 'openai';
import { createOpenAIWithRetry } from '../utils/openai-with-retry.js';
import { db, withRetry } from '../config/database.js';

// Initialize Prisma client for PostgreSQL
const prisma = db;

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
  
  // Handle already parsed arrays
  if (Array.isArray(buffer)) {
    return buffer;
  }
  
  let dataStr = '';
  
  // Handle different buffer formats
  if (Buffer.isBuffer(buffer)) {
    dataStr = buffer.toString('utf8');
  } else if (buffer instanceof Uint8Array) {
    dataStr = Buffer.from(buffer).toString('utf8');
  } else if (buffer && typeof buffer === 'object' && buffer.constructor === Object && buffer.type === 'Buffer') {
    dataStr = Buffer.from(buffer.data || buffer).toString('utf8');
  } else if (typeof buffer === 'string') {
    dataStr = buffer;
  } else {
    console.warn('[Memory] Unknown buffer format:', typeof buffer, buffer.constructor?.name);
    return null;
  }
  
  try {
    // First try to parse as JSON array (new format)
    if (dataStr.trim().startsWith('[')) {
      return JSON.parse(dataStr);
    }
    
    // Handle comma-separated values format (current format in database)
    if (dataStr.includes(',')) {
      const numbers = dataStr.split(',').map(s => parseFloat(s.trim()));
      // Validate that all values are valid numbers
      if (numbers.every(n => !isNaN(n) && isFinite(n))) {
        return numbers;
      }
    }
    
    // If all else fails, try to parse as JSON anyway
    return JSON.parse(dataStr);
    
  } catch (error) {
    console.warn('[Memory] Failed to parse embedding data:', error.message, 'First 100 chars:', dataStr.substring(0, 100));
    return null;
  }
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
    threshold = 0.7, // Semantic similarity threshold for deduplication
    strategy = 'hybrid', // 'exact', 'fuzzy', 'semantic', 'hybrid'
    useNano = false
  } = options;

  console.log(`[Memory] Searching memories for user ${userId} with strategy: ${strategy}`);

  let results = [];

  try {
    // Quick database connectivity check
    const client = await import('../config/database.js').then(m => m.getPrismaClient());
    if (!client) {
      console.warn('[Memory] Database client unavailable, returning empty results');
      return [];
    }
    // Step 1: Exact text search (highest priority)
    if (strategy === 'exact' || strategy === 'hybrid') {
      const exactResults = await withRetry(async (client) => {
        return await client.memories.findMany({
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
      });

      results = exactResults.map(memory => ({
        ...memory,
        similarity: 1.0,
        strategy: 'exact'
      }));

      console.log(`[Memory] Found ${results.length} exact matches`);
    }

    // Step 2: High-quality semantic search (second priority, >0.7 threshold)
    if ((strategy === 'semantic' || strategy === 'hybrid') && results.length < limit) {
      const queryEmbedding = await createEmbedding(query);
      const remaining = limit - results.length;

      // Get all memories with embeddings for this user
      const memoriesWithEmbeddings = await withRetry(async (client) => {
        return await client.memories.findMany({
          where: {
            user_id: userId,
            embedding: { not: null }
          },
          orderBy: { created_at: 'desc' }
        });
      });

      console.log(`[Memory] Found ${memoriesWithEmbeddings.length} memories with embeddings for ${userId}`);

      // Calculate similarities with debug logging
      const allSimilarities = memoriesWithEmbeddings
        .map((memory, index) => {
          const embedding = bufferToFloatArray(memory.embedding);
          if (!embedding || !Array.isArray(embedding)) {
            console.log(`[Memory] Skipping memory ${index}: invalid embedding (${typeof embedding})`);
            return null;
          }

          const similarity = cosineSimilarity(queryEmbedding, embedding);
          if (index < 3) {
            console.log(`[Memory] Memory ${index} similarity: ${similarity.toFixed(4)} (query dims: ${queryEmbedding.length}, memory dims: ${embedding.length})`);
          }
          
          return {
            ...memory,
            similarity,
            strategy: 'semantic'
          };
        })
        .filter(result => result !== null)
        .sort((a, b) => b.similarity - a.similarity);

      // Debug: Log top similarities to understand distribution
      if (allSimilarities.length > 0) {
        const topSimilarities = allSimilarities.slice(0, 3).map(r => r.similarity.toFixed(3));
        console.log(`[Memory] Top semantic similarities: [${topSimilarities.join(', ')}] (threshold: ${threshold})`);
      }

      const semanticResults = allSimilarities
        .filter(result => result.similarity >= threshold)
        .filter(memory => !results.some(r => r.id === memory.id))
        .slice(0, remaining);

      results = [...results, ...semanticResults];
      console.log(`[Memory] Added ${semanticResults.length} high-quality semantic matches (>${threshold})`);
    }

    // Step 3: Fuzzy search as fallback (lowest priority)
    if ((strategy === 'fuzzy' || strategy === 'hybrid') && results.length < limit) {
      const remaining = limit - results.length;
      const words = query.toLowerCase().split(' ').filter(word => word.length > 2);
      
      let fuzzyResults = [];
      if (words.length > 0) {
        // Search for memories containing any of the words
        fuzzyResults = await withRetry(async (client) => {
          return await client.memories.findMany({
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
        });
      }

      const newResults = fuzzyResults
        .filter(memory => !results.some(r => r.id === memory.id))
        .map(memory => ({
          ...memory,
          similarity: 0.6, // Lower score for fuzzy matches
          strategy: 'fuzzy'
        }));

      results = [...results, ...newResults];
      console.log(`[Memory] Added ${newResults.length} fuzzy matches as fallback`);
    }

    // Sort by similarity and limit
    results = results
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, limit);

    console.log(`[Memory] Returning ${results.length} total results (exact: ${results.filter(r => r.strategy === 'exact').length}, semantic: ${results.filter(r => r.strategy === 'semantic').length}, fuzzy: ${results.filter(r => r.strategy === 'fuzzy').length})`);
    return results;

  } catch (error) {
    console.error('[Memory] Error searching memories:', error);
    
    // If it's a database connection error, return empty results instead of throwing
    if (error.message.includes('Engine is not yet connected') || 
        error.message.includes('Connection') ||
        error.message.includes('Closed')) {
      console.warn('[Memory] Database connection failed, returning empty results for graceful degradation');
      return [];
    }
    
    throw error;
  }
}

/**
 * Add a new memory
 */
async function addMemory(content, userId, metadata = null, options = {}) {
  const { 
    useNano = false,
    skipEmbedding = false,
    skipDeduplication = false,
    deduplicationThreshold = 0.7 // Use same threshold as search for consistent deduplication
  } = options;

  console.log(`[Memory] Adding memory for user ${userId}. Content length: ${content.length}`);

  // Skip empty or very short memories
  if (!content || content.trim().length < 10) {
    console.log('[Memory] Skipping empty or very short memory');
    return null;
  }

  try {
    // Check for duplicates before adding (unless skipped)
    if (!skipDeduplication) {
      const similarMemories = await searchMemories(content, userId, {
        limit: 5,
        threshold: deduplicationThreshold,
        strategy: 'semantic'
      });

      if (similarMemories.length > 0) {
        console.log(`[Memory] Found ${similarMemories.length} similar memories with threshold ${deduplicationThreshold}, skipping duplicate`);
        console.log(`[Memory] Most similar: "${similarMemories[0].content.substring(0, 100)}..." (similarity: ${similarMemories[0].similarity?.toFixed(3)})`);
        return similarMemories[0]; // Return existing memory instead
      }
    }

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
    const memory = await withRetry(async (client) => {
      return await client.memories.create({
        data: {
          id,
          user_id: userId,
          content,
          embedding,
          metadata: metadata ? JSON.stringify(metadata) : null,
          updated_at: new Date()
        }
      });
    });

    console.log(`[Memory] Successfully added memory ${id}`);
    return memory;

  } catch (error) {
    console.error('[Memory] Error adding memory:', error);
    
    // If it's a database connection error, return null instead of throwing
    if (error.message.includes('Engine is not yet connected') || 
        error.message.includes('Connection') ||
        error.message.includes('Closed')) {
      console.warn('[Memory] Database connection failed, memory not stored (graceful degradation)');
      return null;
    }
    
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
    const memory = await withRetry(async (client) => {
      return await client.memories.update({
        where: { id: memoryId },
        data: {
          content,
          embedding,
          metadata: metadata ? JSON.stringify(metadata) : null,
          updated_at: new Date()
        }
      });
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
    await withRetry(async (client) => {
      return await client.memories.delete({
        where: { id: memoryId }
      });
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
    const result = await withRetry(async (client) => {
      return await client.memories.deleteMany({
        where: { user_id: userId }
      });
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
    const memories = await withRetry(async (client) => {
      return await client.memories.findMany({
        where: { user_id: userId },
        orderBy: { created_at: 'desc' },
        take: limit,
        skip: offset
      });
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
    const totalCount = await withRetry(async (client) => {
      return await client.memories.count();
    });
    
    const userStats = await withRetry(async (client) => {
      return await client.memories.groupBy({
        by: ['user_id'],
        _count: {
          user_id: true
        }
      });
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
  add: async (content, userId, metadata = {}) => {
    return await addMemory(content, userId, metadata);
  },

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
  },

  // Memory extraction methods
  extractMemorySummary: async (conversationText, context = {}) => {
    // Determine which model to use based on context or environment
    const useNano = process.env.USE_GPT_NANO_FOR_MEMORY === 'true' || context.useNano;
    const model = useNano ? 'gpt-4.1-nano' : 'o4-mini';
    
    try {
      console.log(`[Memory] Using ${model} for extraction`);
      
      // Split long conversations into exchanges
      const exchanges = simpleLocalMemory.splitIntoExchanges(conversationText);
      const allFacts = [];
      
      // Process each exchange separately (max 2 facts per exchange)
      for (const exchange of exchanges) {
        if (exchange.trim().length < 20) continue; // Skip very short exchanges
        
        // Use GPT to extract key facts from this exchange
        const response = await openai.chat.completions.create({
          model: model,
          messages: [
            {
              role: 'system',
              content: `You are a memory extraction system. Extract important facts from conversations as single, self-contained sentences. Each fact should be independently understandable without context.
Rules:
1. Extract facts worth remembering long-term, not temporary conversation state
2. Each fact must be a complete, standalone sentence
3. Maximum 2 facts per message exchange (user message + assistant response)
4. You don't have to extract facts from every exchange. If you don't see any facts, just return an empty list.
5. ALWAYS extract when user says "remember that" or "remember this" or similar
6. Include confirmed facts from assistant responses (e.g., "The CEO is X" when user confirms)
7. Focus on: personal info, preferences, business context, decisions, confirmed information, future plans, and any other relevant information.
8. Format: Return each fact on a new line
Priority facts to extract:
- Explicit "remember" requests: User says to remember something
- Personal information: Names, roles, birthdays, locations
- Preferences: "I prefer X", "I like Y", "My favorite is Z"  
- Business facts: Company info, project names, important metrics
- Confirmed corrections: When user corrects or confirms information
Good examples:
- The user's name is Pranav.
- Pranav works as a generalist at iDrinkCoffee.com.
- Bruno is a customer support chatbot project.
- Espressobot is one of Pranav's recent projects.
- The user prefers to review changes before applying them.
- The CEO of iDrinkCoffee.com is Slawek Janicki.
Do NOT extract:
- Questions or requests: "Can you help with X?"
- Temporary states: "User is looking at Y"
- Process descriptions: "User is focused on gathering requirements"
- Unconfirmed suggestions: "You might want to try X"`
            },
            {
              role: 'user',
              content: exchange
            }
          ],
          reasoning_effort: 'low'
        });
        
        const exchangeFacts = response.choices[0].message.content
          .split('\n')
          .filter(line => line.trim().length > 0)
          .map(fact => fact.trim())
          .slice(0, 2);  // Enforce max 2 facts per exchange
        allFacts.push(...exchangeFacts);
      }
      
      console.log(`[Memory] Extracted ${allFacts.length} total facts from ${exchanges.length} exchanges`);
      
      return allFacts.map(fact => ({
        content: fact,
        metadata: {
          timestamp: new Date().toISOString(),
          conversationId: context.conversationId || 'unknown',
          agent: context.agent || 'unknown',
          extractedFrom: 'conversation',
          source: model
        }
      }));
    } catch (error) {
      console.error(`Error extracting memory with ${model}:`, error);
      
      // Fallback to simple extraction
      const lines = conversationText.trim().split('\n').filter(line => line.trim());
      const summary = lines
        .filter(line => line.includes('User:') || line.includes('Assistant:'))
        .join(' ')
        .replace(/User:|Assistant:/g, '')
        .trim();
      
      return [{
        content: summary,
        metadata: {
          timestamp: new Date().toISOString(),
          conversationId: context.conversationId || 'unknown',
          agent: context.agent || 'unknown',
          extractedFrom: 'conversation',
          source: 'fallback'
        }
      }];
    }
  },

  // Helper method for extractMemorySummary
  splitIntoExchanges: (conversationText) => {
    // Try to split by User:/Assistant: pattern
    const lines = conversationText.split('\n');
    const exchanges = [];
    let currentExchange = '';
    
    for (const line of lines) {
      if (line.startsWith('User:') && currentExchange.includes('Assistant:')) {
        // Start of new exchange, save the previous one
        exchanges.push(currentExchange.trim());
        currentExchange = line;
      } else {
        currentExchange += '\n' + line;
      }
    }
    
    // Don't forget the last exchange
    if (currentExchange.trim()) {
      exchanges.push(currentExchange.trim());
    }
    
    // If no clear pattern, just return the whole conversation
    if (exchanges.length === 0) {
      return [conversationText];
    }
    
    return exchanges;
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