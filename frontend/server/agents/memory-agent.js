import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { tool } from '@openai/agents';
import { z } from 'zod';
import { spawn } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { ENHANCED_MEMORY_INSTRUCTIONS } from './enhanced-instructions.js';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Memory storage tool - stores new memories
const storeMemoryTool = tool({
  name: 'store_memory',
  description: 'Store a new memory or important information for future reference',
  parameters: z.object({
    content: z.string().describe('The content to store in memory'),
    tags: z.array(z.string()).nullable().default([]).describe('Optional tags to categorize the memory'),
    metadata: z.record(z.string()).nullable().default({}).describe('Optional metadata key-value pairs')
  }),
  execute: async ({ content, tags = [], metadata = {} }) => {
    try {
      // Use the MCP memory server via command line
      const memoryData = {
        content,
        tags,
        metadata: {
          ...metadata,
          timestamp: new Date().toISOString(),
          source: 'memory_agent'
        }
      };

      // Call the MCP memory server to store the memory
      const result = await new Promise((resolve, reject) => {
        const proc = spawn('npx', [
          '-y',
          '@modelcontextprotocol/server-memory',
          'store',
          JSON.stringify(memoryData)
        ], {
          env: {
            ...process.env,
            MEMORY_FILE_PATH: process.env.MEMORY_FILE_PATH || '.memories/memory.json'
          }
        });

        let output = '';
        let error = '';

        proc.stdout.on('data', (data) => {
          output += data.toString();
        });

        proc.stderr.on('data', (data) => {
          error += data.toString();
        });

        proc.on('close', (code) => {
          if (code === 0) {
            resolve({ success: true, output });
          } else {
            reject(new Error(`Memory storage failed: ${error}`));
          }
        });
      });

      return { success: true, message: 'Memory stored successfully', details: result };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
});

// Memory search tool - searches existing memories
const searchMemoryTool = tool({
  name: 'search_memory',
  description: 'Search for existing memories based on query or similarity',
  parameters: z.object({
    query: z.string().describe('The search query to find relevant memories'),
    limit: z.number().default(5).describe('Maximum number of results to return'),
    threshold: z.number().default(0.7).describe('Similarity threshold (0-1)')
  }),
  execute: async ({ query, limit, threshold }) => {
    try {
      // Use the memory embeddings search functionality
      const memoryEmbeddings = await import('../memory-embeddings.js');
      // Use findRelevantMemories instead of the non-existent memorySearch
      const results = await memoryEmbeddings.findRelevantMemories(query, 1, limit); // userId defaults to 1
      
      // Filter by threshold (relevance_score is returned by findRelevantMemories)
      const filteredResults = results.filter(r => (r.relevance_score || r.similarity) >= threshold);
      
      return {
        success: true,
        results: filteredResults,
        count: filteredResults.length
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
});

// Deduplication check tool
const checkDuplicateTool = tool({
  name: 'check_duplicate',
  description: 'Check if a memory or information already exists to avoid duplicates',
  parameters: z.object({
    content: z.string().describe('The content to check for duplicates'),
    threshold: z.number().default(0.85).describe('Similarity threshold for duplicate detection')
  }),
  execute: async ({ content, threshold }) => {
    try {
      const memoryEmbeddings = await import('../memory-embeddings.js');
      // Use findRelevantMemories instead of the non-existent memorySearch
      const results = await memoryEmbeddings.findRelevantMemories(content, 1, 3); // userId defaults to 1
      
      const duplicates = results.filter(r => (r.relevance_score || r.similarity) >= threshold);
      
      return {
        hasDuplicates: duplicates.length > 0,
        duplicates: duplicates,
        highestSimilarity: duplicates.length > 0 ? duplicates[0].similarity : 0
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
});

// Use enhanced instructions with domain knowledge
const memoryAgentInstructions = ENHANCED_MEMORY_INSTRUCTIONS + `

Deduplication Process:
1. Before storing any new memory, use check_duplicate to see if similar content exists
2. If highly similar content exists (>0.85 similarity), don't store unless it adds significant new information
3. Consider merging similar memories rather than creating duplicates

If asked to search for products (like "Eureka Mignon Zero"), immediately:
1. Respond: "I only manage conversation memories. For product searches, I need to hand you back to the orchestrator."
2. Hand off to EspressoBot_Orchestrator with message: "User needs product search for [product name]. Please route to Product Update Agent."`;

// Create the Memory Agent
export const memoryAgent = new Agent({
  name: 'Memory_Agent',
  instructions: memoryAgentInstructions,
  handoffDescription: 'Hand off to Memory Agent for storing or retrieving memories, checking for duplicates, or managing the knowledge base',
  model: 'gpt-4.1-mini',  // Using gpt-4.1-mini as it doesn't need heavy reasoning
  tools: [
    storeMemoryTool,
    searchMemoryTool,
    checkDuplicateTool
  ],
  handoffs: [], // Will be populated by orchestrator
  modelSettings: {
    temperature: 0.3,  // Lower temperature for consistent memory operations
    parallelToolCalls: false,
  }
});

console.log('✅ Memory Agent initialized with deduplication capabilities');