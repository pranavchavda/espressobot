import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a test agent with tools to see more events
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant.',
  model: 'gpt-4o-mini',
  tools: [{
    type: 'function',
    function: {
      name: 'get_weather',
      description: 'Get the weather for a location',
      parameters: {
        type: 'object',
        properties: {
          location: { type: 'string' }
        },
        required: ['location']
      }
    }
  }]
});

// Mock tool implementation
testAgent.tools[0].execute = async ({ location }) => {
  return `The weather in ${location} is sunny and 72°F`;
};

async function testTracingCallbacks() {
  console.log('Testing OpenAI Agents Tracing Callbacks\n');
  console.log('According to the docs, these callbacks should fire:\n');
  
  const callbacks = {
    // Thinking events
    onThinkingStart: (thinking) => {
      console.log('✅ onThinkingStart fired');
      console.log('   Thinking:', thinking);
    },
    onThinkingFinish: (thinking) => {
      console.log('✅ onThinkingFinish fired');
      console.log('   Result:', thinking);
    },
    
    // Tool events
    onToolCallStart: (toolCall) => {
      console.log('✅ onToolCallStart fired');
      console.log('   Tool:', toolCall.function?.name);
      console.log('   Args:', toolCall.function?.arguments);
    },
    onToolCallFinish: (toolCall) => {
      console.log('✅ onToolCallFinish fired');
      console.log('   Tool:', toolCall.function?.name);
      console.log('   Result:', toolCall.result);
    },
    
    // Message events
    onMessageStart: (message) => {
      console.log('✅ onMessageStart fired');
      console.log('   Message:', message);
    },
    onMessageFinish: (message) => {
      console.log('✅ onMessageFinish fired');
      console.log('   Content:', message.content);
    },
    onMessageDelta: (delta) => {
      console.log('✅ onMessageDelta fired');
      console.log('   Delta:', delta);
    },
    
    // Step events (these might work)
    onStepStart: (step) => {
      console.log('✅ onStepStart fired');
      console.log('   Step:', step);
    },
    onStepFinish: (step) => {
      console.log('✅ onStepFinish fired');
      console.log('   Step:', step);
    }
  };
  
  try {
    console.log('\nTesting with a tool-calling prompt...\n');
    
    const result = await run(testAgent, "What's the weather in San Francisco?", {
      maxTurns: 2,
      ...callbacks,
      trace: {
        workflow_name: 'Test Workflow'
      }
    });
    
    console.log('\n\nFinal result:', result.finalOutput || result);
    
    // Check which callbacks fired
    console.log('\n\nSummary:');
    console.log('If callbacks fired above, tracing is working in the SDK.');
    console.log('If not, we need a different approach for status updates.');
    
  } catch (error) {
    console.error('Error:', error);
  }
}

testTracingCallbacks();