#!/usr/bin/env node
/**
 * Simple test for EspressoBot orchestrator with Anthropic
 */

import { runDynamicOrchestrator } from './server/espressobot1.js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function testOrchestratorWithAnthropic() {
  console.log('🧪 Testing EspressoBot orchestrator with Anthropic...\n');

  // Set environment to use Anthropic
  process.env.MODEL_PROVIDER = 'anthropic';
  process.env.ANTHROPIC_MODEL = 'claude-sonnet-4-20250514';

  try {
    console.log('📤 Sending test message...');
    
    const result = await runDynamicOrchestrator(
      'Hello! Please tell me what model you are in exactly 10 words.',
      {
        conversationId: 'test-anthropic-orchestrator',
        userId: 'test-user'
      }
    );

    console.log('\n✅ Result received:');
    console.log(JSON.stringify(result, null, 2));

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
  }
}

// Set timeout and run
setTimeout(() => {
  console.log('⏰ Test timed out after 30 seconds');
  process.exit(1);
}, 30000);

testOrchestratorWithAnthropic();