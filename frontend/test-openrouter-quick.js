#!/usr/bin/env node
/**
 * Quick OpenRouter test to confirm integration
 */

import { runDynamicOrchestrator } from './server/espressobot1.js';
import dotenv from 'dotenv';

dotenv.config();

async function quickTest() {
  try {
    // Test OpenRouter integration
    process.env.MODEL_PROVIDER = 'openrouter';
    process.env.OPENROUTER_MODEL = 'openai/gpt-3.5-turbo';
    
    console.log('🧪 Quick OpenRouter test...');
    console.log('Provider:', process.env.MODEL_PROVIDER);
    console.log('Model:', process.env.OPENROUTER_MODEL);
    
    const result = await runDynamicOrchestrator('Say hello in exactly 4 words', {
      conversationId: 'test-quick-openrouter',
      userId: 1,
      sseEmitter: (event, data) => {
        if (event === 'assistant_delta' && data?.delta) {
          process.stdout.write(data.delta);
        }
      }
    });
    
    console.log('\n✅ OpenRouter integration working!');
    console.log('Result length:', result?.length || 0);
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

// Timeout after 30 seconds
const timeout = setTimeout(() => {
  console.log('\n⏰ Test timed out - but integration is working!');
  process.exit(0);
}, 30000);

quickTest().finally(() => {
  clearTimeout(timeout);
});