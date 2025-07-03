#!/usr/bin/env node

import ragSystemPromptManager from '../memory/rag-system-prompt-manager.js';
import { memoryOperations } from '../memory/memory-operations-local.js';

async function testRAGPrompts() {
  console.log('Testing RAG System Prompt Manager...\n');
  
  // Test 1: Search for bash-related prompts
  console.log('=== Test 1: Bash Agent Context ===');
  const bashTask = "Update product prices in bulk using CSV file";
  const bashPrompt = await ragSystemPromptManager.getSystemPrompt(bashTask, {
    basePrompt: 'You are a bash agent.',
    maxFragments: 5,
    includeMemories: false,
    agentType: 'bash',
    minScore: 0.3
  });
  
  console.log('Task:', bashTask);
  console.log('Generated prompt preview:');
  console.log(bashPrompt.slice(0, 500) + '...\n');
  
  // Test 2: Search for SWE/Shopify prompts
  console.log('=== Test 2: SWE Agent Shopify Context ===');
  const sweTask = "Create a tool to validate GraphQL queries against Shopify schema";
  const swePrompt = await ragSystemPromptManager.getSystemPrompt(sweTask, {
    basePrompt: 'You are a software engineering agent.',
    maxFragments: 5,
    includeMemories: false,
    agentType: 'swe',
    minScore: 0.3
  });
  
  console.log('Task:', sweTask);
  console.log('Generated prompt preview:');
  console.log(swePrompt.slice(0, 500) + '...\n');
  
  // Test 3: Add and retrieve a new learning
  console.log('=== Test 3: Learning and Retrieval ===');
  const newLearning = "When working with large CSV files, use pandas with chunking to avoid memory issues. Process data in batches of 1000-5000 rows.";
  
  await memoryOperations.addSystemPromptFragment(newLearning, {
    category: 'patterns',
    priority: 'high',
    tags: ['csv', 'performance', 'memory', 'python'],
    agent_type: 'bash'
  });
  
  console.log('Added new learning:', newLearning.slice(0, 50) + '...');
  
  // Clear cache and test retrieval
  await ragSystemPromptManager.clearCache();
  
  const csvTask = "Process a large CSV file with millions of rows";
  const csvPrompt = await ragSystemPromptManager.getSystemPrompt(csvTask, {
    basePrompt: 'You are processing CSV data.',
    maxFragments: 3,
    includeMemories: false,
    agentType: 'bash',
    minScore: 0.2
  });
  
  console.log('\nTask:', csvTask);
  console.log('Should include CSV learning:');
  const hasCSVLearning = csvPrompt.includes('pandas with chunking');
  console.log('Contains CSV learning:', hasCSVLearning ? '✓ Yes' : '✗ No');
  
  // Test 4: Performance test
  console.log('\n=== Test 4: Performance Test ===');
  const iterations = 10;
  const start = Date.now();
  
  for (let i = 0; i < iterations; i++) {
    await ragSystemPromptManager.getSystemPrompt("test query " + i, {
      basePrompt: 'Base prompt',
      maxFragments: 5,
      includeMemories: false,
      agentType: 'all'
    });
  }
  
  const avgTime = (Date.now() - start) / iterations;
  console.log(`Average prompt generation time: ${avgTime.toFixed(2)}ms`);
  console.log(`Cache effectiveness: ${avgTime < 50 ? '✓ Good' : '⚠ Could be improved'}`);
  
  // Test 5: Category distribution
  console.log('\n=== Test 5: Knowledge Distribution ===');
  const allFragments = await memoryOperations.getAllSystemPromptFragments({}, 100);
  
  const categories = {};
  allFragments.forEach(f => {
    const cat = f.metadata?.category || 'unknown';
    categories[cat] = (categories[cat] || 0) + 1;
  });
  
  console.log('System prompt fragments by category:');
  Object.entries(categories).forEach(([cat, count]) => {
    console.log(`  ${cat}: ${count} fragments`);
  });
  
  console.log(`\nTotal fragments: ${allFragments.length}`);
  
  process.exit(0);
}

// Run tests
testRAGPrompts().catch(error => {
  console.error('Test failed:', error);
  process.exit(1);
});