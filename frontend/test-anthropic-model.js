#!/usr/bin/env node
/**
 * Test script for Anthropic Model Provider
 * Tests both sync and streaming responses
 */

import { AnthropicProvider } from './server/models/anthropic-provider.js';
import { Agent, Runner } from '@openai/agents';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function testAnthropicProvider() {
  console.log('🧪 Testing Anthropic Model Provider...\n');

  try {
    // Create Anthropic provider
    const anthropicProvider = new AnthropicProvider({
      modelName: 'claude-sonnet-4-20250514',
      apiKey: process.env.ANTHROPIC_API_KEY
    });

    console.log('✅ Created Anthropic provider');

    // Test 1: Direct model response
    console.log('\n📋 Test 1: Direct model response');
    const model = anthropicProvider.getModel();
    
    const response = await model.getResponse({
      messages: [
        {
          role: 'user',
          content: 'Say hello and tell me what model you are in exactly 10 words.'
        }
      ],
      temperature: 0.7,
      max_tokens: 100
    });

    console.log('Response:', response.output[0].content);
    console.log('Usage:', response.usage);

    // Test 2: Agent with Anthropic model
    console.log('\n🤖 Test 2: Agent with Anthropic model');
    
    const agent = new Agent({
      name: 'Test Claude Agent',
      instructions: 'You are Claude, a helpful AI assistant. Always mention that you are Claude in your responses.',
      model: anthropicProvider.getModel('claude-sonnet-4-20250514'),
      modelSettings: { 
        temperature: 0.7,
        max_tokens: 150
      }
    });

    const runner = new Runner({ 
      modelProvider: anthropicProvider 
    });

    console.log('✅ Created agent with Anthropic model');
    console.log('Agent model name:', agent.model.name);

    // Test 3: Streaming response
    console.log('\n📡 Test 3: Streaming response');
    
    const streamRequest = {
      messages: [
        {
          role: 'user', 
          content: 'Count from 1 to 5, explaining each number briefly.'
        }
      ],
      temperature: 0.5,
      max_tokens: 200
    };

    console.log('Streaming response:');
    let fullResponse = '';
    
    for await (const chunk of model.getStreamedResponse(streamRequest)) {
      if (chunk.type === 'response.delta') {
        process.stdout.write(chunk.delta.content);
        fullResponse += chunk.delta.content;
      } else if (chunk.type === 'response.completed') {
        console.log('\n\nFinal usage:', chunk.response.usage);
      } else if (chunk.type === 'response.error') {
        console.error('\nStreaming error:', chunk.error);
      }
    }

    console.log('\n\n✅ All tests completed successfully!');
    console.log('\n📊 Summary:');
    console.log('- Direct model response: ✅');
    console.log('- Agent creation: ✅');
    console.log('- Streaming response: ✅');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
  }
}

// Run tests
testAnthropicProvider();