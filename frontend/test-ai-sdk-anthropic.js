#!/usr/bin/env node
/**
 * Test script for AI SDK-based Anthropic integration
 * Compares the AI SDK approach with our direct implementation
 */

import { createAnthropicAISDKProvider } from './server/models/anthropic-ai-sdk-provider.js';
import { Agent, Runner, run } from '@openai/agents';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function testAISDKApproach() {
  console.log('🧪 Testing AI SDK-based Anthropic integration...\n');

  try {
    // Create AI SDK-based provider
    const provider = createAnthropicAISDKProvider({
      modelName: 'claude-sonnet-4-20250514',
      apiKey: process.env.ANTHROPIC_API_KEY
    });

    console.log('✅ Created AI SDK-based Anthropic provider');

    // Create agent with the AI SDK model
    const agent = new Agent({
      name: 'AI SDK Claude Agent',
      instructions: 'You are Claude, a helpful AI assistant. Always mention what model you are in your responses.',
      model: provider.getModel()
    });

    console.log('✅ Created Agent with AI SDK model');

    // Test with run function
    console.log('\n📨 Testing with run function...');
    
    const testMessage = 'This is a test with AI SDK. What model are you using? Answer in exactly 10 words.';
    console.log(`Sending message: "${testMessage}"`);

    let streamingOutput = '';
    
    const result = await run(agent, testMessage, {
      maxTurns: 3,
      stream: true,
      onMessage: (message) => {
        if (message?.content) {
          streamingOutput += message.content;
          console.log('📨 Streaming chunk:', message.content.substring(0, 50));
        }
      }
    });

    console.log('\n📋 Final Result:');
    console.log('Streaming output length:', streamingOutput.length);
    if (result && result.output) {
      console.log('Result output length:', result.output.length);
      if (result.output.length > 0) {
        console.log('First output content:', result.output[0]?.content?.[0]?.text?.substring(0, 100));
      }
    }

    console.log('\n✅ AI SDK test completed successfully!');

  } catch (error) {
    console.error('❌ AI SDK test failed:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
  }
}

// Run test
testAISDKApproach();