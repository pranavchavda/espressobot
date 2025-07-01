#!/usr/bin/env node
/**
 * Test script for Anthropic provider integration
 */

import { AnthropicModelProvider } from './server/providers/anthropic-provider.js';
import { Agent, run } from '@openai/agents';
import { tool } from '@openai/agents';
import { z } from 'zod';

// Simple test tool
const testTool = tool({
  name: 'get_time',
  description: 'Get the current time',
  parameters: z.object({}),
  execute: async () => {
    return new Date().toISOString();
  }
});

async function testAnthropicProvider() {
  console.log('=== Testing Anthropic Provider Integration ===\n');
  
  // Check if API key is set
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error('❌ ANTHROPIC_API_KEY not set in environment');
    console.log('Please set ANTHROPIC_API_KEY in your .env file');
    return;
  }
  
  try {
    // Create provider
    const provider = new AnthropicModelProvider();
    console.log('✅ Anthropic provider created');
    
    // Test 1: Create agent with Claude Sonnet 4.0
    console.log('\n1. Testing Claude Sonnet 4.0...');
    const sonnetAgent = new Agent({
      name: 'Test_Sonnet_Agent',
      model: 'claude-sonnet-4-0',
      modelProvider: provider,
      instructions: 'You are a helpful assistant. Be concise.',
      tools: [testTool]
    });
    
    const sonnetResult = await run(sonnetAgent, 'What time is it? Use the get_time tool.', {
      maxTurns: 3
    });
    console.log('✅ Sonnet 4.0 response received');
    
    // Test 2: Create agent with Claude Haiku (latest)
    console.log('\n2. Testing Claude Haiku Latest...');
    const haikuAgent = new Agent({
      name: 'Test_Haiku_Agent', 
      model: 'claude-3-5-haiku-latest',
      modelProvider: provider,
      instructions: 'You are a helpful assistant. Be very brief.',
      tools: [testTool]
    });
    
    const haikuResult = await run(haikuAgent, 'Tell me the time using the tool.', {
      maxTurns: 3
    });
    console.log('✅ Haiku response received');
    
    // Test 3: Test Opus 4.0 without tools
    console.log('\n3. Testing Claude Opus 4.0...');
    const simpleAgent = new Agent({
      name: 'Test_Simple_Agent',
      model: 'claude-opus-4-0',  // Testing Opus 4.0
      modelProvider: provider,
      instructions: 'You are a helpful assistant.'
    });
    
    const simpleResult = await run(simpleAgent, 'Say hello in one word.', {
      maxTurns: 1
    });
    console.log('✅ Opus 4.0 response received');
    
    console.log('\n=== All tests passed! ===');
    console.log('\nYou can now use Claude models in your orchestrator by:');
    console.log('1. Setting ANTHROPIC_API_KEY in your .env file');
    console.log('2. The orchestrator will automatically use claude-sonnet-4-0');
    console.log('3. Optionally set USE_CLAUDE_FOR_BASH_AGENTS=true to use claude-3-5-haiku-latest for bash agents');
    console.log('\nAvailable Claude 4.0 models:');
    console.log('- claude-opus-4-0 (Claude Opus 4.0)');
    console.log('- claude-sonnet-4-0 (Claude Sonnet 4.0)');
    console.log('\nOther available models:');
    console.log('- claude-3-7-sonnet-latest (Sonnet 3.7)');
    console.log('- claude-3-5-sonnet-latest (Sonnet 3.5)');
    console.log('- claude-3-5-haiku-latest (Haiku 3.5)');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    console.error('\nFull error:', error);
    
    if (error.message.includes('401')) {
      console.log('\n⚠️  Invalid API key. Please check your ANTHROPIC_API_KEY');
    } else if (error.message.includes('model')) {
      console.log('\n⚠️  Model not available. You may need to request access to Claude 4.0 models');
    }
  }
}

// Run the test
testAnthropicProvider().catch(console.error);