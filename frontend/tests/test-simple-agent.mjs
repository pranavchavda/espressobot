import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('Testing simple agent with streaming...\n');

// Create a simple agent
const simpleAgent = new Agent({
  name: 'Simple_Agent',
  instructions: 'You are a helpful assistant. Answer questions directly and concisely.',
  model: 'gpt-4o-mini'
});

// Test without streaming
console.log('=== Test 1: Without streaming ===');
const result1 = await run(simpleAgent, 'What is 2+2?');
console.log('Result type:', typeof result1);
console.log('Result keys:', Object.keys(result1 || {}));
console.log('finalOutput:', result1.finalOutput);

// Test with streaming
console.log('\n=== Test 2: With streaming ===');
const result2 = await run(simpleAgent, 'What is 3+3?', {
  stream: true,
  onMessage: (message) => {
    console.log('onMessage fired!');
    console.log('Message:', message);
  }
});
console.log('Result type:', typeof result2);
console.log('Result keys:', Object.keys(result2 || {}));
console.log('finalOutput:', result2.finalOutput);

console.log('\nDone!');