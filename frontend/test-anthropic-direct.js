#!/usr/bin/env node
/**
 * Direct test of Anthropic SDK without OpenAI Agents wrapper
 */

import Anthropic from '@anthropic-ai/sdk';

async function testAnthropicDirect() {
  console.log('=== Testing Direct Anthropic API ===\n');
  
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error('❌ ANTHROPIC_API_KEY not set');
    return;
  }
  
  try {
    const anthropic = new Anthropic({ apiKey });
    
    // Test 1: Simple message
    console.log('1. Testing basic Claude 3.5 Sonnet...');
    const response1 = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      messages: [{
        role: 'user',
        content: 'Say hello in 5 words or less.'
      }],
      max_tokens: 100
    });
    console.log('✅ Response:', response1.content[0].text);
    
    // Test 2: With system prompt
    console.log('\n2. Testing with system prompt...');
    const response2 = await anthropic.messages.create({
      model: 'claude-3-5-haiku-20241022',
      messages: [{
        role: 'user',
        content: 'What is 2+2?'
      }],
      system: 'You are a helpful math tutor. Be very brief.',
      max_tokens: 50
    });
    console.log('✅ Response:', response2.content[0].text);
    
    // Test 3: Tool use
    console.log('\n3. Testing tool use...');
    const response3 = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      messages: [{
        role: 'user',
        content: 'What time is it? Use the get_current_time tool.'
      }],
      tools: [{
        name: 'get_current_time',
        description: 'Get the current time',
        input_schema: {
          type: 'object',
          properties: {},
          required: []
        }
      }],
      max_tokens: 200
    });
    
    console.log('✅ Tool call response:');
    for (const content of response3.content) {
      if (content.type === 'tool_use') {
        console.log(`   Tool: ${content.name}`);
        console.log(`   Input: ${JSON.stringify(content.input)}`);
      } else if (content.type === 'text') {
        console.log(`   Text: ${content.text}`);
      }
    }
    
    console.log('\n=== Direct Anthropic API works! ===');
    console.log('\nNow testing available models...\n');
    
    // Test different models
    const modelsToTest = [
      'claude-3-5-sonnet-20241022',
      'claude-3-5-haiku-20241022',
      'claude-3-opus-20240229',
      // Try 4.0 models (they might not be available yet)
      'claude-opus-4-0',
      'claude-sonnet-4-0'
    ];
    
    for (const model of modelsToTest) {
      try {
        console.log(`Testing ${model}...`);
        const response = await anthropic.messages.create({
          model: model,
          messages: [{ role: 'user', content: 'Say "yes" if you work.' }],
          max_tokens: 10
        });
        console.log(`✅ ${model} works!`);
      } catch (error) {
        if (error.message.includes('does not exist')) {
          console.log(`❌ ${model} not available`);
        } else {
          console.log(`❌ ${model} error: ${error.message}`);
        }
      }
    }
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
  }
}

testAnthropicDirect().catch(console.error);