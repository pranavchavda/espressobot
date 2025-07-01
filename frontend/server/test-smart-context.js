#!/usr/bin/env node

/**
 * Test script for Smart Context Loading
 * Demonstrates how different requests load different contexts
 */

import { testContextLoading } from './context-loader/context-manager.js';

const testCases = [
  {
    name: "Product Creation",
    message: "Create a new espresso machine product for DeLonghi"
  },
  {
    name: "Preorder Management",
    message: "Add the Breville Barista Express to preorder with July shipping"
  },
  {
    name: "Bulk Pricing",
    message: "Update prices for all coffee grinders with a 15% discount"
  },
  {
    name: "Feature Management",
    message: "Add product features to the new Profitec machine"
  },
  {
    name: "Vendor Discount",
    message: "Apply CD2025 discounts to Mahlkonig products"
  },
  {
    name: "Simple Search",
    message: "Search for all active coffee products"
  },
  {
    name: "Complex Multi-Context",
    message: "Create a combo product with preorder status and bulk update the pricing"
  }
];

async function runTests() {
  console.log('=== Smart Context Loading Test Suite ===\n');
  
  for (const testCase of testCases) {
    console.log(`\n### Test: ${testCase.name}`);
    console.log(`Message: "${testCase.message}"`);
    console.log('-'.repeat(60));
    
    const context = await testContextLoading(testCase.message);
    
    // Show which sections were loaded
    const sections = context.match(/## [^\n]+/g) || [];
    console.log('\nLoaded sections:');
    sections.forEach(section => console.log(`  - ${section}`));
    
    console.log('\n' + '='.repeat(60));
  }
  
  // Test memory integration
  console.log('\n### Testing Memory Integration');
  console.log('(This will work if Mem0 is running and has stored memories)');
  
  try {
    const { getSmartContext } = await import('./context-loader/context-manager.js');
    const contextWithMemory = await getSmartContext(
      "Update pricing for coffee products", 
      { includeMemory: true }
    );
    
    if (contextWithMemory.includes('## Relevant Memories')) {
      console.log('✅ Memory integration working!');
      const memorySection = contextWithMemory.split('## Relevant Memories')[1];
      console.log('Memory preview:', memorySection.substring(0, 200) + '...');
    } else {
      console.log('ℹ️  No memories found (this is normal if Mem0 is empty)');
    }
  } catch (error) {
    console.log('⚠️  Memory integration not available:', error.message);
  }
}

// Run the tests
runTests().catch(console.error);