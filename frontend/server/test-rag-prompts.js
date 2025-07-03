#!/usr/bin/env node
/**
 * Test RAG System with Product Guidelines
 */

import ragManager from './memory/rag-system-prompt-manager.js';

async function testRAGPrompts() {
  console.log('🧪 Testing RAG System with Product Guidelines\n');
  
  // ragManager is already instantiated
  
  const testQueries = [
    {
      context: 'Creating a new coffee product for Colombia beans',
      agentType: 'swe',
      description: 'Coffee product creation'
    },
    {
      context: 'Need to add metafields to a product',
      agentType: 'swe',
      description: 'Metafield reference'
    },
    {
      context: 'What tags should I use for an espresso machine?',
      agentType: 'all',
      description: 'Tag system query'
    },
    {
      context: 'Working with Shopify GraphQL API',
      agentType: 'swe',
      description: 'Technical API guidance'
    }
  ];
  
  for (const test of testQueries) {
    console.log(`\n📋 Test: ${test.description}`);
    console.log(`Context: "${test.context}"`);
    console.log(`Agent Type: ${test.agentType}`);
    console.log('─'.repeat(60));
    
    const prompt = await ragManager.getSystemPrompt(test.context, {
      basePrompt: `You are a helpful AI assistant working with Shopify products.`,
      agentType: test.agentType,
      maxFragments: 5,
      minScore: 0.5
    });
    
    console.log('Generated Prompt:');
    console.log(prompt);
    console.log('─'.repeat(60));
  }
  
  // Test caching
  console.log('\n🔄 Testing cache performance...');
  const startTime = Date.now();
  
  for (let i = 0; i < 5; i++) {
    await ragManager.getSystemPrompt('Creating coffee products', {
      agentType: 'swe'
    });
  }
  
  const endTime = Date.now();
  console.log(`5 cached prompts generated in ${endTime - startTime}ms`);
  
  // Show memory usage
  const fragments = await ragManager.memoryOps.getAllSystemPromptFragments();
  console.log(`\n📊 Total fragments in system: ${fragments.length}`);
  
  const byCategory = {};
  fragments.forEach(f => {
    const cat = f.metadata?.category || 'uncategorized';
    byCategory[cat] = (byCategory[cat] || 0) + 1;
  });
  
  console.log('\nFragments by category:');
  Object.entries(byCategory).forEach(([cat, count]) => {
    console.log(`  ${cat}: ${count}`);
  });
}

// Run test
testRAGPrompts().catch(console.error);