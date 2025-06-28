#!/usr/bin/env node

// Test what the run() function returns with different options

import { run } from '@openai/agents';
import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple test agent
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a test agent. Just respond with "Hello!"',
  model: 'gpt-4.1-mini'
});

async function testRunReturnTypes() {
  console.log('🧪 Testing run() return types\n');
  
  // Test 1: Without streaming
  console.log('Test 1: run() without streaming');
  try {
    const result1 = run(testAgent, 'Hello', { stream: false });
    console.log('- Type:', typeof result1);
    console.log('- Constructor:', result1?.constructor?.name);
    console.log('- Is Promise?', result1 instanceof Promise);
    console.log('- Has Symbol.asyncIterator?', typeof result1?.[Symbol.asyncIterator] === 'function');
    
    const resolved1 = await result1;
    console.log('- Resolved type:', typeof resolved1);
    console.log('- Resolved keys:', Object.keys(resolved1 || {}));
  } catch (e) {
    console.error('- Error:', e.message);
  }
  
  console.log('\nTest 2: run() with stream: true');
  try {
    const result2 = run(testAgent, 'Hello', { stream: true });
    console.log('- Type:', typeof result2);
    console.log('- Constructor:', result2?.constructor?.name);
    console.log('- Is Promise?', result2 instanceof Promise);
    console.log('- Has Symbol.asyncIterator?', typeof result2?.[Symbol.asyncIterator] === 'function');
    
    if (typeof result2?.[Symbol.asyncIterator] === 'function') {
      console.log('- It\'s an async iterable! Collecting events...');
      const events = [];
      for await (const event of result2) {
        events.push({ type: event.type, keys: Object.keys(event) });
      }
      console.log('- Collected events:', events);
    } else {
      console.log('- Not an async iterable, trying to await it');
      const resolved2 = await result2;
      console.log('- Resolved type:', typeof resolved2);
      console.log('- Resolved keys:', Object.keys(resolved2 || {}));
    }
  } catch (e) {
    console.error('- Error:', e.message);
  }
  
  console.log('\nTest 3: run() with no options');
  try {
    const result3 = run(testAgent, 'Hello');
    console.log('- Type:', typeof result3);
    console.log('- Constructor:', result3?.constructor?.name);
    console.log('- Is Promise?', result3 instanceof Promise);
  } catch (e) {
    console.error('- Error:', e.message);
  }
}

// Run the test
testRunReturnTypes().catch(console.error);