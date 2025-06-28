#!/usr/bin/env node

console.log('🧪 Testing Tool Execution with Proper Span Callbacks\n');

import { run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import enhancedOrchestrator from './server/enhanced-multi-agent-orchestrator-v2.js';

setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

async function testWithSpans(message) {
  console.log(`\n📝 Query: "${message}"\n`);
  
  const spans = [];
  
  try {
    const result = await run(enhancedOrchestrator, message, {
      maxTurns: 10,
      onSpanStart: (span) => {
        const entry = {
          type: span.type,
          name: span.name,
          metadata: span.metadata
        };
        spans.push(entry);
        console.log('🟢 Span Start:', entry);
      },
      onSpanEnd: (span) => {
        console.log('🔴 Span End:', span.name);
      },
      onTraceStart: (trace) => {
        console.log('📊 Trace Start:', trace.workflow_name);
      },
      onTraceEnd: (trace) => {
        console.log('📊 Trace End');
      }
    });
    
    console.log('\nFinal State:');
    console.log('  Current Agent:', result?.state?._currentAgent?.name);
    console.log('  Response preview:', result?.state?._currentStep?.output?.substring(0, 100) + '...');
    
  } catch (error) {
    console.error('Error:', error.message);
  }
  
  return spans;
}

// Test tool execution
async function main() {
  // Test 1: Product search (should use search_products tool)
  await testWithSpans("Search for active coffee grinders");
  
  // Test 2: Product creation
  await testWithSpans("Create a product called 'API Test Coffee Maker' with vendor 'Test Vendor', type 'Coffee Equipment', price $99.99, SKU TEST-API-MAKER-001");
  
  // Test 3: Price update
  await testWithSpans("Update the price of product with SKU TEST-API-MAKER-001 to $89.99");
}

main();