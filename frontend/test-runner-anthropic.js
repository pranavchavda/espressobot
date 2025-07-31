#!/usr/bin/env node
/**
 * Test script for Runner-based Anthropic Model Provider
 * Tests if using Runner fixes the message passing issue
 */

import { AnthropicProvider } from './server/models/anthropic-provider.js';
import { Agent, Runner } from '@openai/agents';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function testRunnerApproach() {
  console.log('🧪 Testing Runner-based Anthropic integration...\n');

  try {
    // Create Anthropic provider
    const anthropicProvider = new AnthropicProvider({
      modelName: 'claude-sonnet-4-20250514',
      apiKey: process.env.ANTHROPIC_API_KEY
    });

    console.log('✅ Created Anthropic provider');

    // Create agent WITH model AND use Runner
    const agent = new Agent({
      name: 'Test Claude Agent',
      instructions: 'You are Claude, a helpful AI assistant. Always mention what model you are in your responses.',
      model: anthropicProvider.getModel('claude-sonnet-4-20250514')
    });

    // Create Runner with model provider
    const runner = new Runner({ 
      modelProvider: anthropicProvider 
    });

    console.log('✅ Created Runner with Anthropic model provider');
    console.log('✅ Created Agent without explicit model');

    // Test the actual message passing
    console.log('\n📨 Testing message passing with Runner...');
    
    const testMessage = 'This is a test. What model are you using? Answer in exactly 10 words.';
    console.log(`Sending message: "${testMessage}"`);

    console.log('\n🔄 Starting streaming run...');
    
    const result = await runner.run(agent, testMessage, {
      maxTurns: 3,
      stream: true,
      onMessage: (message) => {
        console.log('📨 Received message:', typeof message, message?.content?.substring(0, 100));
      }
    });

    console.log('\n📋 Final Result:');
    if (result && result.output) {
      console.log('Output length:', result.output.length);
      if (result.output.length > 0) {
        console.log('First output:', result.output[0]);
      }
    } else {
      console.log('Result keys:', Object.keys(result || {}));
    }

    console.log('\n✅ Runner-based test completed successfully!');

  } catch (error) {
    console.error('❌ Runner test failed:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
  }
}

// Run test
testRunnerApproach();