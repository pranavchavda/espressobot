/**
 * Memory operations for EspressoBot
 * Supports Mem0 Platform (hosted), self-hosted, and simple fallback
 */

import { memoryClient, isPlatformAvailable } from './mem0-platform-config.js';
import { simpleMemoryStore } from './simple-memory-store.js';

// Determine which memory system to use
const usingPlatform = isPlatformAvailable && memoryClient;
const activeMemory = usingPlatform ? memoryClient : simpleMemoryStore;

console.log(`[Memory Operations] Using ${usingPlatform ? 'Mem0 Platform (hosted)' : 'simple memory store'}`);

/**
 * Add a memory from conversation
 */
export async function addMemory(messages, userId, metadata = {}) {
  try {
    if (usingPlatform) {
      // Platform API expects messages array format
      const messagesArray = typeof messages === 'string' 
        ? parseMessagesString(messages)
        : messages;
      
      const result = await activeMemory.add(messagesArray, { 
        user_id: userId,
        metadata 
      });
      
      // Platform returns array of memory events
      const memories = Array.isArray(result) ? result : [];
      const memoryIds = memories.map(r => r.id).filter(Boolean);
      const extractedFacts = memories.map(m => m.data?.memory || m.memory).filter(Boolean);
      
      return {
        success: true,
        memory_id: memoryIds[0] || 'unknown',
        memory_ids: memoryIds,
        memories: extractedFacts,
        message: `Memory added successfully (${memoryIds.length} facts extracted)`
      };
    } else {
      // Simple store uses string format
      return await activeMemory.add(messages, userId, metadata);
    }
  } catch (error) {
    console.error('[Memory Operations] Error adding memory:', error);
    return {
      success: false,
      error: error.message,
      message: 'Failed to add memory'
    };
  }
}

/**
 * Search memories for a user
 */
export async function searchMemories(query, userId, limit = 5) {
  try {
    if (usingPlatform) {
      // Platform API requires different format
      const searchParams = {
        query: query || "",  // Ensure query is not null/undefined
        user_id: userId,
        limit
      };
      
      const result = await activeMemory.search(searchParams.query, searchParams);
      
      // Platform returns array directly
      const memories = (Array.isArray(result) ? result : []).map(mem => ({
        id: mem.id,
        memory: mem.memory,
        relevance: mem.score || 0,
        metadata: mem.metadata || {}
      }));
      
      return {
        success: true,
        memories,
        count: memories.length
      };
    } else {
      // Simple store search
      return await activeMemory.search(query, userId, limit);
    }
  } catch (error) {
    console.error('[Memory Operations] Error searching memories:', error);
    return {
      success: false,
      error: error.message,
      memories: [],
      count: 0
    };
  }
}

/**
 * Get all memories for a user
 */
export async function getAllMemories(userId) {
  try {
    if (usingPlatform) {
      // Platform doesn't have a direct getAll, use search with broad query
      const result = await activeMemory.search("*", {
        user_id: userId,
        limit: 100
      });
      
      const memories = (Array.isArray(result) ? result : []).map(mem => ({
        id: mem.id,
        memory: mem.memory,
        metadata: mem.metadata || {}
      }));
      
      return {
        success: true,
        memories,
        count: memories.length
      };
    } else {
      // Simple store getAll
      return await activeMemory.getAll(userId);
    }
  } catch (error) {
    console.error('[Memory Operations] Error getting all memories:', error);
    return {
      success: false,
      error: error.message,
      memories: [],
      count: 0
    };
  }
}

/**
 * Update a memory
 */
export async function updateMemory(memoryId, memory, userId) {
  try {
    if (usingPlatform) {
      await activeMemory.update({
        memory_id: memoryId,
        memory
      });
      return { success: true, message: 'Memory updated successfully' };
    } else {
      return await activeMemory.update(memoryId, memory, userId);
    }
  } catch (error) {
    console.error('[Memory Operations] Error updating memory:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Delete a memory
 */
export async function deleteMemory(memoryId, userId) {
  try {
    if (usingPlatform) {
      await activeMemory.delete({ memory_id: memoryId });
      return { success: true, message: 'Memory deleted successfully' };
    } else {
      return await activeMemory.delete(memoryId, userId);
    }
  } catch (error) {
    console.error('[Memory Operations] Error deleting memory:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Reset all memories for a user
 */
export async function resetMemories(userId) {
  try {
    if (usingPlatform) {
      await activeMemory.deleteAll({ user_id: userId });
      return { success: true, message: 'All memories reset' };
    } else {
      return await activeMemory.reset(userId);
    }
  } catch (error) {
    console.error('[Memory Operations] Error resetting memories:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Parse a string format message into array format for platform API
 */
function parseMessagesString(messagesStr) {
  const lines = messagesStr.split('\n');
  const messages = [];
  
  for (const line of lines) {
    if (line.startsWith('User:')) {
      messages.push({ role: 'user', content: line.substring(5).trim() });
    } else if (line.startsWith('Assistant:')) {
      messages.push({ role: 'assistant', content: line.substring(10).trim() });
    }
  }
  
  return messages;
}

// Main entry point for the Python-compatible API
export async function main(args) {
  const { operation, messages, query, user_id, memory_id, memory, metadata, limit } = args;
  
  switch (operation) {
    case 'add':
      return await addMemory(messages, user_id, metadata);
    case 'search':
      return await searchMemories(query, user_id, limit);
    case 'get_all':
      return await getAllMemories(user_id);
    case 'update':
      return await updateMemory(memory_id, memory, user_id);
    case 'delete':
      return await deleteMemory(memory_id, user_id);
    case 'reset':
      return await resetMemories(user_id);
    default:
      return { success: false, error: `Unknown operation: ${operation}` };
  }
}

// Alias for backward compatibility
export const handleMemoryOperation = main;