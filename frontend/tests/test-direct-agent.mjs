import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('Testing agent callbacks directly...\n');

// Create a simple agent
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant. When asked a question, provide a detailed response.',
  model: 'gpt-4o-mini'
});

console.log('Running agent with callbacks...');
let messageCount = 0;

const result = await run(testAgent, 'What is 2+2? Please explain step by step.', {
  onMessage: (message) => {
    messageCount++;
    console.log(`\n=== onMessage #${messageCount} ===`);
    console.log('Type:', typeof message);
    console.log('Keys:', Object.keys(message || {}));
    console.log('Content type:', typeof message?.content);
    console.log('Content:', message?.content);
    console.log('Tool calls:', message?.tool_calls);
  },
  onStepStart: (step) => {
    console.log('\n=== onStepStart ===');
    console.log('Step type:', step.type);
  },
  onStepFinish: (step) => {
    console.log('\n=== onStepFinish ===');
    console.log('Step type:', step.type);
  }
});

console.log('\n=== Final Result ===');
console.log('Result type:', typeof result);
console.log('Result keys:', Object.keys(result || {}));
console.log('finalOutput:', result.finalOutput);

console.log('\nDone!');