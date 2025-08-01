#!/usr/bin/env node
/**
 * Test script for OpenRouter integration
 * Tests the Direct Provider Pattern with OpenRouter's 300+ models
 */

import { OpenRouterProvider, AGENT_MODEL_MAP } from './server/models/openrouter-provider.js';
import { Agent, Runner, run } from '@openai/agents';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

async function testOpenRouterIntegration() {
  console.log('🧪 Testing OpenRouter integration...\n');

  try {
    // Test 1: Basic OpenRouter provider creation
    console.log('📋 Test 1: OpenRouter provider creation');
    const provider = new OpenRouterProvider({
      apiKey: process.env.OPENROUTER_API_KEY,
      defaultModel: 'openai/gpt-4o-mini' // Start with a fast, cheap model
    });

    console.log('✅ Created OpenRouter provider');

    // Test 2: Create agent with OpenRouter model
    console.log('\n📋 Test 2: Agent creation with OpenRouter model');
    const agent = new Agent({
      name: 'OpenRouter Test Agent',
      instructions: 'You are a helpful AI assistant. Always mention what model you are using in your responses.',
      model: provider.getModel()
    });

    console.log('✅ Created Agent with OpenRouter model');

    // Test 3: Test with run function (non-streaming first)
    console.log('\n📋 Test 3: Non-streaming test');
    const testMessage1 = 'Test 1: What model are you using? Answer in exactly 10 words.';
    console.log(`Sending: "${testMessage1}"`);

    const result1 = await run(agent, testMessage1, {
      maxTurns: 3,
      stream: false
    });

    console.log('📋 Non-streaming result:');
    if (result1 && result1.output) {
      console.log('Output length:', result1.output.length);
      if (result1.output.length > 0) {
        console.log('Response:', result1.output[0]?.content?.[0]?.text?.substring(0, 200));
      }
    } else {
      console.log('Result keys:', Object.keys(result1 || {}));
    }

    // Test 4: Test with Runner and streaming
    console.log('\n📋 Test 4: Streaming test with Runner');
    const runner = new Runner({ 
      modelProvider: provider 
    });

    let streamingOutput = '';
    const testMessage2 = 'Test 2: What model are you using? Answer in exactly 10 words.';
    console.log(`Sending: "${testMessage2}"`);

    const result2 = await runner.run(agent, testMessage2, {
      maxTurns: 3,
      stream: true,
      onMessage: (message) => {
        if (message?.content) {
          streamingOutput += message.content;
          process.stdout.write(message.content);
        }
      }
    });

    console.log('\n📋 Streaming result:');
    console.log('Streaming output length:', streamingOutput.length);
    console.log('Final result output length:', result2?.output?.length || 0);

    // Test 5: Test different models from agent map
    console.log('\n📋 Test 5: Testing specialized models');
    console.log('Available agent models:', Object.keys(AGENT_MODEL_MAP).slice(0, 5));

    // Test with Claude model for comparison
    const claudeProvider = new OpenRouterProvider({
      apiKey: process.env.OPENROUTER_API_KEY,
      defaultModel: 'anthropic/claude-3.5-sonnet'
    });

    const claudeAgent = new Agent({
      name: 'Claude via OpenRouter',
      instructions: 'You are Claude via OpenRouter. Mention your model name.',
      model: claudeProvider.getModel()
    });

    const testMessage3 = 'What model are you? Answer in 8 words exactly.';
    console.log(`\nTesting Claude via OpenRouter: "${testMessage3}"`);

    const result3 = await run(claudeAgent, testMessage3, {
      maxTurns: 2,
      stream: false
    });

    if (result3?.output?.length > 0) {
      console.log('Claude via OpenRouter response:', result3.output[0]?.content?.[0]?.text);
    }

    console.log('\n✅ OpenRouter integration tests completed successfully!');
    console.log('\n📊 Test Summary:');
    console.log('- Provider creation: ✅');
    console.log('- Agent integration: ✅');
    console.log('- Non-streaming: ', result1 ? '✅' : '❌');
    console.log('- Streaming: ', streamingOutput.length > 0 ? '✅' : '❌');
    console.log('- Multi-model support: ', result3 ? '✅' : '❌');

  } catch (error) {
    console.error('❌ OpenRouter test failed:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
  }
}

// Run test
testOpenRouterIntegration();