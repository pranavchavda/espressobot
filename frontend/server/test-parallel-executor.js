/**
 * Test script for parallel executor functionality
 */

import { run } from '@openai/agents';
import { createParallelExecutorAgent, validateParallelExecution } from './agents/parallel-executor-agent.js';

async function testValidation() {
  console.log('\n=== Testing Validation Logic ===\n');
  
  const testCases = [
    {
      items: ['SKU1', 'SKU2', 'SKU3'],
      operation: 'Update prices to $49.99',
      expected: 'Not appropriate (too few items)'
    },
    {
      items: Array(25).fill('SKU').map((s, i) => `${s}-${i+1}`),
      operation: 'Add summer-sale tag to products',
      expected: 'Appropriate for parallel execution'
    },
    {
      items: Array(75).fill('SKU').map((s, i) => `${s}-${i+1}`),
      operation: 'Update inventory quantities',
      expected: 'Not appropriate (too many items, use SWE)'
    },
    {
      items: Array(20).fill('PRODUCT').map((s, i) => `${s}-${i+1}`),
      operation: 'If product has tag X, then update price, unless it already has tag Y',
      expected: 'Complex logic detected, consider SWE'
    }
  ];

  for (const testCase of testCases) {
    console.log(`\nTest: ${testCase.operation}`);
    console.log(`Items: ${testCase.items.length}`);
    const validation = validateParallelExecution(testCase.items, testCase.operation);
    console.log(`Result: ${validation.appropriate ? 'Appropriate' : 'Not appropriate'}`);
    if (validation.warnings.length > 0) {
      console.log(`Warnings: ${validation.warnings.join(', ')}`);
    }
    if (validation.recommendations.length > 0) {
      console.log(`Recommendations: ${validation.recommendations.join(', ')}`);
    }
    console.log(`Expected: ${testCase.expected}`);
  }
}

async function testParallelExecutor() {
  console.log('\n=== Testing Parallel Executor Agent ===\n');
  
  // Test case: Update prices for 15 products
  const testItems = [
    { sku: 'ESP-001', newPrice: 49.99 },
    { sku: 'ESP-002', newPrice: 59.99 },
    { sku: 'ESP-003', newPrice: 69.99 },
    { sku: 'ESP-004', newPrice: 79.99 },
    { sku: 'ESP-005', newPrice: 89.99 },
    { sku: 'GRN-001', newPrice: 149.99 },
    { sku: 'GRN-002', newPrice: 199.99 },
    { sku: 'GRN-003', newPrice: 249.99 },
    { sku: 'ACC-001', newPrice: 19.99 },
    { sku: 'ACC-002', newPrice: 29.99 },
    { sku: 'ACC-003', newPrice: 39.99 },
    { sku: 'ACC-004', newPrice: 14.99 },
    { sku: 'ACC-005', newPrice: 24.99 },
    { sku: 'CLN-001', newPrice: 9.99 },
    { sku: 'CLN-002', newPrice: 12.99 }
  ];

  const operation = `Update product prices using the following mapping:
Each item has 'sku' and 'newPrice' properties.
Use the update_pricing MCP tool to update each product's price.
This is a DRY RUN - simulate the operations without actually executing them.`;

  // Create a single executor instance for testing
  const agent = await createParallelExecutorAgent(
    'test_001',
    testItems.slice(0, 5), // Test with first 5 items
    operation,
    {
      dryRun: true,
      throttleMs: 500,
      customContext: 'This is a test run. Simulate operations and return mock results.'
    }
  );

  console.log('Created parallel executor agent for 5 items');
  console.log('Running agent...');

  try {
    const result = await run(agent, 'Process your assigned items according to the operation described.', {
      maxTurns: 10
    });
    
    console.log('\nAgent completed!');
    console.log('Result:', result.finalOutput || result);
  } catch (error) {
    console.error('Agent failed:', error);
  }
}

// Run tests
async function main() {
  try {
    await testValidation();
    await testParallelExecutor();
  } catch (error) {
    console.error('Test failed:', error);
  }
}

main();