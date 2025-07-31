#!/usr/bin/env node
/**
 * Simple test to verify Anthropic integration works in EspressoBot
 */

import { Agent, run } from '@openai/agents';
import { AnthropicProvider } from './server/models/anthropic-provider.js';
import dotenv from 'dotenv';

dotenv.config();

async function testSimpleAnthropic() {
  console.log('🧪 Testing simple Anthropic integration...\n');

  try {
    // Create Anthropic provider
    const anthropicProvider = new AnthropicProvider({
      modelName: 'claude-sonnet-4-20250514',
      apiKey: process.env.ANTHROPIC_API_KEY
    });

    console.log('✅ Created Anthropic provider');

    // Create simple agent
    const agent = new Agent({
      name: 'Simple Test Agent',
      instructions: 'You are Claude. Answer questions directly and concisely.',
      model: anthropicProvider.getModel('claude-sonnet-4-20250514')
    });

    console.log('✅ Created agent with Anthropic model');
    console.log('Model name:', agent.model.name);

    // Test simple interaction
    console.log('\n📤 Testing simple interaction...');
    
    const result = await run({
      agent,
      messages: [{
        role: 'user',
        content: 'What model are you? Answer in exactly 10 words.'
      }]
    });

    console.log('\n📨 Response received:');
    console.log('Final message:', result.finalMessage);
    console.log('All messages:', result.messages.length);

    console.log('\n✅ Test completed successfully!');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
  }
}

testSimpleAnthropic();