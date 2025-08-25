#!/usr/bin/env node

import { runDynamicOrchestrator } from './server/dynamic-bash-orchestrator.js';

console.log('🚀 Testing Dynamic Bash Orchestrator\n');

async function test(message) {
  console.log(`\n📝 Test: "${message}"`);
  console.log('─'.repeat(50));
  
  try {
    const result = await runDynamicOrchestrator(message);
    console.log('\n✅ Result:', result);
  } catch (error) {
    console.error('\n❌ Error:', error.message);
  }
}

// Run tests
async function runTests() {
  // Test 1: Simple tool check
  await test("Check what Python tools are available for product management");
  
  // Test 2: Search task
  await test("Find all products with 'coffee' in the title that are currently active");
  
  // Test 3: Price update task  
  await test("Revert the sale on HeyCafe Jack variants (both white and black)");
  
  // Test 4: Complex multi-step task
  await test("Find all products from vendor 'Test' and update their status to DRAFT");
}

runTests().then(() => {
  console.log('\n✅ All tests completed!');
  process.exit(0);
}).catch(error => {
  console.error('\n❌ Test suite failed:', error);
  process.exit(1);
});