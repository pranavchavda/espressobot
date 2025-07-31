/**
 * Memory Operations using Simple Local Implementation
 * Provides reliable local memory storage with SQLite and OpenAI embeddings
 */

import { simpleLocalMemory as localMemory } from './simple-local-memory.js';

class MemoryOperations {
  constructor() {
    this.memory = localMemory;
  }

  /**
   * Add a memory for a user
   * @param {string} content - The memory content to add
   * @param {string} userId - The user ID
   * @param {Object} metadata - Additional metadata
   * @returns {Promise<Object>} The created memory
   */
  async add(content, userId, metadata = {}) {
    try {
      const result = await this.memory.add(content, userId, {
        ...metadata,
        timestamp: new Date().toISOString(),
        source: 'espressobot'
      });
      
      // Log memory without embedding to keep console clean
      const logResult = { ...result };
      if (logResult.embedding) {
        logResult.embedding = `[${Array.isArray(logResult.embedding) ? logResult.embedding.length : 'unknown'} dimensions]`;
      }
      console.log(`Memory added locally for user ${userId}:`, logResult);
      return result;
    } catch (error) {
      console.error('Error adding memory:', error);
      throw error;
    }
  }

  /**
   * Search memories for a user
   * @param {string} query - The search query
   * @param {string} userId - The user ID
   * @param {number} limit - Maximum number of results
   * @returns {Promise<Array>} Array of matching memories
   */
  async search(query, userId, limit = 10) {
    try {
      const memories = await this.memory.search(query, userId, limit);
      
      console.log(`Found ${memories.length} local memories for user ${userId}`);
      return memories;
    } catch (error) {
      console.error('Error searching memories:', error);
      return [];
    }
  }

  /**
   * Get all memories for a user
   * @param {string} userId - The user ID
   * @param {number} limit - Maximum number of results
   * @returns {Promise<Array>} Array of all memories
   */
  async getAll(userId, limit = 100) {
    try {
      const result = await this.memory.getAll(userId, limit);
      
      return result;
    } catch (error) {
      console.error('Error getting all memories:', error);
      return [];
    }
  }

  /**
   * Update a memory by ID
   * @param {string} memoryId - The memory ID
   * @param {string} content - The new content
   * @returns {Promise<Object>} Update result
   */
  async update(memoryId, content) {
    try {
      const result = await this.memory.update(memoryId, content);
      console.log(`Memory ${memoryId} updated locally`);
      return result;
    } catch (error) {
      console.error('Error updating memory:', error);
      throw error;
    }
  }

  /**
   * Delete a memory by ID
   * @param {string} memoryId - The memory ID
   * @returns {Promise<Object>} Deletion result
   */
  async delete(memoryId) {
    try {
      const result = await this.memory.delete(memoryId);
      console.log(`Memory ${memoryId} deleted locally`);
      return result;
    } catch (error) {
      console.error('Error deleting memory:', error);
      throw error;
    }
  }

  /**
   * Delete all memories for a user
   * @param {string} userId - The user ID
   * @returns {Promise<Object>} Deletion result
   */
  async deleteAll(userId) {
    try {
      const result = await this.memory.deleteAll(userId);
      console.log(`All memories deleted for user ${userId}`);
      return result;
    } catch (error) {
      console.error('Error deleting all memories:', error);
      throw error;
    }
  }

  /**
   * Get memory history (for debugging)
   * @param {string} memoryId - The memory ID
   * @returns {Promise<Array>} History of changes
   */
  async history(memoryId) {
    try {
      const history = await this.memory.history(memoryId);
      return history || [];
    } catch (error) {
      console.error('Error getting memory history:', error);
      return [];
    }
  }

  /**
   * Extract memory summary from a conversation
   * @param {string} conversationText - The conversation text
   * @param {Object} context - Additional context
   * @returns {Object} Extracted summary with content and metadata
   */
  extractMemorySummary(conversationText, context = {}) {
    return this.memory.extractMemorySummary(conversationText, context);
  }

  /**
   * Add a system prompt fragment
   * @param {string} fragment - The prompt fragment
   * @param {Object} metadata - Metadata including category, priority, tags
   * @returns {Promise<Object>} The created fragment
   */
  async addSystemPromptFragment(fragment, metadata = {}) {
    try {
      const result = await this.memory.add(fragment, 'system_prompts', {
        type: 'system_prompt',
        category: metadata.category || 'general',
        priority: metadata.priority || 'medium',
        tags: metadata.tags || [],
        agent_type: metadata.agent_type || 'all',
        ...metadata,
        timestamp: new Date().toISOString()
      });
      
      console.log('System prompt fragment added:', result);
      return result;
    } catch (error) {
      console.error('Error adding system prompt fragment:', error);
      throw error;
    }
  }

  /**
   * Search system prompt fragments
   * @param {string} query - The search query
   * @param {number} limit - Maximum number of results
   * @returns {Promise<Array>} Array of matching fragments
   */
  async searchSystemPromptFragments(query, limit = 10) {
    try {
      const fragments = await this.memory.search(query, 'system_prompts', limit);
      
      console.log(`Found ${fragments.length} system prompt fragments`);
      return fragments;
    } catch (error) {
      console.error('Error searching system prompt fragments:', error);
      return [];
    }
  }

  /**
   * Get all system prompt fragments
   * @param {Object} filter - Optional filter by category or agent_type
   * @param {number} limit - Maximum number of results
   * @returns {Promise<Array>} Array of all fragments
   */
  async getAllSystemPromptFragments(filter = {}, limit = 100) {
    try {
      const allFragments = await this.memory.getAll('system_prompts', limit);
      
      if (filter.category || filter.agent_type) {
        return allFragments.filter(f => {
          const metadata = f.metadata || {};
          return (!filter.category || metadata.category === filter.category) &&
                 (!filter.agent_type || metadata.agent_type === filter.agent_type);
        });
      }
      
      return allFragments;
    } catch (error) {
      console.error('Error getting system prompt fragments:', error);
      return [];
    }
  }
}

// Export singleton instance
export const memoryOperations = new MemoryOperations();