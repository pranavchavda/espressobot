import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple test agent
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant. When asked, provide a simple response.',
  model: 'gpt-4o-mini'
});

async function testCallbacks() {
  console.log('Testing agent callbacks...\n');
  
  const callbacks = {
    onThinkingStart: () => console.log('✅ onThinkingStart fired'),
    onThinkingFinish: (t) => console.log('✅ onThinkingFinish fired', t),
    onToolCallStart: (t) => console.log('✅ onToolCallStart fired', t),
    onToolCallFinish: (t) => console.log('✅ onToolCallFinish fired', t),
    onMessageStart: () => console.log('✅ onMessageStart fired'),
    onMessageFinish: (m) => console.log('✅ onMessageFinish fired', m),
    onMessageDelta: (d) => console.log('✅ onMessageDelta fired', d),
    onStepStart: (s) => console.log('✅ onStepStart fired', s),
    onStepFinish: (s) => console.log('✅ onStepFinish fired', s),
    onMessage: (m) => console.log('✅ onMessage fired', m)
  };
  
  try {
    const result = await run(testAgent, 'Say hello', {
      maxTurns: 1,
      ...callbacks
    });
    
    console.log('\nFinal result:', result.finalOutput);
    console.log('\nCallbacks summary - check which ones fired above');
  } catch (error) {
    console.error('Error:', error);
  }
}

testCallbacks();