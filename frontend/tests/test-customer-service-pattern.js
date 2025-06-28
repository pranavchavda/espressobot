// Test using the exact pattern from the customer service example
import { Agent, Client } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create client (like in customer service example)
const client = new Client();

// Create a test agent
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant.',
  model: 'gpt-4o-mini'
});

async function testCustomerServicePattern() {
  console.log('Testing with Customer Service Pattern\n');
  
  try {
    // First, let's see if the client.agents.run pattern works
    console.log('Attempting client.agents.run pattern...');
    
    // Try the run directly (SDK might handle client internally)
    const { run } = await import('@openai/agents');
    
    const result = await run(testAgent, 'Hello, tell me about espresso machines', {
      maxTurns: 1,
      onStepStart: (step) => {
        console.log('\n✅ Step started!');
        console.log('  Type:', step.type);
        console.log('  Data:', JSON.stringify(step).substring(0, 200));
      },
      onStepFinish: (step) => {
        console.log('✅ Step finished!');
      },
      // Try the exact callback names from the Japanese docs
      onThinkingStart: () => {
        console.log('🤔 Thinking started!');
      },
      onThinkingFinish: (thinking) => {
        console.log('💭 Thinking finished!');
      },
      onToolCallStart: (toolCall) => {
        console.log('🔧 Tool call started!');
      },
      onToolCallFinish: (toolCall) => {
        console.log('🔨 Tool call finished!');
      },
      onMessageStart: () => {
        console.log('✍️ Message started!');
      },
      onMessageFinish: (message) => {
        console.log('📝 Message finished!');
      },
      onMessageDelta: (delta) => {
        process.stdout.write('.');
      }
    });
    
    console.log('\n\nResult received:', !!result);
    console.log('Final output:', result.finalOutput?.substring(0, 100) + '...');
    
  } catch (error) {
    console.error('Error:', error.message);
    
    // Try to understand the error
    if (error.message.includes('client.agents')) {
      console.log('\nThe client.agents.run pattern might not be the right approach.');
      console.log('The SDK might have a different API in this version.');
    }
  }
}

testCustomerServicePattern();