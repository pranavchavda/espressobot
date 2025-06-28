import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple test agent
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant. When asked about products, think step by step.',
  model: 'gpt-4o-mini'
});

async function testTracingSimple() {
  console.log('Testing OpenAI Agents Tracing (Simple)\n');
  
  let eventsFired = [];
  
  const callbacks = {
    // According to docs, these should work in 0.0.10+
    onThinkingStart: () => {
      console.log('🤔 onThinkingStart fired!');
      eventsFired.push('onThinkingStart');
    },
    onThinkingFinish: (thinking) => {
      console.log('✅ onThinkingFinish fired!');
      console.log('   Content:', thinking?.content?.substring(0, 100) + '...');
      eventsFired.push('onThinkingFinish');
    },
    onMessageStart: () => {
      console.log('✍️ onMessageStart fired!');
      eventsFired.push('onMessageStart');
    },
    onMessageFinish: (message) => {
      console.log('📝 onMessageFinish fired!');
      console.log('   Content:', message?.content?.substring(0, 100) + '...');
      eventsFired.push('onMessageFinish');
    },
    onMessageDelta: (delta) => {
      process.stdout.write('.');
      eventsFired.push('delta');
    },
    onStepStart: (step) => {
      console.log('\n📍 onStepStart fired!');
      console.log('   Type:', step.type);
      eventsFired.push('onStepStart');
    },
    onStepFinish: (step) => {
      console.log('✅ onStepFinish fired!');
      console.log('   Type:', step.type);
      eventsFired.push('onStepFinish');
    }
  };
  
  try {
    console.log('Running agent with tracing callbacks...\n');
    
    const result = await run(testAgent, 'What are Breville espresso machines?', {
      maxTurns: 1,
      ...callbacks,
      trace: {
        workflow_name: 'Test Tracing',
        metadata: { test: true }
      }
    });
    
    console.log('\n\nFinal result:', result.finalOutput?.substring(0, 200) + '...');
    
    console.log('\n\n📊 Events Summary:');
    console.log('Events fired:', eventsFired.length > 0 ? eventsFired : 'NONE');
    console.log('\nDelta count:', eventsFired.filter(e => e === 'delta').length);
    
    if (eventsFired.length === 0) {
      console.log('\n⚠️  No events fired. Possible reasons:');
      console.log('1. SDK version 0.0.9 might not support these callbacks');
      console.log('2. Callbacks might need to be enabled differently');
      console.log('3. Only certain agent types support tracing');
    } else {
      console.log('\n✅ Tracing is working! We can use these for status updates.');
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

testTracingSimple();