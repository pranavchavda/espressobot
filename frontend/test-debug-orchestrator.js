// Direct test of the multi-agent orchestrator
import { espressoBotOrchestrator } from './server/agents/espressobot-orchestrator.js';
import { run } from '@openai/agents';

async function testOrchestrator() {
  console.log('Testing orchestrator directly...\n');
  
  try {
    // Test if orchestrator is properly initialized
    console.log('Orchestrator name:', espressoBotOrchestrator.name);
    console.log('Orchestrator model:', espressoBotOrchestrator.model);
    console.log('Orchestrator handoffs:', espressoBotOrchestrator.handoffs?.map(a => a.name));
    
    console.log('\nRunning orchestrator with callbacks...');
    
    const result = await run(espressoBotOrchestrator, 'Find Breville espresso machines', {
      maxTurns: 5,
      onStepStart: (step) => {
        console.log('\n📍 Step Started:');
        console.log('  Type:', step.type);
        console.log('  Agent:', step.agent?.name);
        console.log('  Tool:', step.tool_name);
      },
      onStepFinish: (step) => {
        console.log('✅ Step Finished:');
        console.log('  Type:', step.type);
        console.log('  Has result:', !!step.result);
      }
    });
    
    console.log('\n\nFinal result:', result.finalOutput || result.state?._currentStep?.output);
    
  } catch (error) {
    console.error('Error:', error);
    console.error('Stack:', error.stack);
  }
}

testOrchestrator();