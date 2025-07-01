/**
 * Hybrid Memory Operations
 * Uses Mem0 Platform when available, falls back to local OSS implementation
 */

import { addMemory, searchMemories, getAllMemories, updateMemory, deleteMemory, resetMemories } from './memory-operations.js';
import { memoryOperations as localMemory } from './memory-operations-local.js';

const USE_PLATFORM = process.env.MEM0_API_KEY && !process.env.MEM0_USE_LOCAL;

class HybridMemoryOperations {
  constructor() {
    console.log(`Using ${USE_PLATFORM ? 'Mem0 Platform' : 'Mem0 OSS Local'} for memory operations`);
  }

  async add(content, userId, metadata = {}) {
    try {
      if (USE_PLATFORM) {
        return await addMemory(content, userId, metadata);
      } else {
        return await localMemory.add(content, userId, metadata);
      }
    } catch (error) {
      console.error('Memory add error:', error);
      if (USE_PLATFORM && (error.response?.status === 403 || error.status === 403)) {
        console.log('API limit reached, falling back to local storage');
        return await localMemory.add(content, userId, metadata);
      }
      throw error;
    }
  }

  async search(query, userId, limit = 10) {
    try {
      if (USE_PLATFORM) {
        const result = await searchMemories(query, userId, limit);
        return result.memories || [];
      } else {
        return await localMemory.search(query, userId, limit);
      }
    } catch (error) {
      console.error('Memory search error:', error);
      if (USE_PLATFORM && (error.response?.status === 403 || error.status === 403)) {
        console.log('API limit reached, falling back to local storage');
        return await localMemory.search(query, userId, limit);
      }
      return [];
    }
  }

  async getAll(userId, limit = 100) {
    try {
      if (USE_PLATFORM) {
        const result = await getAllMemories(userId);
        return result.memories || [];
      } else {
        return await localMemory.getAll(userId, limit);
      }
    } catch (error) {
      console.error('Memory getAll error:', error);
      if (USE_PLATFORM) {
        return await localMemory.getAll(userId, limit);
      }
      return [];
    }
  }

  async update(memoryId, content, userId) {
    if (USE_PLATFORM) {
      return await updateMemory(memoryId, content, userId);
    } else {
      return await localMemory.update(memoryId, content);
    }
  }

  async delete(memoryId, userId) {
    if (USE_PLATFORM) {
      return await deleteMemory(memoryId, userId);
    } else {
      return await localMemory.delete(memoryId);
    }
  }

  async deleteAll(userId) {
    if (USE_PLATFORM) {
      return await resetMemories(userId);
    } else {
      return await localMemory.deleteAll(userId);
    }
  }

  async history(memoryId) {
    if (USE_PLATFORM) {
      // Platform doesn't expose history
      return [];
    } else {
      return await localMemory.history(memoryId);
    }
  }

  extractMemorySummary(conversationText, context = {}) {
    // Simple extraction since both implementations handle this internally
    return `Conversation: ${conversationText}\nContext: ${JSON.stringify(context)}`;
  }
}

export const memoryOperations = new HybridMemoryOperations();