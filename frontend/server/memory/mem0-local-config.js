/**
 * Mem0 OSS Local Configuration
 * Using SQLite for memory history and in-memory vector store
 */

import { Memory } from 'mem0ai/oss';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create local memory configuration
const localConfig = {
  version: "v1.1",
  
  // Use OpenAI for embeddings
  embedder: {
    provider: "openai",
    config: {
      model: "text-embedding-3-small",
      apiKey: process.env.OPENAI_API_KEY
    }
  },
  
  // Use in-memory vector store for now (can switch to Qdrant later)
  vectorStore: {
    provider: "memory",
    config: {
      dimension: 1536, // text-embedding-3-small dimension
      collectionName: "espressobot_memories"
    }
  },
  
  // Use OpenAI for LLM operations
  llm: {
    provider: "openai",
    config: {
      model: "gpt-4o-mini",
      apiKey: process.env.OPENAI_API_KEY,
      modelProperties: {
        temperature: 0.1,
        maxTokens: 2000
      }
    }
  },
  
  // Enable SQLite history storage
  historyDbPath: path.join(__dirname, 'data', 'mem0_history.db'),
  
  // Custom prompt for memory extraction (ensure it mentions JSON)
  customPrompt: `You are an expert at analyzing conversations and extracting relevant memories for EspressoBot Shell Agency, an AI system that helps manage e-commerce operations for iDrinkCoffee.com.

Extract and structure memories about:
- User preferences and patterns
- Business context (products, pricing, inventory)
- Task patterns and workflows
- Technical details and configurations
- Important decisions and outcomes

Be concise but capture important context that would be helpful in future conversations. Provide your response in JSON format with the extracted memory.`
};

// Create and export memory instance
export const localMemory = new Memory(localConfig);

console.log('Mem0 OSS configured with local storage');