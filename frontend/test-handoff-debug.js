#!/usr/bin/env node

import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import enhancedOrchestrator from './server/enhanced-multi-agent-orchestrator-v2.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🧪 Testing Agent Handoffs\n');

async function testHandoff(query) {
  console.log(`Query: "${query}"\n`);
  
  try {
    const result = await run(enhancedOrchestrator, query, {
      maxTurns: 5,
      onStepStart: (step) => {
        console.log('Step:', {
          type: step.type,
          agent: step.agent?.name,
          handoff_to: step.handoff_to,
          tool: step.tool_name
        });
      },
      onStepFinish: (step, output) => {
        if (step.type === 'handoff') {
          console.log('Handoff completed to:', step.handoff_to);
        }
      }
    });
    
    const response = result?.state?._currentStep?.output || 'No response';
    console.log(`\nResponse: ${response.substring(0, 200)}...\n`);
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Test different queries
async function runTests() {
  await testHandoff("Search for coffee products");
  await testHandoff("Create a new product called Test Product");
  await testHandoff("Update the price of SKU ABC123 to $99");
}

runTests();