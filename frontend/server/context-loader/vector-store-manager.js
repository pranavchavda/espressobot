/**
 * Vector Store Manager for OpenAI File Search
 * 
 * This module manages the creation and population of OpenAI Vector Stores
 * for our documentation, enabling semantic search through the fileSearchTool.
 */

import fs from 'fs/promises';
import { createReadStream } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// We'll get OpenAI from the main SDK since we're using @openai/agents
let openai = null;

async function getOpenAIClient() {
  if (!openai) {
    // Import OpenAI from the regular SDK
    const OpenAI = (await import('openai')).default;
    openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });
  }
  return openai;
}

// Vector store configuration
const VECTOR_STORE_NAME = 'EspressoBot Documentation';
const VECTOR_STORE_DESCRIPTION = 'Tool usage guides, business rules, and workflows for iDrinkCoffee.com';

/**
 * Create or get existing vector store
 */
export async function getOrCreateVectorStore() {
  try {
    const openai = await getOpenAIClient();
    
    // List existing vector stores
    const stores = await openai.beta.vectorStores.list();
    
    // Check if our store already exists
    const existingStore = stores.data.find(store => store.name === VECTOR_STORE_NAME);
    
    if (existingStore) {
      console.log(`[VectorStore] Using existing store: ${existingStore.id}`);
      return existingStore;
    }
    
    // Create new vector store
    const vectorStore = await openai.beta.vectorStores.create({
      name: VECTOR_STORE_NAME,
      description: VECTOR_STORE_DESCRIPTION
    });
    
    console.log(`[VectorStore] Created new store: ${vectorStore.id}`);
    return vectorStore;
  } catch (error) {
    console.error('[VectorStore] Error creating/getting store:', error);
    throw error;
  }
}

/**
 * Upload documentation files to vector store
 */
export async function uploadDocumentation(vectorStoreId) {
  const documentsToUpload = [
    {
      path: '../tool-docs/TOOL_USAGE_GUIDE.md',
      name: 'Tool Usage Guide',
      metadata: { category: 'tools', type: 'guide' }
    },
    {
      path: '../prompts/idc-business-rules.md',
      name: 'Business Rules',
      metadata: { category: 'business', type: 'rules' }
    },
    {
      path: '../prompts/bash-agent-enhanced.md',
      name: 'Agent Instructions',
      metadata: { category: 'prompts', type: 'agent' }
    },
    {
      path: '../../docs/product-guidelines/01-overview.md',
      name: 'Product Guidelines Overview',
      metadata: { category: 'products', type: 'guidelines' }
    },
    {
      path: '../../docs/product-guidelines/02-product-creation-basics.md',
      name: 'Product Creation Basics',
      metadata: { category: 'products', type: 'creation' }
    },
    {
      path: '../../docs/product-guidelines/03-metafields-reference.md',
      name: 'Metafields Reference',
      metadata: { category: 'products', type: 'metafields' }
    },
    {
      path: '../../docs/product-guidelines/04-tags-system.md',
      name: 'Tags System',
      metadata: { category: 'products', type: 'tags' }
    }
  ];
  
  const fileIds = [];
  
  for (const doc of documentsToUpload) {
    try {
      const filePath = path.join(__dirname, doc.path);
      const content = await fs.readFile(filePath, 'utf-8');
      
      // Create a temporary file for upload
      const tempPath = path.join('/tmp', `${Date.now()}-${path.basename(doc.path)}`);
      await fs.writeFile(tempPath, content);
      
      // Upload file to OpenAI
      const openai = await getOpenAIClient();
      const file = await openai.files.create({
        file: createReadStream(tempPath),
        purpose: 'file_search'
      });
      
      // Clean up temp file
      await fs.unlink(tempPath);
      
      fileIds.push(file.id);
      console.log(`[VectorStore] Uploaded ${doc.name}: ${file.id}`);
      
    } catch (error) {
      console.error(`[VectorStore] Error uploading ${doc.name}:`, error.message);
    }
  }
  
  // Attach files to vector store
  if (fileIds.length > 0) {
    const openai = await getOpenAIClient();
    const batch = await openai.beta.vectorStores.fileBatches.create(vectorStoreId, {
      file_ids: fileIds
    });
    
    console.log(`[VectorStore] Attached ${fileIds.length} files to store`);
    
    // Wait for processing to complete
    await waitForProcessing(vectorStoreId, batch.id);
  }
  
  return fileIds;
}

/**
 * Wait for vector store processing to complete
 */
async function waitForProcessing(vectorStoreId, batchId) {
  console.log('[VectorStore] Waiting for file processing...');
  const openai = await getOpenAIClient();
  
  while (true) {
    const batch = await openai.beta.vectorStores.fileBatches.retrieve(vectorStoreId, batchId);
    
    if (batch.status === 'completed') {
      console.log('[VectorStore] File processing completed');
      break;
    } else if (batch.status === 'failed') {
      throw new Error('File processing failed');
    }
    
    // Wait 1 second before checking again
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

/**
 * Get or create a fully populated vector store
 */
export async function getVectorStoreId() {
  try {
    // Check if we have a cached vector store ID
    const cacheFile = path.join(__dirname, '.vector-store-cache.json');
    
    try {
      const cache = JSON.parse(await fs.readFile(cacheFile, 'utf-8'));
      const openai = await getOpenAIClient();
      const vectorStore = await openai.beta.vectorStores.retrieve(cache.vectorStoreId);
      
      if (vectorStore && vectorStore.file_counts.total > 0) {
        console.log(`[VectorStore] Using cached store: ${cache.vectorStoreId}`);
        return cache.vectorStoreId;
      }
    } catch (error) {
      // Cache doesn't exist or is invalid
    }
    
    // Create new vector store and populate it
    const vectorStore = await getOrCreateVectorStore();
    await uploadDocumentation(vectorStore.id);
    
    // Cache the vector store ID
    await fs.writeFile(cacheFile, JSON.stringify({
      vectorStoreId: vectorStore.id,
      created: new Date().toISOString()
    }));
    
    return vectorStore.id;
  } catch (error) {
    console.error('[VectorStore] Error getting vector store:', error);
    throw error;
  }
}

/**
 * Test file search
 */
export async function testFileSearch(query) {
  const vectorStoreId = await getVectorStoreId();
  const openai = await getOpenAIClient();
  
  console.log(`\n[VectorStore] Testing search for: "${query}"`);
  
  // Create a temporary thread to test search
  const thread = await openai.beta.threads.create();
  
  // Add a message with file search
  await openai.beta.threads.messages.create(thread.id, {
    role: 'user',
    content: query,
    tools: [{
      type: 'file_search',
      file_search: {
        vector_store_ids: [vectorStoreId]
      }
    }]
  });
  
  // Run the thread
  const run = await openai.beta.threads.runs.create(thread.id, {
    assistant_id: 'asst_abc123' // This would be your assistant ID
  });
  
  console.log('[VectorStore] Search initiated');
}

/**
 * Clear vector store cache (for updates)
 */
export async function clearVectorStoreCache() {
  const cacheFile = path.join(__dirname, '.vector-store-cache.json');
  try {
    await fs.unlink(cacheFile);
    console.log('[VectorStore] Cache cleared');
  } catch (error) {
    // Cache doesn't exist
  }
}