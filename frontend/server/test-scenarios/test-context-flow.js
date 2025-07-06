/**
 * Test script to verify context flow from orchestrator to agents
 * 
 * This tests the critical fix where orchestrator is now the single source
 * of context and passes rich context objects to agents.
 */

import { runDynamicOrchestrator } from '../dynamic-bash-orchestrator.js';

async function testContextFlow() {
  console.log('\n=== TESTING CONTEXT FLOW ===\n');
  
  // Test 1: Discount removal scenario (the problematic case)
  console.log('Test 1: Discount Removal with Specific Products');
  console.log('-----------------------------------------------');
  
  const testMessage1 = `for the items https://idrinkcoffee.com/products/behmor-2000ab-plus-home-coffee-roaster 
https://idrinkcoffee.com/products/behmor-roasting-drum-cylinder 
remove the discount please - so change the base price to be the same as the higher compare at price`;

  // Simulate options that would come from the chat endpoint
  const options1 = {
    conversationId: 'test-context-flow-1',
    userId: 2,
    sseEmitter: (event, data) => {
      if (event === 'agent_processing') {
        console.log(`[${data.agent}] ${data.message}`);
      }
    }
  };

  try {
    console.log('\nRunning orchestrator with discount removal request...\n');
    const result1 = await runDynamicOrchestrator(testMessage1, options1);
    console.log('\nOrchestrator completed successfully');
  } catch (error) {
    console.error('Test 1 failed:', error);
  }

  // Test 2: Price update with specific value
  console.log('\n\nTest 2: Price Update with Specific Value');
  console.log('------------------------------------------');
  
  const testMessage2 = `update https://idrinkcoffee.com/products/breville-barista-pro to $899.99`;

  const options2 = {
    conversationId: 'test-context-flow-2',
    userId: 2,
    sseEmitter: (event, data) => {
      if (event === 'agent_processing') {
        console.log(`[${data.agent}] ${data.message}`);
      }
    }
  };

  try {
    console.log('\nRunning orchestrator with price update request...\n');
    const result2 = await runDynamicOrchestrator(testMessage2, options2);
    console.log('\nOrchestrator completed successfully');
  } catch (error) {
    console.error('Test 2 failed:', error);
  }
}

// Run the test
testContextFlow().catch(console.error);