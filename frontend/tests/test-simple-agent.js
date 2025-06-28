import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple test agent
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant. Just say hello.',
  model: 'gpt-4o-mini'
});

async function testSimpleAgent() {
  console.log('Testing if agents work at all...\n');
  
  try {
    console.log('Running agent with onStepStart/Finish callbacks...');
    
    const result = await run(testAgent, 'Say hello', {
      maxTurns: 1,
      onStepStart: (step) => {
        console.log('✅ onStepStart fired!', step);
      },
      onStepFinish: (step) => {
        console.log('✅ onStepFinish fired!', step);
      }
    });
    
    console.log('\nResult:', result.finalOutput);
    console.log('\nCallbacks work! The issue might be with the multi-agent setup.');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error('\nThis suggests an issue with the OpenAI API key or network.');
  }
}

testSimpleAgent();