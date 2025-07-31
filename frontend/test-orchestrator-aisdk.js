#!/usr/bin/env node
/**
 * Test script to compare AI SDK vs direct implementation in orchestrator context
 */

import { runDynamicOrchestrator } from './server/espressobot1.js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function testOrchestratorApproaches() {
  console.log('🧪 Testing Orchestrator with different Anthropic approaches...\n');

  try {
    // Test 1: Direct implementation (our current working approach)
    console.log('📋 Test 1: Direct Anthropic implementation');
    process.env.MODEL_PROVIDER = 'anthropic';
    process.env.ANTHROPIC_MODEL = 'claude-sonnet-4-20250514';
    process.env.USE_AI_SDK = 'false';
    
    const testMessage1 = 'Test 1: What model are you using? Answer in exactly 10 words.';
    console.log(`Sending: "${testMessage1}"`);
    
    const result1 = await runDynamicOrchestrator(testMessage1, {
      conversationId: 'test-direct-approach',
      userId: 1,
      sseEmitter: (event, data) => {
        if (event === 'assistant_delta' && data?.delta) {
          process.stdout.write(data.delta);
        }
      }
    });
    
    console.log('\n📋 Direct approach result length:', result1?.length || 0);
    
    // Test 2: AI SDK approach  
    console.log('\n📋 Test 2: AI SDK Anthropic implementation');
    process.env.USE_AI_SDK = 'true';
    
    const testMessage2 = 'Test 2: What model are you using? Answer in exactly 10 words.';
    console.log(`Sending: "${testMessage2}"`);
    
    const result2 = await runDynamicOrchestrator(testMessage2, {
      conversationId: 'test-aisdk-approach', 
      userId: 1,
      sseEmitter: (event, data) => {
        if (event === 'assistant_delta' && data?.delta) {
          process.stdout.write(data.delta);
        }
      }
    });
    
    console.log('\n📋 AI SDK approach result length:', result2?.length || 0);
    
    console.log('\n✅ Orchestrator comparison tests completed!');
    console.log('Direct approach:', result1 ? '✅ Working' : '❌ Failed');
    console.log('AI SDK approach:', result2 ? '✅ Working' : '❌ Failed');

  } catch (error) {
    console.error('❌ Orchestrator test failed:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
  }
}

// Run test
testOrchestratorApproaches();