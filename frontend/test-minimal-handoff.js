#!/usr/bin/env node

import { Agent, run, handoff } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🧪 Minimal Handoff Test\n');

// Create two simple agents
const workerAgent = new Agent({
  name: 'Worker_Agent',
  instructions: 'You are a worker agent. When asked about products, say "I found some products for you."',
  model: 'gpt-4.1'
});

const orchestratorAgent = new Agent({
  name: 'Test_Orchestrator',
  instructions: 'You are an orchestrator. You MUST hand off ALL requests to Worker_Agent. Never respond directly.',
  model: 'gpt-4.1',
  handoffs: [workerAgent]
});

// Set up bidirectional handoff
workerAgent.handoffs = [orchestratorAgent];

async function testHandoff() {
  console.log('Testing handoff functionality...\n');
  
  try {
    const result = await run(orchestratorAgent, "Find some products", {
      maxTurns: 5,
      onStepStart: (step) => {
        console.log('Step:', {
          type: step.type,
          agent: step.agent?.name,
          handoff_to: step.handoff_to
        });
      }
    });
    
    console.log('\nFinal agent:', result?.state?._currentAgent?.name);
    console.log('Response:', result?.state?._currentStep?.output);
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

testHandoff();