#!/usr/bin/env node

/**
 * Setup Vector Store for Semantic Search
 * 
 * This script creates and populates an OpenAI Vector Store with
 * all our documentation for semantic search capabilities.
 */

import { getVectorStoreId, clearVectorStoreCache } from './vector-store-manager.js';
import { createSemanticBashAgent } from '../agents/semantic-bash-agent.js';
import { run } from '@openai/agents';

async function setupVectorStore() {
  console.log('🚀 Setting up Vector Store for EspressoBot\n');
  
  // Clear cache to force recreation (optional)
  if (process.argv.includes('--fresh')) {
    console.log('Clearing cache for fresh setup...');
    await clearVectorStoreCache();
  }
  
  try {
    // Create and populate vector store
    const vectorStoreId = await getVectorStoreId();
    console.log(`\n✅ Vector Store ready: ${vectorStoreId}`);
    
    // Get store details
    const OpenAI = (await import('openai')).default;
    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    const store = await openai.beta.vectorStores.retrieve(vectorStoreId);
    console.log(`\n📊 Store Statistics:`);
    console.log(`- Name: ${store.name}`);
    console.log(`- Files: ${store.file_counts.total}`);
    console.log(`- Status: ${store.status}`);
    console.log(`- Created: ${new Date(store.created_at * 1000).toLocaleString()}`);
    
    // Test searches if requested
    if (process.argv.includes('--test')) {
      await runTestSearches(vectorStoreId);
    }
    
    // Save to environment (optional)
    console.log(`\n💡 To use this vector store, add to your .env:`);
    console.log(`VECTOR_STORE_ID=${vectorStoreId}`);
    
  } catch (error) {
    console.error('\n❌ Setup failed:', error);
    process.exit(1);
  }
}

async function runTestSearches(vectorStoreId) {
  console.log('\n🔍 Running test searches...\n');
  
  const testQueries = [
    {
      name: "Preorder Management",
      query: "How do I add a product to preorder? What tags and inventory policy?"
    },
    {
      name: "Product Creation",
      query: "What tools do I use to create a new espresso machine product?"
    },
    {
      name: "Feature Management",
      query: "How do I add features to a product using metaobjects?"
    },
    {
      name: "Pricing Updates",
      query: "What's the process for bulk price updates with CSV?"
    },
    {
      name: "Business Rules",
      query: "What are the publishing channels for iDrinkCoffee?"
    }
  ];
  
  // Create a test agent for each query
  for (const test of testQueries) {
    console.log(`### Test: ${test.name}`);
    console.log(`Query: "${test.query}"`);
    console.log('-'.repeat(60));
    
    try {
      // Create a semantic bash agent
      const agent = await createSemanticBashAgent(
        'Test_Agent',
        `Use the search_documentation tool to answer this question: ${test.query}
        
        IMPORTANT: Only search for information, do not execute any bash commands.
        Return a concise answer based on the search results.`,
        null
      );
      
      // Run the agent
      const result = await run(agent, test.query);
      console.log('Result:', result);
      
    } catch (error) {
      console.error('Error:', error.message);
    }
    
    console.log('\n' + '='.repeat(60) + '\n');
  }
}

// Run setup if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  setupVectorStore().catch(console.error);
}