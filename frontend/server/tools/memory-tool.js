/**
 * Memory tool wrapper for mem0 integration
 * Provides memory operations for EspressoBot using JavaScript SDK
 */

import { z } from 'zod';
import { tool } from '@openai/agents';
import { handleMemoryOperation } from '../memory/memory-operations.js';

// Memory tool for agents
export const memoryTool = tool({
  name: 'memory_operations',
  description: 'Store and retrieve conversation context and user preferences. Use this to remember important information across conversations.',
  parameters: z.object({
    operation: z.enum(['add', 'search', 'get_all', 'update', 'delete', 'reset'])
      .describe('The memory operation to perform'),
    messages: z.string().nullable().optional()
      .describe('The conversation context to store (for add operation)'),
    query: z.string().nullable().optional()
      .describe('The search query to find relevant memories (for search operation)'),
    user_id: z.string()
      .describe('The user/conversation ID'),
    memory_id: z.string().nullable().optional()
      .describe('The specific memory ID (for update/delete operations)'),
    text: z.string().nullable().optional()
      .describe('The updated text (for update operation)'),
    limit: z.number().nullable().optional()
      .describe('Maximum number of memories to return (for search operation)'),
    metadata: z.record(z.any()).nullable().optional()
      .describe('Additional metadata to store with the memory')
  }),
  execute: async (params) => {
    try {
      console.log('[Memory Tool] Executing operation:', params.operation);
      
      // Convert null values to undefined for consistency
      const cleanParams = {
        operation: params.operation,
        user_id: params.user_id,
        ...(params.messages !== null && params.messages !== undefined && { messages: params.messages }),
        ...(params.query !== null && params.query !== undefined && { query: params.query }),
        ...(params.memory_id !== null && params.memory_id !== undefined && { memory_id: params.memory_id }),
        ...(params.text !== null && params.text !== undefined && { text: params.text }),
        ...(params.limit !== null && params.limit !== undefined && { limit: params.limit || 5 }),
        ...(params.metadata !== null && params.metadata !== undefined && { metadata: params.metadata })
      };
      
      const result = await handleMemoryOperation(cleanParams);
      
      // Format response based on operation
      if (params.operation === 'search' && result.memories) {
        // Format search results for agent consumption
        const formattedMemories = result.memories
          .map(m => `[${m.relevance.toFixed(2)}] ${m.memory}`)
          .join('\n');
        
        return {
          success: true,
          message: result.count > 0 
            ? `Found ${result.count} relevant memories:\n${formattedMemories}`
            : 'No relevant memories found',
          memories: result.memories
        };
      }
      
      return result;
    } catch (error) {
      console.error('[Memory Tool] Error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
});

// Helper functions for direct use (not through agents)
export const memoryOperations = {
  /**
   * Add memory from conversation context
   */
  async add(messages, userId, metadata = {}) {
    return handleMemoryOperation({
      operation: 'add',
      messages,
      user_id: userId,
      metadata
    });
  },
  
  /**
   * Search for relevant memories
   */
  async search(query, userId, limit = 5) {
    return handleMemoryOperation({
      operation: 'search',
      query,
      user_id: userId,
      limit
    });
  },
  
  /**
   * Get all memories for a user
   */
  async getAll(userId) {
    return handleMemoryOperation({
      operation: 'get_all',
      user_id: userId
    });
  },
  
  /**
   * Reset all memories for a user
   */
  async reset(userId) {
    return handleMemoryOperation({
      operation: 'reset',
      user_id: userId
    });
  }
};