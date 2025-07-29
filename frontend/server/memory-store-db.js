import prisma from './lib/prisma.js';
import { v4 as uuidv4 } from 'uuid';

class DatabaseMemoryStore {
  // Create a new memory
  async createMemory(userId, content, metadata = {}) {
    try {
      // Check if we already have a similar memory (deduplication)
      const existingMemory = await this.findSimilarMemory(userId, content);
      if (existingMemory) {
        console.log('[Memory Store] Found similar existing memory, skipping creation');
        return existingMemory;
      }
      
      // First create the memory
      const memory = await prisma.user_memories.create({
        data: {
          user_id: userId,
          key: `mem_${uuidv4()}`,
          value: JSON.stringify({
            content,
            category: metadata.category || 'general',
            importance: metadata.importance || 'medium',
            source: metadata.source || 'conversation',
            conversation_id: metadata.conversation_id || null,
            timestamp: new Date().toISOString(),
            ...metadata
          }),
          created_at: new Date()
        }
      });
      
      // If we have an embedding, store it in the cache
      if (metadata.embedding) {
        const embeddingCache = await prisma.embedding_cache.create({
          data: {
            text_hash: this.hashText(content),
            text_content: content,
            embedding_data: Buffer.from(JSON.stringify(metadata.embedding)),
            model_name: metadata.embedding_model || 'text-embedding-3-small',
            created_at: new Date(),
            last_accessed: new Date()
          }
        });
        
        // Link the embedding to the memory
        await prisma.user_memory_embeddings.create({
          data: {
            user_id: userId,
            memory_key: memory.key,
            embedding_cache_id: embeddingCache.id,
            created_at: new Date()
          }
        });
      }
      
      return {
        id: memory.key,
        user_id: memory.user_id,
        ...JSON.parse(memory.value),
        created_at: memory.created_at
      };
    } catch (error) {
      console.error('[Memory Store] Error creating memory:', error);
      throw error;
    }
  }
  
  // Get all memories for a user
  async getMemoriesByUser(userId) {
    try {
      const memories = await prisma.user_memories.findMany({
        where: { user_id: userId },
        orderBy: { created_at: 'desc' }
      });
      
      return memories.map(m => ({
        id: m.key,
        user_id: m.user_id,
        ...JSON.parse(m.value),
        created_at: m.created_at
      }));
    } catch (error) {
      console.error('[Memory Store] Error getting memories:', error);
      return [];
    }
  }
  
  // Get memory by ID
  async getMemoryById(memoryId) {
    try {
      const memory = await prisma.user_memories.findUnique({
        where: { key: memoryId }
      });
      
      if (!memory) return null;
      
      return {
        id: memory.key,
        user_id: memory.user_id,
        ...JSON.parse(memory.value),
        created_at: memory.created_at
      };
    } catch (error) {
      console.error('[Memory Store] Error getting memory by ID:', error);
      return null;
    }
  }
  
  // Update a memory
  async updateMemory(memoryId, updates) {
    try {
      const memory = await prisma.user_memories.findUnique({
        where: { key: memoryId }
      });
      
      if (!memory) return null;
      
      const currentValue = JSON.parse(memory.value);
      const updatedValue = { ...currentValue, ...updates };
      
      const updated = await prisma.user_memories.update({
        where: { key: memoryId },
        data: {
          value: JSON.stringify(updatedValue),
          updated_at: new Date()
        }
      });
      
      return {
        id: updated.key,
        user_id: updated.user_id,
        ...JSON.parse(updated.value),
        created_at: updated.created_at
      };
    } catch (error) {
      console.error('[Memory Store] Error updating memory:', error);
      return null;
    }
  }
  
  // Delete a memory
  async deleteMemory(memoryId) {
    try {
      // First delete the embedding link
      await prisma.user_memory_embeddings.deleteMany({
        where: { memory_key: memoryId }
      });
      
      // Then delete the memory
      const deleted = await prisma.user_memories.delete({
        where: { key: memoryId }
      });
      
      return {
        id: deleted.key,
        user_id: deleted.user_id,
        ...JSON.parse(deleted.value),
        created_at: deleted.created_at
      };
    } catch (error) {
      console.error('[Memory Store] Error deleting memory:', error);
      return null;
    }
  }
  
  // Get memories with embeddings for semantic search
  async getMemoriesWithEmbeddings(userId) {
    try {
      // First get all user memories
      const memories = await prisma.user_memories.findMany({
        where: { user_id: userId },
        orderBy: { created_at: 'desc' }
      });
      
      // Then get embeddings for these memories
      const memoryKeys = memories.map(m => m.key);
      const embeddings = await prisma.user_memory_embeddings.findMany({
        where: {
          user_id: userId,
          memory_key: { in: memoryKeys }
        },
        include: {
          embedding_cache: true
        }
      });
      
      // Create a map of memory_key to embedding for quick lookup
      const embeddingMap = new Map();
      embeddings.forEach(e => {
        embeddingMap.set(e.memory_key, e);
      });
      
      // Join memories with their embeddings
      return memories
        .filter(m => embeddingMap.has(m.key))
        .map(m => {
          const embeddingEntry = embeddingMap.get(m.key).embedding_cache;
          let embeddingData = null;
          
          try {
            // Handle Buffer data properly
            if (Buffer.isBuffer(embeddingEntry.embedding_data)) {
              const embeddingString = embeddingEntry.embedding_data.toString('utf8');
              embeddingData = JSON.parse(embeddingString);
            } else if (typeof embeddingEntry.embedding_data === 'string') {
              embeddingData = JSON.parse(embeddingEntry.embedding_data);
            } else {
              embeddingData = embeddingEntry.embedding_data;
            }
          } catch (parseError) {
            console.error(`Failed to parse embedding for memory ${m.key}:`, parseError.message);
            embeddingData = null;
          }
          
          return {
            id: m.key,
            user_id: m.user_id,
            ...JSON.parse(m.value),
            created_at: m.created_at,
            embedding: embeddingData
          };
        });
    } catch (error) {
      console.error('[Memory Store] Error getting memories with embeddings:', error);
      return [];
    }
  }
  
  // Find similar memory (simple deduplication)
  async findSimilarMemory(userId, content, threshold = 0.9) {
    try {
      const userMemories = await this.getMemoriesByUser(userId);
      
      for (const memory of userMemories) {
        const similarity = this.calculateTextSimilarity(memory.content, content);
        if (similarity > threshold) {
          return memory;
        }
      }
      
      return null;
    } catch (error) {
      console.error('[Memory Store] Error finding similar memory:', error);
      return null;
    }
  }
  
  // Prune old memories if over limit
  async pruneMemories(userId, maxMemories = 1000) {
    try {
      const memories = await this.getMemoriesByUser(userId);
      
      if (memories.length <= maxMemories) return;
      
      // Sort by importance and timestamp
      const sorted = memories.sort((a, b) => {
        const importanceOrder = { high: 3, medium: 2, low: 1 };
        const importanceDiff = (importanceOrder[b.importance] || 2) - 
                               (importanceOrder[a.importance] || 2);
        if (importanceDiff !== 0) return importanceDiff;
        
        return new Date(b.created_at) - new Date(a.created_at);
      });
      
      // Delete excess memories
      const toDelete = sorted.slice(maxMemories);
      for (const memory of toDelete) {
        await this.deleteMemory(memory.id);
      }
      
      console.log(`[Memory Store] Pruned ${toDelete.length} memories for user ${userId}`);
    } catch (error) {
      console.error('[Memory Store] Error pruning memories:', error);
    }
  }
  
  // Simple text similarity (Jaccard similarity)
  calculateTextSimilarity(text1, text2) {
    const words1 = new Set(text1.toLowerCase().split(/\s+/));
    const words2 = new Set(text2.toLowerCase().split(/\s+/));
    
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);
    
    return intersection.size / union.size;
  }
  
  // Hash text for embedding cache
  hashText(text) {
    // Simple hash function for text
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      const char = text.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return hash.toString(36);
  }
}

// Export singleton instance
export const memoryStore = new DatabaseMemoryStore();