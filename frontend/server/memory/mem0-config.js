/**
 * Mem0 configuration for EspressoBot using JavaScript SDK
 * Self-hosted local memory with in-memory vector store
 */

import { Memory } from 'mem0ai/oss';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create data directory for mem0 if it doesn't exist
const dataDir = path.join(__dirname, 'data');
try {
  await fs.mkdir(dataDir, { recursive: true });
} catch (err) {
  console.error('Error creating data directory:', err);
}

// Configuration for self-hosted mem0
const config = {
  version: "v1.1",
  llm: {
    provider: "openai",
    config: {
      model: "gpt-4.1-mini",
      apiKey: process.env.OPENAI_API_KEY,
      modelProperties: {
        temperature: 0.1,
        max_tokens: 2000,
      }
    }
  },
  embedder: {
    provider: "openai",
    config: {
      model: "text-embedding-3-small",
      apiKey: process.env.OPENAI_API_KEY
    }
  },
  vectorStore: {
    provider: "memory",  // Use in-memory vector store for now
    config: {
      collectionName: "espressobot_memories"
    }
  },
  historyDbPath: path.join(dataDir, "memories.db"),
  disableHistory: true  // Disable history for now to avoid SQLite issues
};

// Initialize memory instance
export let memory = null;

// Defer initialization to avoid SQLite issues at import time
export async function initializeMemory() {
  if (memory) return memory;
  
  try {
    memory = new Memory(config);
    console.log('[Mem0] Self-hosted memory instance initialized successfully');
    return memory;
  } catch (error) {
    console.error('[Mem0] Error initializing self-hosted memory:', error.message);
    
    // If SQLite fails, try without history database
    try {
      const fallbackConfig = {
        ...config,
        historyDbPath: undefined,
        disableHistory: true
      };
      memory = new Memory(fallbackConfig);
      console.log('[Mem0] Memory initialized without history database');
      return memory;
    } catch (fallbackError) {
      console.error('[Mem0] Fallback initialization also failed:', fallbackError.message);
      return null;
    }
  }
}

// Call initialization asynchronously
initializeMemory().catch(console.error);

// Export configuration for reference
export const memoryConfig = config;