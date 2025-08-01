#!/usr/bin/env node
/**
 * Test OpenRouter integration with the full orchestrator
 */

import { runDynamicOrchestrator } from './server/espressobot1.js';
import dotenv from 'dotenv';

dotenv.config();

async function testOrchestratorOpenRouter() {
  console.log('🧪 Testing Orchestrator with OpenRouter...\n');

  try {
    // Set environment for OpenRouter
    process.env.MODEL_PROVIDER = 'openrouter';
    process.env.OPENROUTER_MODEL = 'openai/gpt-3.5-turbo'; // Cheapest model
    
    const testMessage = 'What model are you using? Answer in exactly 8 words.';
    console.log(`Sending: "${testMessage}"`);
    
    const result = await runDynamicOrchestrator(testMessage, {
      conversationId: 'test-openrouter-orchestrator',
      userId: 1,
      sseEmitter: (event, data) => {
        if (event === 'assistant_delta' && data?.delta) {
          process.stdout.write(data.delta);
        }
      }
    });
    
    console.log('\n📋 Orchestrator result length:', result?.length || 0);
    console.log('Result preview:', result?.substring(0, 200));
    
    console.log('\n✅ OpenRouter orchestrator test completed!');

  } catch (error) {
    console.error('❌ Orchestrator test failed:', error.message);
    console.error('Stack:', error.stack);
  }
}

testOrchestratorOpenRouter();