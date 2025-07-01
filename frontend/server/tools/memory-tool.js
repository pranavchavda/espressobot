/**
 * Memory tool wrapper for local memory system
 * Provides memory operations for EspressoBot using SQLite and embeddings
 */

import { z } from 'zod';
import { tool } from '@openai/agents';
import { memoryOperations } from '../memory/memory-operations-local.js';

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
      const userId = params.user_id || 'default_user';
      
      switch (params.operation) {
        case 'add':
          if (!params.messages) {
            return { success: false, error: 'Messages required for add operation' };
          }
          const addResult = await memoryOperations.add(params.messages, userId, params.metadata || {});
          return {
            success: true,
            message: 'Memory added successfully',
            result: addResult
          };
          
        case 'search':
          if (!params.query) {
            return { success: false, error: 'Query required for search operation' };
          }
          const memories = await memoryOperations.search(params.query, userId, params.limit || 5);
          const formattedMemories = memories
            .map((m, idx) => `[${idx + 1}] ${m.memory || m}`)
            .join('\n');
          
          return {
            success: true,
            message: memories.length > 0 
              ? `Found ${memories.length} relevant memories:\n${formattedMemories}`
              : 'No relevant memories found',
            memories
          };
          
        case 'get_all':
          const allMemories = await memoryOperations.getAll(userId);
          return {
            success: true,
            memories: allMemories,
            count: allMemories.length
          };
          
        case 'update':
          if (!params.memory_id || !params.text) {
            return { success: false, error: 'Memory ID and text required for update operation' };
          }
          await memoryOperations.update(params.memory_id, params.text);
          return { success: true, message: 'Memory updated successfully' };
          
        case 'delete':
          if (!params.memory_id) {
            return { success: false, error: 'Memory ID required for delete operation' };
          }
          await memoryOperations.delete(params.memory_id);
          return { success: true, message: 'Memory deleted successfully' };
          
        case 'reset':
          await memoryOperations.deleteAll(userId);
          return { success: true, message: 'All memories reset successfully' };
          
        default:
          return { success: false, error: `Unknown operation: ${params.operation}` };
      }
    } catch (error) {
      console.error('[Memory Tool] Error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
});

// Re-export the local memory operations for direct use (not through agents)
export { memoryOperations };