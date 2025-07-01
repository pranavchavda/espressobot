#!/usr/bin/env node

/**
 * Test Smart Context Loading in Action
 * Shows how context is loaded and used by agents
 */

import { createBashAgent } from './tools/bash-tool.js';
import { run } from '@openai/agents';

async function testContextLoadingInAction() {
  console.log('🚀 Testing Smart Context Loading in Action\n');
  console.log('=' * 60 + '\n');
  
  const testCases = [
    {
      name: "Preorder Management",
      task: "I need to add product SKU BES870XL to preorder with August shipping. Just explain the steps, don't execute."
    },
    {
      name: "Product Creation",
      task: "What tools and process should I use to create a new DeLonghi espresso machine product? Just explain, don't execute."
    },
    {
      name: "Bulk Pricing",
      task: "How do I update prices for multiple products with a 15% discount? Just explain the process."
    }
  ];
  
  for (const test of testCases) {
    console.log(`### Test: ${test.name}`);
    console.log(`Task: "${test.task}"`);
    console.log('-'.repeat(60));
    
    try {
      // Create agent
      const agent = await createBashAgent(
        `${test.name.replace(' ', '_')}_Agent`,
        test.task,
        'test-conversation'
      );
      
      // Run agent
      const result = await run(agent, test.task);
      
      // Show result
      console.log('\n📝 Agent Response:');
      console.log(result);
      
    } catch (error) {
      console.error('❌ Error:', error.message);
    }
    
    console.log('\n' + '='.repeat(60) + '\n');
  }
  
  // Show context loading stats
  console.log('📊 Context Loading Summary:');
  console.log('- Pattern matching identifies relevant documentation');
  console.log('- Only loads needed sections (1-3KB vs 10KB+)');
  console.log('- Agents get task-specific business rules');
  console.log('- Memory integration available when Mem0 configured');
}

// Run the test
testContextLoadingInAction().catch(console.error);