#!/usr/bin/env node

// Test the multi-agent orchestrator flow directly

import { run } from '@openai/agents';
import { espressoBotOrchestrator } from './server/agents/espressobot-orchestrator.js';

async function testOrchestratorFlow() {
  console.log('🧪 Testing Multi-Agent Orchestrator Flow\n');
  
  const testInput = `[Conversation ID: test_123]
Please use the task planner to create a plan for searching Eureka products.`;
  
  console.log('Input:', testInput);
  console.log('\n--- Running Agent ---\n');
  
  let stepCount = 0;
  const context = { tasks: [], memories: [] };
  
  try {
    const result = await run(espressoBotOrchestrator, testInput, {
      maxTurns: 10,
      context,
      onStepStart: (step) => {
        stepCount++;
        console.log(`\n[Step ${stepCount} START]`);
        console.log('Type:', step.type);
        console.log('Agent:', step.agent?.name);
        console.log('Tool:', step.tool_name);
        
        if (step.type === 'tool_call' && step.tool_name === 'create_task_plan') {
          console.log('✅ Task Planner is creating a plan!');
        }
      },
      onStepFinish: (step) => {
        console.log(`\n[Step ${stepCount} FINISH]`);
        if (step.result) {
          console.log('Result:', JSON.stringify(step.result, null, 2));
        }
      }
    });
    
    console.log('\n--- Final Result ---');
    console.log(result);
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

// Check if we have the required environment variable
if (!process.env.OPENAI_API_KEY) {
  console.error('❌ OPENAI_API_KEY not set');
  process.exit(1);
}

testOrchestratorFlow();